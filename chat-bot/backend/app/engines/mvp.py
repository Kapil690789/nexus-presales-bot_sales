from backend.app.agents.brief import ProjectBrief

PHASE_TEMPLATES = {
    "mobile_app": {
        "mvp": [
            "Primary user journey on one or both agreed platforms",
            "Account creation and basic profile",
            "Core object (listing, booking, or feed) with create + list",
            "Push or email notification for the one critical event",
        ],
        "later": ["Secondary platform polish and tablet layouts", "Loyalty, referrals, or growth loops", "Advanced search, recommendations, or offline mode"],
    },
    "web_app": {
        "mvp": [
            "Authenticated web app for the primary role",
            "One operational workflow end to end",
            "Basic admin to unblock the operator",
            "Transactional email for the critical event",
        ],
        "later": ["Additional roles and permission matrices", "Reporting suite and exports", "Integrations beyond the first two systems"],
    },
    "ai_product": {
        "mvp": [
            "One assistant job with a clear success metric",
            "Document or API grounding for that job only",
            "Human review path for bad answers",
            "Audit log of prompts and outputs",
        ],
        "later": ["Multi-agent workflows", "Fine-tuning or eval harness at scale", "Embedded widget in a third-party product"],
    },
    "ui_ux": {
        "mvp": ["Research synthesis and problem framing", "Key flows in high fidelity", "Component foundations for engineering"],
        "later": ["Full design system", "Motion and marketing site", "Usability testing on a live build"],
    },
    "staff_augmentation": {
        "mvp": ["Named specialist embedded in your cadence", "First 30-day outcome agreed in writing"],
        "later": ["Additional roles once the first seat is productive"],
    },
}


def recommend_mvp(brief: ProjectBrief) -> dict:
    template = PHASE_TEMPLATES.get(brief.service or "", PHASE_TEMPLATES["web_app"])
    mvp, later = list(template["mvp"]), list(template["later"])
    if brief.goal:
        mvp.insert(0, f"Prove this outcome: {brief.goal}")
    if brief.integrations:
        named = [item for item in brief.integrations if item.lower() not in {"none", "no", "n/a"}]
        if named:
            mvp.append(f"Integrate {', '.join(named[:3])} only — everything else waits")
            later.append("Further third-party integrations")
    if brief.marketplace:
        mvp.append("Two-sided happy path: one buyer action and one seller action")
        later.append("Trust & safety, disputes, and promotions")
    if brief.constraints:
        mvp.append(f"Respect: {brief.constraints[0][:160]}")
    tight = brief.budget_band in {"under_15k", "exploring"}
    if tight and len(mvp) > 3:
        later = mvp[3:] + later
        mvp = mvp[:3]
        rationale = "Budget is tight — protect a thinner first release and sequence the rest."
    else:
        rationale = "Ship the smallest product that can win the first users, then sequence the rest."
    return {
        "mvp": mvp[:6],
        "later": later[:6],
        "rationale": rationale,
    }
