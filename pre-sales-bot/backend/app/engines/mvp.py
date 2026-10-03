from __future__ import annotations

from backend.app.agents.brief import ProjectBrief

PHASE_TEMPLATES = {
    "mobile_app": {
        "mvp": [
            "Primary user journey on the agreed platforms",
            "Account creation and basic profile",
            "Core object with create and list",
            "Notification for the one critical event",
        ],
        "later": ["Secondary platform polish", "Growth loops", "Advanced search or offline mode"],
    },
    "web_app": {
        "mvp": [
            "Authenticated web app for the primary role",
            "One operational workflow end to end",
            "Basic admin to unblock the operator",
        ],
        "later": ["Additional roles", "Reporting suite", "Further integrations"],
    },
    "ai_product": {
        "mvp": [
            "One assistant job with a clear success metric",
            "Document grounding for that job only",
            "Human review path for bad answers",
        ],
        "later": ["Broader workflows", "Eval harness", "Embedded widget"],
    },
    "ui_ux": {
        "mvp": ["Problem framing", "Key flows in high fidelity", "Component foundations"],
        "later": ["Full design system", "Usability testing on a live build"],
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
    named = [item.strip() for item in (brief.features or []) if item.strip()]
    if named:
        mvp[1:1] = [f"Core: {item}" for item in named[:4]]
    if brief.integrations:
        keep = [item for item in brief.integrations if item.lower() not in {"none", "no", "n/a"}]
        if keep:
            mvp.append(f"Integrate {', '.join(keep[:3])} only")
    tight = brief.budget_band in {"under_15k", "exploring"}
    if tight and len(mvp) > 3:
        later = mvp[3:] + later
        mvp = mvp[:3]
        rationale = "Budget is tight, so the first release stays thin."
    else:
        rationale = "Ship the smallest product that can win the first users."
    shown = mvp[:5]
    detail = (brief.feature_detail or "").strip()
    if detail and detail not in {"not_specified", "skipped"}:
        shown.append(f"As described: {detail[:160]}")
    return {"mvp": shown[:6], "later": later[:6], "rationale": rationale}
