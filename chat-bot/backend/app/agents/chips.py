from backend.app.agents.brief import ProjectBrief
from backend.app.engines.calendar import slot_chips

DISCOVERY_PROMPTS = {
    "service": "What are you looking to build — mobile, web, AI, or design?",
    "goal": "In one sentence, what should the first release achieve?",
    "platforms": "Which platforms matter for the first release?",
    "users": "Who is the first user?",
    "integrations": "Any systems this must talk to on day one?",
    "timeline": "When do you want a first version in people's hands?",
    "budget_band": "Which budget band should I estimate against? This stays indicative.",
    "decision_role": "What's your role in the decision?",
    "company_size": "Roughly how large is the company?",
}

ACTION_CHIP_FIELDS = {
    "show_portfolio",
    "show_mvp",
    "continue_contact",
    "booking_window",
    "booking_slot",
    "nda",
    "download_ics",
    "close_out",
}

DISQUALIFIED_CHIPS = [
    {"label": "Book a call", "field": "booking_window", "value": "this_week"},
    {"label": "Thank you", "field": "close_out", "value": "thanks"},
]


def chips_for_field(brief: ProjectBrief, field: str) -> list[dict]:
    if field == "service":
        return [
            {"label": "Mobile app", "field": "service", "value": "mobile_app"},
            {"label": "Web app / SaaS", "field": "service", "value": "web_app"},
            {"label": "AI product", "field": "service", "value": "ai_product"},
            {"label": "UI/UX only", "field": "service", "value": "ui_ux"},
        ]
    if field == "platforms":
        if brief.service == "mobile_app":
            return [
                {"label": "iOS", "field": "platforms", "value": ["ios"]},
                {"label": "Android", "field": "platforms", "value": ["android"]},
                {"label": "iOS + Android", "field": "platforms", "value": ["both"]},
            ]
        return [
            {"label": "Web", "field": "platforms", "value": ["web"]},
            {"label": "API only", "field": "platforms", "value": ["api"]},
        ]
    if field == "users":
        return [
            {"label": "Consumers", "field": "users", "value": "consumers"},
            {"label": "Business users", "field": "users", "value": "business"},
            {"label": "Internal team", "field": "users", "value": "internal"},
        ]
    if field == "integrations":
        return [
            {"label": "None yet", "field": "integrations", "value": ["none"]},
            {"label": "Stripe", "field": "integrations", "value": ["stripe"]},
            {"label": "Salesforce", "field": "integrations", "value": ["salesforce"]},
        ]
    if field == "timeline":
        return [
            {"label": "ASAP", "field": "timeline", "value": "asap"},
            {"label": "1–3 months", "field": "timeline", "value": "1_3_months"},
            {"label": "3–6 months", "field": "timeline", "value": "3_6_months"},
            {"label": "Flexible", "field": "timeline", "value": "flexible"},
        ]
    if field == "budget_band":
        return [
            {"label": "Still exploring", "field": "budget_band", "value": "exploring"},
            {"label": "Under $15k", "field": "budget_band", "value": "under_15k"},
            {"label": "$15–40k", "field": "budget_band", "value": "15_40k"},
            {"label": "$40–80k", "field": "budget_band", "value": "40_80k"},
            {"label": "$80k+", "field": "budget_band", "value": "80k_plus"},
        ]
    if field == "decision_role":
        return [
            {"label": "Founder / exec", "field": "decision_role", "value": "founder_or_exec"},
            {"label": "Product / ops lead", "field": "decision_role", "value": "product_or_ops_lead"},
            {"label": "Manager", "field": "decision_role", "value": "manager"},
            {"label": "Exploring for class / internship", "field": "decision_role", "value": "intern_or_student"},
        ]
    if field == "company_size":
        return [
            {"label": "Startup", "field": "company_size", "value": "startup"},
            {"label": "SMB", "field": "company_size", "value": "smb"},
            {"label": "Mid-market", "field": "company_size", "value": "mid_market"},
            {"label": "Enterprise", "field": "company_size", "value": "enterprise"},
        ]
    return []


def chips_for(brief: ProjectBrief, stage: str) -> list[dict]:
    if stage == "discovery":
        if not brief.service:
            return chips_for_field(brief, "service")
        if not brief.platforms:
            return chips_for_field(brief, "platforms")
        if not brief.users:
            return chips_for_field(brief, "users")
        if not brief.integrations:
            return chips_for_field(brief, "integrations")
        if not brief.timeline:
            return chips_for_field(brief, "timeline")
        if not brief.budget_band:
            return chips_for_field(brief, "budget_band")
        if not brief.decision_role:
            return chips_for_field(brief, "decision_role")
        if not brief.company_size:
            return chips_for_field(brief, "company_size")
    if stage in {"estimation", "solutioning"}:
        return [
            {"label": "Show MVP cut", "field": "show_mvp", "value": "yes"},
            {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
            {"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
        ]
    if stage == "booking":
        return slot_chips("this_week")
    return []
