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
