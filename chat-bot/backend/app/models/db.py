from collections.abc import Generator

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


def init_db() -> None:
    from backend.app.models import entities  # noqa: F401

    Base.metadata.create_all(bind=engine)
    _ensure_sqlite_lead_columns()


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
