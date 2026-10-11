from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest
from fastapi.testclient import TestClient

from backend.app.core.llm import LLMError, _gemini, complete_json
from backend.app.core.settings import ROOT, get_settings
from backend.app.main import app
from backend.app.memory.rewrite import lookup_queries, rewrite_query
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import SessionRow, SystemEventRow


@pytest.fixture
def client(monkeypatch):
    settings = get_settings()
    monkeypatch.setattr(settings, "admin_username", "admin")
    monkeypatch.setattr(settings, "admin_password", "test-admin")
    monkeypatch.setattr(settings, "admin_password_hash", "")
    init_db()
    return TestClient(app)


# ---------------------------------------------------------------------------
# 1. Model Fallback Tests (QA-1 Item 2)
# ---------------------------------------------------------------------------

def test_model_fallback_404_when_fallback_configured(monkeypatch):
    """404 on primary model falls back to secondary model when configured."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_model_fallbacks", "gemini-fallback-model")

    called_models = []

    class MockResponse:
        def __init__(self, status_code, data=None):
            self.status_code = status_code
            self._data = data or {}
            self.text = "Error"

        def json(self):
            return self._data

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            model_name = url.split("/models/")[1].split(":")[0]
            called_models.append(model_name)
            if model_name == "gemini-3.8-flash":
                return MockResponse(404)
            return MockResponse(200, {
                "candidates": [{"content": {"parts": [{"text": '{"result": "fallback_ok"}'}]}}],
                "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 5},
            })

    monkeypatch.setattr("httpx.Client", MockClient)

    res = complete_json("System", "User")
    assert res.get("result") == "fallback_ok"
    assert called_models == ["gemini-3.8-flash", "gemini-fallback-model"]

    # Verify system_events recorded model_fallback
    with SessionLocal() as db:
        event = db.query(SystemEventRow).filter(SystemEventRow.kind == "model_fallback").order_by(SystemEventRow.created_at.desc()).first()
        assert event is not None
        assert "HTTPStatusError" in event.error_class


def test_model_fallback_404_without_fallback_raises_error(monkeypatch):
    """404 with no fallback model configured raises LLMError."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_model_fallbacks", "")

    class MockResponse:
        status_code = 404
        text = "Model not found"

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    with pytest.raises(LLMError, match="404"):
        complete_json("System", "User")


def test_model_fallback_429_does_not_fall_back(monkeypatch):
    """429 does NOT fall back to another model; it raises quota error."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_model_fallbacks", "gemini-fallback-model")

    called_models = []

    class MockResponse:
        status_code = 429
        text = "Quota exceeded"

    class MockClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None, headers=None):
            model_name = url.split("/models/")[1].split(":")[0]
            called_models.append(model_name)
            return MockResponse()

    monkeypatch.setattr("httpx.Client", MockClient)

    with pytest.raises(LLMError, match="quota exceeded"):
        complete_json("System", "User")

    # Only the primary model was called (with retries), never the fallback model
    assert all(m == "gemini-3.8-flash" for m in called_models)


def test_admin_health_shows_configured_and_last_used_model(client, monkeypatch):
    """admin/api/health returns configured_model and last_used_model."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")

    res = client.get("/admin/api/health", auth=("admin", "test-admin"))
    assert res.status_code == 200
    data = res.json()
    assert "configured_model" in data
    assert data["configured_model"] == "gemini-3.8-flash"
    assert "last_used_model" in data


# ---------------------------------------------------------------------------
# 2. Rewrite Bypass Tests (QA-1 Item 3)
# ---------------------------------------------------------------------------

def test_rewrite_query_bypassed_for_clean_query_with_4_or_more_words(monkeypatch):
    """'Which cloud do you host on?' has 6 words and no trigger tokens -> bypass LLM rewrite."""
    llm_called = False

    def fake_complete(*args, **kwargs):
        nonlocal llm_called
        llm_called = True
        return {"query": "rewritten"}

    monkeypatch.setattr("backend.app.memory.rewrite.llm_available", lambda: True)
    monkeypatch.setattr("backend.app.memory.rewrite.complete_json", fake_complete)

    res = rewrite_query("Which cloud do you host on?", "Visitor building SaaS", ["We use AWS"])
    assert res == "Which cloud do you host on?"
    assert not llm_called


def test_rewrite_query_triggers_on_what_about(monkeypatch):
    """'what about Android?' after a Flutter answer contains 'what about' and has <4 words -> rewritten."""
    llm_called = False

    def fake_complete(*args, **kwargs):
        nonlocal llm_called
        llm_called = True
        return {"query": "Does the team also support Android alongside Flutter?"}

    monkeypatch.setattr("backend.app.memory.rewrite.llm_available", lambda: True)
    monkeypatch.setattr("backend.app.memory.rewrite.complete_json", fake_complete)

    res = rewrite_query("what about Android?", "Discussing Flutter mobile apps", ["We build with Flutter"])
    assert res == "Does the team also support Android alongside Flutter?"
    assert llm_called


# ---------------------------------------------------------------------------
# 3. Question-like Detector Tests (QA-1 Item 4)
# ---------------------------------------------------------------------------

@pytest.mark.parametrize("query_text", [
    "I want to know your tech stack",
    "I'd like to know about pricing",
    "I would like to understand the architecture",
    "want to understand your process",
    "wondering if you work with startups",
    "curious about timelines",
    "need more info on mobile apps",
    "need more information about backend",
    "need more details about delivery",
    "looking for info on security",
    "looking for information on payment integrations",
    "looking for details on MVP scope",
    "more about your methodology",
    "your pricing",
    "your process",
    "your team",
    "your stack",
    "your support",
])
def test_question_like_detector_routes_to_retrieval_not_nudge(client, query_text):
    """Phrases from QA-1 item 4 must NOT trigger discovery nudge; they route to retrieval or grounded answer."""
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    res = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": query_text})
    assert res.status_code == 200
    data = res.json()
    # It must not be discovery route (discovery nudge is avoided)
    assert data["route"] in ("faq", "grounded_answer", "case_study", "fallback", "objection")


def test_e1b_starter_chips_still_trigger_discovery(client):
    """Starter chip texts still trigger discovery stage and route."""
    for starter in ["I have an app idea", "I need a web platform", "I want to add AI to my product", "I'm just exploring costs"]:
        s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
        sid = s["session_id"]
        res = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": starter})
        assert res.status_code == 200
        assert res.json()["route"] == "discovery"
        assert res.json()["stage"] == "discovery"


# ---------------------------------------------------------------------------
# 4. Grounded Response Safety Tests (QA-1 Item 5)
# ---------------------------------------------------------------------------

def test_grounded_responses_contain_no_unsupported_claims(client):
    """Pinned deterministic texts contain no past project claims, guarantees, or fake price promises."""
    from backend.app.agents.router import run_turn
    from backend.app.tenants.loader import load_tenant

    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    # 1. Post-booking ack
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        s_row.stage = "handoff"
        s_row.booking_json = json.dumps({"label": "Friday Oct 10, 3:00 PM UTC", "slot_iso": "2026-10-10T15:00:00Z"})
        s_row.brief_json = json.dumps({"service": "mobile_app", "goal": "Fitness app", "platforms": ["ios"]})
        db.commit()

    res = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "sounds good thank you"})
    assert res.status_code == 200
    msg = res.json()["message"]
    # Check exact content
    assert "You're all set for Friday Oct 10, 3:00 PM UTC" in msg
    assert "The team will see this whole conversation" in msg
    # Verify safety: no claims
    banned = ["guarantee", "guaranteed", "similar project", "past client", "delivered in", "$"]
    for b in banned:
        assert b not in msg.lower()


# ---------------------------------------------------------------------------
# 5. UI Rendering & Parity Tests (QA-1 Item 6)
# ---------------------------------------------------------------------------

def test_rendering_strings_and_card_handler_exist_in_widget_and_studio():
    """Card type 'shape', and chips 'Email me instead', 'Show a leaner cut' exist in both widget and studio."""
    for file_path in ["widget/consultant.js", "public/studio.html"]:
        text = (ROOT / file_path).read_text(encoding="utf-8")
        assert "shape" in text, f"Missing 'shape' handler in {file_path}"
        assert "Email me instead" in text, f"Missing 'Email me instead' in {file_path}"
        assert "Show a leaner cut" in text, f"Missing 'Show a leaner cut' in {file_path}"


def test_widget_consultant_and_public_widget_are_byte_identical():
    """widget/consultant.js and public/widget/consultant.js must be 100% byte-identical."""
    src = (ROOT / "widget" / "consultant.js").read_bytes()
    dest = (ROOT / "public" / "widget" / "consultant.js").read_bytes()
    assert src == dest, "widget/consultant.js and public/widget/consultant.js differ!"
