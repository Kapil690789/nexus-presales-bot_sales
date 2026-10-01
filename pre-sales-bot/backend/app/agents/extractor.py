from __future__ import annotations

import logging
from typing import Any

from backend.app.agents.brief import ProjectBrief
from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available

log = logging.getLogger(__name__)

_EXTRACTOR_SYSTEM = (
    "You are a pre-sales discovery assistant that extracts project scope details from client messages into structured JSON.\n"
    f"{UNTRUSTED_RULE}\n"
    "Return JSON matching this exact schema:\n"
    "{\n"
    '  "service": null | "mobile_app" | "web_app" | "ai_product" | "ui_ux" | "staff_augmentation" | "out_of_scope",\n'
    '  "goal": null | "brief description of what the project does",\n'
    '  "platforms": [] | ["ios"] | ["android"] | ["ios", "android"] | ["web"],\n'
    '  "features": [] | ["Feature 1", "Feature 2"],\n'
    '  "feature_detail": null | "details on features",\n'
    '  "users": null | "consumers" | "business" | "internal",\n'
    '  "integrations": [] | ["payments", "crm", "none"],\n'
    '  "timeline": null | "asap" | "1_3_months" | "3_6_months" | "flexible",\n'
    '  "budget_band": null | "exploring" | "under_15k" | "15_40k" | "40_80k" | "80k_plus",\n'
    '  "decision_role": null | "founder_or_exec" | "product_or_ops_lead" | "manager" | "intern_or_student",\n'
    '  "company_size": null | "startup" | "smb" | "mid_market" | "enterprise",\n'
    '  "is_question": true | false,\n'
    '  "is_off_topic": true | false,\n'
    '  "uncertain": true | false\n'
    "}\n"
    "Rules:\n"
    "1. Only set fields that are explicitly mentioned or clearly implied in the message.\n"
    "2. If the user asks a question about services, pricing, stack, or project process, set is_question to true.\n"
    "3. If the user message is general trivia (e.g. world cup, history), non-software chat, or requests for standalone code scripts/algorithms, set is_off_topic to true.\n"
    "4. If the user says 'not sure', 'suggest something', 'no idea', set uncertain to true.\n"
    "5. If the requested work is specifically for homework, crypto, shopify, or web3, set service to 'out_of_scope'.\n"
)


def extract_slots(text: str, pending_field: str | None = None, brief: ProjectBrief | None = None) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned or not llm_available():
        return {}

    context = ""
    if brief:
        current_slots = {k: v for k, v in brief.model_dump().items() if v not in (None, "", [], False)}
        if current_slots:
            context = f"Known project details so far: {current_slots}\n"
    if pending_field:
        context += f"Currently asking user for: {pending_field}\n"

    user_prompt = f"{context}User message:\n{wrap_visitor(cleaned)}"
    try:
        data = complete_json(_EXTRACTOR_SYSTEM, user_prompt)
        if isinstance(data, dict):
            return data
    except LLMError as exc:
        log.info("Slot extraction fallback: %s", exc)
    return {}


def apply_extracted_slots(brief: ProjectBrief, extracted: dict[str, Any], pending_field: str | None = None) -> bool:
    if not extracted:
        return False

    applied_any = False

    # 1. Check out of scope
    if extracted.get("service") == "out_of_scope":
        brief.out_of_scope = "Out of scope request"
        return True

    # 2. Service
    if extracted.get("service") and not brief.service:
        brief.service = extracted["service"]
        applied_any = True

    # 3. Platforms
    if extracted.get("platforms") and not brief.platforms:
        brief.platforms = [p for p in extracted["platforms"] if isinstance(p, str)]
        applied_any = True

    # 4. Goal
    if extracted.get("goal") and not brief.goal:
        brief.goal = str(extracted["goal"]).strip()
        applied_any = True

    # 5. Features
    if extracted.get("features") and not brief.features:
        brief.features = [str(f).strip() for f in extracted["features"] if str(f).strip()]
        brief.features_confirmed = True
        applied_any = True

    # 6. Feature detail
    if extracted.get("feature_detail") and not brief.feature_detail:
        brief.feature_detail = str(extracted["feature_detail"]).strip()
        applied_any = True

    # 7. Users
    if extracted.get("users") and not brief.users:
        brief.users = str(extracted["users"]).strip()
        applied_any = True

    # 8. Integrations
    if extracted.get("integrations") and not brief.integrations:
        brief.integrations = [str(i).strip() for i in extracted["integrations"] if str(i).strip()]
        applied_any = True

    # 9. Timeline
    if extracted.get("timeline") and not brief.timeline:
        brief.timeline = str(extracted["timeline"]).strip()
        applied_any = True

    # 10. Budget band
    if extracted.get("budget_band") and not brief.budget_band:
        brief.budget_band = str(extracted["budget_band"]).strip()
        applied_any = True

    # 11. Decision role
    if extracted.get("decision_role") and not brief.decision_role:
        brief.decision_role = str(extracted["decision_role"]).strip()
        applied_any = True

    # 12. Company size
    if extracted.get("company_size") and not brief.company_size:
        brief.company_size = str(extracted["company_size"]).strip()
        applied_any = True

    # 13. If user is uncertain on pending field, apply sensible default
    if extracted.get("uncertain"):
        if pending_field == "budget_band" and not brief.budget_band:
            brief.budget_band = "15_40k"
            applied_any = True
        elif pending_field == "timeline" and not brief.timeline:
            brief.timeline = "1_3_months"
            applied_any = True
        elif pending_field == "platforms" and not brief.platforms:
            brief.platforms = ["ios", "android"]
            applied_any = True
        elif pending_field == "decision_role" and not brief.decision_role:
            brief.decision_role = "founder_or_exec"
            applied_any = True

    return applied_any
