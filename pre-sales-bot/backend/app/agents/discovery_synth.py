from __future__ import annotations

import logging
from typing import Any

from backend.app.agents.brief import ProjectBrief
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.screening.slots import prompt_for
from backend.app.tenants.schema import TenantConfig

log = logging.getLogger(__name__)

GROUNDING_LINE = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)
CONSULT_SYSTEM_PROMPT = (
    "You are an expert enterprise pre-sales software consultant. Output JSON only. "
    + GROUNDING_LINE
)


def synthesize_discovery_prompt(
    config: TenantConfig,
    brief: ProjectBrief,
    field: str | None,
    user_text: str = "",
) -> str:
    """Generate a warm, consultative transition for the next discovery question using Gemini LLM,
    falling back to refined deterministic templates if LLM is unavailable."""
    brand_name = config.brand.name
    fallback = prompt_for(brief, field)

    if not field:
        return fallback

    if not llm_available():
        return _templated_discovery_prompt(brand_name, brief, field)

    captured_summary = []
    if brief.service:
        captured_summary.append(f"Service: {brief.service}")
    if brief.goal:
        captured_summary.append(f"Goal: {brief.goal}")
    if brief.platforms:
        captured_summary.append(f"Platforms: {', '.join(brief.platforms)}")
    if brief.features:
        captured_summary.append(f"Features: {', '.join(brief.features)}")
    if brief.timeline:
        captured_summary.append(f"Timeline: {brief.timeline}")
    if brief.budget_band:
        captured_summary.append(f"Budget: {brief.budget_band}")
    if brief.decision_role:
        captured_summary.append(f"Role: {brief.decision_role}")

    captured_str = "; ".join(captured_summary) if captured_summary else "Initial discovery"

    prompt = (
        f"You are the senior pre-sales software consultant at {brand_name}. "
        f"The client just replied: {wrap_visitor(user_text)}. "
        f"Current captured scope: [{captured_str}]. "
        f"The next information we need to uncover is: '{field}'. "
        f"Standard question for this step: '{fallback}'. "
        f"{UNTRUSTED_RULE} "
        f"Write a polished, consultative reply (1-2 sentences max). "
        f"Briefly acknowledge the client's input with domain expertise, then naturally ask the question for '{field}'. "
        f"Never use technical jargon or acronyms like 'v1'; instead refer to 'initial launch', 'first release', or 'core MVP'. "
        f"Keep the tone professional, consultative, and concise. "
        f'Return JSON {{"message": "..."}}.'
    )

    try:
        data = complete_json(CONSULT_SYSTEM_PROMPT, prompt)
        msg = str(data.get("message") or "").strip()
        if msg and len(msg) > 10:
            return msg
    except LLMError as exc:
        log.info("Discovery prompt synthesis failed, using template: %s", exc)

    return _templated_discovery_prompt(brand_name, brief, field)


def _templated_discovery_prompt(brand_name: str, brief: ProjectBrief, field: str) -> str:
    if field == "goal":
        if brief.service == "web_app":
            return "Got it — custom web application development. What core problem, workflow, or user experience should this first release solve?"
        if brief.service == "mobile_app":
            return "Understood — mobile app engineering. What is the primary purpose and core user experience for this product?"
        if brief.service == "ai_product":
            return "Exciting — an AI-powered product. What specific intelligence, assistant, or automated workflow will this deliver?"
        if brief.service == "ui_ux":
            return "Great — UI/UX product design. What type of product or platform are we designing?"
        return "What core problem or workflow should this first version solve for your users?"

    if field == "platforms":
        return "Which platforms should we target for the initial launch — iOS, Android, Web, or both mobile platforms?"

    if field == "features":
        from backend.app.agents.brief import named_features
        if brief and named_features(brief):
            return prompt_for(brief, field)
        return "Which core features or capabilities are essential for the initial launch?"

    if field == "timeline":
        return "What is your target launch timeline for getting the first version live?"

    if field == "budget_band":
        return "What budget range are you aiming to size this first release against? (This helps us calibrate architecture and squad size; it is an indicative estimate, not a fixed quote)."

    if field == "decision_role":
        return "What is your role on the project (e.g., Founder, Product Lead, Engineering Director)?"

    return prompt_for(brief, field)
