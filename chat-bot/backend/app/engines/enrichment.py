from __future__ import annotations

from backend.app.config_loader.models import EnrichmentConfig


def enrich_email(email: str, config: EnrichmentConfig) -> dict:
    address = (email or "").strip().lower()
    domain = address.split("@")[-1] if "@" in address else ""
    entry = (config.domains or {}).get(domain)
    if entry:
        return {
            "email": address,
            "domain": domain,
            "company": entry.get("company") or domain,
            "size": entry.get("size") or "unknown",
            "industry": entry.get("industry") or "unknown",
            "website": entry.get("website") or f"https://{domain}",
            "source": "directory",
        }
    defaults = config.defaults or {}
    return {
        "email": address,
        "domain": domain or "unknown",
        "company": domain or "Unknown company",
        "size": defaults.get("size") or "unknown",
        "industry": defaults.get("industry") or "unknown",
        "website": f"https://{domain}" if domain else "",
        "source": "inferred",
    }


def crm_id_for(session_id: str) -> str:
    return f"lead_devconsult_{(session_id or 'session').replace('-', '')[:10]}"
