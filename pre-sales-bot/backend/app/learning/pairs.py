from __future__ import annotations

import json

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.models.entities import ChunkRow, FeedbackPairRow, MessageRow
from backend.app.rag.redact import redact


def save_thumb(db: Session, tenant_id: str, message: MessageRow, previous_user: str, rating: str) -> int:
    label = "positive" if rating in {"up", "positive", "thumbs_up"} else "negative"
    payload = _payload(message)
    chunk_ids = [str(item) for item in payload.get("chunk_ids") or [] if item]
    existing = db.scalars(
        select(FeedbackPairRow).where(FeedbackPairRow.message_id == message.id, FeedbackPairRow.source == "thumb")
    ).all()
    for row in existing:
        db.delete(row)
    query = redact(payload.get("query") or previous_user or "")
    for chunk_id in chunk_ids:
        if db.get(ChunkRow, chunk_id) is None:
            continue
        db.add(
            FeedbackPairRow(
                tenant_id=tenant_id,
                session_id=message.session_id,
                message_id=message.id,
                query=query,
                chunk_id=chunk_id,
                label=label,
                source="thumb",
            )
        )
    db.commit()
    return len(chunk_ids)


def save_booking_pairs(db: Session, tenant_id: str, session_id: str) -> int:
    messages = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session_id, MessageRow.role == "assistant")
    ).all()
    users = db.scalars(select(MessageRow).where(MessageRow.session_id == session_id, MessageRow.role == "user")).all()
    user_text = users[-1].content if users else ""
    added = 0
    for message in messages:
        payload = _payload(message)
        query = redact(payload.get("query") or user_text)
        for chunk_id in payload.get("chunk_ids") or []:
            exists = db.scalar(
                select(FeedbackPairRow).where(
                    FeedbackPairRow.message_id == message.id,
                    FeedbackPairRow.chunk_id == str(chunk_id),
                    FeedbackPairRow.source == "booking",
                )
            )
            if exists or db.get(ChunkRow, str(chunk_id)) is None:
                continue
            db.add(
                FeedbackPairRow(
                    tenant_id=tenant_id,
                    session_id=session_id,
                    message_id=message.id,
                    query=query,
                    chunk_id=str(chunk_id),
                    label="positive",
                    source="booking",
                )
            )
            added += 1
    db.commit()
    return added


def positive_pairs(db: Session, tenant_id: str) -> list[tuple[str, str]]:
    rows = db.scalars(
        select(FeedbackPairRow).where(FeedbackPairRow.tenant_id == tenant_id, FeedbackPairRow.label == "positive")
    ).all()
    pairs: list[tuple[str, str]] = []
    for row in rows:
        chunk = db.get(ChunkRow, row.chunk_id)
        if chunk and row.query.strip() and chunk.content.strip():
            pairs.append((row.query.strip(), chunk.content.strip()))
    return pairs


def _payload(message: MessageRow) -> dict:
    try:
        data = json.loads(message.payload_json or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
