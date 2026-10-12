import json
import time
from unittest.mock import MagicMock, patch

import pytest
from backend.app.agents.brief import ProjectBrief
from backend.app.agents.extractor import extract_slots
from backend.app.agents.router import _truncate_word_boundary, format_shape_message
from backend.app.core.llm import LLMError, _gemini, complete_json
from backend.app.models.db import SessionLocal
from backend.app.models.entities import SystemEventRow
from backend.app.tenants.loader import load_tenant


# ==============================================================================
# Item 1: Natural Shape Sentence & Word-Boundary Cut (Never cut 'agree' to 'agre')
# ==============================================================================


def test_shape_sentence_natural_format_and_no_midword_cut():
    arch = {
        "frontend": ["Flutter"],
        "backend": ["Node.js + PostgreSQL"],
    }
    mvp_res = {
        "mvp": [
            "Primary user journey on the agreed platforms",
            "Core: login",
            "Core: calendar booking",
            "Core: push notifications",
        ],
        "later": ["Secondary platform polish"],
    }
    msg = format_shape_message(arch, mvp_res)
    assert msg == "Channels and UX: Flutter. Core flow: login, calendar booking, push notifications. Backend and APIs: Node.js + PostgreSQL."
    assert "agre" not in msg
    assert "agreed" not in msg


def test_truncate_word_boundary_never_cuts_midword():
    # Length > 35 with 'agreed' at boundary
    long_item = "Primary user journey on the agreed platforms"
    truncated = _truncate_word_boundary(long_item, max_len=35)
    assert truncated == "Primary user journey on the agreed"
    assert "agre" != truncated.split()[-1]
    assert not truncated.endswith("agre")

    # Short item untouched
    assert _truncate_word_boundary("login", max_len=35) == "login"

    # Single long word with no spaces cuts safely at max_len
    long_token = "SupercalifragilisticexpialidociousLongWord"
    assert len(_truncate_word_boundary(long_token, max_len=20)) <= 20


def test_shape_sentence_without_core_items_uses_clean_template():
    arch = {
        "frontend": ["React Native"],
        "backend": ["FastAPI + PostgreSQL"],
    }
    mvp_res = {
        "mvp": [
            "User auth & profiles",
            "Push notifications",
            "Real-time location",
        ],
        "later": [],
    }
    msg = format_shape_message(arch, mvp_res)
    assert msg == "Channels and UX: React Native. Core flow: User auth & profiles, Push notifications, Real-time location. Backend and APIs: FastAPI + PostgreSQL."


# ==============================================================================
# Item 6: Truncation handling (finishReason=MAX_TOKENS, invalid JSON, 600 cap, 9 features)
# ==============================================================================


def test_gemini_truncation_max_tokens_records_system_event():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "finishReason": "MAX_TOKENS",
                "content": {"parts": [{"text": '{"features": ["one", "two"'}]},
            }
        ],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 600, "thoughtsTokenCount": 0},
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(LLMError, match="finishReason=MAX_TOKENS"):
            _gemini("System prompt", "User prompt", api_key="fake-key", model="gemini-3.8-flash")

    # Verify system_event was recorded
    with SessionLocal() as session:
        events = session.query(SystemEventRow).filter(SystemEventRow.kind == "llm_truncation").all()
        assert len(events) >= 1
        assert events[-1].error_class == "TruncationError"
        assert "MAX_TOKENS" in events[-1].reason


def test_gemini_json_parse_error_records_system_event():
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "finishReason": "STOP",
                "content": {"parts": [{"text": "This is plain text, not JSON at all."}]},
            }
        ],
        "usageMetadata": {"promptTokenCount": 50, "candidatesTokenCount": 20, "thoughtsTokenCount": 0},
    }

    with patch("httpx.Client.post", return_value=mock_resp):
        with pytest.raises(LLMError, match="did not parse as JSON"):
            _gemini("System prompt", "User prompt", api_key="fake-key", model="gemini-3.8-flash")

    # Verify system_event was recorded
    with SessionLocal() as session:
        events = session.query(SystemEventRow).filter(SystemEventRow.kind == "llm_json_parse_error").all()
        assert len(events) >= 1
        assert events[-1].error_class == "JSONDecodeError"


def test_nine_feature_message_extraction_deterministic_fallback_on_truncation():
    nine_features_msg = (
        "I need a web app for hospital management. Features: patient registration, doctor scheduling, "
        "telemedicine video, prescription management, billing and insurance, lab diagnostics, "
        "ambulance tracking, medical records archive, and patient feedback ratings."
    )

    # When LLM fails with truncation error, extract_slots safely falls back to heuristic
    mock_resp = MagicMock()
    mock_resp.status_code = 200
    mock_resp.json.return_value = {
        "candidates": [
            {
                "finishReason": "MAX_TOKENS",
                "content": {"parts": [{"text": '{"features": ["incomplete'}]},
            }
        ],
    }

    with patch("backend.app.core.llm.llm_available", return_value=True):
        with patch("httpx.Client.post", return_value=mock_resp):
            extracted = extract_slots(nine_features_msg)
            assert isinstance(extracted, dict)
            # Heuristic extracted features or service
            assert extracted.get("service") == "web_app" or extracted.get("features")


# ==============================================================================
# Item 7: Slow Turns (6s Hard Timeout & Late Answer Discarded)
# ==============================================================================


def test_slow_turn_call_exceeding_15s_discards_late_answer():
    # Simulate a call that returns HTTP 200 but took > 15.0 seconds
    def slow_post(*args, **kwargs):
        time.sleep(0.05)  # slight sleep for test runtime
        resp = MagicMock()
        resp.status_code = 200
        resp.json.return_value = {
            "candidates": [
                {
                    "finishReason": "STOP",
                    "content": {"parts": [{"text": '{"message": "Late response"}'}]},
                }
            ],
            "usageMetadata": {"promptTokenCount": 10, "candidatesTokenCount": 10},
        }
        return resp

    # Patch time.monotonic so elapsed exceeds 20.0s (wall_budget)
    monotonic_vals = [0.0, 0.0, 20.1, 20.1, 20.1]

    def mock_monotonic():
        if monotonic_vals:
            return monotonic_vals.pop(0)
        return 21.0

    with patch("time.monotonic", side_effect=mock_monotonic):
        with patch("httpx.Client.post", side_effect=slow_post):
            with pytest.raises(LLMError, match="exceeded 15.0s timeout"):
                _gemini("System", "User", api_key="fake-key", model="gemini-3.8-flash", mode="request")

    # Verify system_event was recorded
    with SessionLocal() as session:
        events = session.query(SystemEventRow).filter(SystemEventRow.kind == "llm_slow_turn").all()
        assert len(events) >= 1
        assert events[-1].error_class == "TimeoutError"
        assert "exceeded 15.0s" in events[-1].reason
