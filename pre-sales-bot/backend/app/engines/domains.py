from __future__ import annotations

import re
from typing import Any
from backend.app.agents.brief import ProjectBrief


class DomainBlueprint:
    def __init__(
        self,
        id: str,
        label: str,
        keywords: tuple[str, ...],
        compliance: str,
        architecture_notes: list[str],
        frontend_recommendations: list[str],
        backend_recommendations: list[str],
        key_features: list[dict[str, str]],
        discovery_question: str,
    ):
        self.id = id
        self.label = label
        self.keywords = keywords
        self.compliance = compliance
        self.architecture_notes = architecture_notes
        self.frontend_recommendations = frontend_recommendations
        self.backend_recommendations = backend_recommendations
        self.key_features = key_features
        self.discovery_question = discovery_question


DOMAIN_BLUEPRINTS: dict[str, DomainBlueprint] = {
    "health": DomainBlueprint(
        id="health",
        label="HealthTech & Telehealth",
        keywords=(
            "health", "healthcare", "telehealth", "telemedicine", "doctor", "clinic",
            "patient", "ehr", "emr", "hipaa", "fhir", "hospital", "pharma",
            "medical", "prescription", "radiology", "clinical",
        ),
        compliance="HIPAA / HITECH compliance, BAA agreements, HL7/FHIR protocols, AES-256 encrypted PHI storage, WebRTC encrypted consultations",
        architecture_notes=[
            "Enforce HIPAA-compliant infrastructure with encrypted data at rest (AES-256) and in transit.",
            "Ensure BAA agreements and secure audit logging for any Protected Health Information (PHI).",
            "Use WebRTC / LiveKit for end-to-end encrypted doctor-patient video consultations.",
        ],
        frontend_recommendations=["Next.js Clinical Portal", "Flutter / React Native Patient App"],
        backend_recommendations=["HIPAA-compliant AWS ECS + PostgreSQL (Encrypted) + LiveKit WebRTC"],
        key_features=[
            {"label": "HIPAA compliance", "value": "HIPAA compliance"},
            {"label": "Doctor video consults", "value": "Doctor video consults"},
            {"label": "EHR / FHIR integration", "value": "EHR integration"},
            {"label": "Patient records portal", "value": "Patient records portal"},
        ],
        discovery_question="Will this require integration with existing EHR systems (Epic/Cerner) or e-prescriptions?",
    ),
    "fintech": DomainBlueprint(
        id="fintech",
        label="FinTech & Banking",
        keywords=(
            "fintech", "finance", "bank", "banking", "wallet", "payments",
            "payout", "ledger", "crypto", "trading", "investment", "loan",
            "lending", "neobank", "insurance", "insurtech", "credit", "defi",
            "micro-lending", "microlending", "fraud",
        ),
        compliance="PCI-DSS Level 1 compliance, KYC/AML (Persona/Onfido/Plaid), idempotent double-entry ledger",
        architecture_notes=[
            "Enforce PCI-DSS Level 1 tokenized card vaults and strict financial audit trails.",
            "Implement an idempotent double-entry ledger to eliminate transaction race conditions.",
            "Integrate automated KYC/AML verification (Persona/Plaid/Onfido) during customer onboarding.",
        ],
        frontend_recommendations=["Next.js (Web)", "Flutter (iOS & Android)"],
        backend_recommendations=["Node.js / FastAPI + PostgreSQL (ACID Double-Entry) + Redis Cache"],
        key_features=[
            {"label": "KYC / AML verification", "value": "KYC verification"},
            {"label": "Stripe Connect payouts", "value": "Stripe Connect payouts"},
            {"label": "Double-entry ledger", "value": "Double-entry ledger"},
            {"label": "Biometric 2FA auth", "value": "Biometric 2FA auth"},
        ],
        discovery_question="Will you need multi-party escrow payouts or direct bank verification via Plaid?",
    ),
    "logistics": DomainBlueprint(
        id="logistics",
        label="Logistics, Delivery & On-Demand",
        keywords=(
            "delivery", "logistics", "courier", "fleet", "driver", "dispatch",
            "rider", "tracking", "freight", "warehouse", "supply chain", "zepto",
            "blinkit", "uber", "instacart", "doordash", "swiggy", "zomato",
            "taxi", "cargo",
        ),
        compliance="Geospatial indexing (Redis GEO / PostGIS), real-time WebSockets, Mapbox/Google Maps Matrix API routing, automated dispatch",
        architecture_notes=[
            "Use Redis GEO / PostGIS for sub-second geospatial proximity queries and driver matching.",
            "Deploy dual mobile apps (driver vs customer) backed by high-throughput WebSocket events.",
            "Cache route matrices via Mapbox/Google Maps API to minimize external map API expenses.",
        ],
        frontend_recommendations=["Flutter (Customer & Driver Dual Apps)", "Next.js Dispatcher Dashboard"],
        backend_recommendations=["Node.js / Go + PostgreSQL / PostGIS + Redis GEO + WebSockets"],
        key_features=[
            {"label": "Live GPS driver tracking", "value": "Live GPS tracking"},
            {"label": "Automated dispatch engine", "value": "Automated dispatch engine"},
            {"label": "Route optimization", "value": "Route optimization"},
            {"label": "Dual mobile apps", "value": "Dual mobile apps"},
        ],
        discovery_question="Are you deploying separate apps for drivers and customers plus a dispatcher dashboard?",
    ),
    "ecommerce": DomainBlueprint(
        id="ecommerce",
        label="E-Commerce & Marketplaces",
        keywords=(
            "ecommerce", "e-commerce", "marketplace", "shop", "store",
            "multi-vendor", "cart", "catalog", "inventory", "vendor", "seller",
            "orders", "d2c", "retail", "storefront", "checkout",
        ),
        compliance="Multi-vendor commission handling, Redis distributed locks for inventory, Algolia faceted search, headless Next.js",
        architecture_notes=[
            "Implement Redis distributed locks on inventory items to prevent checkout overselling.",
            "Power product search with Algolia / Elasticsearch for instant sub-50ms faceted filtering.",
            "Handle multi-vendor commissions and split vendor payouts automatically via Stripe Connect.",
        ],
        frontend_recommendations=["Headless Next.js Storefront", "React Native Mobile App"],
        backend_recommendations=["Node.js + PostgreSQL + Redis Inventory Locks + Algolia Search"],
        key_features=[
            {"label": "Multi-vendor payouts", "value": "Multi-vendor payouts"},
            {"label": "Inventory locks", "value": "Inventory reservation locks"},
            {"label": "Faceted product search", "value": "Faceted product search"},
            {"label": "Custom checkout", "value": "Custom checkout"},
        ],
        discovery_question="Is this a multi-vendor marketplace with automated vendor payouts and inventory locks?",
    ),
    "saas": DomainBlueprint(
        id="saas",
        label="B2B SaaS & Enterprise Platforms",
        keywords=(
            "saas", "b2b", "multi-tenant", "tenant", "workspace", "rbac",
            "crm", "erp", "enterprise", "dashboard", "billing", "subscription",
            "sso", "saml", "okta", "workos", "ops", "portal",
        ),
        compliance="Multi-tenant DB isolation (row-level security / schema per tenant), granular RBAC/ABAC permissions, Enterprise SSO (SAML 2.0 / Okta / WorkOS), audit trails",
        architecture_notes=[
            "Partition tenant data cleanly with PostgreSQL Row Level Security (RLS) or schema-per-tenant isolation.",
            "Integrate Enterprise SAML 2.0 SSO (Okta, Azure AD via WorkOS) and hierarchical RBAC roles.",
            "Automate recurring tiered subscription billing and metered usage overages via Stripe Billing.",
        ],
        frontend_recommendations=["Next.js App Router + TailwindCSS + shadcn/ui"],
        backend_recommendations=["FastAPI / Node.js + PostgreSQL (RLS) + Redis + Stripe Metered Billing"],
        key_features=[
            {"label": "Enterprise SAML SSO", "value": "Enterprise SAML SSO"},
            {"label": "Multi-tenant RBAC", "value": "Multi-tenant RBAC"},
            {"label": "Stripe metered billing", "value": "Stripe metered billing"},
            {"label": "Audit log exports", "value": "Audit log exports"},
        ],
        discovery_question="Do you need enterprise features like SAML SSO, team workspaces, and custom seat billing?",
    ),
    "ai_product": DomainBlueprint(
        id="ai_product",
        label="AI & GenAI Systems",
        keywords=(
            "ai", "llm", "genai", "rag", "agent", "agents", "langchain",
            "vector", "embeddings", "pinecone", "pgvector", "gemini", "gpt",
            "chatbot", "copilot", "voice ai", "document ai",
        ),
        compliance="Grounded RAG pipelines, Vector DBs (pgvector/Pinecone/Qdrant), semantic caching (token cost saver), streaming sub-second TTFT, human-in-the-loop review",
        architecture_notes=[
            "Store dense embeddings in pgvector / Pinecone with hybrid BM25 + vector reranking.",
            "Implement Redis semantic caching to serve recurring prompt queries and cut LLM token costs by up to 40%.",
            "Stream server-sent events (SSE) for sub-second Time-To-First-Token (TTFT) UX.",
        ],
        frontend_recommendations=["Next.js with Vercel AI SDK streaming UI"],
        backend_recommendations=["FastAPI + LangGraph + PostgreSQL / pgvector + Redis Semantic Cache"],
        key_features=[
            {"label": "pgvector semantic search", "value": "pgvector semantic search"},
            {"label": "Sub-second streaming", "value": "Sub-second streaming TTFT"},
            {"label": "Semantic prompt caching", "value": "Semantic prompt caching"},
            {"label": "Human-in-the-loop review", "value": "Human-in-the-loop review"},
        ],
        discovery_question="What is your expected token volume, and will we need semantic caching to keep API costs lean?",
    ),
    "edtech": DomainBlueprint(
        id="edtech",
        label="EdTech & Learning Platforms",
        keywords=(
            "edtech", "lms", "learning", "course", "courses", "student",
            "teacher", "classroom", "tutor", "quiz", "quizzes", "scorm",
            "exam", "education", "school", "university", "academy",
        ),
        compliance="SCORM / xAPI compliance, video transcoding pipelines (Mux / AWS MediaConvert), live classroom WebSockets, student progress analytics",
        architecture_notes=[
            "Offload video transcoding and adaptive HLS streaming to Mux or AWS MediaConvert.",
            "Build interactive live classroom features and hand-raising over low-latency WebSockets.",
            "Structure modular curriculum progress tracking with SCORM / xAPI export capability.",
        ],
        frontend_recommendations=["Next.js (Web LMS)", "React Native / Flutter (Mobile Learner App)"],
        backend_recommendations=["Node.js + PostgreSQL + Mux Video Streaming API + Redis"],
        key_features=[
            {"label": "Adaptive video streaming", "value": "Adaptive video streaming"},
            {"label": "Live interactive classes", "value": "Live interactive classes"},
            {"label": "Quiz & certificate engine", "value": "Quiz & certificate engine"},
            {"label": "Curriculum analytics", "value": "Curriculum analytics"},
        ],
        discovery_question="Will you host pre-recorded video courses with DRM or live interactive classrooms?",
    ),
    "proptech": DomainBlueprint(
        id="proptech",
        label="PropTech & Real Estate",
        keywords=(
            "real estate", "proptech", "property", "properties", "realtor",
            "broker", "mls", "idx", "rent", "rental", "tenant", "landlord",
            "apartment", "leasing", "housing",
        ),
        compliance="MLS / IDX feed normalization (RESO Web API), GIS polygon spatial mapping, virtual 3D tour embeds (Matterport), automated valuation models (AVM)",
        architecture_notes=[
            "Schedule resilient background sync workers to ingest and normalize MLS/IDX listings via RESO Web API.",
            "Index geographic parcel coordinates in PostGIS for custom polygon and radius boundary map searches.",
            "Embed Matterport 3D interactive virtual tours and integrate DocuSign/HelloSign for digital leases.",
        ],
        frontend_recommendations=["Next.js + Mapbox GL JS (Polygon search)", "Flutter (Buyer/Tenant App)"],
        backend_recommendations=["Python / FastAPI + PostgreSQL / PostGIS + RESO Web API Sync Worker"],
        key_features=[
            {"label": "MLS / IDX feed sync", "value": "MLS / IDX feed sync"},
            {"label": "Polygon map search", "value": "Polygon map search"},
            {"label": "Virtual 3D tour embed", "value": "Virtual 3D tour embed"},
            {"label": "Digital lease signing", "value": "Digital lease signing"},
        ],
        discovery_question="Will you be pulling real-time property listings from MLS/IDX feeds or manual listings?",
    ),
    "legaltech": DomainBlueprint(
        id="legaltech",
        label="LegalTech & GovTech",
        keywords=(
            "legal", "law", "lawyer", "attorney", "contract", "contracts",
            "compliance", "regulatory", "govtech", "court", "nda", "clause",
            "audit", "paralegal",
        ),
        compliance="SOC2 Type II, FedRAMP, automated contract OCR & Named Entity Recognition (NER), clause extraction, immutable audit logs",
        architecture_notes=[
            "Implement secure multi-layer OCR and tokenized entity redaction before document indexing.",
            "Store legal contracts in append-only immutable storage with cryptographic SHA-256 integrity logs.",
            "Enforce SOC2 Type II compliance and client-side encryption for confidential litigation documents.",
        ],
        frontend_recommendations=["Next.js Enterprise Portal with PDF Annotation & Diff Viewer"],
        backend_recommendations=["FastAPI + OCR / LayoutLM Pipeline + PostgreSQL (Encrypted) + S3 Glacier Vault"],
        key_features=[
            {"label": "Contract OCR & parsing", "value": "Contract OCR & parsing"},
            {"label": "Automated redaction", "value": "Automated redaction"},
            {"label": "Immutable audit trails", "value": "Immutable audit trails"},
            {"label": "Clause library diff", "value": "Clause library diff"},
        ],
        discovery_question="Do you need automated clause extraction and strict SOC2/GDPR tenant data isolation?",
    ),
    "iot": DomainBlueprint(
        id="iot",
        label="IoT & Telematics",
        keywords=(
            "iot", "sensor", "sensors", "hardware", "telematics", "mqtt",
            "bluetooth", "ble", "firmware", "device", "devices", "telemetry",
            "gps tracker",
        ),
        compliance="MQTT message brokers (EMQX / AWS IoT Core), time-series DBs (TimescaleDB / InfluxDB), low-bandwidth BLE communication, firmware OTA updates",
        architecture_notes=[
            "Ingest high-frequency telemetry over lightweight MQTT protocols using EMQX or AWS IoT Core.",
            "Store sensor time-series metrics in TimescaleDB or InfluxDB with automated data retention policies.",
            "Manage Bluetooth Low Energy (BLE) mobile provisioning and staged Over-The-Air (OTA) firmware rollouts.",
        ],
        frontend_recommendations=["React Native (BLE Device Pairing)", "Next.js Telemetry Operations Dashboard"],
        backend_recommendations=["Go / Python + EMQX MQTT Broker + TimescaleDB + Redis TimeSeries"],
        key_features=[
            {"label": "MQTT telemetry ingestion", "value": "MQTT telemetry ingestion"},
            {"label": "BLE mobile pairing", "value": "BLE mobile pairing"},
            {"label": "TimescaleDB time-series", "value": "TimescaleDB time-series"},
            {"label": "OTA firmware updates", "value": "OTA firmware updates"},
        ],
        discovery_question="What device telemetry frequency are you targeting, and will we ingest over MQTT or WebSockets?",
    ),
    "taxtech": DomainBlueprint(
        id="taxtech",
        label="TaxTech & Accounting Compliance",
        keywords=(
            "tax", "taxes", "taxation", "accounting", "accountant", "gst", "vat",
            "sales tax", "1099", "w-2", "w2", "w-9", "w9", "irs", "audit", "invoicing",
            "invoice", "payroll", "quickbooks", "xero", "avalara", "taxjar", "deduction",
            "expense tracking", "receipt ocr", "tax filing", "income tax", "corporate tax",
        ),
        compliance="SOC 2 Type II, IRS Pub 1075 data security, AES-256 encrypted tax forms, immutable double-entry ledger audit trails, multi-jurisdiction rules engine",
        architecture_notes=[
            "Store all PII, SSN/EIN, and tax returns in a dedicated AES-256 encrypted vault with access audit logging.",
            "Implement a deterministic, multi-jurisdiction tax calculation engine (integrating Stripe Tax / Avalara / TaxJar).",
            "Deploy an asynchronous document parsing pipeline (OCR + LLM extraction) for receipts, invoices, and bank statements.",
        ],
        frontend_recommendations=["Next.js Secure Client Portal", "Flutter Mobile Tax & Receipt Scanner"],
        backend_recommendations=["FastAPI / Node.js + PostgreSQL (Double-Entry Ledger) + Redis Queue (OCR/Calculation)"],
        key_features=[
            {"label": "Automated GST / VAT calculation", "value": "Automated tax calculation"},
            {"label": "1099 & W-2 / W-9 filing", "value": "Tax forms filing"},
            {"label": "Stripe Tax & Avalara integration", "value": "Tax API integration"},
            {"label": "Receipt OCR & deduction tracker", "value": "Receipt OCR"},
        ],
        discovery_question="Will you need multi-jurisdiction sales tax calculations (like Avalara/Stripe Tax) or direct government e-filing (IRS/GST)?",
    ),
}

DOMAIN_ALIASES: dict[str, str] = {
    "tax": "taxtech",
    "taxes": "taxtech",
    "taxation": "taxtech",
    "accounting": "taxtech",
    "payroll": "taxtech",
    "invoicing": "taxtech",
    "healthtech": "health",
    "healthcare": "health",
    "telehealth": "health",
    "medical": "health",
    "banking": "fintech",
    "finance": "fintech",
    "crypto": "fintech",
    "delivery": "logistics",
    "on_demand": "logistics",
    "ondemand": "logistics",
    "e-commerce": "ecommerce",
    "retail": "ecommerce",
    "marketplace": "ecommerce",
    "b2b_saas": "saas",
    "enterprise": "saas",
    "ai": "ai_product",
    "genai": "ai_product",
    "education": "edtech",
    "lms": "edtech",
    "real_estate": "proptech",
    "realestate": "proptech",
    "property": "proptech",
    "legal": "legaltech",
    "govtech": "legaltech",
    "telematics": "iot",
    "hardware": "iot",
}


def get_domain_blueprint(domain_id: str | None) -> DomainBlueprint | None:
    if not domain_id:
        return None
    normalized = domain_id.lower().strip()
    target = DOMAIN_ALIASES.get(normalized, normalized)
    return DOMAIN_BLUEPRINTS.get(target)


def detect_domain(text: str = "", brief: ProjectBrief | None = None) -> str | None:
    """Detect the industry/domain blueprint from input text and/or project brief context."""
    if brief and brief.industry:
        norm = brief.industry.lower().strip()
        target = DOMAIN_ALIASES.get(norm, norm)
        if target in DOMAIN_BLUEPRINTS:
            return target

    context_parts: list[str] = []
    if text:
        context_parts.append(text.lower())
    if brief:
        if brief.goal:
            context_parts.append(brief.goal.lower())
        if brief.features:
            context_parts.extend(f.lower() for f in brief.features)
        if brief.ai_features:
            context_parts.extend(f.lower() for f in brief.ai_features)

    combined = " ".join(context_parts)
    if not combined.strip():
        return None

    best_domain: str | None = None
    best_score = 0

    for domain_id, bp in DOMAIN_BLUEPRINTS.items():
        score = 0
        for kw in bp.keywords:
            pattern = r"\b" + re.escape(kw) + r"\b"
            matches = len(re.findall(pattern, combined))
            if matches > 0:
                score += matches * (3 if " " in kw else 1)
        if score > best_score and score >= 1:
            best_score = score
            best_domain = domain_id

    return best_domain
