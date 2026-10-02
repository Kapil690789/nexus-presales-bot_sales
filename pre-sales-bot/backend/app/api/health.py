from fastapi import APIRouter

from backend.app.core.llm import get_llm_health
from backend.app.core.security import is_admin_misconfigured
from backend.app.core.settings import get_settings
from backend.app.rag.embeddings import embedding_backend, get_embedding_health
from backend.app.tenants.loader import list_tenant_slugs

router = APIRouter()


@router.get("/health")
def health() -> dict:
    settings = get_settings()
    admin_status = "disabled_misconfigured" if is_admin_misconfigured(settings) else "enabled"
    stale_count = 0
    try:
        from backend.app.models.db import SessionLocal
        from backend.app.rag.store import count_stale_chunks

        with SessionLocal() as db:
            stale_count = count_stale_chunks(db)
    except Exception:
        pass

    emb_health = get_embedding_health()
    emb_health["stale_chunks"] = stale_count

    llm_health = get_llm_health()
    degraded = emb_health.get("degraded", False) or llm_health.get("degraded", False)

    return {
        "status": "degraded" if degraded else "ok",
        "embedding_backend": embedding_backend(),
        "tenants": list_tenant_slugs(),
        "embeddings": emb_health,
        "llm": llm_health,
        "llm_failures": llm_health["failures_1h"],
        "llm_degraded": llm_health["degraded"],
        "stale_chunks": stale_count,
        "admin": admin_status,
    }

