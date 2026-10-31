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
            {"label": "HIPAA-compliant security", "value": "HIPAA compliance"},
            {"label": "Doctor video consults", "value": "Doctor video consults"},
            {"label": "EHR & medical records sync", "value": "EHR integration"},
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
            {"label": "ID & KYC verification", "value": "KYC verification"},
            {"label": "Payments & payouts", "value": "Payments & payouts"},
            {"label": "Secure transaction ledger", "value": "Double-entry ledger"},
            {"label": "Biometric & 2FA security", "value": "Biometric 2FA auth"},
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
            {"label": "Custom checkout & payments", "value": "Custom checkout"},
            {"label": "Smart product search & filters", "value": "Product search & filters"},
            {"label": "Real-time inventory sync", "value": "Real-time inventory sync"},
            {"label": "Multi-vendor payouts", "value": "Multi-vendor payouts"},
        ],
        discovery_question="Is this a multi-vendor marketplace with automated vendor payouts and inventory locks?",
    ),
    "saas": DomainBlueprint(
        id="saas",
        label="B2B SaaS & Enterprise Platforms",
        keywords=(
            "saas", "b2b", "multi-tenant", "tenant", "workspace", "rbac",
            "crm", "erp", "enterprise", "dashboard", "billing", "subscription",
            "sso", "saml", "okta", "workos", "ops",
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
            {"label": "User roles & permissions", "value": "User roles & permissions"},
            {"label": "Team workspaces", "value": "Team workspaces"},
            {"label": "Subscription billing", "value": "Subscription billing"},
            {"label": "Audit & activity logs", "value": "Audit logs"},
        ],
        discovery_question="Do you need enterprise features like SAML SSO, team workspaces, and custom seat billing?",
    ),
    "portal": DomainBlueprint(
        id="portal",
        label="Customer & Client Self-Service Portals",
        keywords=(
            "portal", "client portal", "customer portal", "self-service", "self service",
            "member portal", "partner portal", "vendor portal", "account portal", "user portal",
            "customer self-service", "client self-service", "helpdesk portal",
        ),
        compliance="Secure authenticated client sessions, encrypted document storage, Stripe customer billing integration, granular permission levels",
        architecture_notes=[
            "Provide a secure, authenticated web dashboard where customers can manage profiles, view subscriptions, and access documents.",
            "Integrate self-service billing, card updates, and invoice downloads directly via Stripe Customer Portal.",
            "Deploy an asynchronous ticket management and messaging desk for customer inquiries.",
        ],
        frontend_recommendations=["Next.js Responsive Client Portal", "Mobile-Optimized Web Dashboard"],
        backend_recommendations=["Node.js / FastAPI + PostgreSQL + Stripe Billing Portal + Secure S3 Vault"],
        key_features=[
            {"label": "Profile & account settings", "value": "Account & profile management"},
            {"label": "Invoices & online payments", "value": "Invoices & payments"},
            {"label": "Support tickets & helpdesk", "value": "Support ticket desk"},
            {"label": "Document & file downloads", "value": "Document & file sharing"},
        ],
        discovery_question="Will your clients mainly log in to manage accounts and billing, or submit and track support requests?",
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
            {"label": "AI conversational assistant", "value": "AI chat"},
            {"label": "Document search & Q&A", "value": "Document processing"},
            {"label": "Fast streaming responses", "value": "Streaming responses"},
            {"label": "Human review & approval", "value": "Human-in-the-loop review"},
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
            {"label": "Interactive map search", "value": "Interactive map search"},
            {"label": "MLS / IDX property feed sync", "value": "MLS feed sync"},
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
            {"label": "Document scanning & OCR", "value": "Contract OCR & parsing"},
            {"label": "Automated redaction", "value": "Automated redaction"},
            {"label": "Audit trails & change history", "value": "Audit trails"},
            {"label": "Contract comparison & diff", "value": "Clause diff"},
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
            {"label": "Live device data feed", "value": "Live device data feed"},
            {"label": "Bluetooth mobile pairing", "value": "Bluetooth mobile pairing"},
            {"label": "Device history & charts", "value": "Device history & charts"},
            {"label": "Remote device updates (OTA)", "value": "Remote device updates"},
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
            "cpa", "cpa firm", "tax consultant", "tax consultation", "tax advisor", "tax intake",
        ),
        compliance="SOC 2 Type II, IRS Pub 1075 data security, AES-256 encrypted tax forms, immutable double-entry ledger audit trails, multi-jurisdiction rules engine",
        architecture_notes=[
            "Store all PII, SSN/EIN, and tax returns in a dedicated AES-256 encrypted vault with access audit logging.",
            "Implement a deterministic, multi-jurisdiction tax calculation engine (integrating Stripe Tax / Avalara / TaxJar).",
            "Deploy an asynchronous document parsing pipeline (OCR + LLM extraction) for receipts, invoices, and bank statements.",
            "Integrate automated CPA consultation booking (Calendly/HubSpot) and IRS Circular 230 disclaimer guardrails.",
        ],
        frontend_recommendations=["Next.js Secure Client Portal & Widget", "Flutter Mobile Tax & Receipt Scanner"],
        backend_recommendations=["FastAPI / Node.js + PostgreSQL (Double-Entry Ledger) + Redis Queue (OCR/Calculation)"],
        key_features=[
            {"label": "Client intake & CPA booking", "value": "Client intake & CPA booking"},
            {"label": "1099, W-2 & receipt OCR", "value": "Tax forms OCR"},
            {"label": "Automated GST / VAT calculation", "value": "Automated tax calculation"},
            {"label": "WhatsApp & web tax assistant", "value": "Multi-channel tax assistant"},
        ],
        discovery_question="Are you looking for an AI client intake & consultation booking assistant, or custom tax calculation and e-filing software?",
    ),
    "hrtech": DomainBlueprint(
        id="hrtech",
        label="HRTech & Talent Acquisition",
        keywords=(
            "hr", "recruiting", "recruitment", "staffing", "talent", "hiring",
            "interview", "applicant", "ats", "resume", "resumes", "candidate",
            "candidates", "onboarding", "job board", "greenhouse", "lever", "workday",
        ),
        compliance="EEOC compliance, candidate PII protection (GDPR/CCPA), automated resume parsing (PDF/DOCX), calendar interview scheduling, two-way ATS synchronization",
        architecture_notes=[
            "Implement asynchronous document extraction for resumes with automated PII redacting to prevent hiring bias.",
            "Synchronize interview booking slots directly with interviewers' calendars to eliminate scheduling back-and-forth.",
            "Push structured candidate screening scores and chat transcripts into ATS (Greenhouse, Lever, Workday) via secure webhooks.",
        ],
        frontend_recommendations=["Next.js Candidate Portal & Careers Widget", "Slack / Teams Internal Hiring Bot"],
        backend_recommendations=["FastAPI + OCR / LayoutLM Resume Parser", "PostgreSQL (Encrypted) + Greenhouse / Lever ATS Sync Worker"],
        key_features=[
            {"label": "Automated resume parsing", "value": "Automated resume parsing"},
            {"label": "Candidate pre-screening", "value": "Candidate pre-screening"},
            {"label": "ATS webhook sync (Greenhouse)", "value": "ATS sync"},
            {"label": "Self-service interview booking", "value": "Self-service interview booking"},
        ],
        discovery_question="Will the assistant integrate with an existing ATS like Greenhouse, Lever, or Workday for candidate profile synchronization?",
    ),
    "insurtech": DomainBlueprint(
        id="insurtech",
        label="InsurTech & Claims Processing",
        keywords=(
            "insurance", "insurtech", "claim", "claims", "fnol", "policy",
            "policies", "underwriting", "adjuster", "coverage", "deductible",
            "premium", "auto insurance", "health insurance", "life insurance", "insuretech",
        ),
        compliance="First Notice of Loss (FNOL) automation, damage photo AI triage, insurance fraud anomaly detection, SOC2 Type II and state insurance commission audit trails",
        architecture_notes=[
            "Process First Notice of Loss (FNOL) intake with real-time policy validation and automated deductible calculations.",
            "Deploy computer vision damage classification models to triage vehicle and property claims instantly.",
            "Enforce immutable audit logs and SOC2 Type II compliance for sensitive claim payouts and incident evidence.",
        ],
        frontend_recommendations=["Next.js Claims Intake Portal", "Flutter Mobile Damage Photo Uploader"],
        backend_recommendations=["FastAPI + Gemini Vision Damage Classifier", "PostgreSQL (Encrypted) + S3 Evidence Vault + Policy Sync API"],
        key_features=[
            {"label": "Instant FNOL claims intake", "value": "Instant FNOL claims intake"},
            {"label": "Damage photo AI inspection", "value": "Damage photo AI inspection"},
            {"label": "Policy coverage lookup", "value": "Policy coverage lookup"},
            {"label": "Adjuster appointment booking", "value": "Adjuster appointment booking"},
        ],
        discovery_question="Do you need mobile photo upload with automated damage severity grading for First Notice of Loss (FNOL)?",
    ),
    "auto": DomainBlueprint(
        id="auto",
        label="Automotive & Dealership Intelligence",
        keywords=(
            "auto", "automotive", "dealership", "dealerships", "car", "cars",
            "vehicle", "vehicles", "test drive", "trade-in", "dealersocket",
            "reynolds", "dealer", "showroom", "vin", "service center",
        ),
        compliance="VIN decoding APIs (NHTSA), real-time DMS inventory feeds, trade-in valuation models (KBB/BlackBook), scheduled test drive booking",
        architecture_notes=[
            "Integrate NHTSA VIN decoding APIs to automatically populate vehicle specs, trims, and recall data during valuation.",
            "Synchronize dealership inventory feeds every 15 minutes to reflect real-time on-lot vehicle availability.",
            "Connect test drive and service bookings directly with dealership management systems (DMS) like DealerSocket and Reynolds & Reynolds.",
        ],
        frontend_recommendations=["Next.js Dealership Showroom Widget & Mobile Web", "Dealer Sales Rep Tablet App"],
        backend_recommendations=["Python FastAPI + PostgreSQL + NHTSA VIN Decoder API", "DMS / DealerSocket Sync Queue + Redis Cache"],
        key_features=[
            {"label": "Instant test drive scheduling", "value": "Instant test drive scheduling"},
            {"label": "VIN decoding & spec lookup", "value": "VIN decoding"},
            {"label": "Trade-in appraisal questionnaire", "value": "Trade-in appraisal"},
            {"label": "DMS / CRM lead synchronization", "value": "DMS sync"},
        ],
        discovery_question="Will you connect real-time vehicle inventory from your DMS (DealerSocket, Reynolds & Reynolds) or manual listings?",
    ),
    "hospitality": DomainBlueprint(
        id="hospitality",
        label="Hospitality, Hotels & Dining",
        keywords=(
            "hotel", "hotels", "hospitality", "restaurant", "restaurants", "dining",
            "reservation", "reservations", "guest", "concierge", "opentable",
            "sevenrooms", "toast", "pms", "resort", "room service",
        ),
        compliance="Real-time table/room reservation locks, multi-lingual concierge translation, POS/PMS guest profile synchronization, automated dietary allergy flagging",
        architecture_notes=[
            "Implement distributed reservation locks to prevent double-booking across third-party reservation channels.",
            "Deploy a multi-lingual AI concierge supporting 50+ languages with automated dietary restriction and allergy tagging.",
            "Integrate guest booking confirmations directly into Property Management Systems (PMS) or restaurant POS (OpenTable, Toast).",
        ],
        frontend_recommendations=["Next.js Guest Web Portal & Dining Widget", "Flutter Mobile Concierge & Keyless Entry App"],
        backend_recommendations=["Node.js / FastAPI + PostgreSQL + Redis Table Locks", "OpenTable / Toast POS Webhook Sync + WhatsApp Cloud API"],
        key_features=[
            {"label": "Instant reservation booking", "value": "Instant reservation booking"},
            {"label": "24/7 AI guest concierge", "value": "24/7 AI guest concierge"},
            {"label": "Multi-lingual menu & allergen QA", "value": "Menu & allergen QA"},
            {"label": "PMS & POS system integration", "value": "PMS & POS integration"},
        ],
        discovery_question="Are you looking for table bookings with OpenTable/Toast, or full hotel guest concierge with PMS integration?",
    ),
}

DOMAIN_ALIASES: dict[str, str] = {
    "hr": "hrtech",
    "recruiting": "hrtech",
    "recruitment": "hrtech",
    "staffing": "hrtech",
    "hiring": "hrtech",
    "talent": "hrtech",
    "insurance": "insurtech",
    "claims": "insurtech",
    "insuretech": "insurtech",
    "automotive": "auto",
    "dealership": "auto",
    "cars": "auto",
    "dealer": "auto",
    "hotel": "hospitality",
    "hotels": "hospitality",
    "restaurant": "hospitality",
    "restaurants": "hospitality",
    "dining": "hospitality",
    "tax": "taxtech",
    "taxes": "taxtech",
    "taxation": "taxtech",
    "accounting": "taxtech",
    "payroll": "taxtech",
    "invoicing": "taxtech",
    "cpa": "taxtech",
    "tax consultation": "taxtech",
    "tax consultant": "taxtech",
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
    "client_portal": "portal",
    "customer_portal": "portal",
    "self_service": "portal",
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
