import logging
import pytest
from unittest.mock import patch, MagicMock

from backend.app.agents.fallback import FALLBACK_SYSTEM_PROMPT, GROUNDING_LINE as FALLBACK_GROUNDING
from backend.app.agents.discovery_synth import CONSULT_SYSTEM_PROMPT, GROUNDING_LINE as CONSULT_GROUNDING
from backend.app.agents.router import SOLUTION_SYSTEM_PROMPT, GROUNDING_LINE as ROUTER_GROUNDING
from backend.app.core.guard import sanitize_price_leaks


EXPECTED_GROUNDING = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)


def test_ship1_grounding_lines_present():
    """Grounding line must be verbatim present in fallback, consult, and solution prompts."""
    assert EXPECTED_GROUNDING in FALLBACK_SYSTEM_PROMPT
    assert EXPECTED_GROUNDING in CONSULT_SYSTEM_PROMPT
    assert EXPECTED_GROUNDING in SOLUTION_SYSTEM_PROMPT
    assert FALLBACK_GROUNDING == EXPECTED_GROUNDING
    assert CONSULT_GROUNDING == EXPECTED_GROUNDING
    assert ROUTER_GROUNDING == EXPECTED_GROUNDING


def test_ship1_chip_click_skips_extractor(client):
    """Chip clicks must NOT call LLM slot extractor."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    with patch("backend.app.agents.router.extract_slots") as mock_extract:
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={
                "content": "Web app",
                "chip": {"field": "service", "value": "web_app", "label": "Web application"},
            },
        )
        assert res.status_code == 200
        mock_extract.assert_not_called()


@pytest.mark.parametrize("ack_text", [
    "hi", "hello", "thanks"
])
def test_ship1_always_acknowledgements_skip_retrieval(client, ack_text):
    """hi/hello/thanks always skip embedding/retrieval and return deterministic reply."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    with patch("backend.app.agents.router.search") as mock_search, \
         patch("backend.app.rag.store.embed_query") as mock_embed:
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": ack_text},
        )
        assert res.status_code == 200
        mock_search.assert_not_called()
        mock_embed.assert_not_called()
        data = res.json()
        assert data["route"] in ("fallback", "discovery")
        assert len(data["message"]) > 0


@pytest.mark.parametrize("ack_text", [
    "ok", "yes", "no", "haan", "theek hai"
])
def test_ship1_conditional_acknowledgements_after_estimate_skip_retrieval(client, ack_text):
    """ok/yes/no after estimate when nothing is pending skip embedding/retrieval."""
    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import SessionRow
    import json

    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    # Mark session as having completed estimate with brief ready
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        s_row.stage = "advising"
        s_row.estimate_json = json.dumps({"range_label": "$30k - $50k", "timeline_weeks": 8})
        s_row.brief_json = json.dumps({
            "service": "web_app", "goal": "clinic app", "platforms": ["web"],
            "timeline": "1_3_months", "budget_band": "40_80k", "decision_role": "founder_or_exec",
            "company_size": "startup"
        })
        db.commit()

    with patch("backend.app.agents.router.search") as mock_search, \
         patch("backend.app.rag.store.embed_query") as mock_embed:
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": ack_text},
        )
        assert res.status_code == 200
        mock_search.assert_not_called()
        mock_embed.assert_not_called()
        data = res.json()
        assert data["route"] in ("fallback", "discovery")
        assert len(data["message"]) > 0


def test_ship1_real_questions_use_retrieval(client):
    """Real questions must execute retrieval search."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    search_spy = MagicMock()
    with patch("backend.app.agents.router.search", wraps=search_spy) as mock_search:
        # Give mock search a valid return
        search_spy.return_value = []
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "What tech stack do you recommend for real-time video streaming?"},
        )
        assert res.status_code == 200
        assert mock_search.call_count >= 1


def test_ship1_server_timing_header_and_logging(client, caplog):
    """Server-Timing header must be present and turn timings logged at INFO without user text."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    secret_user_text = "SECRET_USER_QUERY_XYZ_12345"
    with caplog.at_level(logging.INFO):
        res = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": secret_user_text},
        )
    assert res.status_code == 200
    assert "Server-Timing" in res.headers
    server_timing = res.headers["Server-Timing"]
    assert "total;dur=" in server_timing

    # Verify log output has stage durations and no user text
    found_timing_log = False
    for record in caplog.records:
        if "Turn timing:" in record.message:
            found_timing_log = True
            assert secret_user_text not in record.message
            assert "extractor=" in record.message
            assert "retrieval_db=" in record.message
            assert "total=" in record.message
            break
    assert found_timing_log, "Expected timing INFO log line"


def test_ship1_sample_labeling(client):
    """Portfolio/case-study citations must say 'sample' and cards must be tagged is_sample."""
    session = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = session["session_id"]

    # In demo tenant, Zephyr case study citation must say 'sample'
    res = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "The Zephyr clinic companion cut no-shows by 18 percent during the pilot."},
    )
    assert res.status_code == 200
    data = res.json()
    assert "sample" in data["message"].lower()

    # Portfolio chip click returns portfolio cards marked is_sample
    res_port = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"chip": {"field": "show_portfolio", "value": "portfolio", "label": "See similar work"}},
    )
    assert res_port.status_code == 200
    data_port = res_port.json()
    cards = data_port.get("cards", [])
    port_card = next((c for c in cards if c["type"] == "portfolio"), None)
    assert port_card is not None
    assert port_card.get("is_sample") is True
    assert "sample" in data_port["message"].lower()


def test_ship1_price_guard_replacements():
    """sanitize_price_leaks replaces WHOLE sentence containing unauthorized figure."""
    exact_replacement = "Exact pricing depends on scope; the indicative range above is the only figure I can confirm."

    # 1. Hosting fee is $500
    s1 = "Our standard cloud hosting fee is $500 per month. We also provide maintenance."
    r1 = sanitize_price_leaks(s1)
    assert exact_replacement in r1
    assert "$500" not in r1
    assert "We also provide maintenance." in r1

    # 2. Was $20k now $15k
    s2 = "Our initial pilot was $20k now $15k for new customers. Contact us to learn more."
    r2 = sanitize_price_leaks(s2)
    assert exact_replacement in r2
    assert "$20k" not in r2
    assert "$15k" not in r2
    assert "Contact us to learn more." in r2

    # 3. about 5 lakh rupees
    s3 = "Development costs about 5 lakh rupees for the prototype. Delivery takes 6 weeks."
    r3 = sanitize_price_leaks(s3)
    assert exact_replacement in r3
    assert "5 lakh" not in r3
    assert "Delivery takes 6 weeks." in r3

    # Visitor budget passthrough
    budget_s = "Understood that your budget is $30k - $50k. We will tailor the MVP accordingly."
    r_budget = sanitize_price_leaks(budget_s, visitor_budget="30_50k")
    assert "$30k - $50k" in r_budget

    # Engine range passthrough
    est_ctx = {"range_label": "$40,000 - $60,000"}
    est_s = "Our indicative estimate is $40,000 - $60,000 based on the current scope."
    r_est = sanitize_price_leaks(est_s, estimate=est_ctx)
    assert "$40,000 - $60,000" in r_est
