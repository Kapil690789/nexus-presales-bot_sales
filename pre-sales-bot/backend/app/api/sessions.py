import json
import logging
import time
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request, Response
from pydantic import BaseModel, Field

log = logging.getLogger(__name__)
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.router import run_turn
from backend.app.core.guard import REFUSAL_MESSAGE, looks_like_jailbreak
from backend.app.core.security import bind_llm_actor, client_ip, rate_limit_messages, reset_llm_actor
from backend.app.learning.pairs import save_thumb
from backend.app.models.db import get_db
from backend.app.models.entities import MessageRow, SessionRow, TenantRow, _now
from backend.app.screening.slots import DISCOVERY_PROMPTS, chips_for_field
from backend.app.tenants.loader import TenantNotFound, ensure_tenant_row, load_tenant
from backend.app.tenants.schema import TenantConfig

router = APIRouter()
MAX_MESSAGE_CHARS = 1000


class SessionIn(BaseModel):
    tenant: str
    page_url: str = ""
    page_title: str = ""
    path: str = "/"


class ChipIn(BaseModel):
    label: str | None = None
    field: str
    value: Any = None


class MessageIn(BaseModel):
    content: str = ""
    chip: ChipIn | None = None


class FeedbackIn(BaseModel):
    message_id: str
    rating: str = Field(pattern="^(up|down)$")


class NdaIn(BaseModel):
    version: str


def _pair(db: Session, slug: str):
    try:
        config = load_tenant(slug)
        row = ensure_tenant_row(db, slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    return row, config


def _session(db: Session, session_id: str) -> SessionRow:
    row = db.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    return row


def _history(db: Session, session_id: str) -> list[dict]:
    rows = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.created_at.asc())
    ).all()
    return [{"role": row.role, "content": row.content} for row in rows]


def _add(db: Session, session_id: str, role: str, content: str, payload: dict | None = None) -> MessageRow:
    row = MessageRow(
        session_id=session_id,
        role=role,
        content=content,
        payload_json=json.dumps(payload or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _public(session: SessionRow, message: MessageRow, result: dict, config: TenantConfig) -> dict:
    try:
        brief_dict = json.loads(session.brief_json or "{}")
    except Exception:
        brief_dict = {}
    return {
        "session_id": session.id,
        "message_id": message.id,
        "message": result["message"],
        "stage": result["stage"],
        "chips": result["chips"],
        "cards": result["cards"],
        "route": result["route"],
        "brief": brief_dict,
        "nda_accepted": session.nda_accepted,
        "nda_version": config.brand.nda_version,
        "score": (result.get("qualification") or {}).get("score"),
        "band": (result.get("qualification") or {}).get("band"),
        "booking": result.get("booking"),
    }


@router.post("/api/v1/sessions")
def create_session(body: SessionIn, db: Session = Depends(get_db)) -> dict:
    import re as _re
    slug = body.tenant.strip()[:80]
    if not _re.match(r"^[a-z0-9_-]+$", slug):
        raise HTTPException(status_code=400, detail="Invalid tenant identifier")
    tenant, config = _pair(db, slug)
    session = SessionRow(
        tenant_id=tenant.id,
        page_url=body.page_url[:500],
        page_title=body.page_title[:300],
        path="/",
        stage="discovery",
        expires_at=_now() + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    db.refresh(session)

    brand = config.brand
    advisor_name = brand.advisor_name
    advisor_title = brand.advisor_title
    disclosure = f"Hi, I'm {advisor_name}, {brand.name}'s {advisor_title}."

    clean_path = (body.path or "/").split("?")[0].split("#")[0]
    matched_hint = None
    for hint in brand.page_hints:
        if clean_path.startswith(hint.match):
            matched_hint = hint
            break

    if matched_hint and matched_hint.question:
        question = matched_hint.question
    elif brand.opening_variants:
        import hashlib
        idx = int(hashlib.md5(session.id.encode()).hexdigest(), 16) % len(brand.opening_variants)
        question = brand.opening_variants[idx]
    else:
        question = "Tell me what you'd like to build in a sentence, or pick a starting point."

    text = f"{disclosure} {question}".strip()

    human_chip = {"label": brand.human_label, "field": "booking_window", "value": "this_week"}

    if matched_hint and matched_hint.service:
        from backend.app.agents.brief import ProjectBrief
        brief = ProjectBrief(service=matched_hint.service)
        session.brief_json = brief.model_dump_json()
        db.add(session)
        chips = [human_chip]
    else:
        starter_chips = [{"label": s.label, "field": "ask", "value": s.text} for s in brand.starters]
        chips = starter_chips + [human_chip]

    message = _add(
        db,
        session.id,
        "assistant",
        text,
        {"route": "discovery", "chips": chips, "chunk_ids": []},
    )
    db.commit()
    return _public(
        session,
        message,
        {
            "message": text,
            "stage": "discovery",
            "chips": chips,
            "cards": [],
            "route": "discovery",
            "qualification": None,
            "booking": None,
        },
        config,
    )


def _unsafe_message(text: str, chip: ChipIn | None) -> bool:
    parts = [text]
    if chip is not None:
        parts.append(chip.label or "")
        if isinstance(chip.value, (dict, list)):
            parts.append(json.dumps(chip.value))
        elif chip.value is not None:
            parts.append(str(chip.value))
    return any(looks_like_jailbreak(part) for part in parts)


def _is_expired(expires_at: datetime | None) -> bool:
    if not expires_at:
        return False
    if expires_at.tzinfo is not None:
        return expires_at < datetime.now(timezone.utc)
    return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/api/v1/sessions/{session_id}/messages")
def post_message(
    session_id: str,
    body: MessageIn,
    request: Request,
    response: Response = None,
    db: Session = Depends(get_db),
) -> dict:
    t_turn_start = time.perf_counter()
    db_writes_ms = 0.0

    session = _session(db, session_id)
    if _is_expired(session.expires_at):
        raise HTTPException(status_code=410, detail="Session has expired. Please refresh to start a new chat.")
    tenant_row = db.get(TenantRow, session.tenant_id)
    if tenant_row is None:
        raise HTTPException(status_code=404, detail="Unknown client")
    try:
        config = load_tenant(tenant_row.slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    text = (body.content or "").strip()
    if body.chip and not text:
        text = (body.chip.label or "").strip()
    if not text and body.chip is None:
        raise HTTPException(status_code=400, detail="Message is empty")
    if len(text) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=400, detail="Message is too long")
    rate_limit_messages(request)
    if _unsafe_message(text, body.chip):
        t0_db = time.perf_counter()
        _add(db, session.id, "user", text, {"chip": body.chip.model_dump() if body.chip else None})
        assistant = _add(
            db,
            session.id,
            "assistant",
            REFUSAL_MESSAGE,
            {"route": "refused", "chips": [], "chunk_ids": []},
        )
        db_writes_ms += (time.perf_counter() - t0_db) * 1000.0
        total_turn_ms = (time.perf_counter() - t_turn_start) * 1000.0
        log.info(
            "Turn timing: route=refused stage=%s extractor=0.0ms query_embedding=0.0ms retrieval_db=0.0ms answer_llm=0.0ms db_writes=%.1fms total=%.1fms",
            session.stage or "discovery",
            db_writes_ms,
            total_turn_ms,
        )
        if response is not None:
            response.headers["Server-Timing"] = (
                f"extractor;dur=0.0, query_embedding;dur=0.0, retrieval_db;dur=0.0, answer_llm;dur=0.0, db_writes;dur={db_writes_ms:.1f}, total;dur={total_turn_ms:.1f}"
            )
        return _public(
            session,
            assistant,
            {
                "message": REFUSAL_MESSAGE,
                "stage": session.stage or "discovery",
                "chips": [],
                "cards": [],
                "route": "refused",
                "qualification": None,
                "booking": None,
            },
            config,
        )

    history = _history(db, session.id)
    t0_db = time.perf_counter()
    _add(db, session.id, "user", text, {"chip": body.chip.model_dump() if body.chip else None})
    db_writes_ms += (time.perf_counter() - t0_db) * 1000.0

    token = bind_llm_actor(session.id, client_ip(request))
    try:
        result = run_turn(
            db,
            tenant_row,
            config,
            session,
            history,
            text,
            body.chip.model_dump() if body.chip else None,
        )
    finally:
        reset_llm_actor(token)

    t0_db = time.perf_counter()
    assistant = _add(
        db,
        session.id,
        "assistant",
        result["message"],
        {
            "route": result["route"],
            "chunk_ids": result["chunk_ids"],
            "query": result["query"],
            "score": result["score"],
            "chips": result["chips"],
            "cards": result["cards"],
        },
    )
    db.add(session)
    db.commit()
    db_writes_ms += (time.perf_counter() - t0_db) * 1000.0

    turn_timings = result.get("_timings") or {}
    extractor_ms = float(turn_timings.get("extractor", 0.0))
    query_emb_ms = float(turn_timings.get("query_embedding", 0.0))
    retrieval_db_ms = float(turn_timings.get("retrieval_db", 0.0))
    answer_llm_ms = float(turn_timings.get("answer_llm", 0.0))
    total_db_writes_ms = db_writes_ms + float(turn_timings.get("db_writes", 0.0))
    total_turn_ms = (time.perf_counter() - t_turn_start) * 1000.0

    route = result.get("route", "discovery")
    stage = result.get("stage", "discovery")
    log.info(
        "Turn timing: route=%s stage=%s extractor=%.1fms query_embedding=%.1fms retrieval_db=%.1fms answer_llm=%.1fms db_writes=%.1fms total=%.1fms",
        route,
        stage,
        extractor_ms,
        query_emb_ms,
        retrieval_db_ms,
        answer_llm_ms,
        total_db_writes_ms,
        total_turn_ms,
    )

    if response is not None:
        response.headers["Server-Timing"] = (
            f"extractor;dur={extractor_ms:.1f}, "
            f"query_embedding;dur={query_emb_ms:.1f}, "
            f"retrieval_db;dur={retrieval_db_ms:.1f}, "
            f"answer_llm;dur={answer_llm_ms:.1f}, "
            f"db_writes;dur={total_db_writes_ms:.1f}, "
            f"total;dur={total_turn_ms:.1f}"
        )

    return _public(session, assistant, result, config)


@router.post("/api/v1/sessions/{session_id}/feedback")
def post_feedback(session_id: str, body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    session = _session(db, session_id)
    message = db.get(MessageRow, body.message_id)
    if message is None or message.session_id != session.id or message.role != "assistant":
        raise HTTPException(status_code=404, detail="Unknown message")
    rows = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session.id).order_by(MessageRow.created_at.asc())
    ).all()
    previous = ""
    for row in rows:
        if row.id == message.id:
            break
        if row.role == "user":
            previous = row.content
    saved = save_thumb(db, session.tenant_id, message, previous, body.rating)
    return {"saved": saved, "rating": body.rating}


@router.post("/api/v1/sessions/{session_id}/nda")
def accept_nda(
    session_id: str,
    body: NdaIn,
    request: Request,
    response: Response = None,
    db: Session = Depends(get_db),
) -> dict:
    return post_message(
        session_id,
        MessageIn(content="I accept the confidentiality notice", chip=ChipIn(field="nda", value=body.version, label="Accept")),
        request,
        response,
        db,
    )
