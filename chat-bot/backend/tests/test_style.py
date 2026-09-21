from backend.app.agents import orchestrator
from backend.app.agents.brief import ProjectBrief
from backend.app.agents.fallback import fallback_reply
from backend.app.agents.style import apply_live_style, detect_style, overlay_llm, prior_style_for_email
from backend.app.config_loader.loader import load_config
from backend.app.models.db import SessionLocal
from backend.app.models.entities import LeadRow, SessionRow
from backend.app.services.sessions import create_session, loads
from backend.tests.test_api import _discover
from backend.tests.test_booking_contact import _sse


READY = ProjectBrief(
    service="web_app",
    goal="Ops console so distributors track orders in one place",
    platforms=["web"],
    timeline="1_3_months",
    budget_band="40_80k",
    decision_role="founder_or_exec",
)


def test_detect_terse_price_intent() -> None:
    style = detect_style("just the price")
    assert style["pace"] == "terse"
    assert style["mood"] == "impatient"


def test_detect_confused() -> None:
    style = detect_style("I don't understand what you mean")
    assert style["clarity"] == "confused"


def test_technical_register_survives_a_short_ack() -> None:
    first = detect_style("We need Flutter, FastAPI, and pgvector for the RAG layer.")
    assert first["register"] == "technical"
    assert first["pace"] == "detailed" or first["register"] == "technical"
    second = detect_style("ok", previous=first)
    assert second["register"] == "technical"


def test_email_only_does_not_mark_them_terse() -> None:
    style = detect_style("founder@acme.test")
    assert style["pace"] == "balanced"
    assert "@" not in style["notes"]


def test_style_notes_never_contain_an_email() -> None:
    style = overlay_llm(
        detect_style("What stack would you use?"),
        {"notes": "Follow up with dana@acme.test about Flutter"},
    )
    assert "dana@acme.test" not in style["notes"]
    assert "@" not in style["notes"]


def test_fallback_terse_estimate_is_short() -> None:
    config = load_config()
    estimate = {"range_label": "$40k–$80k", "timeline_weeks": 12, "team": ["lead", "engineer"]}
    long = fallback_reply(stage="estimation", brief=READY, estimate=estimate, architecture={}, config=config)
    terse = fallback_reply(
        stage="estimation",
        brief=READY,
        estimate=estimate,
        architecture={},
        config=config,
        style=detect_style("just the price"),
    )
    assert "$40k–$80k" in terse["message"]
    assert "not a contractual quote" in terse["message"].lower()
    assert len(terse["message"].split()) < len(long["message"].split())
    assert len(terse["message"].split()) <= 36


def test_fallback_confused_restates_range_vs_quote() -> None:
    config = load_config()
    estimate = {"range_label": "$40k–$80k", "timeline_weeks": 12, "team": ["lead"]}
    reply = fallback_reply(
        stage="estimation",
        brief=READY,
        estimate=estimate,
        architecture={},
        config=config,
        style=detect_style("I don't understand"),
        last_assistant="Based on what you've shared, an indicative MVP sits around **$40k–$80k**.",
    )
    assert "indicative range" in reply["message"].lower() or "not a contractual quote" in reply["message"].lower()


def test_apply_live_style_confused_uses_last_assistant() -> None:
    text = apply_live_style(
        "Which platforms?",
        detect_style("what do you mean"),
        last_assistant="I asked whether this is iOS, Android, or both.",
    )
    assert text.lower().startswith("in short:")
    assert "which platforms" in text.lower()


def test_llm_prompt_includes_live_style(monkeypatch) -> None:
    config = load_config()
    captured: dict[str, str] = {}

    def fake_complete_json(system: str, user: str) -> dict:
        captured["system"] = system
        captured["user"] = user
        return {
            "brief_updates": {"goal": "A driver app"},
            "ask_field": "platforms",
            "message": "iOS first, or both?",
            "chips": [],
            "stage": "discovery",
            "visitor_style": {"pace": "terse", "clarity": "following"},
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(service="mobile_app"),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="just the price for a driver app",
        chip=None,
        page_opening="Planning a mobile product?",
        extra_questions=[],
        transcript="assistant: Planning a mobile product?",
        page_path="/mobile-app-development",
    )
    assert "How THIS visitor is chatting" in captured["user"]
    assert "live style" in captured["system"].lower() or "terse" in captured["system"].lower()
    assert result.style["pace"] == "terse"


def test_api_terse_price_after_estimate_is_short(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    response = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "just the price"})
    assert response.status_code == 200
    payload = _sse(response.text)
    assert "$" in payload["message"]
    assert len(payload["message"].split()) <= 36
    with SessionLocal() as db:
        style = loads(db.get(SessionRow, session_id).style_json, {})
    assert style["pace"] == "terse"
    page = client.get(f"/admin/sessions/{session_id}", auth=("admin", "test-admin"))
    assert page.status_code == 200
    assert "How they are chatting" in page.text
    assert "terse" in page.text


def test_api_confused_after_estimate_restates_quote(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    response = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "I don't understand"})
    assert response.status_code == 200
    payload = _sse(response.text)
    lowered = payload["message"].lower()
    assert "indicative" in lowered or "not a contractual quote" in lowered
    with SessionLocal() as db:
        style = loads(db.get(SessionRow, session_id).style_json, {})
    assert style["clarity"] == "confused"


def test_returning_email_seeds_prior_style(client) -> None:
    with SessionLocal() as db:
        prior = create_session(db, "", "Prior", "/", ProjectBrief(service="web_app"))
        prior.style_json = (
            '{"pace":"terse","clarity":"following","register":"technical",'
            '"mood":"neutral","notes":"short stack answers","returning":false}'
        )
        prior.learning_json = '{"tone_that_worked":"short answers","tone_to_avoid":"long dumps"}'
        db.add(LeadRow(session_id=prior.id, email="founder@acme.test"))
        db.commit()
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    with SessionLocal() as db:
        style = loads(db.get(SessionRow, session_id).style_json, {})
        assert prior_style_for_email(db, "founder@acme.test", session_id)["register"] == "technical"
    assert style["returning"] is True
    assert style["pace"] == "terse"
    assert style["register"] == "technical"
    assert "founder@acme.test" not in (style.get("notes") or "")

    other = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    assert client.post(f"/api/v1/sessions/{other}/messages", json={"content": "other@acme.test"}).status_code == 200
    with SessionLocal() as db:
        other_style = loads(db.get(SessionRow, other).style_json, {})
    assert other_style.get("returning") is not True
    assert other_style.get("register") != "technical" or other_style.get("pace") != "terse"
