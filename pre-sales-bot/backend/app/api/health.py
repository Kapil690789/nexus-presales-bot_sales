from fastapi import APIRouter

from backend.app.rag.embeddings import embedding_backend
from backend.app.tenants.loader import list_tenant_slugs

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {
        "status": "ok",
        "embedding_backend": embedding_backend(),
        "tenants": list_tenant_slugs(),
    }
