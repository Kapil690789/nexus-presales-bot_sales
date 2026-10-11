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
    '  "ai_features": [] | ["Feature 1", "Feature 2"],\n'
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
    "6. If the user mentions AI, LLM, or chatbot capabilities alongside a mobile or web app, include them in ai_features and keep service as mobile_app or web_app.\n"
)


def _heuristic_extract(
    text: str,
    pending_field: str | None = None,
    brief: ProjectBrief | None = None,
    out_of_scope: list[str] | None = None,
) -> dict[str, Any]:
    import re
    lowered = text.lower().strip()
    res: dict[str, Any] = {}

    # Check off-topic
    if any(token in lowered for token in ("world cup", "fifa", "binary search", "recipe", "capital of", "president of", "tell me a joke", "write a poem", "write code for")):
        res["is_off_topic"] = True
        return res

    # Check out of scope
    oos_tokens = (
        ("homework", "student project", "crypto", "web3", "shopify")
        if out_of_scope is None
        else tuple(t.lower().strip() for t in out_of_scope if t and t.strip())
    )
    if any(token in lowered for token in oos_tokens):
        res["service"] = "out_of_scope"
        return res

    # Check question
    is_q_start = bool(re.match(r"^(how|what|who|why|when|where|can|do|does|is|are|have|tell me about)\b", lowered))
    has_question_mark = "?" in lowered
    is_q_inquiry = bool(re.search(r"\b(i\s+want\s+to\s+know|i'?d\s+like\s+to\s+know|i\s+would\s+like\s+to\s+know|i\s+would\s+like\s+to\s+understand|want\s+to\s+understand|wondering|curious|need\s+more\s+(info|information|details)|looking\s+for\s+(info|information|details)|more\s+about)\b", lowered))
    is_your_noun = bool(re.match(r"^\s*your\s+[a-z0-9_-]+(\s+[a-z0-9_-]+){0,4}\s*$", lowered))
    is_brief_inquiry = any(k in lowered for k in ("we need", "i am", "founder", "budget is", "timeline is", "looking to build", "want to build", "building a", "need a"))

    if (is_q_start or has_question_mark or is_q_inquiry or is_your_noun) and not is_brief_inquiry and len(text.split()) < 15:
        res["is_question"] = True
        return res

    # Role
    if any(title in lowered for title in ("founder", "co-founder", "ceo", "cto", "cpo", "coo", "executive", "owner", "president", "director")):
        res["decision_role"] = "founder_or_exec"
    elif any(title in lowered for title in ("vp", "head of", "lead", "product manager", "project manager", "engineering lead")):
        res["decision_role"] = "product_or_ops_lead"
    elif any(title in lowered for title in ("student", "intern", "college")):
        third_person = bool(re.search(r"\b(my\s+cousin|his|her|their|friend|my\s+friend|our\s+intern|my\s+brother|my\s+sister)\b.{0,30}\b(student|intern|college)\b", lowered))
        if not third_person:
            res["decision_role"] = "intern_or_student"

    # Company size
    if any(term in lowered for term in ("startup", "early stage", "seed", "series a", "bootstrapped")):
        res["company_size"] = "startup"
    elif any(term in lowered for term in ("enterprise", "fortune", "corporation", "multinational")):
        res["company_size"] = "enterprise"

    # Platforms
    has_web_p = "web" in lowered or "browser" in lowered
    has_ios_p = "ios" in lowered or "iphone" in lowered
    has_android_p = "android" in lowered
    has_mobile_p = "mobile" in lowered or "both" in lowered or "phone" in lowered

    if (has_web_p and (has_mobile_p or (has_ios_p and has_android_p))) or ("web and mobile" in lowered or "mobile and web" in lowered):
        res["platforms"] = ["web", "ios", "android"]
    elif has_web_p and has_ios_p:
        res["platforms"] = ["web", "ios"]
    elif has_web_p and has_android_p:
        res["platforms"] = ["web", "android"]
    elif (has_ios_p and has_android_p) or has_mobile_p:
        res["platforms"] = ["ios", "android"]
    elif has_ios_p:
        res["platforms"] = ["ios"]
    elif has_android_p:
        res["platforms"] = ["android"]
    elif has_web_p or "saas" in lowered or "portal" in lowered:
        res["platforms"] = ["web"]

    # AI detection regex with word boundary
    has_ai = bool(re.search(r"\b(ai|llm|gpt|chatgpt|openai|chatbot|chat bot|machine learning|nlp)\b", lowered))

    # Service
    if "mobile" in lowered or "ios" in lowered or "android" in lowered or "cross-platform" in lowered:
        res["service"] = "mobile_app"
    elif "web" in lowered or "saas" in lowered or "portal" in lowered:
        res["service"] = "web_app"
    elif has_ai:
        res["service"] = "ai_product"

    # If AI is mentioned but the resolved service is not ai_product, set ai_features
    if has_ai:
        resolved_service = res.get("service") or (brief.service if brief else None)
        if resolved_service and resolved_service != "ai_product":
            res["ai_features"] = ["AI chat"] if "chat" in lowered else ["AI features"]

    # Features (comma or 'and' separated list when features pending or goal exists)
    if (pending_field == "features" or (brief and not brief.features and brief.goal)) and ("," in text or " and " in text):
        clean_msg = text
        for prefix in ("features:", "for the first release we just need", "we just need", "we need"):
            if prefix in clean_msg.lower():
                idx_p = clean_msg.lower().find(prefix) + len(prefix)
                clean_msg = clean_msg[idx_p:]
        raw_items = [re.sub(r"^(and\s+|a\s+|an\s+|the\s+)", "", part.strip(), flags=re.IGNORECASE).strip() for part in re.split(r",|\band\b", clean_msg)]
        valid_items = [
            it.rstrip(".,!?;:") for it in raw_items
            if it and 1 <= len(it.split()) <= 6
            and not any(k in it.lower() for k in ("budget", "month", "founder", "ios", "android", "dollar", "timeline"))
        ]
        if len(valid_items) >= 2:
            res["features"] = valid_items

    # Timeline
    if any(term in lowered for term in ("urgently", "asap", "immediate", "rush", "this month")):
        res["timeline"] = "asap"
    elif any(term in lowered for term in ("2 months", "1 month", "3 months", "2-3 months", "2 to 3 months", "60 days", "8 weeks", "two months", "one month")):
        res["timeline"] = "1_3_months"
    elif any(term in lowered for term in ("4 months", "5 months", "6 months", "3-6 months", "3 to 6 months", "half year")):
        res["timeline"] = "3_6_months"
    elif "flexible" in lowered:
        res["timeline"] = "flexible"

    # Budget — only match if there is a currency indicator or explicitly in budget context
    has_budget_context = bool(re.search(r"(\$|usd|dollars?|budget|spend|invest)", lowered))
    has_user_metric = bool(re.search(r"\b(users?|visitors?|people|accounts|downloads?|devices?)\b", lowered))

    budget_nums = []
    if has_budget_context or (not has_user_metric and re.search(r"\$\d+|\d+k\b", lowered)):
        budget_nums = [int(n) for n in re.findall(r"\$?(\d+)k\b", lowered)]
        if not budget_nums and has_budget_context:
            comma_nums = [int(n.replace(",", "")) for n in re.findall(r"\$?([\d,]{4,9})\b", lowered) if "," in n]
            if comma_nums:
                budget_nums = [n // 1000 for n in comma_nums]
        if not budget_nums and has_budget_context:
            full_nums = [int(n.replace(",", "")) for n in re.findall(r"\$?(\d{4,6})\b", lowered)]
            if full_nums:
                budget_nums = [n // 1000 for n in full_nums]

    if budget_nums:
        max_b = max(budget_nums)
        if max_b <= 15:
            res["budget_band"] = "under_15k"
        elif max_b <= 40:
            res["budget_band"] = "15_40k"
        elif max_b <= 80:
            res["budget_band"] = "40_80k"
        else:
            res["budget_band"] = "80k_plus"

    # Goal
    if is_brief_inquiry or (pending_field == "goal" and not (is_q_start or has_question_mark)):
        sentences = [s.strip() for s in text.replace("\n", ". ").split(".") if s.strip()]
        for s in sentences:
            if any(w in s.lower() for w in ("need", "build", "want", "app for", "platform for", "startup", "product", "marketplace", "clinic", "system")):
                res["goal"] = s[:120].strip()
                break
        if "goal" not in res and sentences and not (is_q_start or has_question_mark):
            first_sent = sentences[0].strip()
            if len(first_sent.split()) >= 2 and not any(k in first_sent.lower() for k in ("hi", "hello", "thanks", "ok")):
                res["goal"] = first_sent[:120].strip()

    return res


def extract_slots(
    text: str,
    pending_field: str | None = None,
    brief: ProjectBrief | None = None,
    out_of_scope: list[str] | None = None,
) -> dict[str, Any]:
    cleaned = (text or "").strip()
    if not cleaned:
        return {}

    heuristic = _heuristic_extract(cleaned, pending_field, brief, out_of_scope=out_of_scope)
    if llm_available():
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
            if isinstance(data, dict) and data:
                merged = dict(heuristic)
                for k, v in data.items():
                    if v not in (None, "", [], False):
                        merged[k] = v
                if out_of_scope is not None and merged.get("service") == "out_of_scope":
                    lowered = cleaned.lower()
                    oos_tokens = tuple(t.lower().strip() for t in out_of_scope if t and t.strip())
                    if not any(tok in lowered for tok in oos_tokens):
                        merged.pop("service", None)
                return merged
        except LLMError as exc:
            error_cls = type(exc).__name__
            log.warning("Slot extraction fallback to heuristic: %s", error_cls)
            try:
                from backend.app.core.llm import record_system_event

                record_system_event(
                    kind="llm_failure",
                    reason=f"{error_cls} during extraction",
                    stage="extractor",
                    error_class=error_cls,
                )
            except Exception:
                pass

    return heuristic


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
        if not brief.service:
            if any(p in ("ios", "android") for p in brief.platforms):
                brief.service = "mobile_app"
            elif "web" in [p.lower() for p in brief.platforms]:
                brief.service = "web_app"

    # 4. Goal
    if extracted.get("goal") and not brief.goal:
        brief.goal = str(extracted["goal"]).strip()
        applied_any = True

    # 5. Features
    if extracted.get("features") and not brief.features:
        brief.features = [str(f).strip() for f in extracted["features"] if str(f).strip()]
        brief.features_confirmed = True
        applied_any = True

    # 5b. AI features
    if extracted.get("ai_features"):
        existing = set(brief.ai_features or [])
        new_items = [str(f).strip() for f in extracted["ai_features"] if str(f).strip()]
        for item in new_items:
            if item not in existing:
                brief.ai_features.append(item)
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
        role_val = str(extracted["decision_role"]).strip()
        if role_val == "intern_or_student":
            brief.role_unconfirmed = True
            applied_any = True
        else:
            brief.decision_role = role_val
            brief.role_unconfirmed = False
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
