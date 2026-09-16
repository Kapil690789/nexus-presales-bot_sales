from backend.app.agents.brief import ProjectBrief, brief_tags
from backend.app.config_loader.models import PortfolioConfig, RagConfig
from backend.app.rag.learn import OUTCOME_PORTFOLIO, win_rates
from backend.app.rag.retrieve import rag_enabled, semantic_case_scores

# Keyword agreement is scored in whole points, so this weight is sized to break ties
# rather than override a service match.
SEMANTIC_WEIGHT = 4.0


def match_portfolio(
    brief: ProjectBrief,
    portfolio: PortfolioConfig,
    limit: int = 3,
    *,
    db=None,
    rag: RagConfig | None = None,
) -> list[dict]:
    """Rank case studies by metadata agreement, semantic similarity, and track record.

    Without a session (``db is None``) this stays pure keyword matching.
    """
    scored: list[tuple[float, dict]] = []
    platforms = {item.lower() for item in brief.platforms}
    tags = brief_tags(brief)
    semantic = _semantic(brief, db, rag)
    wins = _win_rates(db, rag)
    boost_weight = rag.learning.outcome_boost if rag else 0.0
    for case in portfolio.cases:
        score = 0.0
        if brief.service and case.service == brief.service:
            score += 5
        if platforms and platforms.intersection({p.lower() for p in case.platforms}):
            score += 3
        score += 2 * len(tags.intersection({t.lower() for t in case.tags + [case.industry]}))
        if brief.industry and brief.industry.lower() == case.industry.lower():
            score += 3
        keyword_score = score
        score += SEMANTIC_WEIGHT * semantic.get(case.id, 0.0)
        score += boost_weight * wins.get(case.id, 0.0)
        scored.append(
            (
                round(score, 3),
                {
                    "id": case.id,
                    "title": case.title,
                    "industry": case.industry,
                    "outcome": case.outcome,
                    "url": case.url,
                    "stacks": case.stacks,
                    "score": round(score, 3),
                    "keyword_score": keyword_score,
                    "win_rate": round(wins.get(case.id, 0.0), 3),
                },
            )
        )
    scored.sort(key=lambda item: item[0], reverse=True)
    top = [item[1] for item in scored if item[0] > 0][:limit]
    return top or [item[1] for item in scored[:limit]]


def _semantic(brief: ProjectBrief, db, rag: RagConfig | None) -> dict[str, float]:
    if db is None or rag is None:
        return {}
    return semantic_case_scores(db, brief, rag)


def _win_rates(db, rag: RagConfig | None) -> dict[str, float]:
    if db is None or rag is None or not rag.learning.enabled or not rag_enabled():
        return {}
    try:
        return win_rates(db, OUTCOME_PORTFOLIO, rag.learning.outcome_prior)
    except Exception:
        return {}
