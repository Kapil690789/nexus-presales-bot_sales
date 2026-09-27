from __future__ import annotations

import uuid
from datetime import datetime, timezone

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


def _now() -> datetime:
    return datetime.now(timezone.utc)


class TenantRow(Base):
    __tablename__ = "tenants"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    slug: Mapped[str] = mapped_column(String(80), unique=True, index=True)
    name: Mapped[str] = mapped_column(String(200), default="")
    collection: Mapped[str] = mapped_column(String(80), index=True, default="")
    brand_json: Mapped[str] = mapped_column(Text, default="{}")
    embedding_model: Mapped[str] = mapped_column(String(200), default="")
    google_refresh_token: Mapped[str] = mapped_column(Text, default="")
    google_calendar_id: Mapped[str] = mapped_column(String(200), default="primary")
    slack_webhook_url: Mapped[str] = mapped_column(Text, default="")
    oauth_state: Mapped[str] = mapped_column(String(120), default="")
    oauth_code_verifier: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    page_url: Mapped[str] = mapped_column(String(500), default="")
    page_title: Mapped[str] = mapped_column(String(300), default="")
    path: Mapped[str] = mapped_column(String(300), default="/")
    stage: Mapped[str] = mapped_column(String(40), default="discovery")
    brief_json: Mapped[str] = mapped_column(Text, default="{}")
    summary: Mapped[str] = mapped_column(Text, default="")
    contact_json: Mapped[str] = mapped_column(Text, default="{}")
    qualification_json: Mapped[str] = mapped_column(Text, default="")
    estimate_json: Mapped[str] = mapped_column(Text, default="")
    architecture_json: Mapped[str] = mapped_column(Text, default="")
    mvp_json: Mapped[str] = mapped_column(Text, default="")
    portfolio_json: Mapped[str] = mapped_column(Text, default="")
    nda_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    nda_version: Mapped[str] = mapped_column(String(40), default="")
    booking_json: Mapped[str] = mapped_column(Text, default="")
    handoff_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)
    messages: Mapped[list["MessageRow"]] = relationship(back_populates="session", cascade="all, delete-orphan")


class MessageRow(Base):
    __tablename__ = "messages"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text, default="")
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    session: Mapped[SessionRow] = relationship(back_populates="messages")


class LeadRow(Base):
    __tablename__ = "leads"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    score: Mapped[int] = mapped_column(Integer, default=0)
    band: Mapped[str] = mapped_column(String(20), default="")
    estimate_snapshot: Mapped[str] = mapped_column(Text, default="")
    handoff_summary: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class DocumentRow(Base):
    __tablename__ = "documents"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    storage_key: Mapped[str] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class EventRow(Base):
    __tablename__ = "events"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    tenant_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    kind: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)


class ChunkRow(Base):
    __tablename__ = "rag_chunks"
    __table_args__ = (UniqueConstraint("tenant_id", "doc_id", name="uq_chunk_tenant_doc"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(ForeignKey("tenants.id"), index=True)
    collection: Mapped[str] = mapped_column(String(80), index=True, default="")
    kind: Mapped[str] = mapped_column(String(20), index=True, default="knowledge")
    source: Mapped[str] = mapped_column(String(40), index=True, default="")
    source_id: Mapped[str] = mapped_column(String(200), default="")
    doc_id: Mapped[str] = mapped_column(String(240), index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    embedding_model: Mapped[str] = mapped_column(String(200), default="")
    embedding_dim: Mapped[int] = mapped_column(Integer, default=0)
    embedding_json: Mapped[str] = mapped_column(Text, default="")
    nda_only: Mapped[bool] = mapped_column(Boolean, default=False)
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=_now, onupdate=_now)


class FeedbackPairRow(Base):
    __tablename__ = "feedback_pairs"
    __table_args__ = (UniqueConstraint("message_id", "chunk_id", "source", name="uq_feedback_pair"),)

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    tenant_id: Mapped[str] = mapped_column(String(36), index=True)
    session_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    message_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    query: Mapped[str] = mapped_column(Text, default="")
    chunk_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    label: Mapped[str] = mapped_column(String(20), default="positive")
    source: Mapped[str] = mapped_column(String(20), default="thumb")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=_now)
