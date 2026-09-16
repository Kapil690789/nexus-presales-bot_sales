import uuid
from datetime import datetime

from sqlalchemy import Boolean, DateTime, ForeignKey, String, Text
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
    booking_json: Mapped[str] = mapped_column(Text, default="")
    handoff_summary: Mapped[str] = mapped_column(Text, default="")
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
