from __future__ import annotations

import pytest
from fastapi.testclient import TestClient

from backend.app.core.llm import complete_json
from backend.app.core.settings import get_settings
from backend.app.core.usage import (
    USD_TO_INR,
    calculate_cost,
    get_usage_summary,
    record_usage,
    reset_usage_for_tests,
)
from backend.app.main import app
from backend.app.models.db import SessionLocal, init_db
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


def test_calculate_cost():
    # 1,000,000 prompt tokens on gemini-2.5-flash = $0.075 USD = ₹7.13 INR (at ₹95/USD)
    usd, inr = calculate_cost("gemini-2.5-flash", prompt_tokens=1_000_000, completion_tokens=0)
    assert round(usd, 4) == 0.075
    assert round(inr, 2) == 7.12

    # 1,000,000 completion tokens on gemini-2.5-flash = $0.30 USD = ₹28.50 INR
    usd, inr = calculate_cost("gemini-2.5-flash", prompt_tokens=0, completion_tokens=1_000_000)
    assert round(usd, 4) == 0.30
    assert round(inr, 2) == 28.50

    # Embedding cost: 1M tokens on gemini-embedding-001 = $0.02 USD = ₹1.90 INR
    usd, inr = calculate_cost("gemini-embedding-001", prompt_tokens=1_000_000, completion_tokens=0, call_type="embedding")
    assert round(usd, 4) == 0.02
    assert round(inr, 2) == 1.90


def test_record_usage_and_summary():
    with SessionLocal() as db:
        # Record 10,000 prompt tokens and 1,000 completion tokens
        record_usage(
            provider="gemini",
            model="gemini-2.5-flash",
            call_type="llm",
            prompt_tokens=10_000,
            completion_tokens=1_000,
            session_id="test-session-1",
        )

        summary = get_usage_summary(db=db, initial_budget_inr=500.0)
        assert summary["total_calls"] >= 1
        assert summary["total_tokens"] >= 11_000
        assert float(summary["cost_inr"]) > 0.0
        assert float(summary["balance_remaining_inr"]) < 500.0
        assert "sessions_remaining" in summary
        assert "by_model" in summary
        assert "gemini-2.5-flash" in summary["by_model"]


def test_admin_usage_api_requires_auth(client, auth):
    # Unauthenticated visitor gets 401
    resp = client.get("/admin/api/usage")
    assert resp.status_code == 401

    # Bad password gets 401
    resp_bad = client.get("/admin/api/usage", auth=("admin", "wrong-pass"))
    assert resp_bad.status_code == 401

    # Valid admin credentials get 200 and JSON usage data
    resp_ok = client.get("/admin/api/usage", auth=auth)
    assert resp_ok.status_code == 200
    data = resp_ok.json()
    assert "cost_inr" in data
    assert "cost_usd" in data
    assert "balance_remaining_inr" in data
    assert "total_tokens" in data
    assert "sessions_remaining" in data


def test_admin_home_renders_usage_card(client, auth):
    # Admin home contains the token & cost tracker
    resp = client.get("/admin", auth=auth)
    assert resp.status_code == 200
    assert "LLM Token & Cost Usage Tracker" in resp.text
    assert "Total Spent" in resp.text
    assert "Balance Remaining" in resp.text
    assert "Capacity Remaining" in resp.text


def test_public_chat_endpoints_never_leak_costs(client):
    # Create session
    resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert resp.status_code == 200
    data = resp.json()

    # Never leak internal costs or token metrics to public user
    assert "cost_inr" not in data
    assert "cost_usd" not in data
    assert "llm_api_key" not in data
    assert "total_tokens" not in data


def test_gemini_llm_records_usage_with_metadata(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"result": "success"}'}]
                        }
                    }
                ],
                "usageMetadata": {
                    "promptTokenCount": 1500,
                    "candidatesTokenCount": 250,
                    "totalTokenCount": 1750,
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
    monkeypatch.setattr(get_settings(), "llm_api_key", "test-key")

    data = complete_json("System prompt", "User prompt")
    assert data.get("result") == "success"

    summary = get_usage_summary()
    assert summary["total_calls"] >= 1
    assert summary["prompt_tokens"] >= 1500
    assert summary["completion_tokens"] >= 250
