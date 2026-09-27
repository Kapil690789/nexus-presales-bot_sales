from __future__ import annotations

from backend.app.agents.brief import ProjectBrief, next_discovery_field
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.screening.slots import BOOK_CHIP, PORTFOLIO_CHIP, chips_for_field

_SYSTEM = (
    "You suggest tappable reply chips for a pre-sales consultant. "
    'Return JSON {"chips": [{"label": "short label", "value": "stored answer"}]}. '
    "Return 2 to 4 chips. Each label is at most 6 words. "
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
    suggested = _llm_chips(field, message, passages or [])
    if suggested:
        return suggested
    return [dict(BOOK_CHIP), dict(PORTFOLIO_CHIP)]


def _llm_chips(field: str | None, message: str, passages: list[str]) -> list[dict]:
    if not llm_available():
        return []
    excerpts = "\n\n".join(text.strip()[:500] for text in passages[:3] if text and text.strip())
    if field:
        user = (
            f"The assistant is asking for the visitor's {field}. "
            "Each chip is a plausible answer. value is what to store; label is what they tap.\n\n"
            f"Assistant message:\n{wrap_visitor(message.strip())}\n"
        )
    else:
        user = (
            "The assistant just answered. Each chip is a short follow-up question the visitor might ask. "
            "label and value should be the same question.\n\n"
            f"Assistant message:\n{wrap_visitor(message.strip())}\n"
        )
    if excerpts:
        user += f"\nRetrieved notes:\n{wrap_visitor(excerpts)}\n"
    try:
        data = complete_json(_SYSTEM, user)
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
