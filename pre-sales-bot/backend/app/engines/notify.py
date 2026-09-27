from __future__ import annotations

import json

from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.models.entities import EventRow, TenantRow


def record_event(db: Session, session_id: str, tenant_id: str, kind: str, payload: dict) -> None:
    db.add(
        EventRow(
            session_id=session_id,
            tenant_id=tenant_id,
            kind=kind,
            payload_json=json.dumps(payload),
        )
    )


def slack_webhook(tenant: TenantRow) -> str:
    return (tenant.slack_webhook_url or get_settings().slack_webhook_url).strip()


def notify_slack(db: Session, session_id: str, tenant: TenantRow, text: str) -> None:
    webhook = slack_webhook(tenant)
    payload = {"text": text}
    if not webhook:
        record_event(db, session_id, tenant.id, "slack", {"status": "stub", **payload})
        return
    try:
        import httpx

        response = httpx.post(webhook, json=payload, timeout=5)
        record_event(db, session_id, tenant.id, "slack", {"status": response.status_code, **payload})
    except Exception as exc:
        record_event(db, session_id, tenant.id, "slack", {"status": "error", "error": str(exc), **payload})


def company_from_email(email: str) -> str:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"}:
        return ""
    return domain.split(".")[0].replace("-", " ").title()
