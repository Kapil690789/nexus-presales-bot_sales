import re

from backend.app.agents.brief import ProjectBrief, named_features

LEADING_GOAL_PREFIXES = re.compile(
    r"^(i\s+am\s+building|i'?m\s+building|we\s+are\s+building|we'?re\s+building|"
    r"i\s+am|i'?m|we\s+are|we'?re|we\s+want\s+to\s+build|we\s+want|we\s+need\s+to\s+build|we\s+need|"
    r"i\s+want\s+to\s+build|i\s+want|i\s+need\s+to\s+build|i\s+need|"
    r"looking\s+to\s+build|looking\s+to|planning\s+to\s+build|planning\s+to|"
    r"building|to\s+build|a|an|the)\b\s*",
    re.IGNORECASE,
)
TRAILING_FRAGMENTS = frozenset({"and", "for", "to", "of", "with", "in", "on", "the", "a", "an", "at", "by"})


def display_platforms(platforms: list[str] | None) -> str:
    if not platforms:
        return ""
    clean = [p.strip().lower() for p in platforms if p and p.strip()]
    has_web = "web" in clean
    has_ios = "ios" in clean or "both" in clean
    has_android = "android" in clean or "both" in clean

    if has_web and has_ios and has_android:
        return "web, iOS and Android"
    if has_ios and has_android:
        return "iOS and Android"
    if has_web and has_ios:
        return "web and iOS"
    if has_web and has_android:
        return "web and Android"
    if has_ios:
        return "iOS"
    if has_android:
        return "Android"
    if has_web:
        return "web"
    return ", ".join(platforms)


def goal_short(goal: str | None) -> str | None:
    if not goal:
        return None
    cleaned = goal.strip().rstrip(".,!?;:")
    while True:
        match = LEADING_GOAL_PREFIXES.match(cleaned)
        if match:
            cleaned = cleaned[match.end():].strip().lstrip(".,!?;:")
        else:
            break
    if not cleaned or len(cleaned) < 3:
        return None
    words = cleaned.split()
    if len(words) > 8:
        words = words[:8]
    while words and words[-1].lower().strip(".,!?;:") in TRAILING_FRAGMENTS:
        words.pop()
    if not words:
        return None
    res = " ".join(words).strip().rstrip(".,!?;:")
    if len(res) < 3:
        return None
    return res


def timeline_label(timeline: str | None) -> str:
    if not timeline:
        return ""
    t = timeline.strip().lower()
    if t == "asap":
        return "as soon as possible"
    if t in ("1_3_months", "1_3"):
        return "1 to 3 months"
    if t in ("3_6_months", "3_6"):
        return "3 to 6 months"
    if t == "flexible":
        return "flexible timing"
    return timeline.strip()


def budget_label(budget_band: str | None) -> str:
    if not budget_band:
        return ""
    b = budget_band.strip().lower()
    if b in ("under_15k", "under_15"):
        return "under $15k"
    if b in ("15_40k", "15_40"):
        return "$15k to $40k"
    if b in ("40_80k", "40_80"):
        return "$40k to $80k"
    if b in ("80k_plus", "80k+"):
        return "$80k or more"
    if b == "exploring":
        return "still exploring"
    return budget_band.strip()


def service_label_clean(service: str | None, in_scope_map: dict | None = None) -> str:
    if not service:
        return "digital product"
    if in_scope_map and service in in_scope_map:
        return in_scope_map[service].label.lower()
    return service.replace("_", " ").lower()


def service_article(label: str) -> str:
    cleaned = label.strip().lower()
    if cleaned and cleaned[0] in "aeiou":
        return "an"
    return "a"


DISCOVERY_PROMPTS = {
    "service": "What are you looking to build — mobile, web, AI, or design?",
    "goal": "What should this first version actually do for people?",
    "features": "Which core capabilities or features do you want for the initial launch? Pick any that matter, or type your own list.",
    "feature_detail": "What should those initial capabilities accomplish in the initial release?",
    "user_flow": "If you already have a user journey (sign up, core action, result), sketch it. You can skip this.",
    "platforms": "Which platforms matter for the first release?",
    "users": "Who is the first person this should work well for?",
    "integrations": "Any systems this needs to talk to on day one?",
    "timeline": "When would you like the initial version in users' hands?",
    "budget_band": "A rough ballpark helps me size this, no commitment — which budget range makes sense?",
    "decision_role": "What's your role when this decision gets made?",
    "company_size": "Roughly how large is the company?",
}

REPHRASED_PROMPTS = {
    "service": "I want to make sure I got that right: what type of digital product or application are you looking to create?",
    "goal": "To help us picture this, what is the main problem this first version will solve for users?",
    "features": "What essential building blocks or capabilities do you envision for the initial release?",
    "feature_detail": "Could you describe in simple terms what users will do in this feature?",
    "user_flow": "How do you envision someone signing up and using this from start to finish?",
    "platforms": "Where would your target audience primarily use this — on mobile devices or in a web browser?",
    "users": "Who do you picture using this first — end consumers, business clients, or your own team?",
    "integrations": "Will this connect with any outside systems, like payments, email, or a CRM?",
    "timeline": "Is there a target milestone or launch timeframe you have in mind?",
    "budget_band": "A rough ballpark helps me size this, no commitment: what investment scale are you aiming for?",
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
        return f"Added {_feature_names(brief)} — any other features for the launch, or ready to continue?"
    if field == "feature_detail":
        names = named_features(brief) if brief else []
        if len(names) == 1:
            return f"What should {names[0]} include in the initial release?"
        if len(names) >= 2:
            return f"What should each of {_feature_names(brief)} include in the initial release?"
        return DISCOVERY_PROMPTS.get("feature_detail", "What should those initial capabilities accomplish in the initial release?")
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
        existing = [item.lower().strip() for item in named_features(brief)] if brief else []
        svc = (brief.service or "").lower().strip() if brief else ""
        if svc == "ai_product":
            catalog = [
                {"label": "AI chat / Assistant", "value": "AI chat"},
                {"label": "Document processing", "value": "Document processing"},
                {"label": "User accounts & auth", "value": "User accounts"},
                {"label": "Payments & billing", "value": "Payments"},
                {"label": "Admin dashboard", "value": "Admin dashboard"},
            ]
        elif svc == "mobile_app":
            catalog = [
                {"label": "User login & profiles", "value": "User profiles"},
                {"label": "In-app payments", "value": "Payments"},
                {"label": "Push notifications", "value": "Push notifications"},
                {"label": "Search & discovery", "value": "Search & discovery"},
                {"label": "Admin portal", "value": "Admin portal"},
            ]
        elif svc == "web_app":
            catalog = [
                {"label": "User authentication", "value": "User authentication"},
                {"label": "Payment checkout", "value": "Payments"},
                {"label": "Admin dashboard", "value": "Admin dashboard"},
                {"label": "Analytics & reports", "value": "Analytics"},
                {"label": "Team collaboration", "value": "Team collaboration"},
            ]
        elif svc == "ui_ux":
            catalog = [
                {"label": "Design system & UI kit", "value": "Design system"},
                {"label": "Clickable prototype", "value": "Clickable prototype"},
                {"label": "User wireframes", "value": "User wireframes"},
                {"label": "Responsive design", "value": "Responsive design"},
            ]
        else:
            catalog = [
                {"label": "Login & accounts", "value": "Login & accounts"},
                {"label": "Payments", "value": "Payments"},
                {"label": "Admin", "value": "Admin"},
                {"label": "Analytics & reporting", "value": "Analytics"},
            ]

        from backend.app.engines.domains import detect_domain, get_domain_blueprint
        domain_id = detect_domain(brief=brief) if brief else None
        bp = get_domain_blueprint(domain_id) if domain_id else None
        if bp and bp.key_features:
            seen_vals = {item["value"].lower() for item in bp.key_features}
            catalog = list(bp.key_features) + [c for c in catalog if c["value"].lower() not in seen_vals]

        available = [
            item for item in catalog
            if item["value"].lower().strip() not in existing
            and not any(term in item["value"].lower() for term in existing)
        ]

        if brief and named_features(brief):
            chips.append({"label": "Continue to next step →", "field": "features_done", "value": "yes"})
            for item in available[:3]:
                chips.append({"label": f"+ {item['label']}", "field": "features", "value": [item["value"]]})
            chips.append({"label": "Ready with this list", "field": "features_done", "value": "yes"})
        else:
            for item in available[:4]:
                chips.append({"label": item["label"], "field": "features", "value": [item["value"]]})
            chips.append({"label": "Not sure yet", "field": "features", "value": []})
    elif field == "feature_detail":
        chips = [
            {"label": "Standard functionality is fine", "field": "feature_detail", "value": "not_specified"},
            {"label": "Skip & continue →", "field": "feature_detail", "value": "not_specified"},
        ]
    elif field == "user_flow":
        chips = [
            {"label": "Standard flow is fine", "field": "user_flow", "value": "not_specified"},
            {"label": "Skip for now →", "field": "user_flow", "value": "not_specified"},
        ]
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

    if repeat and chips:
        skip_val = [] if field in ("platforms", "features", "integrations") else "not_sure"
        if not any(c.get("label") == "Not sure yet" for c in chips):
            chips.append({"label": "Not sure yet", "field": field, "value": skip_val})
        if not any(c.get("label") == "Not sure, suggest" for c in chips):
            chips.append({"label": "Not sure, suggest", "field": field, "value": skip_val})

    return chips


def opening(brief: ProjectBrief | None = None) -> tuple[str, list[dict]]:
    return DISCOVERY_PROMPTS["service"], chips_for_field("service")
