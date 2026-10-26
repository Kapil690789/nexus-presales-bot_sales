from __future__ import annotations

import json
from typing import Any

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
    import time
    import httpx

    last_error = ""
    # Retry with backoff: immediate, 0.5s, 1.5s
    for wait_s in (0.0, 0.5, 1.5):
        if wait_s > 0:
            time.sleep(wait_s)
        try:
            response = httpx.post(webhook, json=payload, timeout=5)
            if response.status_code in (200, 201, 204):
                record_event(db, session_id, tenant.id, "slack", {"status": response.status_code, **payload})
                return
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)

    record_event(db, session_id, tenant.id, "slack", {"status": "error", "error": last_error, **payload})


def crm_webhook(tenant: TenantRow) -> str:
    return getattr(get_settings(), "crm_webhook_url", "").strip()


def dispatch_crm_webhook(db: Session, session_id: str, tenant_id: str, lead_data: dict) -> None:
    settings = get_settings()
    webhook = getattr(settings, "crm_webhook_url", "").strip()
    if not webhook:
        record_event(db, session_id, tenant_id, "crm", {"status": "stub", **lead_data})
        return
    import time
    import httpx

    last_error = ""
    for wait_s in (0.0, 0.5, 1.5):
        if wait_s > 0:
            time.sleep(wait_s)
        try:
            response = httpx.post(webhook, json=lead_data, timeout=5)
            if response.status_code in (200, 201, 204):
                record_event(db, session_id, tenant_id, "crm", {"status": response.status_code, **lead_data})
                return
            last_error = f"HTTP {response.status_code}"
        except Exception as exc:
            last_error = str(exc)

    record_event(db, session_id, tenant_id, "crm", {"status": "error", "error": last_error, **lead_data})


def sync_crm_lead(
    db: Session,
    session_id: str,
    tenant: TenantRow,
    email: str,
    qual: dict,
    brief: Any,
    estimate: dict | None = None,
    handoff: str = "",
) -> None:
    company = company_from_email(email)
    lead_data = {
        "session_id": session_id,
        "email": email,
        "company": company,
        "score": int(qual.get("score") or 0),
        "band": qual.get("band") or "exploring",
        "service": getattr(brief, "service", None) or "",
        "budget": getattr(brief, "budget_band", None) or "",
        "timeline": getattr(brief, "timeline", None) or "",
        "platforms": getattr(brief, "platforms", None) or [],
        "features": getattr(brief, "features", None) or [],
        "estimate": estimate.get("range_label") if estimate else None,
        "handoff_summary": handoff,
        "source": "nexus_presales_bot",
    }
    dispatch_crm_webhook(db, session_id, tenant.id, lead_data)


def company_from_email(email: str) -> str:
    domain = email.split("@")[-1].lower() if "@" in email else ""
    if domain in {"gmail.com", "yahoo.com", "outlook.com", "hotmail.com", "icloud.com"}:
        return ""
    return domain.split(".")[0].replace("-", " ").title()


def format_bant_handoff_message(
    brand_name: str,
    brief: Any,
    qual: dict,
    contact: dict,
    estimate: dict | None = None,
    booked: dict | None = None,
    session_id: str = "",
    action_type: str = "Lead captured",
) -> str:
    """Format rich, explainable BANT handoff notification for Slack and email webhooks."""
    score = int(qual.get("score") or 0)
    band = qual.get("band") or "exploring"
    if band == "hot" or score >= 75:
        badge = f"🔥 *[HOT LEAD - Score: {score}/100]*"
    elif band == "warm" or score >= 45:
        badge = f"⚡ *[WARM LEAD - Score: {score}/100]*"
    else:
        badge = f"🌱 *[EXPLORING LEAD - Score: {score}/100]*"

    email = contact.get("email") or "not captured"
    company = company_from_email(email)
    company_str = f" ({company})" if company else ""

    bant = qual.get("bant") or {}
    budget_info = bant.get("budget", {}) if isinstance(bant, dict) else {}
    auth_info = bant.get("authority", {}) if isinstance(bant, dict) else {}
    need_info = bant.get("need", {}) if isinstance(bant, dict) else {}
    time_info = bant.get("timing", {}) if isinstance(bant, dict) else {}

    b_val = budget_info.get("value") or getattr(brief, "budget_band", None) or "exploring"
    b_fit = budget_info.get("fit") or "exploring"
    a_val = auth_info.get("value") or getattr(brief, "decision_role", None) or "unknown"
    a_fit = auth_info.get("fit") or "evaluating"
    n_service = need_info.get("service") or getattr(brief, "service", None) or "custom_software"
    t_val = time_info.get("value") or getattr(brief, "timeline", None) or "flexible"
    t_urgency = time_info.get("urgency") or "flexible"

    features_list = getattr(brief, "features", None)
    features_str = ", ".join(features_list) if features_list else "MVP Scope"
    platforms_list = getattr(brief, "platforms", None)
    platforms_str = ", ".join(platforms_list) if platforms_list else ""

    lines = [
        f"{badge} {action_type} for {brand_name}: {email}{company_str} (Session: {session_id})",
        "• *BANT Qualification*:",
        f"   - 💰 *Budget*: {b_val} (Fit: {b_fit})",
        f"   - 👤 *Authority*: {a_val} (Fit: {a_fit})",
        f"   - 🎯 *Need*: {n_service} (Features: {features_str})",
        f"   - ⏱️ *Timing*: {t_val} (Urgency: {t_urgency})",
    ]

    goal = getattr(brief, "goal", None)
    if goal:
        lines.append(f"• *Goal*: {goal}")
    if platforms_str:
        lines.append(f"• *Platform*: {platforms_str}")

    try:
        from backend.app.engines.domains import detect_domain, get_domain_blueprint

        dom = detect_domain(brief=brief)
        if dom:
            bp = get_domain_blueprint(dom)
            if bp:
                lines.append(f"• *Domain*: {bp.label} (Compliance: {bp.compliance})")
    except Exception:
        pass

    if estimate:
        lines.append(f"• *Estimate*: {estimate.get('range_label')} / {estimate.get('timeline_weeks')} weeks")
    if booked:
        slot = booked.get("label") or booked.get("slot_iso") or "Scheduled"
        lines.append(f"• *Booking*: {slot}")

    return "\n".join(lines)
