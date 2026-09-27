from backend.app.agents.brief import ProjectBrief, next_discovery_field
from backend.app.engines.calendar import slot_chips

DISCOVERY_PROMPTS = {
    "service": "What are you looking to build — mobile, web, AI, or design?",
    "goal": "What should this first version actually do for people?",
    "features": "Which capabilities matter in v1 — the ones you'd be unhappy to ship without?",
    "user_flow": "If you already have a user journey (sign up → core action → result), sketch it. If not, we can skip this.",
    "platforms": "Which platforms matter for the first release?",
    "users": "Who is the first person this should work well for?",
    "integrations": "Any systems this needs to talk to on day one?",
    "timeline": "When would you like a first version in people's hands?",
    "budget_band": "Which budget range should I size this against? It's only a first pass, not a quote.",
    "decision_role": "What's your role when this decision gets made?",
    "company_size": "Roughly how large is the company?",
}

CONTACT_CHIP = {"label": "Talk with the team", "field": "continue_contact", "value": "yes"}

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
    if field == "features":
        return [
            {"label": "Login & accounts", "field": "features", "value": ["Login & accounts"]},
            {"label": "Payments", "field": "features", "value": ["Payments"]},
            {"label": "Admin", "field": "features", "value": ["Admin"]},
            {"label": "Notifications", "field": "features", "value": ["Notifications"]},
            {"label": "Not sure yet — give me a range", "field": "features", "value": "skipped"},
        ]
    if field == "user_flow":
        return [
            {"label": "No flow yet", "field": "user_flow", "value": "not_specified"},
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


def chips_for(brief: ProjectBrief, stage: str, style: dict | None = None) -> list[dict]:
    if stage == "discovery":
        field = next_discovery_field(brief, style)
        chips = chips_for_field(brief, field) if field else []
        if chips:
            return chips
        # Goal is typed, not chipped. Keep page-aware shortcuts (e.g. iOS/Android).
        if field == "goal" and not brief.platforms:
            return chips_for_field(brief, "platforms")
        return []
    if stage in {"estimation", "solutioning"}:
        return [
            {"label": "Show MVP cut", "field": "show_mvp", "value": "yes"},
            {"label": "Show relevant work", "field": "show_portfolio", "value": "yes"},
            CONTACT_CHIP,
        ]
    if stage == "booking":
        return slot_chips("this_week")
    return []
