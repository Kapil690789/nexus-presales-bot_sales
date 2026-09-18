import json
import logging
from typing import Any

import httpx
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import EventRow

logger = logging.getLogger("presales.stubs")


def emit(db: Session, session_id: str, kind: str, payload: dict[str, Any]) -> EventRow:
    row = EventRow(session_id=session_id, kind=kind, payload_json=json.dumps(payload, default=str))
    db.add(row)
    db.flush()
    logger.info("stub %s session=%s", kind, session_id)
    return row


def has_event(db: Session, session_id: str, kind: str) -> bool:
    return db.scalar(select(EventRow.id).where(EventRow.session_id == session_id, EventRow.kind == kind).limit(1)) is not None


def admin_session_url(session_id: str) -> str:
    from backend.app.core.settings import get_settings

    path = f"/admin/sessions/{session_id}"
    base = (get_settings().public_base_url or "").strip().rstrip("/")
    return f"{base}{path}" if base else path


def booking_slack_text(payload: dict[str, Any], session_id: str) -> str:
    lines = ["New consultation booked"]
    label = payload.get("label") or payload.get("window") or ""
    if label:
        lines.append(f"When: {label}")
    email = payload.get("email") or ""
    if email:
        lines.append(f"Email: {email}")
    company = payload.get("company") or ""
    if company:
        lines.append(f"Company: {company}")
    meet = payload.get("meet_url") or ""
    if meet:
        lines.append(f"Meet: {meet}")
    calendar = payload.get("html_link") or ""
    if calendar:
        lines.append(f"Calendar: {calendar}")
    lines.append(f"Session: {admin_session_url(session_id)}")
    return "\n".join(lines)


def post_slack_webhook(text: str) -> str:
    """Post to Slack Incoming Webhook. Never raises — booking must still succeed."""
    from backend.app.config_loader.loader import get_config
    from backend.app.core.settings import get_settings

    slack = get_config().handoff.notify.slack or {}
    if not slack.get("enabled"):
        return "queued_stub"
    url = (get_settings().slack_webhook_url or "").strip()
    if not url:
        return "queued_stub"
    try:
        response = httpx.post(url, json={"text": text}, timeout=8.0)
        response.raise_for_status()
        return "sent"
    except Exception:
        logger.exception("slack webhook failed")
        return "failed"


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
    live = payload.get("status") == "created" or bool(payload.get("event_id"))
    status = payload.get("status") or ("created" if live else "queued_stub")
    emit(
        db,
        session_id,
        "calendar",
        {
            "provider": "google" if live else "stub",
            "status": status,
            "window": payload.get("window"),
            "slot_iso": payload.get("slot_iso"),
            "label": payload.get("label"),
            "meet_url": payload.get("meet_url"),
            "html_link": payload.get("html_link"),
            "event_id": payload.get("event_id"),
            "email": payload.get("email"),
            "preview": f"Booked {payload.get('label') or payload.get('window')}",
        },
    )
    from backend.app.config_loader.loader import get_config

    channel = str((get_config().handoff.notify.slack or {}).get("channel") or "#inbound")
    text = booking_slack_text(payload, session_id)
    slack_status = post_slack_webhook(text)
    emit(
        db,
        session_id,
        "slack",
        {
            "channel": channel,
            "status": slack_status,
            "text": text,
            "preview": f"{channel} · Booked {payload.get('label') or payload.get('window') or 'call'}",
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
