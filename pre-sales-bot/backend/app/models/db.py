from __future__ import annotations

import logging
import os
import ssl
import threading

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.core.settings import get_settings

log = logging.getLogger(__name__)
_ready = False
_ready_lock = threading.Lock()


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    kwargs: dict = {"pool_pre_ping": True}
    if os.environ.get("VERCEL"):
        kwargs["poolclass"] = NullPool
    if "+pg8000://" in url:
        kwargs["connect_args"] = {"ssl_context": ssl.create_default_context()}
    return kwargs


def _build_engine():
    settings = get_settings()
    return create_engine(settings.database_url, **_engine_kwargs(settings.database_url))


def _fallback_engine():
    return create_engine("sqlite:////tmp/presales-fallback.db", connect_args={"check_same_thread": False})


_engine = None
_engine_lock = threading.Lock()
_session_factory = None


def get_engine():
    """Open the database on first use so a bad URL cannot abort import."""
    global _engine
    if _engine is not None:
        return _engine
    with _engine_lock:
        if _engine is None:
            try:
                _engine = _build_engine()
            except Exception:
                log.exception("Database URL is unusable; using a temporary sqlite file.")
                _engine = _fallback_engine()
    return _engine


def __getattr__(name: str):
    if name == "engine":
        return get_engine()
    raise AttributeError(name)


def SessionLocal():
    global _session_factory
    if _session_factory is None:
        _session_factory = sessionmaker(bind=get_engine(), autoflush=False, autocommit=False)
    return _session_factory()


def ensure_ready() -> None:
    """On Vercel, create tables and index the corpus on the first database request."""
    global _ready
    if not os.environ.get("VERCEL") or _ready:
        return
    with _ready_lock:
        if _ready:
            return
        try:
            from backend.app.core.settings import uploads_root
            from backend.app.rag.ingest import ingest_all

            uploads_root().mkdir(parents=True, exist_ok=True)
            init_db()
            with SessionLocal() as db:
                ingest_all(db)
        except Exception:
            log.exception("Startup index failed")
        finally:
            _ready = True


def get_db():
    ensure_ready()
    db = SessionLocal()
    try:
        yield db
    finally:
        db.close()


def _pgvector_setup() -> None:
    bind = get_engine()
    if bind.dialect.name != "postgresql":
        return
    statements = [
        "CREATE EXTENSION IF NOT EXISTS vector",
        "ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS embedding vector(384)",
    ]
    with bind.begin() as conn:
        for statement in statements:
            conn.execute(text(statement))
        try:
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS rag_chunks_embedding_hnsw "
                    "ON rag_chunks USING hnsw (embedding vector_cosine_ops)"
                )
            )
        except Exception:
            pass


def pgvector_ready() -> bool:
    bind = get_engine()
    if bind.dialect.name != "postgresql":
        return False
    try:
        inspector = inspect(bind)
        if "rag_chunks" not in inspector.get_table_names():
            return False
        columns = {column["name"] for column in inspector.get_columns("rag_chunks")}
        return "embedding" in columns
    except Exception:
        return False


def _ensure_columns(table: str, additions: dict[str, str]) -> None:
    bind = get_engine()
    inspector = inspect(bind)
    if table not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table)}
    dialect = bind.dialect.name
    with bind.begin() as conn:
        for name, ddl in additions.items():
            if name in existing:
                continue
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def init_db() -> None:
    from backend.app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=get_engine())
    _ensure_columns("tenants", {"oauth_code_verifier": "TEXT DEFAULT ''"})
    _ensure_columns(
        "sessions",
        {
            "llm_calls_used": "INTEGER DEFAULT 0",
            "expires_at": "TIMESTAMP NULL",
            "handoff_summary": "TEXT DEFAULT ''",
        },
    )
    _ensure_columns("leads", {"handoff_summary": "TEXT DEFAULT ''"})
    _ensure_columns(
        "rag_chunks",
        {
            "embedding_json": "TEXT DEFAULT ''",
            "embedding_dim": "INTEGER DEFAULT 0",
            "embedding_version": "VARCHAR(100) DEFAULT ''",
            "content_hash": "VARCHAR(64) DEFAULT ''",
        },
    )
    _pgvector_setup()
