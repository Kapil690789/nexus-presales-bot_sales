from __future__ import annotations

import json
from typing import Any

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.agents.chips import DISCOVERY_PROMPTS, chips_for
from backend.app.agents.extract import apply_payload, extract_contact
from backend.app.documents.rfp import extract_rfp
from backend.app.agents.fallback import fallback_reply
from backend.app.config_loader.loader import AppConfig
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.objections import match_objection
from backend.app.engines.calendar import confirm_slot, slot_chips
from backend.app.engines.followup import render_followup
from backend.app.engines.portfolio import match_portfolio
from backend.app.engines.pricing import estimate_project
from backend.app.engines.qualification import qualify
from backend.app.rag.retrieve import render_snippets, retrieve_knowledge, retrieve_lessons


class TurnResult:
    def __init__(self, **kwargs: Any) -> None:
        for key, value in kwargs.items():
            setattr(self, key, value)


def _safe_never_say(message: str, never: list[str]) -> str:
    redacted = message
    for phrase in never:
        if phrase and phrase.lower() in redacted.lower():
            redacted = redacted.replace(phrase, "")
    return redacted.strip() or "Let's keep this to scope, estimate, and next steps."


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


def _cards(stage: str, estimate, architecture, mvp, portfolio, qualification, config: AppConfig) -> list[dict]:
    cards: list[dict] = []
    if estimate and stage in {"estimation", "solutioning", "portfolio", "capture", "booking", "handoff"}:
        cards.append(
            {
                "type": "estimate",
                "title": "Indicative MVP range",
                "range": estimate["range_label"],
                "weeks": estimate["timeline_weeks"],
                "team": estimate["team"],
                "inclusions": estimate.get("inclusions") or [],
                "exclusions": estimate.get("exclusions") or [],
                "disclaimer": config.agency.disclaimer.strip(),
            }
        )
    if architecture and stage in {"estimation", "solutioning", "portfolio", "handoff"}:
        cards.append(
            {
                "type": "architecture",
                "title": "Suggested architecture",
                "frontend": architecture.get("frontend"),
                "backend": architecture.get("backend"),
                "notes": architecture.get("notes"),
            }
        )
    if mvp and stage in {"solutioning", "portfolio", "handoff", "estimation"}:
        cards.append({"type": "mvp", "title": "MVP vs later", "mvp": mvp.get("mvp"), "later": mvp.get("later")})
    if portfolio and stage in {"portfolio", "capture", "booking", "handoff"}:
        cards.append({"type": "portfolio", "title": "Related work", "cases": portfolio})
    if qualification and qualification.get("band") == "disqualify":
        cards.append({"type": "qualification", "title": "Fit", "band": "disqualify", "reasons": qualification.get("reasons")})
    return cards


def _is_booked(booking: dict | None) -> bool:
    return bool(booking and booking.get("slot_iso"))


def _next_stage(brief, qualification, has_estimate, has_email, booking, force_rfp, objection, chip_field, book_threshold: int) -> str:
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
    if chip_field == "continue_contact":
        return "capture"
    if not has_email:
        return "capture"
    if _is_booked(booking):
        return "handoff"
    if qualification and qualification.get("score", 0) >= book_threshold:
        return "booking"
    return "capture"


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
) -> TurnResult:
    chip = chip or {}
    chip_field = chip.get("field")
    also = dict(chip.get("also") or {})
    if chip_field == "booking_slot":
        window = str(also.get("window") or (booking or {}).get("window") or "this_week")
        booking = confirm_slot(session_id, window, str(chip.get("value") or "") or None)
    elif chip_field == "booking_window":
        window = str(chip.get("value") or "this_week")
        if also.get("slot_iso") or (booking and booking.get("slot_iso")):
            booking = confirm_slot(session_id, window, also.get("slot_iso") or (booking or {}).get("slot_iso"))
        else:
            booking = {"window": window}
    elif chip_field == "nda":
        nda_accepted = True
    elif chip_field not in {None, "show_portfolio", "show_mvp", "continue_contact", "booking_window", "booking_slot", "nda"}:
        brief.apply_chip(str(chip_field), chip.get("value"))
        for key, value in also.items():
            brief.apply_chip(key, value)
    if user_text:
        brief = apply_payload(brief, None, user_text)
        contact.update(extract_contact(user_text))
    if rfp_text:
        brief = extract_rfp(brief, rfp_text[:4000])

    objection = match_objection(user_text, config.objections, db=db, rag=config.rag) if user_text else None
    qualification = existing_qualification
    estimate = existing_estimate
    architecture = existing_architecture
    mvp = existing_mvp
    portfolio = existing_portfolio

    wait_for_size = brief_ready(brief) and not brief.company_size and chip_field == "decision_role"
    if (brief_ready(brief) or brief.out_of_scope or brief.decision_role == "intern_or_student") and not wait_for_size:
        qualification = qualify(brief, config.qualification, config.services, has_email=bool(contact.get("email")))
        if qualification.get("can_estimate"):
            estimate = estimate_project(brief, config.pricing)
            architecture = recommend_architecture(brief, config.services)
            mvp = recommend_mvp(brief)
            portfolio = match_portfolio(brief, config.portfolio, db=db, rag=config.rag)

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
        )
        if estimate and not existing_estimate and stage not in {"disqualified", "booking", "handoff"}:
            stage = "estimation"
        if chip_field == "show_mvp":
            stage = "solutioning"
            mvp = mvp or recommend_mvp(brief)
        if chip_field == "show_portfolio":
            stage = "portfolio"
            portfolio = portfolio or match_portfolio(brief, config.portfolio, db=db, rag=config.rag)
        if chip_field == "booking_window" and not _is_booked(booking):
            stage = "booking"

    if booking and config.agency.nda.required_before_handoff and not nda_accepted:
        booking = None
        stage = "capture"
        reply = {
            "message": "Before I hand this to the team, please accept the confidentiality notice (checkbox below).",
            "chips": slot_chips("this_week") if contact.get("email") else [],
            "stage": "capture",
        }
    else:
        reply = None
        if llm_available() and not is_opening:
            try:
                rules = "\n".join(f"- {rule}" for rule in config.prompts.rules)
                system = (
                    f"{config.prompts.persona.strip()}\nStage: {stage}. {config.prompts.stage_goals.get(stage, '')}\n"
                    f"Rules:\n{rules}\n{config.prompts.json_contract}"
                )
                knowledge = retrieve_knowledge(db, user_text, brief, config.rag, nda_accepted=nda_accepted)
                lessons = retrieve_lessons(db, brief, stage, config.rag)
                user = (
                    f"Visitor message:\n{user_text or '(chip)'}\n\n"
                    f"Reference knowledge (approved facts, internal source material):\n"
                    f"{render_snippets(knowledge, config.rag.max_snippet_chars)}\n\n"
                    f"Lessons from past conversations (guidance, not quotes):\n"
                    f"{render_snippets(lessons, config.rag.max_snippet_chars)}\n\nEngine JSON:\n"
                    f"{json.dumps({'brief': brief.model_dump(), 'qualification': qualification, 'estimate': estimate, 'architecture': architecture, 'mvp': mvp, 'portfolio': portfolio, 'objection': objection, 'stage': stage, 'booking': booking}, default=str)}"
                )
                data = complete_json(system, user)
                reply = {
                    "message": str(data.get("message") or "").strip(),
                    "chips": data.get("chips") or chips_for(brief, stage if stage != "greeting" else "discovery"),
                    "stage": data.get("stage") or stage,
                }
            except (LLMError, Exception):
                reply = None
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
            )
            stage = reply.get("stage") or stage

    if wait_for_size:
        stage = "discovery"
        reply["chips"] = chips_for(brief, "discovery")
        reply["message"] = DISCOVERY_PROMPTS["company_size"]

    if stage == "booking":
        window = (booking or {}).get("window") or "this_week"
        reply["chips"] = slot_chips(window)

    summary = None
    can_handoff = bool(_is_booked(booking) and contact.get("email") and (nda_accepted or not config.agency.nda.required_before_handoff))
    if stage == "handoff" or can_handoff:
        if config.agency.nda.required_before_handoff and not nda_accepted:
            stage = "capture"
            booking = None
            reply = {
                "message": "Before I hand this to the team, please accept the confidentiality notice (checkbox below).",
                "chips": slot_chips("this_week"),
                "stage": "capture",
            }
        else:
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
            reply = {
                "message": (
                    f"Booked **{label}**. Join via {meet}. "
                    f"I’ve queued a recap to {contact.get('email')} (dummy — not actually sent). "
                    "A strategist has the discovery summary."
                ),
                "chips": [{"label": "Add to calendar", "field": "download_ics", "value": "yes"}] if booking else [],
                "stage": "handoff",
                "follow_up": pack,
            }

    actions = ["upload"]
    if not nda_accepted:
        actions.append("nda")
    if stage in {"capture", "portfolio", "solutioning"} and not contact.get("email"):
        actions.append("email")
    if qualification and qualification.get("can_book") and contact.get("email"):
        actions.append("book")

    return TurnResult(
        message=_safe_never_say(reply["message"], config.agency.never_say),
        stage=stage,
        chips=reply.get("chips") or [],
        cards=_cards(stage, estimate, architecture, mvp, portfolio, qualification, config),
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
    )
