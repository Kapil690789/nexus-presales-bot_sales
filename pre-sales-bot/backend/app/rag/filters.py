from __future__ import annotations

import re

TOPIC_PHRASES = {
    "delivery": (
        "how do you run a project",
        "discovery phase",
        "project progress",
        "stay updated",
        "code quality",
        "testing standards",
        "legacy codebase",
        "project management",
        "kick off",
        "kickoff",
        "scope changes",
        "scope change",
        "cross-browser",
        "cross-device",
        "technical documentation",
        "github",
        "gitlab",
    ),
    "pricing": (
        "project pricing",
        "pricing",
        "billing",
        "payment milestones",
    ),
    "legal": (
        "intellectual property",
        "source code",
        "gdpr",
        "hipaa",
        "soc 2",
        "pci",
        "terminate",
        "contracts",
        "master services",
    ),
    "security": (
        "client data",
        "confidential",
        "nda",
    ),
    "team": (
        "who will actually do the work",
        "scale a development team",
        "time zone",
        "time zones",
        "vet and select",
        "single point of contact",
        "trial period",
        "staff augmentation",
    ),
    "support": (
        "after launch",
        "ongoing support",
        "warranty",
        "on-call",
        "production outages",
        "emergency",
    ),
    "stack": (
        "technology stack",
        "tech stack",
        "cross-platform",
        "native apps",
        "machine learning",
        "llms",
        "llm",
    ),
    "design": (
        "ui/ux",
        "wireframes",
        "wireframe",
        "figma",
    ),
    "infra": (
        "migrating data",
        "data migration",
        "third-party",
        "payment gateways",
        "cloud infrastructure",
        "heavy user loads",
        "auto-scaling",
    ),
    "industries": (
        "which industries",
        "industries",
    ),
}

INDUSTRY_PHRASES = {
    "health": ("healthcare", "telehealth", "radiology", "clinic", "patient"),
    "fintech": ("fintech", "wallet", "lending", "micro-lending", "microlending", "defi", "fraud"),
    "retail": ("e-commerce", "ecommerce", "retail", "storefront", "inventory"),
    "logistics": ("logistics", "warehouse", "fleet", "dispatch"),
    "agriculture": ("agriculture", "agronom", "irrigation"),
    "media": ("paywall", "transcoder", "podcast", "publisher"),
    "real_estate": ("real estate", "virtual staging", "property manager"),
    "travel": ("travel agency", "booking engine"),
    "energy": ("smart grid", "clean-tech", "carbon"),
    "nonprofit": ("non-profit", "nonprofit", "donation"),
    "insurance": ("auto insurance", "insurance", "claims"),
    "hr": ("payroll",),
    "education": ("edtech", "classroom", "language school"),
    "aviation": ("aviation", "logbook"),
    "sales": ("crm",),
    "events": ("virtual event", "event organizer"),
    "security": ("threat intelligence", "soc analyst", "penetration"),
    "fitness": ("fitness",),
    "legal": ("contract analyzer", "legal counsel"),
    "hospitality": ("hospitality",),
    "government": ("municipal", "citizen feedback"),
    "supply_chain": ("supply chain", "traceability"),
    "mobility": ("parking",),
    "culture": ("museum",),
    "technology": ("ci/cd", "cloud migration", "single sign-on"),
    "support": ("customer support", "level-1"),
}

SERVICE_PHRASES = {
    "mobile_app": ("mobile apps", "mobile app"),
    "web_app": ("web application", "web app"),
    "ui_ux": ("ui/ux",),
    "staff_augmentation": ("staff augmentation",),
    "ai_product": ("ai product",),
}

DOC_TYPE_PHRASES = {
    "case_study": ("case studies", "case study", "similar project", "similar work", "portfolio"),
    "testimonial": ("testimonials", "testimonial", "client quote"),
}

ROLE_PHRASES = {
    "engineering_directors": ("engineering directors", "engineering director"),
    "product_managers": ("product managers", "product manager"),
    "ctos": ("ctos", "cto"),
    "finance_leads": ("finance leads", "finance lead"),
    "security_officers": ("security officers", "security officer"),
    "logistics_managers": ("logistics managers", "logistics manager"),
    "healthcare_administrators": ("healthcare administrators", "healthcare administrator"),
    "retail_executives": ("retail executives", "retail executive"),
    "operations_heads": ("operations heads", "operations head"),
    "edtech_founders": ("edtech founders", "edtech founder"),
    "sales_vps": ("sales vps", "sales vp"),
    "ecommerce_owners": ("e-commerce owners", "ecommerce owners", "e-commerce owner"),
    "risk_managers": ("risk managers", "risk manager"),
    "radiology_leads": ("radiology leads", "radiology lead"),
    "property_managers": ("property managers", "property manager"),
    "soc_analysts": ("soc analysts", "soc analyst"),
    "agronomists": ("agronomists", "agronomist"),
    "travel_agency_directors": ("travel agency directors", "travel agency director"),
    "legal_counsels": ("legal counsels", "legal counsel"),
    "fitness_app_founders": ("fitness app founders", "fitness app founder"),
    "fleet_supervisors": ("fleet supervisors", "fleet supervisor"),
    "hr_directors": ("hr directors", "hr director"),
    "delivery_operations_heads": ("delivery operations heads", "delivery operations head"),
    "bioinformaticians": ("bioinformaticians", "bioinformatician"),
    "insurance_claims_vps": ("insurance claims vps", "insurance claims vp"),
    "event_organizers": ("event organizers", "event organizer"),
    "clean_tech_engineers": ("clean-tech engineers", "clean-tech engineer"),
    "support_leads": ("support leads", "support lead"),
    "defi_founders": ("defi founders", "defi founder"),
    "store_managers": ("store managers", "store manager"),
    "media_engineers": ("media engineers", "media engineer"),
    "nonprofit_directors": ("non-profit directors", "nonprofit directors", "non-profit director"),
    "auto_insurance_heads": ("auto insurance heads", "auto insurance head"),
    "municipal_commissioners": ("municipal commissioners", "municipal commissioner"),
    "supply_chain_leads": ("supply chain leads", "supply chain lead"),
    "telehealth_directors": ("telehealth directors", "telehealth director"),
    "real_estate_brokers": ("real estate brokers", "real estate broker"),
    "devops_leads": ("devops leads", "devops lead"),
    "hospitality_executives": ("hospitality executives", "hospitality executive"),
    "microlending_founders": ("micro-lending founders", "microlending founders", "micro-lending founder"),
    "museum_curators": ("museum curators", "museum curator"),
    "print_shop_owners": ("print shop owners", "print shop owner"),
    "warehouse_managers": ("warehouse managers", "warehouse manager"),
    "enterprise_cisos": ("enterprise cisos", "enterprise ciso", "cisos", "ciso"),
    "sustainability_officers": ("sustainability officers", "sustainability officer"),
    "language_school_leads": ("language school leads", "language school lead"),
    "parking_operators": ("parking operators", "parking operator"),
    "aviation_supervisors": ("aviation supervisors", "aviation supervisor"),
    "publishers": ("publishers", "publisher"),
}

PAST_WORK = (
    "case studies",
    "case study",
    "similar project",
    "similar work",
    "portfolio",
    "testimonials",
    "testimonial",
    "client quote",
    "past work",
    "have you built",
    "previous project",
)


def query_filters(text: str, *, service: str | None = None, industry: str | None = None) -> dict[str, str]:
    lowered = (text or "").lower()
    if not lowered.strip():
        return {}
    filters: dict[str, str] = {}
    topic = _best(lowered, TOPIC_PHRASES)
    if topic:
        filters["topic"] = topic
    found_industry = _best(lowered, INDUSTRY_PHRASES)
    if found_industry:
        filters["industry"] = found_industry
    found_service = _best(lowered, SERVICE_PHRASES)
    if found_service:
        filters["service"] = found_service
    role = _best(lowered, ROLE_PHRASES)
    if role:
        filters["role"] = role
    doc_type = _best(lowered, DOC_TYPE_PHRASES)
    if doc_type:
        filters["doc_type"] = doc_type
    if _contains_any(lowered, PAST_WORK):
        if service and "service" not in filters:
            filters["service"] = service
        if industry and "industry" not in filters:
            filters["industry"] = industry
    return filters


def _best(text: str, table: dict[str, tuple[str, ...]]) -> str:
    found = ""
    found_len = 0
    for label, phrases in table.items():
        for phrase in phrases:
            if len(phrase) <= found_len or not _has(text, phrase):
                continue
            found = label
            found_len = len(phrase)
    return found


def _contains_any(text: str, phrases: tuple[str, ...]) -> bool:
    return any(_has(text, phrase) for phrase in phrases)


def _has(text: str, phrase: str) -> bool:
    return re.search(rf"(?<![a-z0-9]){re.escape(phrase)}(?![a-z0-9])", text) is not None
