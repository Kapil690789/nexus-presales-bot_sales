from __future__ import annotations

import logging

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.tenants.schema import TenantConfig

log = logging.getLogger(__name__)


def fallback_message(config: TenantConfig, brief: ProjectBrief, estimate: dict | None, query: str = "") -> str:
    name = config.brand.name
    service_labels = [item.label for item in config.services.in_scope.values()] if config.services and config.services.in_scope else ["custom web apps", "mobile apps", "AI solutions"]
    services_str = ", ".join(service_labels[:4])

    if llm_available() and query:
        prompt = (
            f"You are the senior pre-sales software consultant at {name}. "
            f"The visitor asked: {wrap_visitor(query)}. "
            f"We specialize in {services_str}, dedicated agile squads, and bespoke digital products. "
            f"{UNTRUSTED_RULE} "
            f"Write a warm, concise, professional reply (2-3 sentences max). "
            f"Explain how {name} can help with custom software engineering, and invite them to share what kind of product they are looking to build or book a quick call. "
            f"Never make up fake fixed prices or promises not grounded in our scope. "
            f'Return JSON {{"message": "..."}}.'
        )
        try:
            data = complete_json("You are an expert enterprise pre-sales software consultant. Output JSON only.", prompt)
            msg = str(data.get("message") or "").strip()
            if msg:
                if brief_ready(brief) and estimate:
                    msg += f"\n\nBased on the details you've shared so far, an indicative range is **{estimate['range_label']}** (~{estimate['timeline_weeks']} weeks). A short discovery call with our team can confirm the exact scope."
                return msg
        except LLMError as exc:
            log.info("LLM fallback synthesis: %s", exc)

    if not brief_ready(brief):
        return (
            f"I'm {name}'s assistant and pre-sales consultant. We specialize in custom web applications, "
            f"cross-platform mobile apps (iOS & Android), and AI solutions. "
            f"I'd love to learn more about what you're looking to build so we can tailor the right approach."
        )

    parts = []
    if estimate:
        parts.append(
            f"Based on what you've shared, our indicative range is **{estimate['range_label']}** over about {estimate['timeline_weeks']} weeks."
        )
    parts.append("The best next step is a short discovery call with our engineering team to review your specific requirements.")
    return " ".join(parts)
