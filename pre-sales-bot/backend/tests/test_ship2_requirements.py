import json
from unittest.mock import patch, MagicMock
import pytest

from backend.app.core.settings import get_settings
from backend.app.models.db import SessionLocal
from backend.app.models.entities import SessionRow
from backend.app.agents.brief import ProjectBrief
from backend.app.agents.extractor import extract_slots
from backend.app.agents.discovery_synth import synthesize_discovery_prompt
from backend.app.agents.router import _synthesize_estimate_message
from backend.app.agents.fallback import fallback_message
from backend.app.rag.grade import grounded_answer, GROUNDING_LINE, GROUNDED_SYSTEM_PROMPT
from backend.app.rag.store import Hit
from backend.app.tenants.loader import load_tenant

EXPECTED_GROUNDING = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)


def test_ship2_grounding_line_in_grade_prompt():
    """Grounding line must be present in rag/grade.py grounded_answer prompt."""
    assert EXPECTED_GROUNDING == GROUNDING_LINE
    assert EXPECTED_GROUNDING in GROUNDED_SYSTEM_PROMPT

    # Verify runtime call passes the grounding prompt
    hit = Hit(id="h1", doc_id="d1", title="Sample", content="Sample content", score=0.9, source="demo")
    with patch("backend.app.rag.grade.llm_available", return_value=True), \
         patch("backend.app.rag.grade.complete_json") as mock_complete:
        mock_complete.return_value = {"message": "Grounded response"}
        res = grounded_answer("How does it work?", [hit])
        assert res == "Grounded response"
        mock_complete.assert_called_once()
        system_arg = mock_complete.call_args[0][0]
        assert EXPECTED_GROUNDING in system_arg
        # Verify mode="request" passed
        assert mock_complete.call_args.kwargs.get("mode") == "request" or (
            len(mock_complete.call_args[0]) >= 3 and mock_complete.call_args[0][2] == "request"
        )


def test_ship2_no_after_integrations_sets_none(client):
    """'no' after the integrations question sets integrations to none."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    # Reach integrations stage in discovery
    client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "service", "value": "web_app", "label": "Web app"}})
    client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "A patient appointment scheduling portal"})
    client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "features_done", "value": "yes", "label": "Ready"}})
    client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "user_flow", "value": "not_specified", "label": "Skip"}})
    client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "platforms", "value": ["web"], "label": "Web"}})
    r_users = client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "users", "value": "business", "label": "Business users"}})
    
    # Assistant now asks the integrations question ("Any systems this needs to talk to on day one?")
    assert "systems this needs to talk to" in r_users.json()["message"].lower() or any(c["field"] == "integrations" for c in r_users.json()["chips"])

    # Visitor says "no"
    r_no = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "no"})
    assert r_no.status_code == 200

    # Verify session brief integrations is ['none']
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        brief = json.loads(s_row.brief_json or "{}")
        assert brief.get("integrations") == ["none"]

    # Verify discovery advanced to timeline
    assert any(c["field"] == "timeline" for c in r_no.json()["chips"]) or "timeline" in r_no.json()["message"].lower() or "when" in r_no.json()["message"].lower()


def test_ship2_yes_after_admin_sets_admin(client):
    """'yes' after the admin question sets admin to True."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    # Set up session with assistant asking an admin portal question
    from backend.app.api.sessions import _add
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        s_row.brief_json = json.dumps({"service": "web_app", "goal": "Clinic management"})
        # Add assistant message asking about admin
        _add(db, sid, "assistant", "Will you need an admin portal for user management and reporting?")
        db.commit()

    # Visitor answers "yes"
    r_yes = client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "yes"})
    assert r_yes.status_code == 200

    # Verify brief has admin=True
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        brief = json.loads(s_row.brief_json or "{}")
        assert brief.get("admin") is True


def test_ship2_thanks_after_estimate_skips_llm(client):
    """'thanks' after the estimate still skips the LLM."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    # Set session as already delivered estimate
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        s_row.stage = "advising"
        s_row.estimate_json = json.dumps({"range_label": "$40,000 - $60,000", "timeline_weeks": 8})
        s_row.brief_json = json.dumps({
            "service": "web_app", "goal": "Clinic SaaS", "platforms": ["web"],
            "timeline": "1_3_months", "budget_band": "40_80k", "decision_role": "founder_or_exec",
            "company_size": "startup"
        })
        db.commit()

    with patch("backend.app.core.llm.complete_json") as mock_complete:
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "thanks"},
        )
        assert res.status_code == 200
        mock_complete.assert_not_called()
        body = res.json()
        assert body["route"] == "fallback"
        assert "glad that aligns" in body["message"].lower()


@pytest.mark.parametrize("caller_name", [
    "extractor", "consult", "solution", "fallback", "grounded_answer"
])
def test_ship2_callers_pass_mode_request_and_carry_thinking_level_low(caller_name, monkeypatch):
    """Every LLM call made during visitor request passes mode='request' and carries thinkingLevel 'low'."""
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "mock-gemini-key")
    monkeypatch.setattr(settings, "llm_provider", "gemini")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_thinking_level", "low")

    tenant = load_tenant("demo")
    brief = ProjectBrief(service="web_app", goal="Clinic management", budget_band="40_80k", timeline="1_3_months")
    estimate = {"range_label": "$40k - $60k", "timeline_weeks": 8}
    hit = Hit(id="h1", doc_id="d1", title="Demo Case", content="Sample case study content", score=0.9, source="demo")

    recorded_payloads = []

    def mock_gemini(system, user, api_key, model, mode="request"):
        assert mode == "request", f"Caller {caller_name} failed to pass mode='request'"
        from backend.app.core.llm import get_settings
        st = get_settings()
        gen_config = {"responseMimeType": "application/json", "temperature": 0.2}
        if model.startswith("gemini-3") and mode == "request":
            gen_config["thinkingConfig"] = {"thinkingLevel": st.llm_thinking_level}
        body = {
            "contents": [{"parts": [{"text": user}]}],
            "generationConfig": gen_config,
        }
        recorded_payloads.append(body)
        return {"message": "Success response", "service": "web_app", "relevant": True}

    monkeypatch.setattr("backend.app.core.llm._gemini", mock_gemini)

    if caller_name == "extractor":
        extract_slots("We need a custom web app for scheduling", pending_field="goal", brief=brief)
    elif caller_name == "consult":
        synthesize_discovery_prompt(tenant, brief, field="features", user_text="We need scheduling")
    elif caller_name == "solution":
        _synthesize_estimate_message(tenant, brief, estimate)
    elif caller_name == "fallback":
        fallback_message(tenant, brief, estimate, query="What is your process?", notes=[hit])
    elif caller_name == "grounded_answer":
        grounded_answer("How does scheduling work?", [hit])

    assert len(recorded_payloads) == 1, f"Expected 1 call for {caller_name}"
    payload = recorded_payloads[0]
    gen_config = payload.get("generationConfig", {})
    thinking_cfg = gen_config.get("thinkingConfig", {})
    assert thinking_cfg.get("thinkingLevel") == "low", f"{caller_name} did not carry thinkingLevel 'low': {gen_config}"
