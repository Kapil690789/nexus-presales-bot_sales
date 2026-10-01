from __future__ import annotations

import json
from datetime import datetime, timedelta, timezone
from typing import Any

from fastapi import APIRouter, Depends, HTTPException, Request
from pydantic import BaseModel, Field
from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.router import run_turn
from backend.app.core.guard import REFUSAL_MESSAGE, looks_like_jailbreak
from backend.app.core.security import bind_llm_actor, client_ip, rate_limit_messages, reset_llm_actor
from backend.app.learning.pairs import save_thumb
from backend.app.models.db import get_db
from backend.app.models.entities import MessageRow, SessionRow, TenantRow, _now
from backend.app.screening.slots import DISCOVERY_PROMPTS, chips_for_field
from backend.app.tenants.loader import TenantNotFound, ensure_tenant_row, load_tenant
from backend.app.tenants.schema import TenantConfig

router = APIRouter()
MAX_MESSAGE_CHARS = 1000


class SessionIn(BaseModel):
    tenant: str
    page_url: str = ""
    page_title: str = ""
    path: str = "/"


class ChipIn(BaseModel):
    label: str | None = None
    field: str
    value: Any = None


class MessageIn(BaseModel):
    content: str = ""
    chip: ChipIn | None = None


class FeedbackIn(BaseModel):
    message_id: str
    rating: str = Field(pattern="^(up|down)$")


class NdaIn(BaseModel):
    version: str


def _pair(db: Session, slug: str):
    try:
        config = load_tenant(slug)
        row = ensure_tenant_row(db, slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    return row, config


def _session(db: Session, session_id: str) -> SessionRow:
    row = db.get(SessionRow, session_id)
    if row is None:
        raise HTTPException(status_code=404, detail="Unknown session")
    return row


def _history(db: Session, session_id: str) -> list[dict]:
    rows = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.created_at.asc())
    ).all()
    return [{"role": row.role, "content": row.content} for row in rows]


def _add(db: Session, session_id: str, role: str, content: str, payload: dict | None = None) -> MessageRow:
    row = MessageRow(
        session_id=session_id,
        role=role,
        content=content,
        payload_json=json.dumps(payload or {}),
    )
    db.add(row)
    db.commit()
    db.refresh(row)
    return row


def _public(session: SessionRow, message: MessageRow, result: dict, config: TenantConfig) -> dict:
    return {
        "session_id": session.id,
        "message_id": message.id,
        "message": result["message"],
        "stage": result["stage"],
        "chips": result["chips"],
        "cards": result["cards"],
        "route": result["route"],
        "nda_accepted": session.nda_accepted,
        "nda_version": config.brand.nda_version,
        "score": (result.get("qualification") or {}).get("score"),
        "band": (result.get("qualification") or {}).get("band"),
        "booking": result.get("booking"),
    }


@router.post("/api/v1/sessions")
def create_session(body: SessionIn, db: Session = Depends(get_db)) -> dict:
    tenant, config = _pair(db, body.tenant.strip())
    session = SessionRow(
        tenant_id=tenant.id,
        page_url=body.page_url[:500],
        page_title=body.page_title[:300],
        path=body.path[:300] or "/",
        stage="discovery",
        expires_at=_now() + timedelta(days=7),
    )
    db.add(session)
    db.commit()
    db.refresh(session)
    prompt = DISCOVERY_PROMPTS["service"]
    text = f"I'm {config.brand.name}'s assistant. {prompt}"
    message = _add(
        db,
        session.id,
        "assistant",
        text,
        {"route": "discovery", "chips": chips_for_field("service"), "chunk_ids": []},
    )
    return _public(
        session,
        message,
        {
            "message": text,
            "stage": "discovery",
            "chips": chips_for_field("service"),
            "cards": [],
            "route": "discovery",
            "qualification": None,
            "booking": None,
        },
        config,
    )


def _unsafe_message(text: str, chip: ChipIn | None) -> bool:
    parts = [text]
    if chip is not None:
        parts.append(chip.label or "")
        if isinstance(chip.value, (dict, list)):
            parts.append(json.dumps(chip.value))
        elif chip.value is not None:
            parts.append(str(chip.value))
    return any(looks_like_jailbreak(part) for part in parts)


def _is_expired(expires_at: datetime | None) -> bool:
    if not expires_at:
        return False
    if expires_at.tzinfo is not None:
        return expires_at < datetime.now(timezone.utc)
    return expires_at < datetime.now(timezone.utc).replace(tzinfo=None)


@router.post("/api/v1/sessions/{session_id}/messages")
def post_message(session_id: str, body: MessageIn, request: Request, db: Session = Depends(get_db)) -> dict:
    session = _session(db, session_id)
    if _is_expired(session.expires_at):
        raise HTTPException(status_code=410, detail="Session has expired. Please refresh to start a new chat.")
    tenant_row = db.get(TenantRow, session.tenant_id)
    if tenant_row is None:
        raise HTTPException(status_code=404, detail="Unknown client")
    try:
        config = load_tenant(tenant_row.slug)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    text = (body.content or "").strip()
    if body.chip and not text:
        text = (body.chip.label or "").strip()
    if not text and body.chip is None:
        raise HTTPException(status_code=400, detail="Message is empty")
    if len(text) > MAX_MESSAGE_CHARS:
        raise HTTPException(status_code=400, detail="Message is too long")
    rate_limit_messages(request)
    if _unsafe_message(text, body.chip):
        _add(db, session.id, "user", text, {"chip": body.chip.model_dump() if body.chip else None})
        assistant = _add(
            db,
            session.id,
            "assistant",
            REFUSAL_MESSAGE,
            {"route": "refused", "chips": [], "chunk_ids": []},
        )
        return _public(
            session,
            assistant,
            {
                "message": REFUSAL_MESSAGE,
                "stage": session.stage or "discovery",
                "chips": [],
                "cards": [],
                "route": "refused",
                "qualification": None,
                "booking": None,
            },
            config,
        )
    history = _history(db, session.id)
    _add(db, session.id, "user", text, {"chip": body.chip.model_dump() if body.chip else None})
    token = bind_llm_actor(session.id, client_ip(request))
    try:
        result = run_turn(
            db,
            tenant_row,
            config,
            session,
            history,
            text,
            body.chip.model_dump() if body.chip else None,
        )
    finally:
        reset_llm_actor(token)
    assistant = _add(
        db,
        session.id,
        "assistant",
        result["message"],
        {
            "route": result["route"],
            "chunk_ids": result["chunk_ids"],
            "query": result["query"],
            "score": result["score"],
            "chips": result["chips"],
            "cards": result["cards"],
        },
    )
    db.add(session)
    db.commit()
    return _public(session, assistant, result, config)


@router.post("/api/v1/sessions/{session_id}/feedback")
def post_feedback(session_id: str, body: FeedbackIn, db: Session = Depends(get_db)) -> dict:
    session = _session(db, session_id)
    message = db.get(MessageRow, body.message_id)
    if message is None or message.session_id != session.id or message.role != "assistant":
        raise HTTPException(status_code=404, detail="Unknown message")
    rows = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session.id).order_by(MessageRow.created_at.asc())
    ).all()
    previous = ""
    for row in rows:
        if row.id == message.id:
            break
        if row.role == "user":
            previous = row.content
    saved = save_thumb(db, session.tenant_id, message, previous, body.rating)
    return {"saved": saved, "rating": body.rating}


@router.post("/api/v1/sessions/{session_id}/nda")
def accept_nda(session_id: str, body: NdaIn, request: Request, db: Session = Depends(get_db)) -> dict:
    return post_message(
        session_id,
        MessageIn(content="I accept the confidentiality notice", chip=ChipIn(field="nda", value=body.version, label="Accept")),
        request,
        db,
    )
