from fastapi import APIRouter

from backend.app.core.llm import get_llm_health
from backend.app.rag.embeddings import get_embedding_health

router = APIRouter()


@router.get("/health")
def health() -> dict[str, str]:
    emb_health = get_embedding_health()
    llm_health = get_llm_health()
    degraded = emb_health.get("degraded", False) or llm_health.get("degraded", False)
    return {"status": "degraded" if degraded else "ok"}


@router.get("/api/v1/debug-db")
def debug_db():
    import traceback

    result = {"status": "starting"}
    try:
        from backend.app.core.settings import get_settings

        settings = get_settings()
        result["db_url_prefix"] = settings.database_url.split("://")[0]
        result["environment"] = settings.environment
        result["is_production_like"] = settings.is_production_like

        from backend.app.models.db import SessionLocal, get_engine, init_db

        engine = get_engine()
        result["dialect"] = engine.dialect.name

        try:
            init_db()
            result["init_db"] = "ok"
        except Exception as e:
            result["init_db_error"] = str(e)
            result["init_db_traceback"] = traceback.format_exc()

        with SessionLocal() as db:
            from sqlalchemy import inspect, select

            inspector = inspect(engine)
            tables = inspector.get_table_names()
            result["tables"] = tables
            if "sessions" in tables:
                result["session_columns"] = [c["name"] for c in inspector.get_columns("sessions")]
            from backend.app.models.entities import SessionRow, TenantRow

            tenant = db.scalar(select(TenantRow).limit(1))
            result["tenant"] = tenant.slug if tenant else None
            test_sess = SessionRow(
                tenant_id=tenant.id if tenant else "demo",
                stage="discovery",
            )
            db.add(test_sess)
            db.flush()
            result["test_session_create"] = "ok"
            db.rollback()

        result["status"] = "success"
    except Exception as e:
        result["status"] = "error"
        result["error"] = str(e)
        result["traceback"] = traceback.format_exc()
    return result
