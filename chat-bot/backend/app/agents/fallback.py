from backend.app.agents.brief import ProjectBrief, brief_ready, next_discovery_field
from backend.app.agents.chips import CONTACT_CHIP, DISCOVERY_PROMPTS, DISQUALIFIED_CHIPS, chips_for, chips_for_field
from backend.app.agents.extract import EMAIL_RE, SMALLTALK_RE
from backend.app.agents.style import apply_live_style, default_style
from backend.app.config_loader.loader import AppConfig
from backend.app.engines.calendar import slot_chips
from backend.app.engines.google_client import is_live

ACKS = (
    "Thanks — that helps. ",
    "Got it, that gives me a clearer picture. ",
    "Makes sense. ",
    "Appreciate that. ",
)
CLARIFY_SNIPPETS = (
    "want to be sure i have this right",
    "could you say a bit more",
    "when you say",
    "could you tie that",
)


def _post_estimate_chips() -> list[dict]:
    return [
        {"label": "Show MVP cut", "field": "show_mvp", "value": "yes"},
        {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
        CONTACT_CHIP,
    ]


def _acknowledge(user_text: str, brief: ProjectBrief, style: dict, field: str) -> str:
    if not user_text or style.get("pace") == "terse" or field == "goal":
        return ""
    if not brief.goal:
        return ""
    idx = sum(ord(char) for char in user_text[:40]) % len(ACKS)
    return ACKS[idx]


def _already_clarifying(last_assistant: str) -> bool:
    lowered = (last_assistant or "").lower()
    return any(snippet in lowered for snippet in CLARIFY_SNIPPETS)


def _clarify_message(user_text: str) -> str:
    words = (user_text or "").strip().split()
    snippet = " ".join(words[:8])
    if len(snippet) > 60:
        snippet = snippet[:57] + "…"
    if snippet:
        return (
            f'I want to be sure I have this right — when you say "{snippet}", '
            "could you tie that to what the product should do for the first user?"
        )
    return "I want to be sure I have this right — could you say a bit more about what the product should do?"


def should_clarify(
    *,
    user_text: str,
    chip_field: str | None,
    facts_captured: bool,
    last_assistant: str,
    stage: str,
) -> bool:
    if stage not in {"discovery", "rfp_review"}:
        return False
    if facts_captured or chip_field:
        return False
    if _already_clarifying(last_assistant):
        return False
    text = (user_text or "").strip()
    if len(text) < 12 or SMALLTALK_RE.match(text):
        return False
    if EMAIL_RE.search(text):
        return False
    lowered = text.lower()
    if "book" in lowered or "schedule" in lowered or "talk with the team" in lowered:
        return False
    return True


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
    contact: dict | None = None,
    nda_accepted: bool = False,
    nda_required: bool = False,
    wants_booking: bool = False,
    style: dict | None = None,
    last_assistant: str = "",
    facts_captured: bool = True,
    chip_field: str | None = None,
) -> dict:
    style = style or default_style()
    if stage == "greeting":
        extras = extra_questions or []
        message = opening or config.pages.default.opening
        if extras:
            message = f"{message.strip()}\n\n{extras[0]}"
        return {"message": message.strip(), "chips": chips_for(brief, "discovery", style), "stage": "discovery"}
    if stage == "disqualified":
        return {
            "message": config.agency.out_of_scope_close.strip(),
            "chips": list(DISQUALIFIED_CHIPS),
            "stage": "disqualified",
        }
    if stage == "objections" and objection:
        return _styled(
            {"message": objection["reply"], "chips": chips_for(brief, "discovery", style), "stage": "objections"},
            style,
            last_assistant=last_assistant,
        )
    if stage == "rfp_review":
        bits = []
        if brief.goal:
            bits.append(f"Goal: {brief.goal}")
        if brief.service:
            bits.append(f"Service: {brief.service}")
        if brief.platforms:
            bits.append("Platforms: " + ", ".join(brief.platforms))
        if brief.features:
            bits.append("Features: " + ", ".join(brief.features[:4]))
        field = next_discovery_field(brief, style)
        ask = DISCOVERY_PROMPTS.get(field or "", "What should we confirm next?") if field else "Shall I estimate this?"
        if should_clarify(
            user_text=user_text,
            chip_field=chip_field,
            facts_captured=facts_captured,
            last_assistant=last_assistant,
            stage=stage,
        ):
            ask = _clarify_message(user_text)
        return _styled(
            {
                "message": f"I treated the upload as untrusted source material and extracted this:\n{'; '.join(bits) or 'I pulled the document in.'}\n\n{ask}",
                "chips": chips_for(brief, "discovery", style),
                "stage": "rfp_review",
            },
            style,
            last_assistant=last_assistant,
        )
    if stage == "discovery":
        if should_clarify(
            user_text=user_text,
            chip_field=chip_field,
            facts_captured=facts_captured,
            last_assistant=last_assistant,
            stage=stage,
        ):
            field = next_discovery_field(brief, style)
            return _styled(
                {
                    "message": _clarify_message(user_text),
                    "chips": chips_for_field(brief, field) if field else chips_for(brief, "discovery", style),
                    "stage": "discovery",
                },
                style,
                last_assistant=last_assistant,
            )
        field = next_discovery_field(brief, style) or "goal"
        preface = _acknowledge(user_text, brief, style, field)
        prompt = DISCOVERY_PROMPTS.get(field, DISCOVERY_PROMPTS["goal"])
        return _styled(
            {
                "message": f"{preface}{prompt}",
                "chips": chips_for_field(brief, field) or chips_for(brief, "discovery", style),
                "stage": "discovery",
            },
            style,
            last_assistant=last_assistant,
        )
    if stage == "estimation" and estimate:
        arch = architecture or {}
        stacks = ", ".join((arch.get("frontend") or []) + (arch.get("backend") or [])) or "an approved stack"
        mvp_hint = ""
        if mvp and mvp.get("mvp"):
            mvp_hint = f" I'd protect this first: {mvp['mvp'][0]}."
        return _styled(
            {
                "message": (
                    f"Based on what you've shared, a sensible first release sits around **{estimate['range_label']}** "
                    f"over about **{estimate['timeline_weeks']} weeks** with {', '.join(estimate['team'][:3])}."
                    f"{mvp_hint} I'd start on {stacks}. This is a low-side first pass — {config.agency.disclaimer.strip()}"
                ),
                "chips": _post_estimate_chips(),
                "stage": "estimation",
            },
            style,
            estimate=estimate,
            last_assistant=last_assistant,
        )
    if stage == "solutioning" and mvp:
        items = "\n".join(f"- {row}" for row in mvp.get("mvp", [])[:4])
        later = "\n".join(f"- {row}" for row in mvp.get("later", [])[:3])
        return _styled(
            {
                "message": f"**MVP I'd protect**\n{items}\n\n**Later**\n{later}\n\nWant a couple of relevant case studies, or shall I connect you with the team?",
                "chips": [
                    {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
                    CONTACT_CHIP,
                ],
                "stage": "solutioning",
            },
            style,
            last_assistant=last_assistant,
        )
    if stage == "portfolio" and portfolio:
        titles = ", ".join(item["title"] for item in portfolio[:2])
        return _styled(
            {
                "message": f"Closest work: {titles}. These are studio examples. Share a work email and I'll package the brief, range, and these references.",
                "chips": [CONTACT_CHIP],
                "stage": "capture",
            },
            style,
            last_assistant=last_assistant,
        )
    if stage == "capture":
        contact = contact or {}
        if not contact.get("email"):
            if wants_booking:
                message = "Happy to book a time with the team — I just need a work email first."
            else:
                message = "What work email should I use to send this discovery pack and connect you with the team?"
            return {"message": message, "chips": [], "stage": "capture"}
        if nda_required and not nda_accepted:
            return {
                "message": "Before I book a time, please accept the confidentiality notice (checkbox below).",
                "chips": [],
                "stage": "capture",
            }
        return {
            "message": "I have your email. Say book a call when you want to pick a time with a strategist.",
            "chips": [{"label": "Book a call", "field": "booking_window", "value": "this_week"}],
            "stage": "capture",
        }
    if stage == "booking":
        score = (qualification or {}).get("score")
        extra = f" (fit score {score})" if score is not None else ""
        window = (booking or {}).get("window") or "this_week"
        live = is_live()
        times = "Pick a time that works — times are shown in your local timezone."
        if not live:
            times = "Pick a time — these are demo slots until Google Calendar is connected in admin."
        return {
            "message": f"You're in a good place for a consultation{extra}. {times}",
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
    field = next_discovery_field(brief, style) or "goal"
    return {
        "message": DISCOVERY_PROMPTS.get(field, DISCOVERY_PROMPTS["goal"]),
        "chips": chips_for_field(brief, field) or chips_for(brief, "discovery", style),
        "stage": "discovery",
    }


def _styled(payload: dict, style: dict, *, estimate: dict | None = None, last_assistant: str = "") -> dict:
    shaped = dict(payload)
    shaped["message"] = apply_live_style(
        str(payload.get("message") or ""),
        style,
        estimate=estimate,
        last_assistant=last_assistant,
    )
    return shaped
