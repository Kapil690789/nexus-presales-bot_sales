from fastapi import APIRouter, HTTPException

from backend.app.tenants.loader import TenantNotFound, load_tenant, public_brand

router = APIRouter()


@router.get("/api/v1/public-config")
def public_config(tenant: str) -> dict:
    try:
        config = load_tenant(tenant)
    except TenantNotFound:
        raise HTTPException(status_code=404, detail="Unknown client") from None
    brand = public_brand(config)
    return {
        "tenant": config.slug,
        "brand": brand,
        "nda": {"version": config.brand.nda_version, "text": config.brand.nda_text},
        "disclaimer": config.brand.disclaimer,
    }
