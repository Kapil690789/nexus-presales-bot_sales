from fastapi import APIRouter

from backend.app.config_loader.loader import get_config

router = APIRouter()


@router.get("/api/v1/public-config")
def public_config() -> dict:
    config = get_config()
    return {
        "agency": {"name": config.agency.name, "tagline": config.agency.tagline, "ask_email": config.agency.ask_email},
        "brand": config.brand.model_dump(),
        "nda": {"label": config.agency.nda.checkbox_label, "body": config.agency.nda.body},
        "disclaimer": config.agency.disclaimer.strip(),
    }
