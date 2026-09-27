from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.tenants.schema import PortfolioConfig


def match_portfolio(brief: ProjectBrief, portfolio: PortfolioConfig, limit: int = 3) -> list[dict]:
    scored: list[tuple[float, dict]] = []
    platforms = {item.lower() for item in brief.platforms}
    for case in portfolio.cases:
        score = 0.0
        if brief.service and case.service == brief.service:
            score += 5
        if platforms and platforms.intersection({item.lower() for item in case.platforms}):
            score += 3
        if brief.industry and brief.industry.lower() == case.industry.lower():
            score += 3
        haystack = " ".join([brief.goal or "", brief.industry or ""]).lower()
        for tag in case.tags + [case.industry]:
            if tag and tag.lower() in haystack:
                score += 2
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
