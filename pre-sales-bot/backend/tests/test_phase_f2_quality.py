from __future__ import annotations

import json
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.router import run_turn
from backend.app.core.guard import sanitize_price_leaks
from backend.app.core.llm import LLMError, complete_json, record_system_event
from backend.app.core.settings import get_settings
from backend.app.main import app
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import SessionRow, SystemEventRow, TenantRow
from backend.app.rag.embeddings import EmbeddingError, record_query_failure, set_failure_listener
from backend.app.rag.grade import grade
from backend.app.rag.store import Hit, search
from backend.app.engines.qualification import qualify
from backend.app.tenants.loader import ensure_tenant_row, load_tenant


@pytest.fixture
def auth():
    return ("admin", "test-admin")


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "test-admin")
    monkeypatch.setattr(settings, "admin_password_hash", "")
    monkeypatch.setattr(settings, "usage_budget_inr", 500.0)
    init_db()
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. LLM request-time budget (Item 1)
# ---------------------------------------------------------------------------

def test_llm_request_time_budget_exceeded(monkeypatch):
    """Visitor request-time LLM mode has max 1 retry and 12s wall budget, then raises LLMError."""
    call_count = 0

    class Fake429Response:
        status_code = 429
        text = "Rate limit hit"

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None):
            nonlocal call_count
            call_count += 1
            return Fake429Response()

    monkeypatch.setattr("httpx.Client", FakeClient)
    monkeypatch.setattr("time.sleep", lambda s: None)
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-2.5-flash")

    # In request mode, 1 initial attempt + 1 retry = 2 calls total before LLMError
    with pytest.raises(LLMError, match="Gemini quota exceeded"):
        complete_json("system instructions", "user message", mode="request")

    assert call_count == 2, f"Expected 2 attempts (initial + 1 retry), got {call_count}"


# ---------------------------------------------------------------------------
# 2. Public /health is minimal and admin health is detailed (Item 2)
# ---------------------------------------------------------------------------

def test_public_health_exposes_no_internals(client, auth):
    """Public /health must only return {'status': 'ok' | 'degraded'} with no model, counts, or error class."""
    res = client.get("/health")
    assert res.status_code == 200
    data = res.json()
    assert set(data.keys()) == {"status"}
    assert data["status"] in ("ok", "degraded")
    assert "model" not in data
    assert "embedding_backend" not in data
    assert "tenants" not in data
    assert "llm" not in data
    assert "embeddings" not in data
    assert "stale_chunks" not in data
    assert "admin" not in data

    # Admin health retains full diagnostics
    admin_res = client.get("/admin/api/health", auth=auth)
    assert admin_res.status_code == 200
    admin_data = admin_res.json()
    assert "status" in admin_data
    assert "embedding_backend" in admin_data
    assert "tenants" in admin_data
    assert "embeddings" in admin_data
    assert "llm" in admin_data
    assert "stale_chunks" in admin_data
    assert "admin" in admin_data


# ---------------------------------------------------------------------------
# 3. Explicit embedding failure listener (Item 3)
# ---------------------------------------------------------------------------

def test_explicit_failure_listener_creates_event_and_db_error_isolated(monkeypatch):
    """Forced embedding failure records a system_events row; DB error inside listener never breaks caller."""
    listener_called = False

    def custom_listener(exc: Exception):
        nonlocal listener_called
        listener_called = True

    set_failure_listener(custom_listener)

    # Trigger failure
    record_query_failure(EmbeddingError("Quota exhausted", status_code=429))
    assert listener_called is True

    # Verify system_events row was recorded
    with SessionLocal() as db:
        events = db.query(SystemEventRow).filter(SystemEventRow.kind == "embedding_failure").all()
        assert len(events) >= 1
        assert "EmbeddingError" in events[-1].error_class

    # Test DB error inside a listener does not break record_query_failure
    def faulty_listener(exc: Exception):
        raise RuntimeError("Database connection terminated")

    set_failure_listener(faulty_listener)
    # Must not raise
    record_query_failure(EmbeddingError("Another failure", status_code=500))


# ---------------------------------------------------------------------------
# 4. Role confirmation does NOT inflate qualification score (Item 4)
# ---------------------------------------------------------------------------

def test_student_role_confirmation_does_not_inflate_score():
    """Answering 'live project at a company' leaves decision_role neutral, matching a visitor who never mentioned student."""
    config = load_tenant("demo")

    # Brief A: Never mentioned being a student
    brief_a = ProjectBrief(
        service="mobile_app",
        platforms=["ios", "android"],
        company_size="startup",
    )
    qual_a = qualify(brief_a, config.qualification, config.services)

    # Brief B: Mentioned student, then confirmed live company project
    brief_b = ProjectBrief(
        service="mobile_app",
        platforms=["ios", "android"],
        company_size="startup",
        role_unconfirmed=True,
    )
    brief_b.apply_chip("confirm_role", "company_project")
    assert brief_b.role_unconfirmed is False
    assert brief_b.decision_role is None  # Neutral, not founder_or_exec
    qual_b = qualify(brief_b, config.qualification, config.services)

    # Score must be identical
    assert qual_a["score"] == qual_b["score"]
    assert qual_a["band"] == qual_b["band"]


# ---------------------------------------------------------------------------
# 5. Price guard 30-sample matrix (Item 5)
# ---------------------------------------------------------------------------

GUARD_SAMPLES = [
    # (input_text, allowed_estimate, visitor_budget, expected_contains_or_exact, should_pass_figure)
    # 1. Legit engine lower band $36k
    ("Estimated range is $36k for your scope.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36k", True),
    # 2. Legit engine upper band $45k
    ("Total could be up to $45k.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$45k", True),
    # 3. Legit uppercase K
    ("Pricing band: $36K to $45K.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36K to $45K", True),
    # 4. Legit comma format
    ("The baseline is 36,000 USD.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "36,000 USD", True),
    # 5. Legit USD 36000 prefix
    ("Target cost is USD 36000.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "USD 36000", True),
    # 6. Legit word format
    ("Overall investment is 36 thousand dollars.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "36 thousand dollars", True),
    # 7. Legit high word format
    ("Capped at 45 thousand dollars.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "45 thousand dollars", True),
    # 8. Visitor-stated budget echoed back ($25k-$50k)
    ("Aligned with your $25k-$50k budget.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, "$25k-$50k", "$25k-$50k", True),
    # 9. Visitor-stated budget single figure
    ("Fits inside your $50k envelope.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, "50k", "$50k", True),
    # 10. Visitor-stated budget range with text
    ("Referencing your 25k to 50k budget.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, "25k to 50k", "25k to 50k", True),
    # 11. Unauthorized cheap figure $5,000
    ("We can deliver this for only $5,000.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 12. Unauthorized $12k
    ("Special discount rate is $12k.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 13. Unauthorized $15,000 comma
    ("It will cost exactly $15,000.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 14. Unauthorized USD 20000
    ("Fixed price: USD 20000.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 15. Unauthorized 80 thousand dollars
    ("Total quote is 80 thousand dollars.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 16. Unauthorized Rupee figure Rs 30 lakh without estimate
    ("Rough estimate is Rs 30 lakh.", None, None, "custom indicative pricing", False),
    # 17. Unauthorized ₹50,000
    ("Development fee is ₹50,000.", None, None, "custom indicative pricing", False),
    # 18. Unauthorized Rs. 25 lakh
    ("Starts from Rs. 25 lakh.", None, None, "custom indicative pricing", False),
    # 19. Unauthorized INR 500000
    ("Budget needed: INR 500000.", None, None, "custom indicative pricing", False),
    # 20. Exact range label match passes through
    ("Project quote: $36,000–$45,000 USD.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", True),
    # 21. Bare legit number 36000
    ("Budget baseline: 36000 dollars.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "36000 dollars", True),
    # 22. Bare unauthorized number 10,000
    ("Budget baseline: 10,000 dollars.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 23. Legit range label without estimate object
    ("Consultation is free.", None, None, "Consultation is free.", True),
    # 24. Multiple unauthorized figures in one sentence
    ("Was $20k now $15k.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 25. Mixed legit engine figure and unauthorized figure
    ("Between $36k and $90k.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36k", True),
    # 26. Visitor budget 15k to 40k
    ("Based on your $15k-$40k range.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, "$15k-$40k", "$15k-$40k", True),
    # 27. Unauthorized $100k
    ("Enterprise edition is $100k.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 28. Small unauthorized $500
    ("Hosting fee is $500.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 29. Unauthorized 999 USD
    ("Setup cost is 999 USD.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$36,000–$45,000 USD", False),
    # 30. Legit high figure $45,000
    ("The upper ceiling is $45,000.", {"low": 36000, "high": 45000, "range_label": "$36,000–$45,000 USD"}, None, "$45,000", True),
]


def test_price_guard_30_sample_matrix():
    """Verify all 30 price guard samples pass legit figures and replace unauthorized ones."""
    table_rows = []
    for idx, (input_text, estimate, visitor_budget, expected_token, should_pass) in enumerate(GUARD_SAMPLES, 1):
        actual = sanitize_price_leaks(input_text, allowed_estimate=estimate, visitor_budget=visitor_budget)
        assert expected_token in actual, f"Sample {idx} failed:\nInput: {input_text}\nExpected: {expected_token}\nActual: {actual}"
        table_rows.append((idx, input_text, actual, "PASSED"))
    assert len(table_rows) == 30


# ---------------------------------------------------------------------------
# 6. Lexical-only mode cap at weak (Item 6)
# ---------------------------------------------------------------------------

def test_lexical_only_mode_caps_at_weak_never_show():
    """During embedding outage, lexical hits can never return 'show'; irrelevant questions return 'low'."""
    # Relevant chunk in lexical fallback
    rel_hit = Hit(
        id="c1",
        doc_id="doc1",
        title="Flutter Mobile Engineering",
        content="We build iOS and Android apps using Flutter and Dart.",
        score=0.85,  # High score
        source="knowledge",
        lexical_only=True,
    )
    decision, score = grade("Do you build Flutter mobile apps?", [rel_hit])
    assert decision == "weak"  # Capped at weak, never 'show'

    # Irrelevant query in lexical fallback
    irrel_hit = Hit(
        id="c2",
        doc_id="doc2",
        title="Healthcare Medical Record Portal",
        content="HIPAA compliant backend systems for hospital clinics.",
        score=0.15,  # Low score < weak_min_score (0.35)
        source="knowledge",
        lexical_only=True,
    )
    irrel_decision, irrel_score = grade("What is the recipe for chocolate cake?", [irrel_hit])
    assert irrel_decision == "low"  # Falls below weak threshold


# ---------------------------------------------------------------------------
# 7. Golden end-to-end Sarah prompt test (Item 7)
# ---------------------------------------------------------------------------

def test_sarah_golden_prompt_pinned_estimate():
    """Pin the exact estimate produced by README sample prompt with Sarah's inquiry."""
    init_db()
    with SessionLocal() as db:
        tenant = ensure_tenant_row(db, "demo")
        config = load_tenant("demo")
        session = SessionRow(tenant_id=tenant.id)
        db.add(session)
        db.commit()

        prompt = (
            "Hi, I am Sarah, Founder at a Fintech startup. We urgently need a cross-platform mobile app "
            "for iOS & Android with AI chat, timeline is 2 months, and our budget is around $25k to $50k. "
            "Can we schedule a discussion?"
        )
        res = run_turn(db, tenant, config, session, [], prompt, None)

        assert res["route"] == "estimate"
        assert res["stage"] == "advising"
        assert res["estimate"] is not None
        est = res["estimate"]
        assert est["low"] == 36000
        assert est["high"] == 45000
        assert est["range_label"] == "$36,000–$45,000 USD"
        assert est["complexity_band"] == "complex"
        # "urgently" extracts to "asap", which takes complex band (22 weeks) * 0.85 = 19 weeks
        assert est["timeline_weeks"] == 19

        brief_data = json.loads(session.brief_json)
        assert brief_data["service"] == "mobile_app"
        assert set(brief_data["platforms"]) == {"ios", "android"}
        assert "AI chat" in brief_data["ai_features"]
        assert brief_data["timeline"] == "asap"
        assert brief_data["budget_band"] == "40_80k"
        assert brief_data["decision_role"] == "founder_or_exec"
