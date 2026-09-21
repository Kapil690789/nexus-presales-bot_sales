import os
import re
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker
from sqlalchemy.pool import NullPool

from backend.app.core.settings import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    kwargs: dict = {"pool_pre_ping": True}
    if os.environ.get("VERCEL"):
        kwargs["poolclass"] = NullPool
    return kwargs


settings = get_settings()
engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_columns(table: str, additions: dict[str, str]) -> None:
    inspector = inspect(engine)
    if table not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns(table)}
    dialect = engine.dialect.name
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name in existing:
                continue
            if dialect == "postgresql":
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN IF NOT EXISTS {name} {ddl}"))
            else:
                conn.execute(text(f"ALTER TABLE {table} ADD COLUMN {name} {ddl}"))


def _ensure_optional_columns() -> None:
    _ensure_columns(
        "leads",
        {
            "crm_id": "VARCHAR(80) DEFAULT ''",
            "company": "VARCHAR(200) DEFAULT ''",
            "enrichment_json": "TEXT DEFAULT ''",
        },
    )
    _ensure_columns(
        "sessions",
        {
            "nda_version": "VARCHAR(40) DEFAULT ''",
            "nda_ip": "VARCHAR(80) DEFAULT ''",
            "nda_user_agent": "VARCHAR(300) DEFAULT ''",
        },
    )
    _ensure_columns(
        "calendar_credentials",
        {"oauth_code_verifier": "TEXT DEFAULT ''"},
    )


@lru_cache
def vector_column_dim() -> int:
    """Dimension of the native pgvector column, or 0 when there isn't one.

    Cached because the store consults it on every search; ``init_db`` clears it
    after any DDL.
    """
    if not str(engine.url).startswith("postgresql"):
        return 0
    try:
        with engine.connect() as conn:
            declared = conn.execute(
                text(
                    "SELECT format_type(a.atttypid, a.atttypmod) FROM pg_attribute a "
                    "WHERE a.attrelid = 'rag_chunks'::regclass AND a.attname = 'embedding' AND NOT a.attisdropped"
                )
            ).scalar()
    except Exception:
        return 0
    match = re.search(r"\((\d+)\)", declared or "")
    return int(match.group(1)) if match else 0


def _ensure_pgvector_column() -> None:
    """Add a native vector column sized to the active embedding model.

    Silently gives up if the extension is unavailable; the store then uses the
    portable ``embedding_json`` path instead.
    """
    settings_now = get_settings()
    if not str(engine.url).startswith("postgresql") or not settings_now.rag_enabled:
        return
    if settings_now.rag_backend.strip().lower() == "fallback":
        return

    from backend.app.rag.embeddings import active_model

    _, dim = active_model()
    existing = vector_column_dim()
    try:
        with engine.begin() as conn:
            conn.execute(text("CREATE EXTENSION IF NOT EXISTS vector"))
            if existing and existing != dim:
                # The embedding model changed; the old vectors are meaningless anyway.
                conn.execute(text("DROP INDEX IF EXISTS rag_chunks_embedding_idx"))
                conn.execute(text("ALTER TABLE rag_chunks DROP COLUMN embedding"))
                existing = 0
            if not existing:
                conn.execute(text(f"ALTER TABLE rag_chunks ADD COLUMN IF NOT EXISTS embedding vector({dim})"))
            conn.execute(
                text(
                    "CREATE INDEX IF NOT EXISTS rag_chunks_embedding_idx ON rag_chunks "
                    "USING ivfflat (embedding vector_cosine_ops) WITH (lists = 100)"
                )
            )
    except Exception:
        pass
    vector_column_dim.cache_clear()


def init_db() -> None:
    from backend.app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_optional_columns()
    _ensure_pgvector_column()


def get_db() -> Generator[Session, None, None]:
    db = SessionLocal()
    try:
        yield db
        db.commit()
    except Exception:
        db.rollback()
        raise
    finally:
        db.close()
