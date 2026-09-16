from fastapi import APIRouter, Depends, File, Form, HTTPException, Request, UploadFile
from fastapi.responses import StreamingResponse
from sqlalchemy.orm import Session

from backend.app.api.sessions import _payload, _run
from backend.app.config_loader.loader import get_config
from backend.app.core.security import origin_allowed, rate_limit
from backend.app.core.sse import encode, stream_text
from backend.app.documents.extract import extract_text
from backend.app.documents.storage import store_bytes
from backend.app.models.db import get_db
from backend.app.models.entities import DocumentRow
from backend.app.services.sessions import add_message, brief_of, get_session, loads, persist_turn

router = APIRouter()
MAX_BYTES = 8 * 1024 * 1024


@router.post("/api/v1/sessions/{session_id}/documents")
async def upload(
    session_id: str,
    request: Request,
    file: UploadFile = File(...),
    nda_accepted: bool = Form(False),
    db: Session = Depends(get_db),
):
    rate_limit(request, limit=10)
    origin_allowed(request)
    row = get_session(db, session_id)
    if not row:
        raise HTTPException(status_code=404, detail="Unknown session")

    if nda_accepted and not row.nda_accepted:
        nda_turn = type(
            "NdaOnly",
            (),
            {
                "brief": brief_of(row),
                "stage": row.stage,
                "contact": loads(row.contact_json, {}),
                "qualification": loads(row.qualification_json, None),
                "estimate": loads(row.estimate_json, None),
                "architecture": loads(row.architecture_json, None),
                "mvp": loads(row.mvp_json, None),
                "portfolio": loads(row.portfolio_json, None),
                "nda_accepted": True,
                "booking": loads(row.booking_json, None),
                "handoff_summary": row.handoff_summary,
            },
        )()
        persist_turn(db, row, nda_turn)
        db.flush()

    if get_config().agency.nda.required_before_rfp and not row.nda_accepted:
        raise HTTPException(status_code=400, detail="Accept the confidentiality notice before uploading.")

    data = await file.read()
    if len(data) > MAX_BYTES:
        raise HTTPException(status_code=400, detail="File is larger than 8MB")
    try:
        text = extract_text(file.filename or "upload.txt", data)
    except ValueError as exc:
        raise HTTPException(status_code=400, detail=str(exc)) from exc

    key = store_bytes(file.filename or "upload.bin", data)
    db.add(DocumentRow(session_id=row.id, filename=file.filename or "upload", storage_key=key, excerpt=text[:1500]))
    turn = _run(db, row, f"I uploaded {file.filename}", None, True if nda_accepted else row.nda_accepted, rfp_text=text)
    add_message(db, row.id, "user", f"Uploaded {file.filename}", {"filename": file.filename})
    payload = _payload(turn)

    def events():
        yield from stream_text(turn.message)
        yield encode("cards", {"cards": payload["cards"]})
        yield encode("chips", {"chips": payload["chips"]})
        yield encode("meta", {k: payload[k] for k in ("stage", "actions", "nda_accepted", "can_book", "score", "band")})
        yield encode("done", {"ok": True})

    return StreamingResponse(events(), media_type="text/event-stream")
