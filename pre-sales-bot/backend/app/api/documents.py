from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, HTTPException, Request, UploadFile
from sqlalchemy.orm import Session

from backend.app.api.sessions import _add, _public, _session
from backend.app.core.guard import UPLOAD_REFUSAL, looks_like_jailbreak
from backend.app.core.security import rate_limit_messages
from backend.app.core.settings import uploads_root
from backend.app.documents.extract import UnsafeUpload, extract_text
from backend.app.models.db import get_db
from backend.app.models.entities import DocumentRow, SessionRow, TenantRow
from backend.app.tenants.loader import TenantNotFound, load_tenant
from backend.app.tenants.schema import TenantConfig

router = APIRouter()


def _refused_upload(db: Session, session: SessionRow, config: TenantConfig) -> dict:
    assistant = _add(
        db,
        session.id,
        "assistant",
        UPLOAD_REFUSAL,
        {"route": "refused", "chips": [], "chunk_ids": []},
    )
    db.commit()
    return _public(
        session,
        assistant,
        {
            "message": UPLOAD_REFUSAL,
            "stage": session.stage,
            "chips": [],
            "cards": [],
            "route": "refused",
            "qualification": None,
            "booking": None,
        },
        config,
    )


@router.post("/api/v1/sessions/{session_id}/documents")
async def upload_document(
    session_id: str,
    request: Request,
    file: UploadFile = File(...),
    db: Session = Depends(get_db),
) -> dict:
    rate_limit_messages(request)
    session = _session(db, session_id)
    tenant = db.get(TenantRow, session.tenant_id)
    if tenant is None:
        raise HTTPException(status_code=404, detail="Unknown client")
    try:
        config = load_tenant(tenant.slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    data = await file.read()
    if not data:
        raise HTTPException(status_code=400, detail="Empty file")
    if len(data) > 5_000_000:
        raise HTTPException(status_code=400, detail="File is too large")
    filename = Path(file.filename or "upload.txt").name
    if looks_like_jailbreak(filename):
        return _refused_upload(db, session, config)
    try:
        excerpt = extract_text(filename, data)
    except UnsafeUpload:
        return _refused_upload(db, session, config)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc
    folder = uploads_root() / tenant.slug / session.id
    folder.mkdir(parents=True, exist_ok=True)
    target = folder / filename
    target.write_bytes(data)
    db.add(
        DocumentRow(
            session_id=session.id,
            filename=filename,
            storage_key=str(target),
            excerpt=excerpt[:2000],
        )
    )
    message = f"I read {filename}. Here is the part I can use: {excerpt[:500]}"
    chips = []
    if not session.nda_accepted:
        message += f"\n\n{config.brand.nda_text}"
        chips = [{"label": "Accept confidentiality", "field": "nda", "value": config.brand.nda_version}]
    assistant = _add(db, session.id, "assistant", message, {"route": "rfp", "chips": chips, "chunk_ids": []})
    db.commit()
    return _public(
        session,
        assistant,
        {"message": message, "stage": session.stage, "chips": chips, "cards": [], "route": "rfp", "qualification": None, "booking": None},
        config,
    )
