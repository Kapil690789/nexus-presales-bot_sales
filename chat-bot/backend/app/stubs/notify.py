import json
import logging
from typing import Any

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import EventRow

logger = logging.getLogger("presales.stubs")


def emit(db: Session, session_id: str, kind: str, payload: dict[str, Any]) -> EventRow:
    row = EventRow(session_id=session_id, kind=kind, payload_json=json.dumps(payload, default=str))
    db.add(row)
    logger.info("stub %s session=%s", kind, session_id)
    return row


def has_event(db: Session, session_id: str, kind: str) -> bool:
    return db.scalar(select(EventRow.id).where(EventRow.session_id == session_id, EventRow.kind == kind).limit(1)) is not None


def notify_handoff(db: Session, session_id: str, payload: dict[str, Any]) -> None:
    if has_event(db, session_id, "crm"):
        return
    status = "queued_stub"
    email = payload.get("email") or ""
    company = payload.get("company") or ""
    score = payload.get("score")
    crm_id = payload.get("crm_id") or ""
    summary = payload.get("summary") or ""
    admin_url = payload.get("admin_url") or f"/admin/sessions/{session_id}"
    emit(
        db,
        session_id,
        "crm",
        {
            "provider": "stub",
            "status": status,
            "crm_id": crm_id,
            "email": email,
            "company": company,
            "score": score,
            "band": payload.get("band"),
            "page": payload.get("page"),
            "preview": f"CRM {crm_id} · {company or email}",
        },
    )
    emit(
        db,
        session_id,
        "slack",
        {
            "channel": "#inbound",
            "status": status,
            "text": f"New qualified lead {email} ({company}) score {score}. {admin_url}",
            "preview": f"#inbound · {email} score {score}",
        },
    )
    emit(
        db,
        session_id,
        "email",
        {
            "channel": "sales",
            "status": status,
            "to": payload.get("sales_to") or "hello@devconsult.example",
            "subject": payload.get("subject") or f"New qualified lead — {company or email}",
            "body": summary,
            "preview": f"Sales email · {email}",
        },
    )


def notify_booking(db: Session, session_id: str, payload: dict[str, Any]) -> None:
    if has_event(db, session_id, "calendar"):
        return
    emit(
        db,
        session_id,
        "calendar",
        {
            "provider": "stub",
            "status": "queued_stub",
            "window": payload.get("window"),
            "slot_iso": payload.get("slot_iso"),
            "label": payload.get("label"),
            "meet_url": payload.get("meet_url"),
            "email": payload.get("email"),
            "preview": f"Booked {payload.get('label') or payload.get('window')}",
        },
    )


def notify_follow_up(db: Session, session_id: str, payload: dict[str, Any]) -> None:
    if has_event(db, session_id, "visitor_follow_up"):
        return
    emit(
        db,
        session_id,
        "visitor_follow_up",
        {
            "status": "queued_stub",
            "to": payload.get("email") or payload.get("to"),
            "subject": payload.get("subject"),
            "body": payload.get("body"),
            "preview": payload.get("preview") or f"Recap queued to {payload.get('email')}",
        },
    )
