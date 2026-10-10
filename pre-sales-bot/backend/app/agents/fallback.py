from __future__ import annotations

import logging

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.tenants.schema import TenantConfig

log = logging.getLogger(__name__)

GROUNDING_LINE = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)
FALLBACK_SYSTEM_PROMPT = (
    "You are an expert enterprise pre-sales software consultant and principal solutions architect. Output JSON only. "
    + GROUNDING_LINE
)

from backend.app.core.platform import get_platform

FALLBACK_RECOVERY_TEXT = "That's outside what I have on hand right now. I can connect you with the team, or keep scoping your estimate."


def fallback_recovery() -> tuple[str, list[dict]]:
    chips = [
        {"label": "Book a call", "field": "booking_window", "value": "booking"},
        {"label": "Continue estimate", "field": "continue_discovery", "value": "continue"},
    ]
    return FALLBACK_RECOVERY_TEXT, chips


def fallback_recovery_message() -> str:
    return FALLBACK_RECOVERY_TEXT


def fallback_message(
    config: TenantConfig,
    brief: ProjectBrief,
    estimate: dict | None,
    query: str = "",
    notes: list[Any] | None = None,
) -> str:
    name = config.brand.name
    service_labels = [item.label for item in config.services.in_scope.values()] if config.services and config.services.in_scope else ["custom web apps", "mobile apps", "AI solutions"]
    services_str = ", ".join(service_labels[:4])

    cleaned_q = (query or "").strip().lower()
    is_ack = cleaned_q in {
        "ok", "okay", "cool", "got it", "sounds good", "great", "thanks", "thank you",
        "sure", "nice", "perfect", "done", "alright", "hi", "hello", "hey", "yes", "no",
        "haan", "ha", "theek hai", "thik hai",
    }

    if is_ack:
        if not (brief and brief_ready(brief)):
            _goal_hint = ""
            if brief and (brief.goal or brief.service):
                _g = (brief.goal or brief.service or "").replace("_", " ").strip()
                _goal_hint = f" Looks like you're building around '{_g}' — let's keep scoping that out."
            return (
                f"I'm {name}'s pre-sales consultant, focused on custom web, mobile, and AI software.{_goal_hint} "
                f"What's the next thing on your mind?"
            )
        return (
            f"Glad that aligns! If you'd like to talk through the technical architecture, team setup, or confirm the timeline, "
            f"feel free to schedule a short discovery call with our team anytime."
        )

    notes_instruction = ""
    if notes:
        extracted_notes = []
        for n in notes:
            if hasattr(n, "content"):
                extracted_notes.append(str(getattr(n, "content", "")).strip())
            elif isinstance(n, str) and n.strip():
                extracted_notes.append(n.strip())
        if extracted_notes:
            notes_text = "\n\n".join(extracted_notes)
            notes_instruction = (
                f"\n\nPossibly relevant notes:\n{notes_text}\n"
                "Use the notes only if they answer the question; otherwise say you are not sure and offer to connect the team."
            )
    elif not is_ack:
        notes_instruction = (
            "\n\nYou have NO verified knowledge about this topic in the knowledge base. "
            "Do NOT make up, assume, or guess specific capabilities, frameworks, or past client projects. "
            "Clearly state that you do not have this information on hand and offer to connect them with the technical team."
        )

    if llm_available() and query:
        if brief and brief_ready(brief) and estimate:
            goal_str = brief.goal or brief.service or "custom software product"
            duration_min = get_platform().calendar.duration_minutes
            prompt = (
                f"You are the senior pre-sales software consultant at {name}. "
                f"The client has already scoped their project ('{goal_str}') and received an indicative estimate of "
                f"{estimate['range_label']} over ~{estimate['timeline_weeks']} weeks. "
                f"The client just said: {wrap_visitor(query)}. "
                f"{UNTRUSTED_RULE} "
                f"Write a warm, concise, professional reply (1-3 sentences max). "
                f"Acknowledge their input, offer to answer any technical/stack questions or help them book a {duration_min}-minute discovery call with the engineering team. "
                f"Do not redundantly paste the full estimate range unless explicitly asked. "
                f"{notes_instruction} "
                f'Return JSON {{"message": "..."}}.'
            )
        else:
            prompt = (
                f"You are the senior pre-sales software consultant at {name}. "
                f"The visitor asked: {wrap_visitor(query)}. "
                f"We specialize in {services_str}, dedicated agile squads, and bespoke digital products. "
                f"{UNTRUSTED_RULE} "
                f"Write a warm, concise, professional reply (2-3 sentences max). "
                f"Explain how {name} can help with custom software engineering, and invite them to share what kind of product they are looking to build or book a quick call. "
                f"Never make up fake fixed prices or promises not grounded in our scope. "
                f"{notes_instruction} "
                f'Return JSON {{"message": "..."}}.'
            )
        try:
            data = complete_json(FALLBACK_SYSTEM_PROMPT, prompt, mode="request")
            msg = str(data.get("message") or "").strip()
            if msg:
                return msg
        except LLMError as exc:
            error_cls = type(exc).__name__
            log.warning("LLM fallback synthesis failed: %s", error_cls)
            try:
                from backend.app.core.llm import record_system_event

                record_system_event(
                    kind="llm_failure",
                    reason=f"{error_cls} during fallback",
                    stage="fallback",
                    error_class=error_cls,
                )
            except Exception:
                pass

    if not brief_ready(brief):
        _partial_ctx = ""
        if brief:
            _parts_ctx = []
            if brief.goal or brief.service:
                _parts_ctx.append((brief.goal or brief.service or "").replace("_", " ").strip())
            if brief.platforms:
                _parts_ctx.append(" + ".join(brief.platforms))
            if _parts_ctx:
                _partial_ctx = f" So far we've scoped: {', '.join(_parts_ctx)}."
        return (
            f"I'm {name}'s pre-sales consultant, focused on bespoke web, mobile, and AI software.{_partial_ctx} "
            f"What else would you like to know or build out?"
        )

    if is_ack:
        _goal_ctx = (brief.goal or brief.service or "your project").replace("_", " ").strip() if brief else "your project"
        return (
            f"Sounds like we're aligned on '{_goal_ctx}'. "
            f"When you're ready, book a short call with the team to lock in architecture and delivery."
        )

    parts = []
    if estimate:
        _goal_label = (brief.goal or brief.service or "this scope").replace("_", " ").strip() if brief else "this scope"
        parts.append(
            f"Based on what you've shared for '{_goal_label}', our indicative range is **{estimate['range_label']}** over about {estimate['timeline_weeks']} weeks."
        )
    parts.append("The best next step is a short discovery call with our engineering team to review your specific requirements.")
    return " ".join(parts)
