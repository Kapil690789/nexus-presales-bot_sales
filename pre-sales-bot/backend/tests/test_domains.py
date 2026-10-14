from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.engines.domains import (
    DOMAIN_BLUEPRINTS,
    detect_domain,
    get_domain_blueprint,
)


def test_domain_blueprints_completeness():
    expected_domains = {
        "health", "fintech", "logistics", "ecommerce", "saas",
        "ai_product", "edtech", "proptech", "legaltech", "iot", "taxtech"
    }
    assert set(DOMAIN_BLUEPRINTS.keys()) == expected_domains
    for domain_id, bp in DOMAIN_BLUEPRINTS.items():
        assert bp.id == domain_id
        assert bp.label
        assert len(bp.keywords) > 5
        assert bp.compliance
        assert len(bp.architecture_notes) >= 2
        assert len(bp.frontend_recommendations) >= 1
        assert len(bp.backend_recommendations) >= 1
        assert len(bp.key_features) >= 3
        assert bp.discovery_question


def test_detect_domain_from_text():
    assert detect_domain("I want a telehealth clinic appointment booking app") == "health"
    assert detect_domain("We are building a micro-lending wallet with crypto payouts") == "fintech"
    assert detect_domain("I need an on-demand grocery delivery platform like Zepto with driver tracking") == "logistics"
    assert detect_domain("Multi-vendor e-commerce marketplace with custom checkout and storefront") == "ecommerce"
    assert detect_domain("B2B SaaS with multi-tenant workspaces and enterprise SAML SSO") == "saas"
    assert detect_domain("RAG agent with pgvector semantic search and LLM copilot") == "ai_product"
    assert detect_domain("Online learning platform with video courses, LMS, and quizzes") == "edtech"
    assert detect_domain("Real estate property management with MLS IDX feed sync and tenant portal") == "proptech"
    assert detect_domain("Legal contract analyzer with OCR clause extraction and compliance audit") == "legaltech"
    assert detect_domain("IoT hardware sensor telemetry with MQTT ingestion and TimescaleDB") == "iot"
    assert detect_domain("Automated tax calculation with GST filing and receipt OCR") == "taxtech"


def test_detect_domain_from_brief_context():
    brief = ProjectBrief(goal="Telemedicine doctor consultations", service="mobile_app")
    assert detect_domain(brief=brief) == "health"

    brief_logistics = ProjectBrief(goal="Courier fleet dispatch", features=["Live GPS driver tracking"])
    assert detect_domain(brief=brief_logistics) == "logistics"

    brief_tax = ProjectBrief(goal="Freelance tax return preparation", features=["Automated tax calculation"])
    assert detect_domain(brief=brief_tax) == "taxtech"


def test_detect_domain_returns_none_for_generic():
    assert detect_domain("I have an app idea") is None
    assert detect_domain("I need a web platform") is None
    assert detect_domain("") is None


def test_get_domain_blueprint_aliases():
    assert get_domain_blueprint("healthtech").id == "health"
    assert get_domain_blueprint("banking").id == "fintech"
    assert get_domain_blueprint("delivery").id == "logistics"
    assert get_domain_blueprint("e-commerce").id == "ecommerce"
    assert get_domain_blueprint("accounting").id == "taxtech"
    assert get_domain_blueprint("b2b_saas").id == "saas"
    assert get_domain_blueprint("unknown_xyz") is None
