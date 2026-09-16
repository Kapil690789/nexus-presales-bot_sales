from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import PlainTextResponse, StreamingResponse
from pydantic import BaseModel
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.orchestrator import run_turn
from backend.app.config_loader.loader import get_config
from backend.app.core.security import origin_allowed, rate_limit
from backend.app.core.sse import encode, stream_text
from backend.app.engines.calendar import ics_for
from backend.app.engines.enrichment import crm_id_for, enrich_email
from backend.app.engines.followup import render_followup
from backend.app.models.db import get_db
from backend.app.models.entities import MessageRow
from backend.app.services.sessions import add_message, brief_of, create_session, get_session, loads, persist_turn
from backend.app.stubs.notify import notify_booking, notify_follow_up, notify_handoff

router = APIRouter()


class SessionIn(BaseModel):
    page_url: str = ""
    page_title: str = ""
    path: str = "/"


class ChipIn(BaseModel):
    label: str | None = None
    field: str
    value: Any = None
    also: dict[str, Any] | None = None


class MessageIn(BaseModel):
    content: str = ""
    chip: ChipIn | None = None
    nda_accepted: bool = False


class BookingIn(BaseModel):
    window: str = "flex"
    slot: str = ""
    note: str = ""


def _payload(turn) -> dict:
    return {
        "message": turn.message,
        "stage": turn.stage,
        "chips": turn.chips,
        "cards": turn.cards,
        "actions": turn.actions,
        "nda_accepted": turn.nda_accepted,
        "can_book": bool(turn.qualification and turn.qualification.get("can_book")),
        "score": (turn.qualification or {}).get("score"),
        "band": (turn.qualification or {}).get("band"),
        "handoff_summary": turn.handoff_summary,
        "booking": turn.booking,
    }


def _emit_integrations(db: Session, row, turn) -> None:
    config = get_config()
    email = (turn.contact or {}).get("email") or ""
    profile = enrich_email(email, config.enrichment) if email else {}
    if turn.handoff_summary:
        notify_handoff(
            db,
            row.id,
            {
                "email": email,
                "score": (turn.qualification or {}).get("score"),
                "band": (turn.qualification or {}).get("band"),
                "summary": turn.handoff_summary,
                "company": profile.get("company") if profile else "",
                "crm_id": crm_id_for(row.id),
                "page": row.path,
                "admin_url": f"/admin/sessions/{row.id}",
                "sales_to": (config.handoff.notify.email.get("to") or ["hello@devconsult.example"])[0],
                "subject": (config.handoff.notify.email.get("subject") or "New qualified lead").replace(
                    "{{company_or_email}}", profile.get("company") or email
                ),
            },
        )
        pack = getattr(turn, "follow_up", None) or render_followup(
            email=email,
            intro=config.handoff.follow_up.get("intro") or "",
            estimate=turn.estimate,
            portfolio=turn.portfolio,
            booking=turn.booking,
            agency=config.agency.name,
        )
        pack["subject"] = config.handoff.follow_up.get("subject") or "Your DevConsult discovery notes"
        pack["email"] = email
        notify_follow_up(db, row.id, pack)
    if turn.booking and turn.booking.get("slot_iso"):
        notify_booking(db, row.id, {**turn.booking, "email": email})


def _run(db: Session, row, user_text: str, chip, nda: bool, rfp_text: str | None = None, booking=None):
    config = get_config()
    _, opening, extras = config.page_for(row.path)
    turn = run_turn(
        config=config,
        brief=brief_of(row),
        contact=loads(row.contact_json, {}),
        nda_accepted=nda,
        booking=booking if booking is not None else loads(row.booking_json, None),
        user_text=user_text,
        chip=chip,
        page_opening=opening,
        extra_questions=extras,
        rfp_text=rfp_text,
        existing_estimate=loads(row.estimate_json, None),
        existing_qualification=loads(row.qualification_json, None),
        existing_architecture=loads(row.architecture_json, None),
        existing_mvp=loads(row.mvp_json, None),
        existing_portfolio=loads(row.portfolio_json, None),
        session_id=row.id,
    )
    persist_turn(db, row, turn)
    add_message(db, row.id, "assistant", turn.message, _payload(turn))
    _emit_integrations(db, row, turn)
    return turn


@router.post("/api/v1/sessions")
def create(body: SessionIn, request: Request, db: Session = Depends(get_db)) -> dict:
    rate_limit(request)
    origin_allowed(request)
    config = get_config()
    service, opening, extras = config.page_for(body.path)
    brief = ProjectBrief(service=service)
    row = create_session(db, body.page_url, body.page_title, body.path, brief)
    turn = run_turn(
        config=config,
        brief=brief,
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="",
        chip=None,
        page_opening=opening,
        extra_questions=extras,
        is_opening=True,
        session_id=row.id,
    )
    persist_turn(db, row, turn)
    add_message(db, row.id, "assistant", turn.message, _payload(turn))
    return {"session_id": row.id, **_payload(turn)}


@router.get("/api/v1/sessions/{session_id}")
def read_session(session_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")
    messages = db.scalars(select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.created_at.asc())).all()
    last_payload = loads(messages[-1].payload_json, {}) if messages else {}
    return {
        "session_id": row.id,
        "stage": row.stage,
        "nda_accepted": row.nda_accepted,
        "booking": loads(row.booking_json, None),
        "can_book": bool((loads(row.qualification_json, {}) or {}).get("can_book")),
        "messages": [{"role": item.role, "content": item.content} for item in messages],
        "chips": last_payload.get("chips") or [],
        "cards": last_payload.get("cards") or [],
    }


@router.post("/api/v1/sessions/{session_id}/messages")
def message(session_id: str, body: MessageIn, request: Request, db: Session = Depends(get_db)) -> StreamingResponse:
    rate_limit(request)
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")
    chip = body.chip.model_dump() if body.chip else None
    if body.nda_accepted and not chip:
        chip = {"field": "nda", "value": True}
    add_message(db, row.id, "user", body.content or (chip or {}).get("label") or "", chip)
    turn = _run(db, row, body.content, chip, row.nda_accepted or body.nda_accepted)
    payload = _payload(turn)

    def events():
        yield from stream_text(turn.message)
        yield encode("cards", {"cards": payload["cards"]})
        yield encode("chips", {"chips": payload["chips"]})
        yield encode("meta", {k: payload[k] for k in ("stage", "actions", "nda_accepted", "can_book", "score", "band")})
        yield encode("done", {"ok": True})

    return StreamingResponse(events(), media_type="text/event-stream")


@router.post("/api/v1/sessions/{session_id}/nda")
def accept_nda(session_id: str, request: Request, db: Session = Depends(get_db)) -> dict:
    rate_limit(request)
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")
    turn = _run(db, row, "I accept the confidentiality notice.", {"field": "nda", "value": True}, True)
    return _payload(turn)


@router.post("/api/v1/sessions/{session_id}/booking")
def book(session_id: str, body: BookingIn, request: Request, db: Session = Depends(get_db)) -> dict:
    rate_limit(request)
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")
    config = get_config()
    if config.agency.nda.required_before_handoff and not row.nda_accepted:
        raise HTTPException(status_code=400, detail="Accept the confidentiality notice before booking.")
    turn = _run(
        db,
        row,
        f"Please book {body.slot or body.window}. {body.note}".strip(),
        {"field": "booking_slot", "value": body.slot, "also": {"window": body.window}},
        row.nda_accepted,
    )
    return _payload(turn)


@router.get("/api/v1/sessions/{session_id}/calendar.ics")
def calendar_ics(session_id: str, request: Request, db: Session = Depends(get_db)) -> PlainTextResponse:
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")
    booking = loads(row.booking_json, None) or {}
    if not booking.get("slot_iso"):
        raise HTTPException(status_code=404, detail="No booking on this session")
    return PlainTextResponse(
        ics_for(booking),
        media_type="text/calendar",
        headers={"Content-Disposition": 'attachment; filename="devconsult-consult.ics"'},
    )
