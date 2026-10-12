from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.tenants.schema import PortfolioConfig


def match_portfolio(brief: ProjectBrief, portfolio: PortfolioConfig, limit: int = 3) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    platforms = {item.lower() for item in brief.platforms}

    inferred_industry = (brief.industry or "").lower().strip()
    full_text_context = " ".join(
        filter(None, [
            brief.goal or "",
            brief.industry or "",
            " ".join(brief.features or []),
            " ".join(brief.ai_features or []),
        ])
    ).lower()

    if not inferred_industry and full_text_context:
        if any(w in full_text_context for w in ("deliver", "delivery", "food", "grocery", "courier", "logistics", "zepto", "blinkit", "uber", "taxi")):
            inferred_industry = "logistics"
        elif any(w in full_text_context for w in ("health", "clinic", "doctor", "patient", "medical", "telemedicine", "hospital", "prescription")):
            inferred_industry = "health"
        elif any(w in full_text_context for w in ("fintech", "finance", "bank", "wallet", "crypto", "payment", "ledger", "invoice", "accounting")):
            inferred_industry = "fintech"
        elif any(w in full_text_context for w in ("shop", "ecommerce", "e-commerce", "retail", "store", "cart", "checkout")):
            inferred_industry = "ecommerce"
        elif any(w in full_text_context for w in ("fitness", "workout", "gym", "habit", "exercise", "wellness")):
            inferred_industry = "fitness"
        elif any(w in full_text_context for w in ("social", "community", "chat", "creator", "feed", "dating")):
            inferred_industry = "social"
        elif any(w in full_text_context for w in ("ai", "llm", "rag", "bot", "assistant", "document")):
            inferred_industry = "ai"
        elif any(w in full_text_context for w in ("marketplace", "buyer", "seller", "two-sided", "farm")):
            inferred_industry = "marketplace"
        elif any(w in full_text_context for w in ("saas", "dashboard", "b2b", "portal", "ops", "admin")):
            inferred_industry = "saas"
        elif any(w in full_text_context for w in ("design", "figma", "ui", "ux", "prototype")):
            inferred_industry = "b2b"

    for case in portfolio.cases:
        score = 0.0
        if brief.service and case.service == brief.service:
            score += 5.0
        if platforms and platforms.intersection({item.lower() for item in case.platforms}):
            score += 3.0
        if inferred_industry and (case.industry.lower() == inferred_industry or inferred_industry in [t.lower() for t in case.tags]):
            score += 8.0
        for tag in case.tags + [case.industry]:
            if tag and tag.lower() in full_text_context:
                score += 4.0
        case_words = set(case.title.lower().split() + case.outcome.lower().split())
        for token in full_text_context.split():
            if len(token) >= 4 and token in case_words:
                score += 2.0

        scored.append(
            (
                score,
                {
                    "id": case.id,
                    "title": case.title,
                    "industry": case.industry,
                    "outcome": case.outcome,
                    "url": case.url,
                    "stacks": case.stacks,
                },
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in scored if item[0] > 0][:limit]
    return top or [item[1] for item in scored[:limit]]
