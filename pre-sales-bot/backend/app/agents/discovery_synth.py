from __future__ import annotations

import hashlib
import logging
import re
from typing import Any

from backend.app.agents.brief import ProjectBrief, named_features
from backend.app.core.guard import UNTRUSTED_RULE, sanitize_price_leaks, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.screening.slots import prompt_for
from backend.app.tenants.schema import ServicesConfig, TenantConfig, VoiceConfig

log = logging.getLogger(__name__)

GROUNDING_LINE = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)
CONSULT_SYSTEM_PROMPT = (
    "You are an expert enterprise pre-sales software consultant and principal solutions architect. Output JSON only. "
    + GROUNDING_LINE
)

PRIORITY_FIELDS = ("features", "goal", "platforms", "timeline", "service")


def _stable_hash(session_id: str, field: str, attempt: int) -> int:
    key = f"{session_id}:{field}:{attempt}".encode("utf-8")
    return int(hashlib.sha256(key).hexdigest(), 16)


def ack_from_brief(
    brief: ProjectBrief,
    changed_fields: list[str],
    voice: VoiceConfig,
    session_id: str = "",
    services_config: ServicesConfig | None = None,
    attempt: int = 0,
) -> str | None:
    """Deterministic acknowledgement mentioning only values present in the brief,
    picking by priority (features, goal, platforms, timeline, service). Never repeats
    an ack id within 3 turns (tracked in brief.recent_acks)."""
    if not changed_fields:
        return None

    target_field = None
    for f in PRIORITY_FIELDS:
        if f in changed_fields:
            val = getattr(brief, f, None)
            if val:
                target_field = f
                break

    if not target_field:
        return None

    # Handle scope coach when >4 features
    if target_field == "features" and brief.features and len(brief.features) > 4:
        brief.recent_acks = (brief.recent_acks + ["scope_coach"])[-3:]
        return voice.scope_coach

    templates = voice.acks.get(target_field, [])
    if not templates:
        return None

    raw_idx = _stable_hash(session_id, target_field, attempt) % len(templates)
    chosen_idx = raw_idx
    for offset in range(len(templates)):
        cand_idx = (raw_idx + offset) % len(templates)
        cand_id = f"{target_field}_{cand_idx}"
        if cand_id not in brief.recent_acks:
            chosen_idx = cand_idx
            break

    ack_id = f"{target_field}_{chosen_idx}"
    template = templates[chosen_idx]

    # Compute formatting placeholders strictly from present brief values
    features_list = ", ".join(brief.features[:3]) if brief.features else ""
    goal_short = brief.goal[:60].strip() if brief.goal else ""
    platforms = " and ".join(brief.platforms) if brief.platforms else ""
    timeline_map = {
        "asap": "ASAP",
        "1_3_months": "1 to 3 months",
        "3_6_months": "3 to 6 months",
        "flexible": "flexible",
    }
    timeline_label = timeline_map.get(brief.timeline or "", brief.timeline or "")

    service_label = ""
    if brief.service:
        if services_config and brief.service in services_config.in_scope:
            service_label = services_config.in_scope[brief.service].label
        else:
            service_label = brief.service.replace("_", " ")

    # Ensure template does not mention absent values
    if "{service_label}" in template and not brief.service:
        template = template.replace("A {service_label} for ", "").replace("Building a {service_label} focused on ", "Focusing on ")

    try:
        ack_text = template.format(
            service_label=service_label,
            goal_short=goal_short,
            platforms=platforms,
            features_list=features_list,
            timeline_label=timeline_label,
        )
    except KeyError:
        return None

    brief.recent_acks = (brief.recent_acks + [ack_id])[-3:]
    return ack_text


def question_variant_for(
    config: TenantConfig,
    brief: ProjectBrief,
    field: str | None,
    session_id: str = "",
    attempt: int = 0,
) -> str:
    """Return the consultative question variant for the discovery field."""
    if not field:
        return ""

    if field == "features" and brief and named_features(brief) and not brief.features_confirmed:
        return prompt_for(brief, field)
    if field == "feature_detail" and brief and named_features(brief):
        return prompt_for(brief, field)

    voice = getattr(config, "voice", None)
    if voice and voice.questions and field in voice.questions:
        variants = voice.questions[field]
        if variants:
            idx = _stable_hash(session_id, field, attempt) % len(variants)
            return variants[idx]

    return prompt_for(brief, field, repeat=(attempt >= 1))


def validate_discovery_reply(
    reply: str,
    voice: VoiceConfig,
    deterministic_fallback: str,
) -> str:
    """Validate consultative reply against length, sentence count, emoji count, and banned phrases."""
    cleaned = (reply or "").strip()
    if not cleaned:
        return deterministic_fallback
    if len(cleaned) > voice.max_chars:
        return deterministic_fallback

    # Split into sentences
    sentences = [s.strip() for s in re.split(r"(?<=[.!?])\s+", cleaned) if s.strip()]
    if len(sentences) > 2:
        return deterministic_fallback

    # Check emojis
    emojis = re.findall(r"[\U00010000-\U0010ffff]", cleaned)
    if len(emojis) > voice.emoji_max:
        return deterministic_fallback

    # Check banned phrases
    lowered = cleaned.lower()
    for phrase in voice.banned_phrases:
        if phrase.lower() in lowered:
            return deterministic_fallback

    # Check price leaks
    sanitized = sanitize_price_leaks(cleaned)
    return sanitized


def deterministic_discovery_prompt(
    config: TenantConfig,
    brief: ProjectBrief,
    field: str | None,
    changed_fields: list[str] | None = None,
    session_id: str = "",
    attempt: int = 0,
) -> str:
    """Deterministic message composition: ack + next question (at most 2 sentences, <= max_chars)."""
    voice = getattr(config, "voice", None) or VoiceConfig()
    ack = ack_from_brief(
        brief,
        changed_fields or [],
        voice,
        session_id=session_id,
        services_config=config.services,
        attempt=attempt,
    )
    question = question_variant_for(config, brief, field, session_id=session_id, attempt=attempt)

    if ack and question:
        res = f"{ack.strip()} {question.strip()}"
    else:
        res = question or ack or ""

    return res[: voice.max_chars].strip()


def synthesize_discovery_prompt(
    config: TenantConfig,
    brief: ProjectBrief,
    field: str | None,
    user_text: str = "",
    session_id: str = "",
    changed_fields: list[str] | None = None,
    attempt: int = 0,
) -> str:
    """Generate a consultative transition and next discovery question using Gemini LLM,
    validated against voice rules and falling back to deterministic composition."""
    voice = getattr(config, "voice", None) or VoiceConfig()
    deterministic_msg = deterministic_discovery_prompt(
        config,
        brief,
        field,
        changed_fields=changed_fields,
        session_id=session_id,
        attempt=attempt,
    )

    if not field:
        return deterministic_msg

    if not llm_available():
        return deterministic_msg

    brand_name = config.brand.name
    captured_summary = []
    if brief.service:
        captured_summary.append(f"Service: {brief.service}")
    if brief.goal:
        captured_summary.append(f"Goal: {brief.goal}")
    if brief.platforms:
        captured_summary.append(f"Platforms: {', '.join(brief.platforms)}")
    if brief.features:
        captured_summary.append(f"Features: {', '.join(brief.features)}")
    if brief.timeline:
        captured_summary.append(f"Timeline: {brief.timeline}")
    if brief.budget_band:
        captured_summary.append(f"Budget: {brief.budget_band}")
    if brief.decision_role:
        captured_summary.append(f"Role: {brief.decision_role}")

    captured_str = "; ".join(captured_summary) if captured_summary else "Initial discovery"
    question = question_variant_for(config, brief, field, session_id=session_id, attempt=attempt)
    recent_acks_str = ", ".join(f'"{a}"' for a in brief.recent_acks) if brief.recent_acks else "None"
    banned_str = ", ".join(f'"{p}"' for p in voice.banned_phrases) if voice.banned_phrases else "None"

    prompt = (
        f"You are Alex, the senior AI project advisor and enterprise software consultant at {brand_name}. "
        f"The client just shared: {wrap_visitor(user_text)}. "
        f"Values updated this turn: [{', '.join(changed_fields) if changed_fields else 'None'}]. "
        f"Current scoped brief: [{captured_str}]. "
        f"The next discovery parameter to uncover: '{field}'. "
        f"Standard consultative question: '{question}'. "
        f"Advisory instructions:\n"
        f"- Provide a crisp, highly specific acknowledgement validating what changed from an engineering/product perspective, followed immediately by the question.\n"
        f"- Voice rules:\n"
        f"  * At most 2 sentences total.\n"
        f"  * Maximum length: {voice.max_chars} characters.\n"
        f"  * Maximum {voice.emoji_max} emoji.\n"
        f"  * Banned phrases: [{banned_str}].\n"
        f"  * Recent acks to avoid repeating: [{recent_acks_str}].\n"
        f"  * Be specific, objective, and consultative. Never use flattering phrases like 'Love it', 'Great idea', 'Smart approach', or 'v1'.\n"
        f"{UNTRUSTED_RULE}\n"
        f'Return JSON {{"message": "..."}}.'
    )

    try:
        data = complete_json(CONSULT_SYSTEM_PROMPT, prompt)
        msg = str(data.get("message") or "").strip()
        validated = validate_discovery_reply(msg, voice, deterministic_msg)
        return validated
    except LLMError as exc:
        log.info("Discovery prompt synthesis failed, using deterministic: %s", exc)
        return deterministic_msg
