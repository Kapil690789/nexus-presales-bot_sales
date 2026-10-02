from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import HTMLResponse, RedirectResponse
from fastapi.templating import Jinja2Templates
from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.core.security import require_admin
from backend.app.core.settings import ROOT, get_settings
from backend.app.models.db import get_db
from backend.app.models.entities import ChunkRow, EventRow, FeedbackPairRow, MessageRow, SessionRow, TenantRow
from backend.app.rag.ingest import ingest_tenant
from backend.app.tenants.loader import (
    TenantNotFound,
    clear_tenant_cache,
    create_tenant_folder,
    ensure_tenant_row,
    list_tenant_slugs,
    load_tenant,
)

router = APIRouter()
templates = Jinja2Templates(directory=str(ROOT / "backend" / "app" / "admin" / "templates"))


def _render(request: Request, name: str, **context) -> HTMLResponse:
    return templates.TemplateResponse(request, name, context)


@router.get("/admin", response_class=HTMLResponse)
def admin_home(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    from backend.app.core.usage import get_usage_summary

    tenants = []
    for slug in list_tenant_slugs():
        row = ensure_tenant_row(db, slug)
        count = db.scalar(select(func.count()).select_from(ChunkRow).where(ChunkRow.tenant_id == row.id)) or 0
        tenants.append({"slug": slug, "name": row.name, "chunks": count, "model": row.embedding_model or "base"})
    sessions = db.scalars(select(SessionRow).order_by(SessionRow.created_at.desc()).limit(30)).all()
    labels = {row.id: row.slug for row in db.scalars(select(TenantRow)).all()}
    usage = get_usage_summary(db=db)
    return _render(request, "index.html", tenants=tenants, sessions=sessions, labels=labels, usage=usage)


@router.get("/admin/api/usage")
def admin_usage_api(db: Session = Depends(get_db), _: str = Depends(require_admin)):
    from backend.app.core.usage import get_usage_summary

    return get_usage_summary(db=db)


@router.post("/admin/tenants")
def admin_create_tenant(
    slug: str = Form(...),
    name: str = Form(...),
    logo_text: str = Form(""),
    primary: str = Form("#1A2B4C"),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        create_tenant_folder(slug.strip().lower(), name.strip(), logo_text.strip(), primary.strip())
        row = ensure_tenant_row(db, slug.strip().lower())
        ingest_tenant(db, row)
    except (ValueError, TenantNotFound) as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    return RedirectResponse("/admin", status_code=303)


@router.get("/admin/sessions/{session_id}", response_class=HTMLResponse)
def admin_session(session_id: str, request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    session = db.get(SessionRow, session_id)
    if session is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    tenant = db.get(TenantRow, session.tenant_id)
    messages = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session.id).order_by(MessageRow.created_at.asc())
    ).all()
    events = db.scalars(select(EventRow).where(EventRow.session_id == session.id)).all()
    return _render(
        request,
        "session.html",
        session=session,
        tenant=tenant,
        messages=messages,
        events=events,
        brief=session.brief_json,
        estimate=session.estimate_json,
        booking=session.booking_json,
        handoff=session.handoff_summary,
    )


@router.get("/admin/rag", response_class=HTMLResponse)
def admin_rag(request: Request, tenant: str = "demo", db: Session = Depends(get_db), _: str = Depends(require_admin)):
    try:
        row = ensure_tenant_row(db, tenant)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    chunks = db.scalars(select(ChunkRow).where(ChunkRow.tenant_id == row.id)).all()
    positives = db.scalar(
        select(func.count()).select_from(FeedbackPairRow).where(
            FeedbackPairRow.tenant_id == row.id, FeedbackPairRow.label == "positive"
        )
    ) or 0
    return _render(request, "rag.html", tenant=row, chunks=chunks, positives=positives)


@router.post("/admin/tenants/{slug}/upload")
async def admin_upload(
    slug: str,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
    _: str = Depends(require_admin),
):
    try:
        load_tenant(slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    data = await file.read()
    filename = Path(file.filename or "upload.md").name
    folder = ROOT / "tenants" / slug / "content" / "uploads"
    folder.mkdir(parents=True, exist_ok=True)
    (folder / filename).write_bytes(data)
    clear_tenant_cache()
    row = ensure_tenant_row(db, slug)
    ingest_tenant(db, row)
    return RedirectResponse(f"/admin/rag?tenant={slug}", status_code=303)


@router.get("/admin/google/start")
def google_start(tenant: str, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    settings = get_settings()
    if not settings.google_client_id.strip() or not settings.google_client_secret.strip():
        raise HTTPException(status_code=400, detail="Set GOOGLE_CLIENT_ID and GOOGLE_CLIENT_SECRET in .env")
    try:
        row = ensure_tenant_row(db, tenant)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id.strip(),
                "client_secret": settings.google_client_secret.strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=settings.google_redirect_uri.strip(),
    )
    auth_url, state = flow.authorization_url(access_type="offline", prompt="consent")
    row.oauth_state = state
    row.oauth_code_verifier = flow.code_verifier or ""
    db.commit()
    return RedirectResponse(auth_url)


@router.get("/admin/google/callback")
def google_callback(request: Request, db: Session = Depends(get_db), _: str = Depends(require_admin)):
    state = request.query_params.get("state") or ""
    code = request.query_params.get("code") or ""
    row = db.scalar(select(TenantRow).where(TenantRow.oauth_state == state))
    if row is None or not code:
        raise HTTPException(status_code=400, detail="OAuth state was not recognized")
    verifier = (row.oauth_code_verifier or "").strip()
    if not verifier:
        raise HTTPException(status_code=400, detail="Google sign-in expired. Click Connect and try again.")
    settings = get_settings()
    from google_auth_oauthlib.flow import Flow

    flow = Flow.from_client_config(
        {
            "web": {
                "client_id": settings.google_client_id.strip(),
                "client_secret": settings.google_client_secret.strip(),
                "auth_uri": "https://accounts.google.com/o/oauth2/auth",
                "token_uri": "https://oauth2.googleapis.com/token",
                "redirect_uris": [settings.google_redirect_uri.strip()],
            }
        },
        scopes=["https://www.googleapis.com/auth/calendar"],
        redirect_uri=settings.google_redirect_uri.strip(),
        state=state,
        code_verifier=verifier,
        autogenerate_code_verifier=False,
    )
    try:
        flow.fetch_token(code=code)
    except Exception as exc:
        raise HTTPException(
            status_code=400,
            detail="Google sign-in failed. Click Connect and finish in one pass. Reloading this page will not work.",
        ) from exc
    token = flow.credentials.refresh_token
    if token:
        row.google_refresh_token = token
    row.oauth_state = ""
    row.oauth_code_verifier = ""
    db.commit()
    return RedirectResponse(f"/admin/rag?tenant={row.slug}", status_code=303)
