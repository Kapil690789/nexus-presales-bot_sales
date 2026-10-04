from __future__ import annotations

from pathlib import Path

from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
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
    notes: str = Form(""),
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
    clean_notes = (notes or "").strip()
    if looks_like_jailbreak(filename) or (clean_notes and looks_like_jailbreak(clean_notes)):
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
    # Record user upload message in session history
    user_msg_text = f"📎 Uploaded document: {filename}"
    if clean_notes:
        user_msg_text += f"\n\n{clean_notes}"
    _add(db, session.id, "user", user_msg_text, {"filename": filename, "kind": "upload", "notes": clean_notes})

    message = ""
    from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
    from backend.app.core.llm import LLMError, complete_json, llm_available

    if llm_available():
        notes_section = f"\nVisitor additional notes/instructions:\n{wrap_visitor(clean_notes)}\n" if clean_notes else ""
        prompt = (
            f"You are the senior pre-sales consultant at {config.brand.name}. "
            f"The visitor uploaded a project document/spec named '{filename}'. "
            f"{notes_section}"
            f"Document excerpt:\n{wrap_visitor(excerpt[:2000])}\n\n"
            f"{UNTRUSTED_RULE} "
            f"Provide a concise, professional 2-3 sentence assessment of the uploaded spec taking into account any visitor instructions provided. "
            f"Acknowledge the key features or scope identified and invite them to generate an architectural estimate or book a discovery call. "
            f'Return JSON {{"message": "..."}}.'
        )
        try:
            res_data = complete_json("You are an expert enterprise pre-sales software consultant. Output JSON only.", prompt)
            message = str(res_data.get("message") or "").strip()
        except LLMError:
            pass

    if not message:
        clean_excerpt = excerpt[:300].strip().replace("\n", " ")
        message = f"I've reviewed **{filename}**"
        if clean_notes:
            message += f" and your instructions (\"{clean_notes}\")"
        message += f". Key notes extracted:\n\n> \"{clean_excerpt}...\"\n\nWould you like me to generate an indicative architecture and timeline estimate for this?"

    chips = []
    if not session.nda_accepted:
        message += f"\n\n*{config.brand.nda_text}*"
        chips = [{"label": "Accept confidentiality", "field": "nda", "value": config.brand.nda_version}]
    else:
        chips = [
            {"label": "Generate estimate", "field": "ask", "value": "Give me an estimate"},
            {"label": "Book discovery call", "field": "booking_window", "value": "now"},
        ]

    assistant = _add(db, session.id, "assistant", message, {"route": "rfp", "chips": chips, "chunk_ids": []})
    db.commit()
    return _public(
        session,
        assistant,
        {"message": message, "stage": session.stage, "chips": chips, "cards": [], "route": "rfp", "qualification": None, "booking": None},
        config,
    )
