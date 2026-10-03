from __future__ import annotations

import asyncio
import logging
from datetime import date
from unittest.mock import MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.core.llm import complete_json
from backend.app.core.settings import get_settings
from backend.app.core.usage import (
    calculate_cost,
    get_active_session,
    get_usage_summary,
    record_usage,
    reset_active_session,
    reset_usage_for_tests,
    set_active_session,
)
from backend.app.main import app
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import TokenUsageRow
from backend.app.rag.embeddings import _gemini_embed


@pytest.fixture(autouse=True)
def clean_usage():
    reset_usage_for_tests()
    yield
    reset_usage_for_tests()


@pytest.fixture
def auth():
    return ("admin", "test-admin")


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "test-admin")
    monkeypatch.setattr(settings, "admin_password_hash", "")
    init_db()
    return TestClient(app)


def test_gemini_38_rates_before_and_after_2027():
    """Literal test: 1M input + 1M output tokens on gemini-3.8-flash.

    Before 2027-01-01: $0.75 + $3.75 = $4.50 (= ₹427.50 at 95.0)
    From 2027-01-01: $1.50 + $7.50 = $9.00 (= ₹855.00 at 95.0)
    """
    # Before 2027-01-01
    cost_usd_2026, cost_inr_2026 = calculate_cost(
        "gemini-3.8-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        as_of_date="2026-10-01",
    )
    assert cost_usd_2026 == pytest.approx(4.50, rel=1e-4)
    assert cost_inr_2026 == pytest.approx(427.50, rel=1e-4)

    # From 2027-01-01
    cost_usd_2027, cost_inr_2027 = calculate_cost(
        "gemini-3.8-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        as_of_date="2027-01-01",
    )
    assert cost_usd_2027 == pytest.approx(9.00, rel=1e-4)
    assert cost_inr_2027 == pytest.approx(855.00, rel=1e-4)


def test_gemini_37_introductory_rates():
    """Gemini 3.7 Flash introductory rates match 3.8 Flash."""
    cost_usd, cost_inr = calculate_cost(
        "gemini-3.7-flash",
        prompt_tokens=1_000_000,
        completion_tokens=1_000_000,
        as_of_date="2026-06-01",
    )
    assert cost_usd == pytest.approx(4.50, rel=1e-4)
    assert cost_inr == pytest.approx(427.50, rel=1e-4)


def test_unknown_model_returns_none_and_never_falls_back():
    """Unknown models must record tokens, cost null, and never fall back to other rates."""
    usd, inr = calculate_cost("unknown-future-model-99", prompt_tokens=1000, completion_tokens=500)
    assert usd is None
    assert inr is None

    # Record usage with unknown model
    record_usage(
        provider="custom",
        model="unknown-future-model-99",
        call_type="llm",
        prompt_tokens=1000,
        completion_tokens=500,
        session_id="session-unknown",
    )
    summary = get_usage_summary()
    assert summary["total_tokens"] >= 1500
    assert "unknown-future-model-99" in summary["by_model"]
    assert summary["by_model"]["unknown-future-model-99"]["cost_inr"] is None
    assert summary["by_model"]["unknown-future-model-99"]["rate_status"] == "unknown"


def test_thinking_tokens_billed_as_output(monkeypatch):
    """Gemini usageMetadata thoughtsTokenCount must be added to completion_tokens."""
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [{"content": {"parts": [{"text": '{"status": "ok"}'}]}}],
                "usageMetadata": {
                    "promptTokenCount": 1000,
                    "candidatesTokenCount": 200,
                    "thoughtsTokenCount": 350,
                    "totalTokenCount": 1550,
                },
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")

    complete_json("system instructions", "user message")
    summary = get_usage_summary()
    # 200 candidates + 350 thoughts = 550 output tokens
    assert summary["prompt_tokens"] == 1000
    assert summary["completion_tokens"] == 550
    assert summary["total_tokens"] == 1550


def test_two_concurrent_sessions_do_not_mix():
    """Verify ContextVar isolates active session_id across concurrent asyncio tasks."""
    recorded_sessions: list[str] = []

    async def worker(session_id: str, prompt_tokens: int):
        token = set_active_session(session_id)
        try:
            # Yield control to let another task run
            await asyncio.sleep(0.01)
            # Verify active session matches
            current = get_active_session()
            assert current == session_id
            record_usage(
                provider="gemini",
                model="gemini-3.8-flash",
                call_type="llm",
                prompt_tokens=prompt_tokens,
                completion_tokens=10,
            )
            recorded_sessions.append(current)
        finally:
            reset_active_session(token)

    async def run_both():
        await asyncio.gather(
            worker("session-alpha-111", 500),
            worker("session-beta-222", 800),
        )

    asyncio.run(run_both())
    assert set(recorded_sessions) == {"session-alpha-111", "session-beta-222"}

    summary = get_usage_summary()
    assert summary["sample_size"] == 2
    recent_sids = [c["session_id"] for c in summary["recent_calls"]]
    assert "session-" in recent_sids[0]


def test_embedding_missing_tokens_is_estimated(monkeypatch):
    """When Gemini embedding API response lacks usageMetadata, store estimate with estimated=True."""
    class FakeEmbedResponse:
        status_code = 200

        def json(self):
            # No usageMetadata provided
            return {
                "embeddings": [
                    {"values": [0.1] * 768},
                    {"values": [0.2] * 768},
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, headers=None, json=None):
            return FakeEmbedResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "embedding_backend", "gemini")

    texts = ["short text", "a slightly longer text sample"]
    _gemini_embed(texts, model_id="gemini-embedding-001")

    summary = get_usage_summary()
    assert len(summary["recent_calls"]) >= 1
    call = summary["recent_calls"][0]
    assert call["estimated"] is True
    assert call["call_type"] == "embedding"


def test_db_error_in_record_usage_logs_warning_class_only_and_does_not_raise(caplog, monkeypatch):
    """DB errors during record_usage must log WARNING with class name only and never fail."""
    import backend.app.models.db as db_mod

    def faulty_session_local():
        raise RuntimeError("Disk is read-only or connection terminated")

    monkeypatch.setattr(db_mod, "SessionLocal", faulty_session_local)

    with caplog.at_level(logging.WARNING):
        # Must not raise
        record_usage(
            provider="gemini",
            model="gemini-3.8-flash",
            call_type="llm",
            prompt_tokens=100,
            completion_tokens=50,
            session_id="session-err-test",
        )

    # Check warning log: class name only
    warning_records = [r for r in caplog.records if r.levelname == "WARNING" and "Token usage DB write failed" in r.message]
    assert len(warning_records) == 1
    assert "Token usage DB write failed: RuntimeError" in warning_records[0].message
    assert "Disk is read-only" not in warning_records[0].message


def test_budget_unset_hides_balance_and_projections_require_20(client, auth, monkeypatch):
    """When USAGE_BUDGET_INR is unset, balance remaining card is hidden.

    When sample size n < 20, projections show 'Not enough data yet'.
    """
    settings = get_settings()
    monkeypatch.setattr(settings, "usage_budget_inr", None)

    # Record 5 sessions (n=5 < 20)
    for i in range(5):
        record_usage(
            provider="gemini",
            model="gemini-3.8-flash",
            call_type="llm",
            prompt_tokens=1000,
            completion_tokens=200,
            session_id=f"session-{i}",
        )

    summary = get_usage_summary()
    assert summary["sample_size"] == 5
    assert summary["projections_available"] is False
    assert summary["sessions_remaining"] is None
    assert summary["initial_budget_inr"] is None
    assert summary["balance_remaining_inr"] is None

    # Check Admin UI HTML
    resp = client.get("/admin", auth=auth)
    assert resp.status_code == 200
    assert "Balance Remaining" not in resp.text
    assert "Not enough data yet (n &lt; 20)" in resp.text or "Not enough data yet (n < 20)" in resp.text
