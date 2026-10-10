from unittest.mock import patch, MagicMock
import pytest
from fastapi.testclient import TestClient

from backend.app.main import app

client = TestClient(app)

STARTERS = [
    "I have an app idea",
    "I need a web platform",
    "I want to add AI to my product",
    "I'm just exploring costs",
]


@pytest.mark.parametrize("starter_text", STARTERS)
def test_starter_plain_gives_discovery_with_question_and_chips(starter_text):
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    res = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": starter_text})
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "discovery"
    assert "?" in data["message"]
    assert len(data["chips"]) > 0


@pytest.mark.parametrize("starter_text", STARTERS)
def test_starter_ask_chip_gives_discovery_with_question_and_chips(starter_text):
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    res = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": starter_text, "chip": {"label": starter_text, "field": "ask", "value": starter_text}},
    )
    assert res.status_code == 200
    data = res.json()
    assert data["route"] == "discovery"
    assert "?" in data["message"]
    assert len(data["chips"]) > 0


def test_extractor_runs_once_for_ask_chip_zero_for_normal_chip():
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    # 1. Ask chip should run extract_slots once
    with patch("backend.app.agents.router.extract_slots") as mock_ext:
        mock_ext.return_value = {}
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "I have an app idea", "chip": {"label": "I have an app idea", "field": "ask", "value": "I have an app idea"}},
        )
        assert res.status_code == 200
        assert mock_ext.call_count == 1

    # 2. Normal chip should run extract_slots zero times
    with patch("backend.app.agents.router.extract_slots") as mock_ext:
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "Web app", "chip": {"label": "Web app", "field": "service", "value": "web_app"}},
        )
        assert res.status_code == 200
        assert mock_ext.call_count == 0


def test_tell_me_about_your_process_uses_retrieval():
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    with patch("backend.app.agents.router._merge") as mock_merge:
        mock_hit = MagicMock()
        mock_hit.score = 0.85
        mock_hit.content = "Our engineering process follows agile sprints and weekly reviews."
        mock_hit.id = "p1"
        mock_merge.return_value = [mock_hit]
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "Tell me about your process"},
        )
        assert res.status_code == 200
        assert mock_merge.called


def test_do_you_use_flutter_uses_retrieval():
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    with patch("backend.app.agents.router._merge") as mock_merge:
        mock_hit = MagicMock()
        mock_hit.score = 0.90
        mock_hit.content = "Yes, we specialize in Flutter and React Native for cross-platform apps."
        mock_hit.id = "f1"
        mock_merge.return_value = [mock_hit]
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "Do you use Flutter?"},
        )
        assert res.status_code == 200
        assert mock_merge.called


def test_too_expensive_gets_objection_reply():
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    res = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "That seems too expensive"},
    )
    assert res.status_code == 200
    assert res.json()["route"] == "objection"


def test_ok_thanks_is_acknowledgement():
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    res = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "ok thanks"},
    )
    assert res.status_code == 200
    assert res.json()["route"] == "fallback"

    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import SessionRow
    import json
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        s_row.stage = "advising"
        s_row.estimate_json = json.dumps({"range_label": "$30,000 - $45,000", "timeline_weeks": 8})
        s_row.brief_json = json.dumps({
            "service": "web_app", "goal": "Clinic SaaS", "platforms": ["web"],
            "timeline": "1_3_months", "budget_band": "40_80k", "decision_role": "founder_or_exec",
            "company_size": "startup"
        })
        db.commit()
    res2 = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "ok thanks"},
    )
    assert res2.status_code == 200
    assert res2.json()["route"] == "fallback"
    assert "glad" in res2.json()["message"].lower()
