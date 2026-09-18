from fastapi import APIRouter

from backend.app.core.llm import llm_available

router = APIRouter()


@router.get("/health")
def health() -> dict:
    return {"ok": True, "service": "northline-presales", "llm": llm_available()}
