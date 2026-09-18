import re
from typing import Any

from backend.app.agents.brief import ProjectBrief

SERVICE_ALIASES = {
    "mobile app": "mobile_app",
    "ios app": "mobile_app",
    "android app": "mobile_app",
    "react native": "mobile_app",
    "flutter": "mobile_app",
    "web app": "web_app",
    "web application": "web_app",
    "web ops": "web_app",
    "ops console": "web_app",
    "saas": "web_app",
    "dashboard": "web_app",
    "website": "web_app",
    "webpage": "web_app",
    "web site": "web_app",
    "web page": "web_app",
    "ai": "ai_product",
    "chatbot": "ai_product",
    "assistant": "ai_product",
    "ui/ux": "ui_ux",
    "staff": "staff_augmentation",
}
OUT_OF_SCOPE = {"shopify theme": "shopify_only", "crypto": "crypto_web3", "web3": "crypto_web3", "brochure": "pure_marketing_site"}
SITE_RE = re.compile(r"web\s*site|web\s*page", re.I)
MARKETING_SITE_NEEDLES = (
    "brochure",
    "landing page",
    "marketing site",
    "personal website",
    "personal webpage",
    "portfolio site",
    "normal webpage",
    "normal web page",
)
BUDGET_RULES = [
    (re.compile(r"80\s*k|\b80,000\b|above 80|over 80", re.I), "80k_plus"),
    (re.compile(r"40\s*k|40,000|50k|60k|70k", re.I), "40_80k"),
    (re.compile(r"15\s*k|15,000|20k|25k|30k", re.I), "15_40k"),
    (re.compile(r"under 15|less than 15|10k|8k|small budget", re.I), "under_15k"),
    (re.compile(r"not sure|explor|no budget|tbd", re.I), "exploring"),
]
TIMELINE_RULES = [
    (re.compile(r"asap|next month|4 weeks|urgent", re.I), "asap"),
    (re.compile(r"1[-– ]?3 month|8 weeks|12 weeks|quarter", re.I), "1_3_months"),
    (re.compile(r"3[-– ]?6 month|half year", re.I), "3_6_months"),
    (re.compile(r"flexib|no rush|when ready", re.I), "flexible"),
]
ROLE_RULES = [
    (re.compile(r"founder|ceo|cto|owner|director|exec", re.I), "founder_or_exec"),
    (re.compile(r"product|ops lead|head of", re.I), "product_or_ops_lead"),
    (re.compile(r"manager", re.I), "manager"),
    (re.compile(r"\b(?:interns?|internship|students?)\b|homework|college", re.I), "intern_or_student"),
    (re.compile(r"agency|reseller|white label", re.I), "agency_or_reseller"),
]
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")
SMALLTALK_RE = re.compile(
    r"^(hi|hello|hey|thanks|thank you|ok|okay|yo|good morning|good afternoon)[\s!.]*$",
    re.I,
)
LIST_FIELDS = {"platforms", "integrations", "ai_features", "constraints"}
BOOL_FIELDS = {"auth", "admin", "realtime", "marketplace"}
STRING_FIELDS = {"goal", "users", "industry"}
SKIP_GOAL_TOKENS = ("my email", "@", "nda", "book", "schedule")


def _looks_like_marketing_site(text: str) -> bool:
    lowered = text.lower()
    if any(needle in lowered for needle in MARKETING_SITE_NEEDLES):
        return True
    if not SITE_RE.search(lowered):
        return False
    return any(needle in lowered for needle in ("general info", "about me", "personal", "marketing", "portfolio"))


def _maybe_capture_goal(brief: ProjectBrief, text: str) -> None:
    if brief.goal or not (brief.service or brief.out_of_scope):
        return
    stripped = (text or "").strip()
    if len(stripped) < 12 or stripped.startswith("__") or SMALLTALK_RE.match(stripped):
        return
    lowered = stripped.lower()
    if any(token in lowered for token in SKIP_GOAL_TOKENS):
        return
    brief.goal = stripped[:240]


def extract_from_text(brief: ProjectBrief, text: str) -> ProjectBrief:
    """High-precision keyword extract. Does not treat the whole message as the goal."""
    lowered = text.lower()
    if _looks_like_marketing_site(text):
        brief.out_of_scope = "pure_marketing_site"
    if not brief.out_of_scope:
        for needle, code in OUT_OF_SCOPE.items():
            if needle in lowered:
                brief.out_of_scope = code
                break
    if not brief.service and not brief.out_of_scope:
        for needle, service in SERVICE_ALIASES.items():
            if needle in lowered:
                brief.service = service
                break
    for token in ("ios", "android", "both", "web"):
        if token in lowered and token not in brief.platforms:
            if token != "both" or brief.service == "mobile_app":
                brief.platforms.append(token)
    if "auth" in lowered or "login" in lowered:
        brief.auth = True
    if "admin" in lowered:
        brief.admin = True
    if "realtime" in lowered or "real-time" in lowered:
        brief.realtime = True
    if "marketplace" in lowered:
        brief.marketplace = True
        brief.industry = brief.industry or "marketplace"
    for pattern, band in BUDGET_RULES:
        if pattern.search(text):
            brief.budget_band = band
            break
    for pattern, value in TIMELINE_RULES:
        if pattern.search(text):
            brief.timeline = value
            break
    for pattern, value in ROLE_RULES:
        if pattern.search(text):
            brief.decision_role = value
            break
    for vendor in ("stripe", "shopify", "salesforce", "hubspot", "firebase", "twilio"):
        if vendor in lowered and vendor not in brief.integrations:
            brief.integrations.append(vendor)
    if "no integration" in lowered and "none" not in brief.integrations:
        brief.integrations.append("none")
    if "patient" in lowered or "clinic" in lowered or "hipaa" in lowered:
        brief.industry = brief.industry or "health"
    _maybe_capture_goal(brief, text)
    return brief


def capture_goal_reply(brief: ProjectBrief, text: str) -> ProjectBrief:
    """Offline wizard only: the answer to the goal prompt becomes the goal.

    The LLM path must extract `goal` via `brief_updates` instead of grabbing
    whatever the visitor last typed — except when extract already captured a
    stated goal from a real project description.
    """
    if brief.goal or not (text or "").strip():
        return brief
    missing = brief.missing_discovery()
    if not (brief.service or brief.out_of_scope or (missing and missing[0] == "goal")):
        return brief
    _maybe_capture_goal(brief, text)
    return brief


def extract_contact(text: str) -> dict[str, str]:
    found: dict[str, str] = {}
    email = EMAIL_RE.search(text or "")
    if email:
        found["email"] = email.group(0)
    phone = PHONE_RE.search(text or "")
    if phone:
        found["phone"] = re.sub(r"\s+", " ", phone.group(0)).strip()
    return found


def apply_payload(brief: ProjectBrief, chip: dict[str, Any] | None, text: str) -> ProjectBrief:
    if chip:
        brief.apply_chip(str(chip.get("field") or ""), chip.get("value"))
    return extract_from_text(brief, text or "")


def _enum_values(config: Any, field: str) -> set[str] | None:
    if field == "service":
        return set(config.services.in_scope)
    if field == "budget_band":
        return {str(key) for key in config.qualification.budget_bands}
    if field == "timeline":
        return {str(key) for key in config.qualification.timeline_scores}
    if field == "decision_role":
        return {str(key) for key in config.qualification.decision_role_scores}
    if field == "company_size":
        return {str(key) for key in config.qualification.company_size_scores}
    if field == "out_of_scope":
        return set(config.services.out_of_scope)
    return None


def apply_brief_updates(brief: ProjectBrief, payload: Any, config: Any) -> ProjectBrief:
    """Merge model-extracted fields. Invalid or empty values are ignored."""
    if not isinstance(payload, dict):
        return brief
    for field, value in payload.items():
        if field not in brief.model_fields or field.startswith("_"):
            continue
        if value in (None, "", [], {}):
            continue
        allowed = _enum_values(config, field)
        if field in LIST_FIELDS:
            items = value if isinstance(value, list) else [value]
            current = list(getattr(brief, field) or [])
            for item in items:
                text = str(item).strip()
                if not text:
                    continue
                if allowed is not None and text not in allowed:
                    continue
                if text not in current:
                    current.append(text)
            setattr(brief, field, current)
            continue
        if field in BOOL_FIELDS:
            setattr(brief, field, value if isinstance(value, bool) else str(value).lower() in {"true", "yes", "1"})
            continue
        if isinstance(value, list):
            value = value[0] if value else None
        if value in (None, ""):
            continue
        if field in STRING_FIELDS:
            text = str(value).strip()[:240]
            if text:
                setattr(brief, field, text)
            continue
        text = str(value).strip()
        if allowed is not None and text not in allowed:
            continue
        setattr(brief, field, text)
    return brief


def _canonical_stack(name: str, allowed: list[str]) -> str | None:
    needle = name.strip().lower()
    if not needle:
        return None
    for item in allowed:
        if item.lower() == needle:
            return item
    return None


def _string_list(value: Any, cap: int = 6) -> list[str]:
    if not isinstance(value, list):
        return []
    out: list[str] = []
    for item in value:
        text = str(item).strip()[:240]
        if text and text not in out:
            out.append(text)
        if len(out) >= cap:
            break
    return out


def apply_architecture(current: dict | None, payload: Any, config: Any, service_key: str | None) -> dict:
    """Overlay model stack picks. Unknown stacks are dropped; empty overlay keeps the engine rec."""
    baseline = dict(current or {"frontend": [], "backend": [], "notes": []})
    if not isinstance(payload, dict):
        return baseline
    allowed: list[str] = []
    service = (config.services.in_scope or {}).get(service_key) if service_key else None
    if service:
        allowed.extend(service.stacks)
        allowed.extend(service.backend_stacks)
    allowed.extend(baseline.get("frontend") or [])
    allowed.extend(baseline.get("backend") or [])
    frontend = [_canonical_stack(str(item), allowed) for item in (payload.get("frontend") or [])]
    backend = [_canonical_stack(str(item), allowed) for item in (payload.get("backend") or [])]
    frontend = [item for item in frontend if item]
    backend = [item for item in backend if item]
    notes = _string_list(payload.get("notes"), cap=6)
    if frontend:
        baseline["frontend"] = frontend
    if backend:
        baseline["backend"] = backend
    if notes:
        baseline["notes"] = notes
    return baseline


def apply_mvp(current: dict | None, payload: Any) -> dict:
    """Overlay model MVP/later lists. Empty overlay keeps the engine cut."""
    baseline = dict(current or {"mvp": [], "later": [], "rationale": ""})
    if not isinstance(payload, dict):
        return baseline
    mvp = _string_list(payload.get("mvp"), cap=6)
    later = _string_list(payload.get("later"), cap=6)
    rationale = str(payload.get("rationale") or "").strip()[:400]
    if mvp:
        baseline["mvp"] = mvp
    if later:
        baseline["later"] = later
    if rationale:
        baseline["rationale"] = rationale
    return baseline
