from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.agents.brief import FLOW_SKIPPED, ProjectBrief, brief_ready, engine_gaps, next_discovery_field
from backend.app.agents.chips import ACTION_CHIP_FIELDS, DISCOVERY_PROMPTS, DISQUALIFIED_CHIPS, chips_for, chips_for_field
from backend.app.agents.extract import (
    apply_architecture,
    apply_brief_updates,
    apply_mvp,
    apply_payload,
    capture_features_reply,
    capture_goal_reply,
    capture_user_flow_reply,
    extract_contact,
)
from backend.app.agents.style import apply_live_style, default_style, detect_style, overlay_llm, prior_style_for_email
from backend.app.documents.rfp import extract_rfp
from backend.app.agents.fallback import fallback_reply
from backend.app.config_loader.loader import AppConfig
from backend.app.core.guard import sanitize_reply
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.objections import match_objection
from backend.app.engines.calendar import booking_card, confirm_slot, slot_chips
from backend.app.engines.google_client import CalendarError
from backend.app.engines.followup import render_followup
from backend.app.engines.portfolio import match_portfolio
from backend.app.engines.pricing import estimate_project
from backend.app.engines.qualification import qualify
from backend.app.rag.retrieve import render_snippets, retrieve_knowledge, retrieve_lessons, retrieve_solution

log = logging.getLogger(__name__)
THANKS_RE = re.compile(r"^(thanks|thank you|thx|cheers)[\s!.]*$", re.I)
BOOK_INTENT_RE = re.compile(
    r"\b("
    r"book(?:\s+(?:a|me\s+a))?\s+(?:call|slot|meeting|consultation)"
    r"|schedule(?:\s+a)?\s+(?:call|meeting|consultation|time)"
    r"|continue to contact"
    r"|talk with the team"
    r")\b",
    re.I,
)


def _looks_like_thanks(text: str) -> bool:
    return bool(THANKS_RE.match((text or "").strip()))


def _wants_booking(user_text: str, chip_field: str | None) -> bool:
    if chip_field in {"continue_contact", "booking_window", "booking_slot"}:
        return True
    return bool(BOOK_INTENT_RE.search(user_text or ""))


class TurnResult:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def build_handoff_summary(
    brief: ProjectBrief,
    qualification: dict | None,
    estimate: dict | None,
    architecture: dict | None,
    mvp: dict | None,
    portfolio: list[dict] | None,
    contact: dict[str, str],
    config: AppConfig,
) -> str:
    lines = [
        f"# Discovery summary — {config.agency.name}",
        "",
        "## Snapshot",
        f"- Contact: {contact.get('email') or 'not captured'} {contact.get('phone') or ''}".strip(),
        f"- Service: {brief.service or 'unspecified'}",
        f"- Goal: {brief.goal or '—'}",
        f"- Score: {(qualification or {}).get('score', '—')} ({(qualification or {}).get('band', '—')})",
    ]
    if brief.features:
        lines.append(f"- Features: {', '.join(brief.features)}")
    elif brief.features == []:
        lines.append("- Features: not specified")
    if brief.user_flow and brief.user_flow != FLOW_SKIPPED:
        lines.append(f"- User flow: {brief.user_flow}")
    if estimate:
        lines += [
            "",
            "## Indicative estimate",
            f"- Range: {estimate['range_label']}",
            f"- Timeline: {estimate['timeline_weeks']} weeks",
            f"- Team: {', '.join(estimate['team'])}",
            f"- Disclaimer: {config.agency.disclaimer.strip()}",
        ]
    lines += [
        "",
        "## Brief",
        f"- Platforms: {', '.join(brief.platforms) or '—'}",
        f"- Users: {brief.users or '—'}",
        f"- Integrations: {', '.join(brief.integrations) or '—'}",
        f"- Timeline: {brief.timeline or '—'}",
        f"- Budget band: {brief.budget_band or '—'}",
        f"- Role: {brief.decision_role or '—'}",
    ]
    if architecture:
        lines += [
            "",
            "## Architecture",
            f"- Frontend: {', '.join(architecture.get('frontend') or [])}",
            f"- Backend: {', '.join(architecture.get('backend') or [])}",
        ]
    if mvp:
        lines += ["", "## MVP", *[f"- {item}" for item in mvp.get("mvp", [])], "", "## Later", *[f"- {item}" for item in mvp.get("later", [])]]
    if portfolio:
        lines += ["", "## Matching work", *[f"- {item['title']}: {item['outcome']}" for item in portfolio]]
    if qualification:
        lines += ["", "## Qualification", *[f"- {reason}" for reason in qualification.get("reasons", [])]]
    lines += ["", "## Next steps", "- Strategist reviews this brief and confirms a live conversation."]
    return "\n".join(lines)


def _cards(stage: str, estimate, architecture, mvp, portfolio, qualification, config: AppConfig, booking=None, db=None) -> list[dict]:
    cards: list[dict] = []
    if estimate and stage == "estimation":
        cards.append(
            {
                "type": "estimate",
                "title": "Indicative MVP range",
                "range": estimate["range_label"],
                "weeks": estimate["timeline_weeks"],
                "team": estimate["team"],
                "inclusions": estimate.get("inclusions") or [],
                "exclusions": estimate.get("exclusions") or [],
                "assumptions": estimate.get("assumptions") or [],
                "disclaimer": config.agency.disclaimer.strip(),
            }
        )
    if architecture and stage in {"estimation", "solutioning", "portfolio"}:
        cards.append(
            {
                "type": "architecture",
                "title": "Suggested architecture",
                "frontend": architecture.get("frontend"),
                "backend": architecture.get("backend"),
                "notes": architecture.get("notes"),
            }
        )
    if mvp and stage in {"solutioning", "portfolio", "estimation"}:
        cards.append({"type": "mvp", "title": "MVP vs later", "mvp": mvp.get("mvp"), "later": mvp.get("later")})
    if portfolio and stage == "portfolio":
        cards.append({"type": "portfolio", "title": "Related work", "cases": portfolio})
    if qualification and qualification.get("band") == "disqualify":
        cards.append({"type": "qualification", "title": "Fit", "band": "disqualify", "reasons": qualification.get("reasons")})
    if stage == "booking":
        window = (booking or {}).get("window") or "this_week"
        cards.append(booking_card(window, booking if not _is_booked(booking) else None, db=db))
    if stage == "handoff" and _is_booked(booking):
        cards.append(booking_card((booking or {}).get("window") or "this_week", booking, db=db))
    return cards


def _is_booked(booking: dict | None) -> bool:
    return bool(booking and booking.get("slot_iso"))


def _valid_chip(chip: Any, config: AppConfig) -> bool:
    if not isinstance(chip, dict) or not chip.get("field"):
        return False
    field = str(chip.get("field"))
    if field in ACTION_CHIP_FIELDS:
        return True
    if field not in ProjectBrief.model_fields:
        return False
    value = chip.get("value")
    if field in {"platforms", "integrations", "ai_features", "constraints", "features", "user_flow"}:
        return True
    if field in {"auth", "admin", "realtime", "marketplace"}:
        return True
    if value in (None, ""):
        return False
    if field == "service":
        return str(value) in config.services.in_scope
    if field == "budget_band":
        return str(value) in {str(key) for key in config.qualification.budget_bands}
    if field == "timeline":
        return str(value) in {str(key) for key in config.qualification.timeline_scores}
    if field == "decision_role":
        return str(value) in {str(key) for key in config.qualification.decision_role_scores}
    if field == "company_size":
        return str(value) in {str(key) for key in config.qualification.company_size_scores}
    return True


def _consult_chips(data: dict, brief: ProjectBrief, stage: str, config: AppConfig) -> list[dict]:
    raw = data.get("chips") if isinstance(data.get("chips"), list) else []
    cleaned = [chip for chip in raw if _valid_chip(chip, config)]
    if cleaned:
        return cleaned
    ask_field = data.get("ask_field")
    if ask_field and str(ask_field) not in {"", "null", "None"}:
        return chips_for_field(brief, str(ask_field))
    if stage in {"estimation", "solutioning", "booking"}:
        return chips_for(brief, stage)
    return []


def _hint_stage(
    brief,
    rfp_text,
    objection,
    qualification,
    estimate,
    contact,
    booking,
    chip_field,
    book_threshold: int,
    wants_booking: bool = False,
    nda_accepted: bool = True,
    nda_required: bool = False,
) -> str:
    if brief.out_of_scope or brief.decision_role == "intern_or_student":
        return "disqualified"
    if not brief_ready(brief):
        if rfp_text:
            return "rfp_review"
        if objection:
            return "objections"
        return "discovery"
    return _next_stage(
        brief,
        qualification,
        bool(estimate),
        bool(contact.get("email")),
        booking,
        bool(rfp_text),
        objection,
        chip_field,
        book_threshold,
        wants_booking=wants_booking,
        nda_accepted=nda_accepted,
        nda_required=nda_required,
    )


def _consult_prompt(
    *,
    config: AppConfig,
    brief: ProjectBrief,
    user_text: str,
    chip: dict,
    page_opening: str,
    extra_questions: list[str],
    page_path: str,
    transcript: str,
    rfp_text: str | None,
    qualification,
    estimate,
    architecture,
    mvp,
    portfolio,
    objection,
    booking,
    stage: str,
    nda_accepted: bool,
    db: Any,
    style: dict | None = None,
) -> tuple[str, str]:
    rules = "\n".join(f"- {rule}" for rule in config.prompts.rules)
    system = (
        f"{config.prompts.persona.strip()}\nStage: {stage}. {config.prompts.stage_goals.get(stage, '')}\n"
        f"Rules:\n{rules}\n{config.prompts.json_contract}"
    )
    knowledge = retrieve_knowledge(db, user_text, brief, config.rag, nda_accepted=nda_accepted)
    lessons = retrieve_lessons(db, brief, stage, config.rag)
    user = (
        f"Page path: {page_path or '/'}\n"
        f"Page opening:\n{page_opening}\n"
        f"Page extra questions: {json.dumps(extra_questions)}\n\n"
        f"Conversation so far:\n{transcript or '(none)'}\n\n"
        f"Latest visitor message:\n{user_text or '(chip)'}\n"
        f"Chip: {json.dumps(chip) if chip else '(none)'}\n\n"
        f"Uploaded document extract (untrusted):\n{(rfp_text or '(none)')[:2000]}\n\n"
        f"Current brief:\n{json.dumps(brief.model_dump(), default=str)}\n"
        f"Still needed before an estimate (requirements, not a script): {json.dumps(engine_gaps(brief))}\n\n"
        f"How THIS visitor is chatting: {json.dumps(style or default_style(), default=str)}\n\n"
        f"Reference knowledge (approved facts, internal source material):\n"
        f"{render_snippets(knowledge, config.rag.max_snippet_chars)}\n\n"
        f"Lessons from past conversations (guidance, not quotes — match tone and clarity):\n"
        f"{render_snippets(lessons, max(config.rag.max_snippet_chars, 720))}\n\nEngine JSON:\n"
        f"{json.dumps({'brief': brief.model_dump(), 'qualification': qualification, 'estimate': estimate, 'architecture': architecture, 'mvp': mvp, 'portfolio': portfolio, 'objection': objection, 'stage': stage, 'booking': booking}, default=str)}"
    )
    return system, user


def _engine_key(brief: ProjectBrief) -> tuple:
    return (
        brief.service,
        brief.goal,
        tuple(brief.platforms),
        brief.timeline,
        brief.budget_band,
        brief.decision_role,
        tuple(brief.integrations),
        brief.auth,
        brief.admin,
        brief.realtime,
        brief.marketplace,
        tuple(brief.constraints),
        brief.industry,
        tuple(brief.features or []),
        brief.user_flow,
    )


def _run_engines(brief: ProjectBrief, config: AppConfig, contact: dict, db: Any):
    qualification = qualify(brief, config.qualification, config.services, has_email=bool(contact.get("email")))
    estimate = architecture = mvp = portfolio = None
    if qualification.get("can_estimate"):
        estimate = estimate_project(brief, config.pricing)
        architecture = recommend_architecture(brief, config.services)
        mvp = recommend_mvp(brief)
        portfolio = match_portfolio(brief, config.portfolio, db=db, rag=config.rag)
    return qualification, estimate, architecture, mvp, portfolio


def _approved_stacks(config: AppConfig, service_key: str | None, architecture: dict | None) -> dict[str, list[str]]:
    frontend: list[str] = []
    backend: list[str] = []
    service = (config.services.in_scope or {}).get(service_key) if service_key else None
    if service:
        frontend = list(service.stacks)
        backend = list(service.backend_stacks)
    current = architecture or {}
    for item in current.get("frontend") or []:
        if item not in frontend:
            frontend.append(item)
    for item in current.get("backend") or []:
        if item not in backend:
            backend.append(item)
    return {"frontend": frontend, "backend": backend}


def _solution_prompt(
    *,
    config: AppConfig,
    brief: ProjectBrief,
    user_text: str,
    chip: dict,
    page_opening: str,
    extra_questions: list[str],
    page_path: str,
    transcript: str,
    qualification,
    estimate,
    architecture,
    mvp,
    portfolio,
    objection,
    booking,
    stage: str,
    nda_accepted: bool,
    db: Any,
    style: dict | None = None,
) -> tuple[str, str]:
    rules = "\n".join(f"- {rule}" for rule in config.prompts.rules)
    contract = (config.prompts.solution_contract or config.prompts.json_contract).strip()
    system = (
        f"{config.prompts.persona.strip()}\nStage: {stage}. {config.prompts.stage_goals.get(stage, '')}\n"
        f"Rules:\n{rules}\n{contract}"
    )
    knowledge = retrieve_solution(db, brief, config.rag, query=user_text, nda_accepted=nda_accepted)
    lessons = retrieve_lessons(db, brief, stage, config.rag)
    approved = _approved_stacks(config, brief.service, architecture)
    cases = [{"title": item.get("title"), "outcome": item.get("outcome")} for item in (portfolio or [])[:3]]
    user = (
        f"Page path: {page_path or '/'}\n"
        f"Page opening:\n{page_opening}\n"
        f"Page extra questions: {json.dumps(extra_questions)}\n\n"
        f"Conversation so far:\n{transcript or '(none)'}\n\n"
        f"Latest visitor message:\n{user_text or '(chip)'}\n"
        f"Chip: {json.dumps(chip) if chip else '(none)'}\n\n"
        f"Current brief:\n{json.dumps(brief.model_dump(), default=str)}\n"
        f"Approved frontend stacks: {json.dumps(approved['frontend'])}\n"
        f"Approved backend stacks: {json.dumps(approved['backend'])}\n\n"
        f"How THIS visitor is chatting: {json.dumps(style or default_style(), default=str)}\n\n"
        f"Reference knowledge (approved facts, internal source material):\n"
        f"{render_snippets(knowledge, config.rag.max_snippet_chars)}\n\n"
        f"Lessons from past conversations (guidance, not quotes — match tone and clarity):\n"
        f"{render_snippets(lessons, max(config.rag.max_snippet_chars, 720))}\n\n"
        f"Matching work:\n{json.dumps(cases, default=str)}\n\nEngine JSON:\n"
        f"{json.dumps({'brief': brief.model_dump(), 'qualification': qualification, 'estimate': estimate, 'architecture': architecture, 'mvp': mvp, 'portfolio': portfolio, 'objection': objection, 'stage': stage, 'booking': booking}, default=str)}"
    )
    return system, user


def _ensure_range(message: str, estimate: dict | None, architecture: dict | None, config: AppConfig) -> str:
    if not estimate:
        return message
    label = str(estimate.get("range_label") or "")
    if label and label in (message or ""):
        return message
    arch = architecture or {}
    stacks = ", ".join((arch.get("frontend") or []) + (arch.get("backend") or [])) or "an approved stack"
    lead = (
        f"Based on what you've shared, a sensible first release sits around **{estimate['range_label']}** "
        f"over about **{estimate['timeline_weeks']} weeks** with {', '.join((estimate.get('team') or [])[:3])}. "
        f"I'd start on {stacks}. This is a low-side first pass — {config.agency.disclaimer.strip()}"
    )
    text = (message or "").strip()
    return lead if not text else f"{lead}\n\n{text}"


def _next_stage(
    brief,
    qualification,
    has_estimate,
    has_email,
    booking,
    force_rfp,
    objection,
    chip_field,
    book_threshold: int,
    wants_booking: bool = False,
    nda_accepted: bool = True,
    nda_required: bool = False,
) -> str:
    if qualification and qualification.get("band") == "disqualify":
        return "disqualified"
    if force_rfp:
        return "rfp_review"
    if objection and not brief_ready(brief):
        return "objections"
    if not brief_ready(brief):
        return "discovery"
    if not has_estimate:
        return "estimation"
    if chip_field == "show_mvp":
        return "solutioning"
    if chip_field == "show_portfolio":
        return "portfolio"
    if not has_email:
        return "capture"
    if _is_booked(booking):
        return "handoff"
    contact_path = wants_booking or chip_field in {"continue_contact", "booking_window", "nda"}
    if nda_required and not nda_accepted and contact_path:
        return "capture"
    if contact_path or (qualification and qualification.get("score", 0) >= book_threshold):
        return "booking"
    return "capture"


def _dedupe_message(
    message: str,
    last_assistant: str,
    *,
    stage: str,
    contact: dict,
    nda_accepted: bool,
    nda_required: bool,
) -> str:
    current = (message or "").strip()
    previous = (last_assistant or "").strip()
    if not previous or current != previous:
        return message
    if stage == "capture" and not contact.get("email"):
        if "email" in previous.lower():
            return "I still need a work email before I can attach the discovery pack or book a time."
        return "Happy to book a time — I just need a work email first."
    if stage == "capture" and nda_required and not nda_accepted:
        return "Please accept the confidentiality notice below, then I'll show available times."
    if stage == "booking":
        return "Pick a time that works — the open slots are in the card below."
    return "Got it. What would you like to do next?"


def run_turn(
    *,
    config: AppConfig,
    brief: ProjectBrief,
    contact: dict[str, str],
    nda_accepted: bool,
    booking: dict | None,
    user_text: str,
    chip: dict[str, Any] | None,
    page_opening: str,
    extra_questions: list[str],
    is_opening: bool = False,
    rfp_text: str | None = None,
    existing_estimate: dict | None = None,
    existing_qualification: dict | None = None,
    existing_architecture: dict | None = None,
    existing_mvp: dict | None = None,
    existing_portfolio: list[dict] | None = None,
    session_id: str = "",
    db: Any = None,
    transcript: str = "",
    page_path: str = "",
    last_assistant: str = "",
    existing_style: dict | None = None,
) -> TurnResult:
    chip = chip or {}
    chip_field = chip.get("field")
    also = dict(chip.get("also") or {})
    before_dump = brief.model_dump()
    pending_field = next_discovery_field(brief, existing_style)
    already_disqualified = bool(brief.out_of_scope or brief.decision_role == "intern_or_student")
    thanks_close = chip_field == "close_out" or (already_disqualified and _looks_like_thanks(user_text))
    booking_error = ""
    pending_slot = None
    pending_window = None
    had_email = bool((contact or {}).get("email"))
    nda_required = bool(config.agency.nda.required_before_handoff)
    if chip_field == "booking_slot":
        pending_window = str(also.get("window") or (booking or {}).get("window") or "this_week")
        pending_slot = str(chip.get("value") or "") or None
    elif chip_field == "booking_window":
        window = str(chip.get("value") or "this_week")
        if not _is_booked(booking):
            booking = {"window": window}
    elif chip_field == "nda":
        nda_accepted = True
    elif chip_field not in {None, "show_portfolio", "show_mvp", "continue_contact", "booking_window", "booking_slot", "nda", "close_out"}:
        brief.apply_chip(str(chip_field), chip.get("value"))
        for key, value in also.items():
            brief.apply_chip(key, value)
    if user_text:
        brief = apply_payload(brief, None, user_text)
        contact.update(extract_contact(user_text))
    just_got_email = bool(contact.get("email")) and not had_email
    wants_booking = _wants_booking(user_text, chip_field) or just_got_email
    style = detect_style(user_text, transcript, previous=existing_style)
    if just_got_email:
        prior = prior_style_for_email(db, str(contact.get("email") or ""), session_id)
        if prior:
            style = detect_style("", "", previous=prior)
            style = detect_style(user_text, transcript, previous=style)
            style["returning"] = True
            if not style.get("notes"):
                style["notes"] = (
                    f"Returning visitor — they previously preferred {prior.get('pace')}/{prior.get('register')}."
                )
    if wants_booking and chip_field != "booking_slot" and not _is_booked(booking):
        booking = dict(booking or {})
        booking.setdefault("window", "this_week")
    if rfp_text:
        brief = extract_rfp(brief, rfp_text[:4000])
    use_llm = llm_available() and not is_opening and not thanks_close
    if not use_llm and user_text:
        brief = capture_goal_reply(brief, user_text)
        if pending_field == "features":
            brief = capture_features_reply(brief, user_text, chip_field)
        if pending_field == "user_flow":
            brief = capture_user_flow_reply(brief, user_text, chip_field)
    facts_captured = brief.model_dump() != before_dump

    if pending_slot:
        if nda_required and not nda_accepted:
            booking = {**(booking or {}), "window": pending_window or "this_week"}
        else:
            try:
                booking = confirm_slot(
                    session_id,
                    pending_window or "this_week",
                    pending_slot,
                    email=contact.get("email"),
                    db=db,
                )
            except CalendarError as exc:
                booking_error = str(exc)
                booking = {**(booking or {}), "window": pending_window or "this_week", "error": booking_error}

    objection = match_objection(user_text, config.objections, db=db, rag=config.rag) if user_text else None
    qualification = existing_qualification
    estimate = existing_estimate
    architecture = existing_architecture
    mvp = existing_mvp
    portfolio = existing_portfolio

    consult_data: dict | None = None
    ready_before_llm = brief_ready(brief)
    if use_llm and not ready_before_llm:
        try:
            hint = _hint_stage(
                brief,
                rfp_text,
                objection,
                qualification,
                estimate,
                contact,
                booking,
                chip_field,
                config.qualification.book_threshold,
                wants_booking=wants_booking,
                nda_accepted=nda_accepted,
                nda_required=nda_required,
            )
            system, user = _consult_prompt(
                config=config,
                brief=brief,
                user_text=user_text,
                chip=chip,
                page_opening=page_opening,
                extra_questions=extra_questions,
                page_path=page_path,
                transcript=transcript,
                rfp_text=rfp_text,
                qualification=qualification,
                estimate=estimate,
                architecture=architecture,
                mvp=mvp,
                portfolio=portfolio,
                objection=objection,
                booking=booking,
                stage=hint,
                nda_accepted=nda_accepted,
                db=db,
                style=style,
            )
            consult_data = complete_json(system, user)
            brief = apply_brief_updates(brief, consult_data.get("brief_updates"), config)
            style = overlay_llm(style, consult_data.get("visitor_style"))
        except (LLMError, Exception) as exc:
            log.warning("Discovery LLM failed: %s", exc)
            consult_data = None

    wait_for_size = (
        not use_llm
        and brief_ready(brief)
        and not brief.company_size
        and chip_field == "decision_role"
    )
    if (brief_ready(brief) or brief.out_of_scope or brief.decision_role == "intern_or_student") and not wait_for_size:
        qualification, estimate, architecture, mvp, portfolio = _run_engines(brief, config, contact, db)

    if is_opening:
        stage = "greeting"
    elif wait_for_size:
        stage = "discovery"
    else:
        stage = _next_stage(
            brief,
            qualification,
            bool(estimate),
            bool(contact.get("email")),
            booking,
            bool(rfp_text),
            objection,
            chip_field,
            config.qualification.book_threshold,
            wants_booking=wants_booking,
            nda_accepted=nda_accepted,
            nda_required=nda_required,
        )
        if estimate and not existing_estimate and stage not in {"disqualified", "booking", "handoff"} and not wants_booking:
            stage = "estimation"
        if chip_field == "show_mvp":
            stage = "solutioning"
            mvp = mvp or recommend_mvp(brief)
        if chip_field == "show_portfolio":
            stage = "portfolio"
            portfolio = portfolio or match_portfolio(brief, config.portfolio, db=db, rag=config.rag)
        if chip_field == "booking_window" and not _is_booked(booking):
            if stage == "disqualified":
                stage = "booking"
            elif not contact.get("email"):
                stage = "capture"
            elif nda_required and not nda_accepted:
                stage = "capture"
            else:
                stage = "booking"
        if thanks_close:
            stage = "disqualified"

    if (
        estimate
        and stage in {"capture", "qualification", "discovery"}
        and not wants_booking
        and not just_got_email
        and (
            style.get("clarity") == "confused"
            or style.get("pace") == "terse"
            or style.get("mood") in {"impatient", "skeptical"}
        )
    ):
        stage = "estimation"

    advise = use_llm and bool(estimate) and stage in {"estimation", "solutioning", "portfolio"}

    if chip_field == "booking_slot" and nda_required and not nda_accepted and not _is_booked(booking):
        booking = {**(booking or {}), "window": pending_window or (booking or {}).get("window") or "this_week"}
        stage = "capture"
        reply = {
            "message": "Before I book that time, please accept the confidentiality notice (checkbox below).",
            "chips": [],
            "stage": "capture",
        }
    else:
        reply = None
        if advise:
            try:
                before = _engine_key(brief)
                system, user = _solution_prompt(
                    config=config,
                    brief=brief,
                    user_text=user_text,
                    chip=chip,
                    page_opening=page_opening,
                    extra_questions=extra_questions,
                    page_path=page_path,
                    transcript=transcript,
                    qualification=qualification,
                    estimate=estimate,
                    architecture=architecture,
                    mvp=mvp,
                    portfolio=portfolio,
                    objection=objection,
                    booking=booking,
                    stage=stage,
                    nda_accepted=nda_accepted,
                    db=db,
                    style=style,
                )
                data = complete_json(system, user)
                style = overlay_llm(style, data.get("visitor_style"))
                brief = apply_brief_updates(brief, data.get("brief_updates"), config)
                if _engine_key(brief) != before:
                    qualification, estimate, architecture, mvp, portfolio = _run_engines(brief, config, contact, db)
                else:
                    architecture = apply_architecture(architecture, data.get("architecture"), config, brief.service)
                    mvp = apply_mvp(mvp, data.get("mvp"))
                message = _ensure_range(str(data.get("message") or "").strip(), estimate, architecture, config)
                if message:
                    reply = {
                        "message": message,
                        "chips": _consult_chips(data, brief, stage, config) or chips_for(brief, stage),
                        "stage": stage,
                    }
            except (LLMError, Exception) as exc:
                log.warning("Solutioning LLM failed: %s", exc)
                reply = None
        elif consult_data and str(consult_data.get("message") or "").strip():
            reply = {
                "message": str(consult_data.get("message") or "").strip(),
                "chips": _consult_chips(consult_data, brief, stage if stage != "greeting" else "discovery", config),
                "stage": stage,
            }
        if reply is None:
            reply = fallback_reply(
                stage=stage,
                brief=brief,
                opening=page_opening,
                extra_questions=extra_questions,
                qualification=qualification,
                estimate=estimate,
                architecture=architecture,
                mvp=mvp,
                portfolio=portfolio,
                objection=objection,
                config=config,
                user_text=user_text,
                booking=booking,
                contact=contact,
                nda_accepted=nda_accepted,
                nda_required=nda_required,
                wants_booking=wants_booking,
                style=style,
                last_assistant=last_assistant,
                facts_captured=facts_captured,
                chip_field=chip_field,
            )
            stage = reply.get("stage") or stage

    if wait_for_size:
        stage = "discovery"
        reply["chips"] = chips_for_field(brief, "company_size")
        reply["message"] = DISCOVERY_PROMPTS["company_size"]

    if thanks_close and not is_opening:
        stage = "disqualified"
        reply = {
            "message": (config.agency.out_of_scope_thanks or config.agency.out_of_scope_close).strip(),
            "chips": [],
            "stage": "disqualified",
        }
    elif stage == "disqualified":
        reply["message"] = config.agency.out_of_scope_close.strip()
        reply["chips"] = list(DISQUALIFIED_CHIPS)
        reply["stage"] = "disqualified"

    if stage == "booking":
        window = (booking or {}).get("window") or "this_week"
        reply["chips"] = slot_chips(window)
        if booking_error:
            reply["message"] = f"{booking_error} Pick another time."

    summary = None
    can_handoff = bool(_is_booked(booking) and contact.get("email") and (nda_accepted or not nda_required))
    if _is_booked(booking) and contact.get("email") and nda_required and not nda_accepted:
        stage = "capture"
        reply = {
            "message": "Before I hand this to the team, please accept the confidentiality notice (checkbox below).",
            "chips": [],
            "stage": "capture",
        }
    elif stage == "handoff" or can_handoff:
        summary = build_handoff_summary(brief, qualification, estimate, architecture, mvp, portfolio, contact, config)
        stage = "handoff"
        pack = render_followup(
            email=contact.get("email") or "",
            intro=config.handoff.follow_up.get("intro") or "",
            estimate=estimate,
            portfolio=portfolio,
            booking=booking,
            agency=config.agency.name,
        )
        meet = (booking or {}).get("meet_url") or ""
        label = (booking or {}).get("label") or ""
        join = f" Join via {meet}." if meet else ""
        reply = {
            "message": (
                f"Booked **{label}**.{join} "
                f"I've queued a recap to {contact.get('email')} (dummy — not actually sent). "
                "A strategist has the discovery summary."
            ),
            "chips": [{"label": "Add to calendar", "field": "download_ics", "value": "yes"}] if booking else [],
            "stage": "handoff",
            "follow_up": pack,
        }

    reply["message"] = _dedupe_message(
        reply["message"],
        last_assistant,
        stage=stage,
        contact=contact,
        nda_accepted=nda_accepted,
        nda_required=nda_required,
    )

    actions = ["upload"]
    if not nda_accepted:
        actions.append("nda")
    if stage in {"capture", "portfolio", "solutioning"} and not contact.get("email"):
        actions.append("email")
    if qualification and qualification.get("can_book") and contact.get("email") and stage != "handoff":
        actions.append("book")

    return TurnResult(
        message=sanitize_reply(reply["message"], estimate, config.agency.never_say),
        stage=stage,
        chips=reply.get("chips") or [],
        cards=_cards(stage, estimate, architecture, mvp, portfolio, qualification, config, booking, db),
        actions=actions,
        brief=brief,
        qualification=qualification,
        estimate=estimate,
        architecture=architecture,
        mvp=mvp,
        portfolio=portfolio,
        contact=contact,
        nda_accepted=nda_accepted,
        booking=booking,
        follow_up=reply.get("follow_up"),
        handoff_summary=summary,
        objection=objection,
        style=style,
    )
