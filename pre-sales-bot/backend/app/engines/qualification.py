from __future__ import annotations

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.tenants.schema import QualificationConfig, ServicesConfig


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
    score = 0
    score += qualification.budget_bands.get(brief.budget_band or "exploring", 5)
    if brief.budget_band == "under_15k" and qualification.budget_floor_usd >= 15000:
        if "below_budget_floor" in qualification.disqualify_if:
            return {
                "score": score,
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
    can_estimate = brief_ready(brief)
    requires = qualification.book_requires or {}
    can_book = score >= int(requires.get("min_score", qualification.book_threshold)) and (
        has_email or not bool(requires.get("has_email", True))
    )
    bant = {
        "budget": {
            "value": brief.budget_band or "exploring",
            "fit": "high" if brief.budget_band in ("40_80k", "80k_plus") else ("medium" if brief.budget_band == "15_40k" else "exploring"),
            "score": qualification.budget_bands.get(brief.budget_band or "exploring", 5),
        },
        "authority": {
            "value": brief.decision_role or "unknown",
            "fit": "direct" if brief.decision_role in ("founder_or_exec", "product_or_ops_lead") else "evaluating",
            "score": qualification.decision_role_scores.get(brief.decision_role or "unknown", 6),
        },
        "need": {
            "service": brief.service or "custom_software",
            "features_count": len(brief.features or []),
            "fit": "clear" if brief.goal and brief.features else "early_concept",
        },
        "timing": {
            "value": brief.timeline or "flexible",
            "urgency": "urgent" if brief.timeline == "asap" else ("planned" if brief.timeline in ("1_3_months", "3_6_months") else "flexible"),
            "score": qualification.timeline_scores.get(brief.timeline or "unknown", 4),
        },
    }
    if band == "hot":
        reasons = [
            "Strong fit: budget, role, and scope line up.",
            f"BANT Breakdown: Budget={brief.budget_band or 'exploring'} | Role={brief.decision_role or 'founder_or_exec'} | Timeline={brief.timeline or 'flexible'}"
        ]
    elif band == "warm":
        reasons = [
            "Promising fit. A strategist should confirm assumptions.",
            f"BANT Breakdown: Budget={brief.budget_band or 'exploring'} | Role={brief.decision_role or 'unknown'} | Timeline={brief.timeline or 'flexible'}"
        ]
    else:
        reasons = ["Needs more commercial clarity before a consultation."]
    return {
        "score": score,
        "band": band,
        "reasons": reasons,
        "bant": bant,
        "can_book": can_book,
        "can_estimate": can_estimate,
        "ready": brief_ready(brief),
    }
