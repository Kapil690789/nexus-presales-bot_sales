from __future__ import annotations

from backend.app.agents.brief import ProjectBrief, named_features

DISCOVERY_PROMPTS = {
    "service": "What are you looking to build — mobile, web, AI, or design?",
    "goal": "What should this first version actually do for people?",
    "features": "Which features do you want in v1? Pick any that matter, or type your own list.",
    "feature_detail": "What should those features actually do in the first version?",
    "user_flow": "If you already have a user journey (sign up, core action, result), sketch it. You can skip this.",
    "platforms": "Which platforms matter for the first release?",
    "users": "Who is the first person this should work well for?",
    "integrations": "Any systems this needs to talk to on day one?",
    "timeline": "When would you like a first version in people's hands?",
    "budget_band": "Which budget range should I size this against? It's only a first pass, not a quote.",
    "decision_role": "What's your role when this decision gets made?",
    "company_size": "Roughly how large is the company?",
}

REPHRASED_PROMPTS = {
    "service": "No problem! What type of product or application are you hoping to create?",
    "goal": "To help us picture this, what is the main problem this first version will solve for users?",
    "features": "What are the essential building blocks or capabilities you imagine for v1?",
    "feature_detail": "Could you describe in simple terms what users will do in this feature?",
    "user_flow": "How do you envision someone signing up and using this from start to finish?",
    "platforms": "Where would your target audience primarily use this — on mobile devices or in a web browser?",
    "users": "Who do you picture using this first — end consumers, business clients, or your own team?",
    "integrations": "Will this connect with any outside systems, like payments, email, or a CRM?",
    "timeline": "Is there a target milestone or launch timeframe you have in mind?",
    "budget_band": "What rough budget range or scale makes sense for this initial phase?",
    "decision_role": "What is your role or involvement in deciding on this project?",
    "company_size": "Roughly what size or stage is your organization right now?",
}

BOOK_CHIP = {"label": "Book a meeting", "field": "booking_window", "value": "this_week"}
PORTFOLIO_CHIP = {"label": "See similar work", "field": "show_portfolio", "value": "yes"}


def _feature_names(brief: ProjectBrief | None) -> str:
    names = named_features(brief) if brief else []
    if not names:
        return "those features"
    if len(names) == 1:
        return names[0]
    if len(names) == 2:
        return f"{names[0]} and {names[1]}"
    return ", ".join(names[:-1]) + f", and {names[-1]}"


def prompt_for(brief: ProjectBrief | None, field: str | None, repeat: bool = False) -> str:
    if field == "features" and brief and named_features(brief) and not brief.features_confirmed:
        return f"Got it: {_feature_names(brief)}. Any other features for v1, or is that the list?"
    if field == "feature_detail":
        return f"You mentioned {_feature_names(brief)}. What should each of those do in the first version?"
    if repeat and field in REPHRASED_PROMPTS:
        return REPHRASED_PROMPTS[field]
    return DISCOVERY_PROMPTS.get(field or "", "What should we confirm next?")


def chips_for_field(field: str, brief: ProjectBrief | None = None, repeat: bool = False) -> list[dict]:
    chips: list[dict] = []
    if field == "service":
        chips = [
            {"label": "Mobile app", "field": "service", "value": "mobile_app"},
            {"label": "Web app", "field": "service", "value": "web_app"},
            {"label": "AI product", "field": "service", "value": "ai_product"},
            {"label": "UI/UX", "field": "service", "value": "ui_ux"},
        ]
    elif field == "goal":
        chips = []
    elif field == "features":
        chips = [
            {"label": "Login & accounts", "field": "features", "value": ["Login & accounts"]},
            {"label": "Payments", "field": "features", "value": ["Payments"]},
            {"label": "Admin", "field": "features", "value": ["Admin"]},
            {"label": "Not sure yet", "field": "features", "value": []},
        ]
        if brief and named_features(brief):
            chips.append({"label": "That's all", "field": "features_done", "value": "yes"})
    elif field == "feature_detail":
        chips = [{"label": "That's enough", "field": "feature_detail", "value": "not_specified"}]
    elif field == "user_flow":
        chips = [{"label": "Skip for now", "field": "user_flow", "value": "not_specified"}]
    elif field == "users":
        chips = [
            {"label": "Consumers", "field": "users", "value": "consumers"},
            {"label": "Business users", "field": "users", "value": "business"},
            {"label": "Internal team", "field": "users", "value": "internal"},
        ]
    elif field == "platforms":
        if brief and brief.service in ("web_app", "ai_product"):
            chips = [
                {"label": "Web", "field": "platforms", "value": ["web"]},
                {"label": "API", "field": "platforms", "value": ["api"]},
            ]
        elif brief and brief.service == "mobile_app":
            chips = [
                {"label": "iOS", "field": "platforms", "value": ["ios"]},
                {"label": "Android", "field": "platforms", "value": ["android"]},
                {"label": "iOS and Android", "field": "platforms", "value": ["ios", "android"]},
            ]
        else:
            chips = [
                {"label": "iOS", "field": "platforms", "value": ["ios"]},
                {"label": "Android", "field": "platforms", "value": ["android"]},
                {"label": "iOS and Android", "field": "platforms", "value": ["ios", "android"]},
                {"label": "Web", "field": "platforms", "value": ["web"]},
            ]
    elif field == "integrations":
        chips = [
            {"label": "None on day one", "field": "integrations", "value": ["none"]},
            {"label": "Payments", "field": "integrations", "value": ["payments"]},
            {"label": "CRM", "field": "integrations", "value": ["crm"]},
        ]
    elif field == "timeline":
        chips = [
            {"label": "ASAP", "field": "timeline", "value": "asap"},
            {"label": "1–3 months", "field": "timeline", "value": "1_3_months"},
            {"label": "3–6 months", "field": "timeline", "value": "3_6_months"},
            {"label": "Flexible", "field": "timeline", "value": "flexible"},
        ]
    elif field == "budget_band":
        chips = [
            {"label": "Still exploring", "field": "budget_band", "value": "exploring"},
            {"label": "Under $15k", "field": "budget_band", "value": "under_15k"},
            {"label": "$15–40k", "field": "budget_band", "value": "15_40k"},
            {"label": "$40–80k", "field": "budget_band", "value": "40_80k"},
            {"label": "$80k+", "field": "budget_band", "value": "80k_plus"},
        ]
    elif field == "decision_role":
        chips = [
            {"label": "Founder / exec", "field": "decision_role", "value": "founder_or_exec"},
            {"label": "Product or ops", "field": "decision_role", "value": "product_or_ops_lead"},
            {"label": "Manager", "field": "decision_role", "value": "manager"},
            {"label": "Student / intern", "field": "decision_role", "value": "intern_or_student"},
        ]
    elif field == "company_size":
        chips = [
            {"label": "Startup", "field": "company_size", "value": "startup"},
            {"label": "SMB", "field": "company_size", "value": "smb"},
            {"label": "Mid-market", "field": "company_size", "value": "mid_market"},
            {"label": "Enterprise", "field": "company_size", "value": "enterprise"},
        ]

    if repeat and chips and not any(c.get("label") == "Not sure yet" for c in chips):
        skip_val = [] if field in ("platforms", "features", "integrations") else "not_sure"
        chips.append({"label": "Not sure yet", "field": field, "value": skip_val})

    return chips


def opening(brief: ProjectBrief | None = None) -> tuple[str, list[dict]]:
    return DISCOVERY_PROMPTS["service"], chips_for_field("service")
