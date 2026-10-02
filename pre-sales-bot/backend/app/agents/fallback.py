from __future__ import annotations

import logging

from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.tenants.schema import TenantConfig

log = logging.getLogger(__name__)


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
    is_ack = cleaned_q in {"ok", "okay", "cool", "got it", "sounds good", "great", "thanks", "thank you", "sure", "nice", "perfect", "done", "alright"}

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
            prompt = (
                f"You are the senior pre-sales software consultant at {name}. "
                f"The client has already scoped their project ('{goal_str}') and received an indicative estimate of "
                f"{estimate['range_label']} over ~{estimate['timeline_weeks']} weeks. "
                f"The client just said: {wrap_visitor(query)}. "
                f"{UNTRUSTED_RULE} "
                f"Write a warm, concise, professional reply (1-3 sentences max). "
                f"Acknowledge their input, offer to answer any technical/stack questions or help them book a 30-minute discovery call with the engineering team. "
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
            data = complete_json("You are an expert enterprise pre-sales software consultant. Output JSON only.", prompt)
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
        return (
            f"I'm {name}'s assistant and pre-sales consultant. We specialize in custom web applications, "
            f"cross-platform mobile apps (iOS & Android), and AI solutions. "
            f"I'd love to learn more about what you're looking to build so we can tailor the right approach."
        )

    if is_ack:
        return (
            f"Glad that aligns! If you'd like to talk through the technical architecture, team setup, or confirm the timeline, "
            f"feel free to schedule a short discovery call with our team anytime."
        )

    parts = []
    if estimate:
        parts.append(
            f"Based on what you've shared, our indicative range is **{estimate['range_label']}** over about {estimate['timeline_weeks']} weeks."
        )
    parts.append("The best next step is a short discovery call with our engineering team to review your specific requirements.")
    return " ".join(parts)
