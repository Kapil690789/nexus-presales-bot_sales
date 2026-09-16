from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.agents.chips import DISCOVERY_PROMPTS, chips_for
from backend.app.config_loader.loader import AppConfig
from backend.app.engines.calendar import slot_chips


def _post_estimate_chips() -> list[dict]:
    return [
        {"label": "Show MVP cut", "field": "show_mvp", "value": "yes"},
        {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
        {"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
    ]


def fallback_reply(
    *,
    stage: str,
    brief: ProjectBrief,
    opening: str | None = None,
    extra_questions: list[str] | None = None,
    qualification: dict | None = None,
    estimate: dict | None = None,
    architecture: dict | None = None,
    mvp: dict | None = None,
    portfolio: list[dict] | None = None,
    objection: dict | None = None,
    config: AppConfig,
    user_text: str = "",
    booking: dict | None = None,
) -> dict:
    if stage == "greeting":
        extras = extra_questions or []
        message = opening or config.pages.default.opening
        if extras:
            message = f"{message.strip()}\n\n{extras[0]}"
        return {"message": message.strip(), "chips": chips_for(brief, "discovery"), "stage": "discovery"}
    if stage == "disqualified":
        return {"message": config.agency.out_of_scope_close.strip(), "chips": [], "stage": "disqualified"}
    if stage == "objections" and objection:
        return {"message": objection["reply"], "chips": chips_for(brief, "discovery"), "stage": "objections"}
    if stage == "rfp_review":
        bits = []
        if brief.goal:
            bits.append(f"Goal: {brief.goal}")
        if brief.service:
            bits.append(f"Service: {brief.service}")
        if brief.platforms:
            bits.append("Platforms: " + ", ".join(brief.platforms))
        missing = brief.missing_discovery()
        ask = DISCOVERY_PROMPTS.get(missing[0], "What should we confirm next?") if missing else "Shall I estimate this?"
        return {
            "message": f"I treated the upload as untrusted source material and extracted this:\n{'; '.join(bits) or 'I pulled the document in.'}\n\n{ask}",
            "chips": chips_for(brief, "discovery"),
            "stage": "rfp_review",
        }
    if stage == "discovery":
        missing = brief.missing_discovery()
        if missing:
            field = missing[0]
        elif not brief.company_size:
            field = "company_size"
        else:
            field = "goal"
        preface = "Noted. " if user_text and brief.goal and field != "goal" else ""
        return {"message": f"{preface}{DISCOVERY_PROMPTS[field]}", "chips": chips_for(brief, "discovery"), "stage": "discovery"}
    if stage == "estimation" and estimate:
        arch = architecture or {}
        stacks = ", ".join((arch.get("frontend") or []) + (arch.get("backend") or [])) or "an approved stack"
        return {
            "message": (
                f"Based on what you've shared, an indicative MVP sits around **{estimate['range_label']}** "
                f"over about **{estimate['timeline_weeks']} weeks** with {', '.join(estimate['team'][:3])}. "
                f"I'd start on {stacks}. This is a low-side first pass — {config.agency.disclaimer.strip()}"
            ),
            "chips": _post_estimate_chips(),
            "stage": "estimation",
        }
    if stage == "solutioning" and mvp:
        items = "\n".join(f"- {row}" for row in mvp.get("mvp", [])[:4])
        later = "\n".join(f"- {row}" for row in mvp.get("later", [])[:3])
        return {
            "message": f"**MVP I'd protect**\n{items}\n\n**Later**\n{later}\n\nWant a couple of relevant case studies?",
            "chips": [
                {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
                {"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
            ],
            "stage": "solutioning",
        }
    if stage == "portfolio" and portfolio:
        titles = ", ".join(item["title"] for item in portfolio[:2])
        return {
            "message": f"Closest work: {titles}. These are studio examples. Share a work email and I'll package the brief, range, and these references.",
            "chips": [{"label": "Continue to contact", "field": "continue_contact", "value": "yes"}],
            "stage": "capture",
        }
    if stage == "capture":
        return {"message": "What work email should I attach this discovery pack to?", "chips": [], "stage": "capture"}
    if stage == "booking":
        score = (qualification or {}).get("score")
        extra = f" (fit score {score})" if score is not None else ""
        window = (booking or {}).get("window") or "this_week"
        return {
            "message": f"You're in a good place for a consultation{extra}. Pick a time — these are dummy slots, not a live calendar.",
            "chips": chips_for(brief, "booking") if window == "this_week" else slot_chips(window),
            "stage": "booking",
        }
    if stage == "handoff":
        return {
            "message": "I have enough to brief the team. You'll get a discovery summary — problem, range, stack, MVP cut, and matching work. A human takes it from here.",
            "chips": [],
            "stage": "handoff",
        }
    if brief_ready(brief):
        return {"message": "I have enough to run a first-pass estimate. One moment.", "chips": [], "stage": "qualification"}
    return {
        "message": DISCOVERY_PROMPTS[brief.missing_discovery()[0]],
        "chips": chips_for(brief, "discovery"),
        "stage": "discovery",
    }
