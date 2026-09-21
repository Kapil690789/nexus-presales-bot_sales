import json
from datetime import datetime
from typing import Any

from sqlalchemy.orm import Session

from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import get_config
from backend.app.core.security import client_ip, client_user_agent
from backend.app.engines.enrichment import crm_id_for, enrich_email
from backend.app.models.entities import LeadRow, MessageRow, SessionRow


def dumps(value: Any) -> str:
    return "" if value is None else json.dumps(value, default=str)


def loads(raw: str, default: Any) -> Any:
    if not raw:
        return default
    try:
        return json.loads(raw)
    except json.JSONDecodeError:
        return default


def create_session(db: Session, page_url: str, page_title: str, path: str, brief: ProjectBrief) -> SessionRow:
    row = SessionRow(page_url=page_url, page_title=page_title, path=path, brief_json=brief.model_dump_json())
    db.add(row)
    db.flush()
    return row


def get_session(db: Session, session_id: str) -> SessionRow | None:
    return db.get(SessionRow, session_id)


def brief_of(row: SessionRow) -> ProjectBrief:
    return ProjectBrief.model_validate(loads(row.brief_json, {}))


def add_message(db: Session, session_id: str, role: str, content: str, payload: Any = None) -> MessageRow:
    row = MessageRow(session_id=session_id, role=role, content=content, payload_json=dumps(payload) if payload is not None else "")
    db.add(row)
    return row


def grant_nda(row: SessionRow, version: str, request: Any = None) -> SessionRow:
    row.nda_accepted = True
    if not row.nda_accepted_at:
        row.nda_accepted_at = datetime.utcnow()
    row.nda_version = version
    if request is not None:
        row.nda_ip = client_ip(request)
        row.nda_user_agent = client_user_agent(request)
    return row


def persist_turn(db: Session, row: SessionRow, turn) -> SessionRow:
    row.brief_json = turn.brief.model_dump_json()
    row.stage = turn.stage
    row.contact_json = dumps(turn.contact)
    row.qualification_json = dumps(turn.qualification)
    row.estimate_json = dumps(turn.estimate)
    row.architecture_json = dumps(turn.architecture)
    row.mvp_json = dumps(turn.mvp)
    row.portfolio_json = dumps(turn.portfolio)
    row.nda_accepted = turn.nda_accepted
    if turn.nda_accepted and not row.nda_accepted_at:
        row.nda_accepted_at = datetime.utcnow()
    row.booking_json = dumps(turn.booking)
    row.handoff_summary = turn.handoff_summary or row.handoff_summary
    if getattr(turn, "style", None) is not None:
        row.style_json = dumps(turn.style)
    row.updated_at = datetime.utcnow()
    email = (turn.contact or {}).get("email") or ""
    if email or turn.handoff_summary:
        lead = row.lead or LeadRow(session_id=row.id)
        lead.email = email
        lead.phone = (turn.contact or {}).get("phone") or ""
        if turn.qualification:
            lead.score = int(turn.qualification.get("score") or 0)
            lead.band = str(turn.qualification.get("band") or "")
        if turn.estimate:
            lead.estimate_snapshot = dumps(turn.estimate)
        if turn.handoff_summary:
            lead.handoff_summary = turn.handoff_summary
        if email:
            profile = enrich_email(email, get_config().enrichment)
            if not lead.crm_id:
                lead.crm_id = crm_id_for(row.id)
            lead.company = profile["company"]
            lead.enrichment_json = dumps(profile)
        db.add(lead)
    return row
