import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, Integer, String, Text, UniqueConstraint
from sqlalchemy.orm import Mapped, mapped_column, relationship

from backend.app.models.db import Base


def _uuid() -> str:
    return str(uuid.uuid4())


class SessionRow(Base):
    __tablename__ = "sessions"

    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    page_url: Mapped[str] = mapped_column(String(500), default="")
    page_title: Mapped[str] = mapped_column(String(300), default="")
    path: Mapped[str] = mapped_column(String(300), default="/")
    stage: Mapped[str] = mapped_column(String(40), default="greeting")
    brief_json: Mapped[str] = mapped_column(Text, default="{}")
    contact_json: Mapped[str] = mapped_column(Text, default="{}")
    qualification_json: Mapped[str] = mapped_column(Text, default="")
    estimate_json: Mapped[str] = mapped_column(Text, default="")
    architecture_json: Mapped[str] = mapped_column(Text, default="")
    mvp_json: Mapped[str] = mapped_column(Text, default="")
    portfolio_json: Mapped[str] = mapped_column(Text, default="")
    nda_accepted: Mapped[bool] = mapped_column(Boolean, default=False)
    nda_accepted_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    nda_version: Mapped[str] = mapped_column(String(40), default="")
    nda_ip: Mapped[str] = mapped_column(String(80), default="")
    nda_user_agent: Mapped[str] = mapped_column(String(300), default="")
    booking_json: Mapped[str] = mapped_column(Text, default="")
    handoff_summary: Mapped[str] = mapped_column(Text, default="")
    learning_json: Mapped[str] = mapped_column(Text, default="")
    style_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
    messages: Mapped[list["MessageRow"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    documents: Mapped[list["DocumentRow"]] = relationship(back_populates="session", cascade="all, delete-orphan")
    lead: Mapped["LeadRow | None"] = relationship(back_populates="session", uselist=False)


class MessageRow(Base):
    __tablename__ = "messages"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    role: Mapped[str] = mapped_column(String(20))
    content: Mapped[str] = mapped_column(Text)
    payload_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session: Mapped[SessionRow] = relationship(back_populates="messages")


class LeadRow(Base):
    __tablename__ = "leads"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), unique=True)
    email: Mapped[str] = mapped_column(String(200), default="")
    phone: Mapped[str] = mapped_column(String(40), default="")
    score: Mapped[int] = mapped_column(default=0)
    band: Mapped[str] = mapped_column(String(20), default="")
    estimate_snapshot: Mapped[str] = mapped_column(Text, default="")
    handoff_summary: Mapped[str] = mapped_column(Text, default="")
    crm_id: Mapped[str] = mapped_column(String(80), default="")
    company: Mapped[str] = mapped_column(String(200), default="")
    enrichment_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session: Mapped[SessionRow] = relationship(back_populates="lead")


class DocumentRow(Base):
    __tablename__ = "documents"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(ForeignKey("sessions.id"), index=True)
    filename: Mapped[str] = mapped_column(String(300))
    storage_key: Mapped[str] = mapped_column(String(500))
    excerpt: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    session: Mapped[SessionRow] = relationship(back_populates="documents")


class EventRow(Base):
    __tablename__ = "events"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    session_id: Mapped[str] = mapped_column(String(36), index=True, default="")
    kind: Mapped[str] = mapped_column(String(40))
    payload_json: Mapped[str] = mapped_column(Text, default="{}")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)


class RagChunkRow(Base):
    """One retrievable document: either approved knowledge or a learned lesson.

    ``embedding_json`` is the portable representation. On Postgres a native
    ``vector`` column is added alongside it by ``init_db`` and used for search.
    """

    __tablename__ = "rag_chunks"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    kind: Mapped[str] = mapped_column(String(20), index=True, default="knowledge")
    source: Mapped[str] = mapped_column(String(40), index=True, default="")
    source_id: Mapped[str] = mapped_column(String(120), index=True, default="")
    doc_id: Mapped[str] = mapped_column(String(200), unique=True, index=True)
    title: Mapped[str] = mapped_column(String(300), default="")
    content: Mapped[str] = mapped_column(Text, default="")
    metadata_json: Mapped[str] = mapped_column(Text, default="{}")
    content_hash: Mapped[str] = mapped_column(String(64), default="")
    embedding_model: Mapped[str] = mapped_column(String(80), default="")
    embedding_dim: Mapped[int] = mapped_column(Integer, default=0)
    embedding_json: Mapped[str] = mapped_column(Text, default="")
    created_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)


class CalendarCredentialRow(Base):
    """Singleton OAuth tokens for the agency Google Calendar."""

    __tablename__ = "calendar_credentials"
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default="default")
    refresh_token: Mapped[str] = mapped_column(Text, default="")
    access_token: Mapped[str] = mapped_column(Text, default="")
    token_uri: Mapped[str] = mapped_column(String(200), default="https://oauth2.googleapis.com/token")
    scopes: Mapped[str] = mapped_column(Text, default="")
    email: Mapped[str] = mapped_column(String(200), default="")
    expiry: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)
    oauth_state: Mapped[str] = mapped_column(String(120), default="")
    oauth_code_verifier: Mapped[str] = mapped_column(Text, default="")
    connected_at: Mapped[datetime | None] = mapped_column(DateTime, nullable=True)


class RagOutcomeRow(Base):
    """How often a retrievable subject appeared in a conversation that converted."""

    __tablename__ = "rag_outcomes"
    __table_args__ = (UniqueConstraint("subject_kind", "subject_id", name="uq_rag_outcome_subject"),)
    id: Mapped[str] = mapped_column(String(36), primary_key=True, default=_uuid)
    subject_kind: Mapped[str] = mapped_column(String(40), index=True)
    subject_id: Mapped[str] = mapped_column(String(200), index=True)
    sessions: Mapped[int] = mapped_column(Integer, default=0)
    handoffs: Mapped[int] = mapped_column(Integer, default=0)
    score_sum: Mapped[int] = mapped_column(Integer, default=0)
    updated_at: Mapped[datetime] = mapped_column(DateTime, default=datetime.utcnow, onupdate=datetime.utcnow)
