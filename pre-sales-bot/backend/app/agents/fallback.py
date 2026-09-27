from __future__ import annotations

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.tenants.schema import TenantConfig


def fallback_message(config: TenantConfig, brief: ProjectBrief, estimate: dict | None) -> str:
    name = config.brand.name
    parts = [
        f"I'm {name}'s assistant, and I don't have a matching source in our project library for that."
    ]
    if not brief_ready(brief):
        return " ".join(parts)
    if estimate:
        parts.append(
            f"If it helps, a clearly indicative range from the details so far is {estimate['range_label']}. That is not a quote."
        )
    parts.append("The useful next step is a short call with the team so a person can confirm it.")
    return " ".join(parts)
