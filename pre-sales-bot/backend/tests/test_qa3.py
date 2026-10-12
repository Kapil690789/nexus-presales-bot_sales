import os
import json
import re
from unittest.mock import patch, MagicMock
import pytest
from starlette.testclient import TestClient

from backend.app.main import app
from backend.app.agents.brief import ProjectBrief, brief_ready, next_discovery_field
from backend.app.agents.extractor import extract_slots, apply_extracted_slots, _heuristic_extract, is_product_idea
from backend.app.agents.router import (
    run_turn,
    recap_line_from_brief,
    format_shape_message,
    _resolve_flow,
    _is_objection_eligible,
    _next_chips,
    BOOK_CHIP,
    PORTFOLIO_CHIP,
)
from backend.app.core.guard import sanitize_price_leaks, UNAUTHORIZED_PRICE_MESSAGE
from backend.app.tenants.schema import TenantConfig, BrandConfig, VoiceConfig
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.architecture import recommend_architecture
from backend.app.models.entities import SessionRow, TenantRow
from backend.app.models.db import Base
from backend.app.rag.store import Hit
from sqlalchemy import create_engine
from sqlalchemy.orm import sessionmaker


@pytest.fixture
def client():
    return TestClient(app)


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sess = session_factory()
    yield sess
    sess.close()


@pytest.fixture
def tenant(db):
    row = TenantRow(id="demo", slug="demo", name="Nexus")
    db.add(row)
    db.commit()
    return row


@pytest.fixture
def config():
    from backend.app.tenants.loader import load_tenant
    return load_tenant("demo")


# ==============================================================================
# Item 1: Latency & Instrumentation
# ==============================================================================


def test_thinking_level_low_and_purpose_tracking():
    from backend.app.core.llm import complete_json, LLMError

    # Verify complete_json signature accepts purpose
    try:
        complete_json("test system", "test prompt", purpose="test_purpose")
    except LLMError:
        pass  # Expected if no LLM key configured


def test_rag_grade_skip_when_top_score_high():
    from backend.app.rag.grade import grade

    hit = Hit(
        id="1",
        doc_id="d1",
        title="Agile",
        content="Agile development process",
        score=0.82,
        source="knowledge",
        lexical_only=False,
    )

    # With score >= 0.75, grade should return show without calling LLM
    decision, score = grade("tell me about agile", [hit])
    assert decision == "show"
    assert score == 0.82


# ==============================================================================
# Item 2: Objection Gating
# ==============================================================================


def test_objection_gating_eligible_and_ineligible():
    # Ineligible: Starters, acknowledgements, slot answers, <= 4 words without cues
    assert not _is_objection_eligible("I have an app idea")
    assert not _is_objection_eligible("I'm just exploring costs")
    assert not _is_objection_eligible("im just exploring costs")
    assert not _is_objection_eligible("$40k to $80k")
    assert not _is_objection_eligible("my budget is $40k to $80k")
    assert not _is_objection_eligible("3 to 6 months")
    assert not _is_objection_eligible("iOS and Android")
    assert not _is_objection_eligible("web and mobile")
    assert not _is_objection_eligible("yes")
    assert not _is_objection_eligible("no")
    assert not _is_objection_eligible("ok")
    assert not _is_objection_eligible("sounds good")
    assert not _is_objection_eligible("founder")
    assert not _is_objection_eligible("startup")

    # Eligible: explicit objection cues or pressure words
    assert _is_objection_eligible("that's too expensive")
    assert _is_objection_eligible("can you do a fixed price?")
    assert _is_objection_eligible("Can you guarantee 4 weeks?")
    assert _is_objection_eligible("can you do it cheaper?")
    assert _is_objection_eligible("is there a discount?")


# ==============================================================================
# Item 3: Budget Capture
# ==============================================================================


def test_budget_capture_midpoint_and_exact_text():
    # "$40k to $80k" -> midpoint 60k -> 40_80k
    ext = _heuristic_extract("my budget is $40k to $80k", pending_field="budget_band")
    assert ext.get("budget_band") == "40_80k"
    assert "$40k" in ext.get("budget_text", "")
    assert "$80k" in ext.get("budget_text", "")

    # "under 30k" -> midpoint < 30k -> 15_40k
    ext2 = _heuristic_extract("under 30k", pending_field="budget_band")
    assert ext2.get("budget_band") == "15_40k"
    assert "30k" in ext2.get("budget_text", "")

    brief = ProjectBrief()
    apply_extracted_slots(brief, ext)
    assert brief.budget_band == "40_80k"
    assert brief.budget_text is not None


def test_recap_preserves_budget_text(config):
    brief = ProjectBrief(
        service="mobile_app",
        goal="Ride sharing app for local campus",
        platforms=["ios", "android"],
        features=["Ride booking", "Driver tracking"],
        timeline="3_6_months",
        budget_band="40_80k",
        budget_text="$40k to $80k",
        decision_role="founder_or_exec",
    )
    recap = recap_line_from_brief(config, brief)
    assert "Budget: $40k to $80k." in recap
    assert "still exploring" not in recap.lower()


# ==============================================================================
# Item 4: Price Guard
# ==============================================================================


def test_price_guard_deletes_sentence_on_non_estimate_turn():
    # On a discovery turn where session_has_estimate is False:
    # Sentence with unauthorized figure is dropped entirely, without UNAUTHORIZED_PRICE_MESSAGE
    msg = "Thanks for sharing! Most mobile apps cost around $50,000 to $80,000 to launch. What platforms are you targeting?"
    sanitized = sanitize_price_leaks(msg, session_has_estimate=False)
    assert "$50,000" not in sanitized
    assert "$80,000" not in sanitized
    assert UNAUTHORIZED_PRICE_MESSAGE not in sanitized
    assert "What platforms are you targeting?" in sanitized


def test_price_guard_whitelists_visitor_budget():
    msg = "Understood, working under $30k keeps the initial scope disciplined."
    sanitized = sanitize_price_leaks(msg, visitor_budget="under 30k", session_has_estimate=False)
    assert "$30k" in sanitized


# ==============================================================================
# Item 5: Brief Consistency & Silent Service Swap
# ==============================================================================


def test_web_and_mobile_defaults_service_and_platforms():
    brief = ProjectBrief()
    ext = _heuristic_extract("we need web and mobile", pending_field="platforms", brief=brief)
    assert "web" in ext.get("platforms", [])
    assert "ios" in ext.get("platforms", [])
    assert "android" in ext.get("platforms", [])

    apply_extracted_slots(brief, ext)
    assert brief.platforms == ["web", "ios", "android"]
    assert brief.service == "mobile_app"


def test_silent_service_swap_when_service_source_guess():
    brief = ProjectBrief(service="mobile_app", service_source="guess", platforms=["ios", "android"])
    ext = {"service": "web_app"}
    apply_extracted_slots(brief, ext)
    assert brief.service == "web_app"
    assert brief.service_source == "explicit"

    # Chip change also updates silently
    brief.apply_chip("service", "ai_product")
    assert brief.service == "ai_product"
    assert brief.service_source == "chip"


def test_starters_do_not_set_service_or_goal():
    assert not is_product_idea("I'm just exploring costs")
    assert not is_product_idea("I have an app idea")
    assert not is_product_idea("explore costs")

    ext = _heuristic_extract("I have an app idea", pending_field="goal")
    assert ext.get("goal") is None
    assert ext.get("service") is None


# ==============================================================================
# Item 6: Structured Recap Format
# ==============================================================================


def test_structured_recap_format(config):
    brief = ProjectBrief(
        service="web_app",
        goal="I am building a B2B warehouse inventory platform on web",
        platforms=["web"],
        features=["Barcode scanning", "Stock alerts", "Purchase orders", "Audit log", "Analytics", "Reports"],
        timeline="3_6_months",
        budget_band="40_80k",
        decision_role="founder_or_exec",
    )
    recap = recap_line_from_brief(config, brief)
    # Grammar pattern: Here's what I understood: a web platform - B2B warehouse inventory platform. Platforms: Web. Features: ..., and 2 more. Timeline: 3 to 6 months. Budget: $40k to $80k.
    assert "Here's what I understood: a web application - B2B warehouse inventory platform." in recap
    assert "Platforms: web." in recap
    assert "Features: Barcode scanning, Stock alerts, Purchase orders, Audit log, and 2 more." in recap
    assert "Timeline: 3 to 6 months." in recap
    assert "Budget: $40k to $80k." in recap


# ==============================================================================
# Item 7: Shape Message Top MVP Items
# ==============================================================================


def test_shape_message_uses_top_mvp_items():
    arch = {"frontend": ["React Native"], "backend": ["FastAPI + PostgreSQL"]}
    mvp_res = {
        "mvp": ["User auth & profiles", "Push notifications", "Real-time location"],
        "later": ["Admin analytics dashboard"],
    }
    shape_msg = format_shape_message(arch, mvp_res)
    assert "Channels and UX: React Native" in shape_msg
    assert "Core flow: User auth & profiles, Push notifications, Real-time location" in shape_msg
    assert "Backend and APIs: FastAPI + PostgreSQL" in shape_msg
    assert "for the Core flow" not in shape_msg


# ==============================================================================
# Item 8: Post-Estimate Deduplication
# ==============================================================================


def test_post_estimate_role_answer_does_not_resend_estimate(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    brief = ProjectBrief(
        service="mobile_app",
        goal="Fitness tracker",
        platforms=["ios", "android"],
        features=["Logger"],
        features_confirmed=True,
        timeline="1_3_months",
        budget_band="15_40k",
        decision_role="founder_or_exec",
    )
    session.brief_json = brief.model_dump_json()

    # Turn 1: Generates estimate
    res1 = run_turn(db, tenant, config, session, [], "", {"field": "decision_role", "value": "founder_or_exec"})
    estimate_cards = [c for c in res1["cards"] if c.get("type") == "estimate"]
    assert len(estimate_cards) == 1

    # Turn 2: User answers company size post-estimate
    res2 = run_turn(db, tenant, config, session, [], "", {"field": "company_size", "value": "startup"})
    estimate_cards_2 = [c for c in res2["cards"] if c.get("type") == "estimate"]
    assert len(estimate_cards_2) == 0  # Estimate block is NEVER sent twice
    assert "designing for startup scale" in res2["message"]


def test_consecutive_faq_deduplication(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="advising")
    db.add(session)
    db.commit()

    with patch("backend.app.agents.router._merge") as mock_merge:
        h1 = MagicMock(content="We work in 2-week agile sprints with weekly client reviews.", score=0.88, id="faq_1")
        h2 = MagicMock(content="Our engineering contracts include a 30-day warranty and handoff documentation.", score=0.85, id="faq_2")
        mock_merge.return_value = [h1, h2]

        history = [
            {"role": "user", "content": "Tell me about your sprints"},
            {"role": "assistant", "content": "We work in 2-week agile sprints with weekly client reviews."},
        ]

        # Same question again should pick h2 or fallback
        res = run_turn(db, tenant, config, session, history, "Can you repeat about sprints?", None)
        assert res["message"] != "We work in 2-week agile sprints with weekly client reviews."
        assert (h2.content in res["message"]) or ("detail on a call" in res["message"])


# ==============================================================================
# Item 9: Scope Caution for >= 5 Features at Base Tier
# ==============================================================================


def test_scope_caution_for_5_features_at_base_tier(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    brief = ProjectBrief(
        service="web_app",
        goal="Clinic management software",
        platforms=["web"],
        features=["Patient scheduling", "Doctor portal", "Prescriptions", "Billing engine", "Lab records"],
        features_confirmed=True,
        timeline="3_6_months",
        budget_band="40_80k",
        decision_role="founder_or_exec",
    )
    session.brief_json = brief.model_dump_json()

    res = run_turn(db, tenant, config, session, [], "", {"field": "decision_role", "value": "founder_or_exec"})
    chip_labels = [c["label"] for c in res["chips"]]
    assert "Show the Core cut" in chip_labels
    assert "This range assumes the Core scope; a list this long will likely need more" in res["message"]
    assert "has room to add scope" not in res["message"]


# ==============================================================================
# Item 10: Flow Resolution Source of Truth
# ==============================================================================


def test_flow_resolution_priority():
    test_brand = BrandConfig(name="Test", slug="test", logo_text="Test", primary="#000", flow="classic")
    test_cfg = TenantConfig(brand=test_brand)

    if "ENABLE_FAST_FLOW" in os.environ:
        del os.environ["ENABLE_FAST_FLOW"]
    assert _resolve_flow(test_cfg) == "classic"

    test_brand.flow = "fast"
    assert _resolve_flow(test_cfg) == "fast"

    # Environment variable overrides for testing
    os.environ["ENABLE_FAST_FLOW"] = "1"
    assert _resolve_flow(test_cfg) == "fast"

    os.environ["ENABLE_FAST_FLOW"] = "0"
    assert _resolve_flow(test_cfg) == "classic"
    del os.environ["ENABLE_FAST_FLOW"]
