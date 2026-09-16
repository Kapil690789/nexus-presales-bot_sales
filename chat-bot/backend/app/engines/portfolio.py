from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.models import PortfolioConfig


def match_portfolio(brief: ProjectBrief, portfolio: PortfolioConfig, limit: int = 3) -> list[dict]:
    scored: list[tuple[int, dict]] = []
    platforms = {item.lower() for item in brief.platforms}
    tags = set()
    if brief.industry:
        tags.add(brief.industry.lower())
    if brief.marketplace:
        tags.add("marketplace")
    if brief.ai_features or brief.service == "ai_product":
        tags.add("ai")
    goal = (brief.goal or "").lower()
    for word in ("marketplace", "saas", "health", "fintech", "onboarding"):
        if word in goal:
            tags.add(word)
    for case in portfolio.cases:
        score = 0
        if brief.service and case.service == brief.service:
            score += 5
        if platforms and platforms.intersection({p.lower() for p in case.platforms}):
            score += 3
        score += 2 * len(tags.intersection({t.lower() for t in case.tags + [case.industry]}))
        if brief.industry and brief.industry.lower() == case.industry.lower():
            score += 3
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
                    "score": score,
                },
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in scored if item[0] > 0][:limit]
    return top or [item[1] for item in scored[:limit]]
