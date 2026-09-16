import json

from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.app.documents.rfp import extract_rfp
from backend.app.engines.calendar import confirm_slot, ics_for, slots_for
from backend.app.engines.enrichment import crm_id_for, enrich_email
from backend.app.engines.followup import render_followup
from backend.tests.test_api import _chip, _discover


def test_enrichment_directory_vs_inferred() -> None:
    config = load_config()
    known = enrich_email("founder@acme.test", config.enrichment)
    assert known["source"] == "directory"
    assert known["company"] == "Acme Ops"
    assert known["size"] == "smb"
    unknown = enrich_email("hello@unknown-xyz.test", config.enrichment)
    assert unknown["source"] == "inferred"
    assert unknown["company"] == "unknown-xyz.test"
    assert unknown["size"] == "unknown"
    assert crm_id_for("abc-123").startswith("lead_devconsult_")


def test_dummy_calendar_slots_and_ics() -> None:
    slots = slots_for("this_week")
    assert len(slots) == 3
    booked = confirm_slot("session-1", "this_week")
    assert booked["slot_iso"] == slots[0]["slot_iso"]
    assert booked["meet_url"].startswith("https://meet.devconsult.example/")
    calendar = ics_for(booked)
    assert "BEGIN:VCALENDAR" in calendar
    assert booked["meet_url"] in calendar


def test_followup_pack_includes_estimate_and_meeting() -> None:
    pack = render_followup(
        email="founder@acme.test",
        intro="Thank you for walking through the product.",
        estimate={"range_label": "$40–80k"},
        portfolio=[{"title": "Ops console", "outcome": "Cut dispatch time"}],
        booking={"label": "Thu 11:00 UTC", "meet_url": "https://meet.devconsult.example/abc"},
        agency="DevConsult",
    )
    assert "founder@acme.test" in pack["preview"]
    assert "$40–80k" in pack["body"]
    assert "Ops console" in pack["body"]
    assert "Thu 11:00 UTC" in pack["body"]
    assert "dummy email" in pack["body"]


def test_rfp_keyword_extract() -> None:
    brief = extract_rfp(
        ProjectBrief(service="web_app"),
        "Goal: Track orders in one place.\nMust-have HIPAA controls.\nSalesforce and Stripe on day one.",
    )
    assert brief.goal
    assert "salesforce" in brief.integrations
    assert "stripe" in brief.integrations
    assert any("hipaa" in item.lower() or "must-have" in item.lower() for item in brief.constraints)


def test_company_size_chip_does_not_block_estimate(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    body = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Show relevant work", "chip": _chip("Show relevant work", "show_portfolio", "yes")},
    )
    assert body.status_code == 200
    assert "$" in body.text or "event: cards" in body.text


def test_company_size_asked_after_role(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    steps = [
        ("Ops console for distributors to track orders and inventory alerts", None),
        ("Web", _chip("Web", "platforms", ["web"])),
        ("Internal team", _chip("Internal team", "users", "internal")),
        ("None yet", _chip("None yet", "integrations", ["none"])),
        ("1-3 months", _chip("1–3 months", "timeline", "1_3_months")),
        ("$40-80k", _chip("$40–80k", "budget_band", "40_80k")),
    ]
    for content, chip in steps:
        assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content, "chip": chip}).status_code == 200
    role = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "I'm the founder", "chip": _chip("Founder / exec", "decision_role", "founder_or_exec")},
    )
    assert role.status_code == 200
    assert "company_size" in role.text


def test_session_resume_returns_thread(client) -> None:
    created = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()
    resumed = client.get(f"/api/v1/sessions/{created['session_id']}")
    assert resumed.status_code == 200
    body = resumed.json()
    assert body["session_id"] == created["session_id"]
    assert body["messages"]
    assert body["messages"][0]["role"] == "assistant"


def test_unknown_domain_inferred_on_lead(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "hello@unknown-xyz.test"}).status_code == 200
    from sqlalchemy import select

    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import LeadRow

    with SessionLocal() as db:
        lead = db.scalar(select(LeadRow).where(LeadRow.session_id == session_id))
        assert lead is not None
        profile = json.loads(lead.enrichment_json)
    assert profile["source"] == "inferred"
    assert lead.company == "unknown-xyz.test"
