from urllib.parse import quote

from fastapi import APIRouter, Depends, HTTPException, Request
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import select
from sqlalchemy.orm import Session, selectinload

from backend.app.config_loader.loader import get_config
from backend.app.core.security import require_admin
from backend.app.core.settings import ROOT
from backend.app.engines.google_client import (
    CalendarError,
    authorization_url,
    complete_oauth,
    connection_status,
    disconnect_google,
    google_configured,
)
from backend.app.models.db import get_db
from backend.app.models.entities import EventRow, LeadRow, RagChunkRow, RagOutcomeRow, SessionRow
from backend.app.rag.ingest import ingest, scan_summary
from backend.app.rag.store import corpus_stats, get_store
from backend.app.services.sessions import loads

router = APIRouter()
_TEMPLATES_DIR = ROOT / "backend" / "app" / "admin" / "templates"
templates = Jinja2Templates(directory=str(_TEMPLATES_DIR)) if _TEMPLATES_DIR.is_dir() else None


def _page(request: Request, name: str, context: dict) -> HTMLResponse:
    if templates is None:
        raise HTTPException(status_code=503, detail="Admin templates are not packaged.")
    return templates.TemplateResponse(request, name, context)


@router.get("/admin/calendar", response_class=HTMLResponse)
def admin_calendar(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    return _page(
        request,
        "calendar.html",
        {"status": connection_status(db), "error": request.query_params.get("error") or ""},
    )


@router.get("/admin/google/connect")
def admin_google_connect(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    if not google_configured():
        return RedirectResponse(url="/admin/calendar?error=Missing+Google+client+id+or+secret", status_code=303)
    try:
        return RedirectResponse(url=authorization_url(db), status_code=303)
    except CalendarError as exc:
        return RedirectResponse(url=f"/admin/calendar?error={quote(str(exc))}", status_code=303)


@router.get("/admin/google/callback")
def admin_google_callback(
    request: Request,
    code: str = "",
    state: str = "",
    error: str = "",
    db: Session = Depends(get_db),
):
    if error:
        return RedirectResponse(url="/admin/calendar?error=denied", status_code=303)
    try:
        complete_oauth(db, code, state)
    except CalendarError as exc:
        reason = "state" if "expired" in str(exc).lower() else str(exc)
        return RedirectResponse(url=f"/admin/calendar?error={quote(reason)}", status_code=303)
    return RedirectResponse(url="/admin/calendar?connected=1", status_code=303)


@router.post("/admin/google/disconnect")
def admin_google_disconnect(db: Session = Depends(get_db), _: str = Depends(require_admin)) -> RedirectResponse:
    disconnect_google(db)
    return RedirectResponse(url="/admin/calendar", status_code=303)


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    leads = db.scalars(select(LeadRow).order_by(LeadRow.created_at.desc())).all()
    sessions = db.scalars(select(SessionRow).order_by(SessionRow.updated_at.desc()).limit(40)).all()
    return _page(request, "index.html", {"leads": leads, "sessions": sessions})


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
                "meet_url": payload.get("meet_url") or "",
                "html_link": payload.get("html_link") or "",
                "event_id": payload.get("event_id") or "",
            }
        )
    return _page(
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


def _lessons(db: Session) -> list[dict]:
    rows = db.scalars(
        select(RagChunkRow).where(RagChunkRow.kind == "lesson").order_by(RagChunkRow.updated_at.desc())
    ).all()
    return [
        {
            "doc_id": row.doc_id,
            "session_id": row.source_id,
            "title": row.title,
            "content": row.content,
            "metadata": loads(row.metadata_json, {}),
            "updated_at": row.updated_at,
        }
        for row in rows
    ]


def _outcomes(db: Session, prior: int) -> list[dict]:
    rows = db.scalars(
        select(RagOutcomeRow).order_by(RagOutcomeRow.subject_kind.asc(), RagOutcomeRow.handoffs.desc())
    ).all()
    return [
        {
            "subject_kind": row.subject_kind,
            "subject_id": row.subject_id,
            "sessions": row.sessions,
            "handoffs": row.handoffs,
            "avg_score": round(row.score_sum / row.handoffs, 1) if row.handoffs else 0,
            "win_rate": round(row.handoffs / (row.sessions + prior), 3) if row.sessions else 0,
        }
        for row in rows
    ]


@router.get("/admin/rag", response_class=HTMLResponse)
def admin_rag(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    config = get_config()
    return _page(
        request,
        "rag.html",
        {
            "stats": corpus_stats(db),
            "lessons": _lessons(db),
            "outcomes": _outcomes(db, config.rag.learning.outcome_prior),
            "rag": config.rag,
        },
    )


@router.post("/admin/rag/reindex")
def admin_rag_reindex(db: Session = Depends(get_db), _: str = Depends(require_admin)) -> RedirectResponse:
    ingest(db)
    return RedirectResponse(url="/admin/rag", status_code=303)


@router.post("/admin/rag/lessons/{session_id}/delete")
def admin_rag_forget(session_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)) -> RedirectResponse:
    get_store().delete_doc(db, f"session:{session_id}")
    return RedirectResponse(url="/admin/rag", status_code=303)


@router.get("/api/v1/admin/rag")
def admin_rag_json(db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    config = get_config()
    return {
        "corpus": corpus_stats(db),
        "lessons": [
            {**lesson, "updated_at": lesson["updated_at"].isoformat()} for lesson in _lessons(db)
        ],
        "outcomes": _outcomes(db, config.rag.learning.outcome_prior),
    }


@router.post("/api/v1/admin/rag/reindex")
def admin_rag_reindex_json(db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    result = ingest(db)
    scan = result.pop("scan", None)
    return {**result, "content": scan_summary(scan)}


@router.delete("/api/v1/admin/rag/lessons/{session_id}")
def admin_rag_forget_json(session_id: str, db: Session = Depends(get_db), _: str = Depends(require_admin)) -> dict:
    return {"deleted": get_store().delete_doc(db, f"session:{session_id}")}


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
