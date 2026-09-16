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
    "saas": "web_app",
    "dashboard": "web_app",
    "ai": "ai_product",
    "chatbot": "ai_product",
    "assistant": "ai_product",
    "ui/ux": "ui_ux",
    "staff": "staff_augmentation",
}
OUT_OF_SCOPE = {"shopify theme": "shopify_only", "crypto": "crypto_web3", "web3": "crypto_web3", "brochure": "pure_marketing_site"}
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
    (re.compile(r"intern|student|homework|college", re.I), "intern_or_student"),
    (re.compile(r"agency|reseller|white label", re.I), "agency_or_reseller"),
]
EMAIL_RE = re.compile(r"[A-Z0-9._%+-]+@[A-Z0-9.-]+\.[A-Z]{2,}", re.I)
PHONE_RE = re.compile(r"\+?\d[\d\s().-]{7,}\d")


def extract_from_text(brief: ProjectBrief, text: str) -> ProjectBrief:
    lowered = text.lower()
    if not brief.service:
        for needle, service in SERVICE_ALIASES.items():
            if needle in lowered:
                brief.service = service
                break
    for needle, code in OUT_OF_SCOPE.items():
        if needle in lowered:
            brief.out_of_scope = code
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
    if not brief.goal and len(text.strip()) > 24 and not text.strip().startswith("__"):
        if not any(token in lowered for token in ("my email", "@", "nda", "book", "schedule")):
            brief.goal = text.strip()[:240]
    if "patient" in lowered or "clinic" in lowered or "hipaa" in lowered:
        brief.industry = brief.industry or "health"
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
