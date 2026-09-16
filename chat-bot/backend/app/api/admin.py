from fastapi import APIRouter, Depends, Request
from fastapi.responses import HTMLResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.core.security import require_admin
from backend.app.core.settings import ROOT
from backend.app.models.db import get_db
from backend.app.models.entities import EventRow, LeadRow, SessionRow
from backend.app.services.sessions import loads

router = APIRouter()
templates = Jinja2Templates(directory=str(ROOT / "backend" / "app" / "admin" / "templates"))


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    leads = db.scalars(select(LeadRow).order_by(LeadRow.created_at.desc())).all()
    sessions = db.scalars(select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(40)).all()
    return templates.TemplateResponse(request, "index.html", {"leads": leads, "sessions": sessions})


@router.get("/admin/sessions/{session_id}", response_class=HTMLResponse)
def admin_session(session_id: str, request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    row = db.scalar(
        select(SessionRow)
        .where(SessionRow.id == session_id)
        .options(selectinload(SessionRow.messages), selectinload(SessionRow.lead), selectinload(SessionRow.documents))
    )
    if not row:
        return HTMLResponse("Not found", status_code=404)
    events = db.scalars(select(EventRow).where(EventRow.session_id == session_id).order_by(EventRow.created_at.asc())).all()
    outbound = []
    for event in events:
        payload = loads(event.payload_json, {})
        outbound.append(
            {
                "kind": event.kind,
                "created_at": event.created_at,
                "status": payload.get("status") or "queued_stub",
                "preview": payload.get("preview") or payload.get("text") or payload.get("subject") or event.kind,
                "body": payload.get("body") or payload.get("text") or "",
            }
        )
    return templates.TemplateResponse(
        request,
        "session.html",
        {
            "row": row,
            "brief": loads(row.brief_json, {}),
            "qualification": loads(row.qualification_json, {}),
            "estimate": loads(row.estimate_json, {}),
            "architecture": loads(row.architecture_json, {}),
            "mvp": loads(row.mvp_json, {}),
            "portfolio": loads(row.portfolio_json, []),
            "contact": loads(row.contact_json, {}),
            "documents": list(row.documents or []),
            "events": outbound,
            "lead": row.lead,
            "messages": sorted(row.messages, key=lambda item: item.created_at),
        },
    )


@router.get("/api/v1/admin/leads")
def admin_leads(db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    leads = db.scalars(select(LeadRow).order_by(LeadRow.created_at.desc())).all()
    return {
        "leads": [
            {
                "id": lead.id,
                "session_id": lead.session_id,
                "email": lead.email,
                "phone": lead.phone,
                "score": lead.score,
                "band": lead.band,
                "company": lead.company,
                "crm_id": lead.crm_id,
                "created_at": lead.created_at.isoformat(),
            }
            for lead in leads
        ]
    }
