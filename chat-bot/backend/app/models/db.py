import re
from collections.abc import Generator
from functools import lru_cache

from sqlalchemy import create_engine, inspect, text
from sqlalchemy.orm import DeclarativeBase, Session, sessionmaker

from backend.app.core.settings import get_settings


class Base(DeclarativeBase):
    pass


def _engine_kwargs(url: str) -> dict:
    if url.startswith("sqlite"):
        return {"connect_args": {"check_same_thread": False}}
    return {"pool_pre_ping": True}


settings = get_settings()
engine = create_engine(settings.database_url, **_engine_kwargs(settings.database_url))
SessionLocal = sessionmaker(bind=engine, autoflush=False, autocommit=False)


def _ensure_sqlite_lead_columns() -> None:
    if not str(engine.url).startswith("sqlite"):
        return
    inspector = inspect(engine)
    if "leads" not in inspector.get_table_names():
        return
    existing = {column["name"] for column in inspector.get_columns("leads")}
    additions = {
        "crm_id": "VARCHAR(80) DEFAULT ''",
        "company": "VARCHAR(200) DEFAULT ''",
        "enrichment_json": "TEXT DEFAULT ''",
    }
    with engine.begin() as conn:
        for name, ddl in additions.items():
            if name not in existing:
                conn.execute(text(f"ALTER TABLE leads ADD COLUMN {name} {ddl}"))


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
    _ensure_sqlite_lead_columns()
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
