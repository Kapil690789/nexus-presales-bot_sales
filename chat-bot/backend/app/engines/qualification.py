from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.config_loader.models import QualificationConfig, ServicesConfig


def qualify(
    brief: ProjectBrief,
    qualification: QualificationConfig,
    services: ServicesConfig,
    has_email: bool = False,
) -> dict:
    if brief.out_of_scope or (brief.service and brief.service not in services.in_scope):
        return {
            "score": 0,
            "band": "disqualify",
            "reasons": ["Project is outside the services we take on."],
            "can_book": False,
            "can_estimate": False,
        }
    if brief.decision_role == "intern_or_student" and "intern_or_student" in qualification.disqualify_if:
        return {
            "score": 0,
            "band": "disqualify",
            "reasons": ["We partner with decision-makers on funded product work."],
            "can_book": False,
            "can_estimate": False,
        }

    reasons: list[str] = []
    score = 0
    budget_points = qualification.budget_bands.get(brief.budget_band or "exploring", 5)
    score += budget_points
    if brief.budget_band == "under_15k" and qualification.budget_floor_usd >= 15000:
        if "below_budget_floor" in qualification.disqualify_if:
            return {
                "score": budget_points,
                "band": "disqualify",
                "reasons": [f"Engagements typically start at ${qualification.budget_floor_usd:,}."],
                "can_book": False,
                "can_estimate": False,
            }
    score += qualification.timeline_scores.get(brief.timeline or "unknown", 4)
    score += qualification.decision_role_scores.get(brief.decision_role or "unknown", 6)
    score += qualification.company_size_scores.get(brief.company_size or "unknown", 5)
    if brief.service in services.in_scope:
        score += qualification.weights.get("in_scope", 20)
    score += round(brief.completeness() * qualification.weights.get("completeness", 5))
    score = max(0, min(100, score))

    if score >= qualification.book_threshold:
        band = "hot"
    elif score >= qualification.warm_threshold:
        band = "warm"
    else:
        band = "cold"

    can_estimate = brief_ready(brief) and band != "disqualify"
    can_book = (
        score >= qualification.book_requires.get("min_score", qualification.book_threshold)
        and (has_email or not qualification.book_requires.get("has_email", True))
        and band != "disqualify"
    )
    if band == "hot":
        reasons.append("Strong fit: budget, role, and scope line up.")
    elif band == "warm":
        reasons.append("Promising fit. A strategist should confirm assumptions.")
    else:
        reasons.append("Needs more commercial clarity before a consultation.")
    return {
        "score": score,
        "band": band,
        "reasons": reasons,
        "can_book": can_book,
        "can_estimate": can_estimate,
        "ready": brief_ready(brief),
    }
