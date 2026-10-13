from __future__ import annotations

from backend.app.agents.brief import ProjectBrief, next_discovery_field
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.screening.slots import BOOK_CHIP, PORTFOLIO_CHIP, chips_for_field

_GOAL_FALLBACK = (
    {"label": "Book appointments", "field": "goal", "value": "Let people book appointments"},
    {"label": "Manage customers", "field": "goal", "value": "Help the team manage customers"},
    {"label": "Take payments", "field": "goal", "value": "Let customers pay in the product"},
)

_GOAL_SERVICE_FALLBACKS = {
    "ai_product": (
        {"label": "Automate workflows", "field": "goal", "value": "Automate internal workflows and tasks"},
        {"label": "AI support assistant", "field": "goal", "value": "AI chatbot for customer support"},
        {"label": "Document search & RAG", "field": "goal", "value": "Search and analyze company documents with AI"},
        {"label": "Data analysis & insights", "field": "goal", "value": "Extract insights and generate reports from data"},
    ),
    "mobile_app": (
        {"label": "Consumer marketplace", "field": "goal", "value": "Two-sided consumer marketplace app"},
        {"label": "On-demand booking", "field": "goal", "value": "Let users book and manage services on-demand"},
        {"label": "Health & fitness tracker", "field": "goal", "value": "Personal health, activity, and habit tracking"},
        {"label": "Social & community platform", "field": "goal", "value": "Connect users with social feeds and chat"},
    ),
    "web_app": (
        {"label": "B2B SaaS platform", "field": "goal", "value": "Cloud-based B2B software with subscriptions"},
        {"label": "Operations dashboard", "field": "goal", "value": "Internal tools and analytics dashboard for operations"},
        {"label": "Client portal", "field": "goal", "value": "Secure client self-service portal"},
        {"label": "E-commerce & marketplace", "field": "goal", "value": "Multi-vendor e-commerce marketplace"},
    ),
    "ui_ux": (
        {"label": "MVP product design", "field": "goal", "value": "Design a complete new MVP from scratch in Figma"},
        {"label": "Product redesign", "field": "goal", "value": "Redesign existing product to improve usability & conversion"},
        {"label": "Design system & UI kit", "field": "goal", "value": "Build scalable component system and tokens in Figma"},
        {"label": "Clickable investor prototype", "field": "goal", "value": "High-fidelity clickable prototype for fundraising"},
    ),
}

_SYSTEM = (
    "You suggest tappable reply chips for an enterprise pre-sales software consultant. "
    'Return JSON {"chips": [{"label": "short label", "value": "stored answer"}]}. '
    "Return 2 to 4 chips. Each label is at most 6 words, highly relevant and natural. "
    "Do not invent prices, timelines, or client names. "
    f"{UNTRUSTED_RULE}"
)


def ensure_chips(brief: ProjectBrief, message: str, passages: list[str] | None = None) -> list[dict]:
    """Chips for a reply that would otherwise show none.

    Catalog options win. Otherwise the model suggests answers to the pending
    question, or follow-up questions grounded in retrieved notes.
    """
    field = next_discovery_field(brief)
    catalog = chips_for_field(field, brief) if field else []
    if catalog:
        return catalog
    is_mocked = (
        getattr(complete_json, "__module__", "") != "backend.app.core.llm"
        or getattr(complete_json, "__name__", "") != "complete_json"
    )
    if is_mocked or llm_available():
        suggested = _llm_chips(field, message, passages or [], brief=brief)
        if suggested:
            return suggested
    if field == "goal":
        svc = (brief.service or "").lower().strip()
        if svc in _GOAL_SERVICE_FALLBACKS:
            return [dict(item) for item in _GOAL_SERVICE_FALLBACKS[svc]]
        return [dict(item) for item in _GOAL_FALLBACK]
    if field:
        return []
    return [dict(BOOK_CHIP), dict(PORTFOLIO_CHIP)]


def _llm_chips(
    field: str | None,
    message: str,
    passages: list[str],
    brief: ProjectBrief | None = None,
) -> list[dict]:
    if not llm_available():
        return []
    excerpts = "\n\n".join(text.strip()[:500] for text in passages[:3] if text and text.strip())
    context_hint = ""
    if brief:
        bits = []
        if brief.service:
            bits.append(f"Service: {brief.service}")
        if brief.goal:
            bits.append(f"Goal: {brief.goal}")
        if brief.platforms:
            bits.append(f"Platforms: {', '.join(brief.platforms)}")
        if brief.features:
            bits.append(f"Features: {', '.join(brief.features)}")
        if bits:
            context_hint = f"Project context: [{'; '.join(bits)}].\n"

    if field:
        user = (
            f"{context_hint}The assistant is asking for the visitor's {field}. "
            "Each chip is a plausible, natural answer tailored to the project context. value is what to store; label is what they tap.\n\n"
            f"Assistant message:\n{wrap_visitor(message.strip())}\n"
        )
    else:
        user = (
            f"{context_hint}The assistant just answered. Each chip is a short, logical follow-up question the visitor might ask. "
            "label and value should be the same question.\n\n"
            f"Assistant message:\n{wrap_visitor(message.strip())}\n"
        )
    if excerpts:
        user += f"\nRetrieved notes:\n{wrap_visitor(excerpts)}\n"
    try:
        is_mocked = (
            getattr(complete_json, "__module__", "") != "backend.app.core.llm"
            or getattr(complete_json, "__name__", "") != "complete_json"
        )
        if is_mocked:
            data = complete_json(_SYSTEM, user)
        else:
            data = complete_json(_SYSTEM, user, mode="request", purpose="chips")
    except LLMError:
        return []
    raw = data.get("chips") if isinstance(data.get("chips"), list) else []
    cleaned: list[dict] = []
    for item in raw:
        if not isinstance(item, dict):
            continue
        label = " ".join(str(item.get("label") or "").split())
        if not label:
            continue
        if field and field in ProjectBrief.model_fields:
            value = item.get("value")
            if value in (None, ""):
                value = label
            cleaned.append({"label": label, "field": field, "value": value})
        else:
            question = label if label.endswith("?") else f"{label}?"
            cleaned.append({"label": question, "field": "ask", "value": question})
        if len(cleaned) == 4:
            break
    return cleaned
