from fastapi import APIRouter

from backend.app.config_loader.loader import get_config
from backend.app.engines.google_client import is_live

router = APIRouter()


@router.get("/api/v1/public-config")
def public_config() -> dict:
    config = get_config()
    try:
        live = is_live()
    except Exception:
        live = False
    return {
        "agency": {"name": config.agency.name, "tagline": config.agency.tagline, "ask_email": config.agency.ask_email},
        "brand": config.brand.model_dump(),
        "nda": {
            "version": config.agency.nda.version,
            "title": config.agency.nda.title,
            "label": config.agency.nda.checkbox_label,
            "body": config.agency.nda.body,
        },
        "disclaimer": config.agency.disclaimer.strip(),
        "booking": {
            "live": live,
            "timezone": config.calendar.timezone,
            "duration_minutes": config.calendar.duration_minutes,
        },
    }
