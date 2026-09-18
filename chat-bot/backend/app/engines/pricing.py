from math import ceil

from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.models import PricingConfig


def _platform_multiplier(brief: ProjectBrief, pricing: PricingConfig) -> float:
    table = pricing.multipliers.get("platforms", {})
    platforms = [item.lower() for item in brief.platforms]
    if not platforms:
        return 1.0
    if "both" in platforms or ({"ios", "android"} <= set(platforms)):
        return float(table.get("both", 1.32))
    values = [float(table.get(item, 1.0)) for item in platforms]
    product = 1.0
    for value in values:
        product *= value
    return product if len(values) == 1 else min(product, float(table.get("both", 1.32)) * 1.05)


def _integration_multiplier(brief: ProjectBrief, pricing: PricingConfig) -> float:
    table = pricing.multipliers.get("integration_count", {})
    count = len([item for item in brief.integrations if item.lower() not in {"none", "no", "n/a"}])
    key = 4 if count >= 4 else count
    return float(table.get(key, table.get(str(key), 1.0)))


def _flag_multiplier(brief: ProjectBrief, pricing: PricingConfig) -> float:
    flags = pricing.multipliers.get("flags", {})
    product = 1.0
    if brief.auth:
        product *= float(flags.get("auth", 1.0))
    if brief.admin:
        product *= float(flags.get("admin", 1.0))
    if brief.realtime:
        product *= float(flags.get("realtime", 1.0))
    if brief.marketplace or "marketplace" in (brief.industry or "") or "marketplace" in (brief.goal or "").lower():
        product *= float(flags.get("marketplace", 1.0))
    if brief.ai_features or brief.service == "ai_product":
        product *= float(flags.get("ai_features", 1.0))
    return product


def estimate_project(brief: ProjectBrief, pricing: PricingConfig) -> dict:
    service = brief.service if brief.service in pricing.bases else "unknown"
    complexity = _platform_multiplier(brief, pricing) * _integration_multiplier(brief, pricing) * _flag_multiplier(
        brief, pricing
    )
    raw = float(pricing.bases[service]) * complexity
    low = int(round(raw * pricing.low_side_factor / 500.0) * 500)
    high = int(round(low * pricing.range_factor / 500.0) * 500)
    if high <= low:
        high = low + 2500
    if complexity >= pricing.complexity_thresholds.get("complex", 1.55):
        size = "complex"
    elif complexity >= pricing.complexity_thresholds.get("medium", 1.25):
        size = "medium"
    else:
        size = "simple"
    weeks = pricing.timeline_weeks[size]
    if brief.timeline == "asap":
        weeks = max(6, ceil(weeks * 0.85))
    elif brief.timeline == "flexible":
        weeks = ceil(weeks * 1.1)
    return {
        "currency": pricing.currency,
        "service": service,
        "raw": int(round(raw)),
        "low": low,
        "high": high,
        "range_label": f"${low:,}–${high:,} {pricing.currency}",
        "complexity": round(complexity, 3),
        "complexity_band": size,
        "timeline_weeks": weeks,
        "team": list(pricing.team_mix.get(service, pricing.team_mix["unknown"])),
        "inclusions": list(pricing.inclusions),
        "exclusions": list(pricing.exclusions),
        "low_side_factor": pricing.low_side_factor,
        "assumptions": _assumptions(brief),
    }


def _assumptions(brief: ProjectBrief) -> list[str]:
    items: list[str] = []
    platforms = [item.lower() for item in brief.platforms]
    if "both" in platforms or ({"ios", "android"} <= set(platforms)):
        items.append("Range assumes iOS and Android in the first release.")
    elif platforms:
        items.append(f"Range assumes {', '.join(platforms)} only.")
    count = len([item for item in brief.integrations if item.lower() not in {"none", "no", "n/a"}])
    if count:
        items.append(f"Includes {count} named integration(s) on day one.")
    else:
        items.append("No third-party integrations in the first-pass number.")
    if brief.auth:
        items.append("Includes authentication and roles.")
    if brief.admin:
        items.append("Includes an operator/admin surface.")
    if brief.realtime:
        items.append("Includes realtime behaviour.")
    if brief.marketplace or "marketplace" in (brief.industry or "") or "marketplace" in (brief.goal or "").lower():
        items.append("Includes two-sided / marketplace mechanics.")
    if brief.ai_features or brief.service == "ai_product":
        items.append("Includes an AI/retrieval feature in the MVP.")
    if brief.timeline == "asap":
        items.append("Timeline is compressed because you asked for ASAP.")
    elif brief.timeline == "flexible":
        items.append("Timeline is a little longer because the date is flexible.")
    items.append("Low-side indicative range, not a fixed quote.")
    return items
