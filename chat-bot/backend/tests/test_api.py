from pathlib import Path

from backend.app.config_loader.loader import load_config


def test_health(client) -> None:
    assert client.get("/health").json()["ok"] is True


def test_root_serves_standalone_chat(client) -> None:
    response = client.get("/", follow_redirects=False)
    assert response.status_code == 200
    assert "consultant.js" in response.text
    assert "/demo/" not in (response.headers.get("location") or "")


def test_public_config_hides_pricing(client) -> None:
    body = client.get("/api/v1/public-config").json()
    assert body["brand"]["logo_text"]
    assert body["nda"]["label"]
    assert body["nda"]["body"]
    assert "low_side_factor" not in str(body)


def test_session_is_page_aware(client) -> None:
    mobile = client.post("/api/v1/sessions", json={"path": "/demo/mobile-app-development.html", "page_title": "Mobile"}).json()
    web = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html", "page_title": "Web"}).json()
    assert "mobile" in mobile["message"].lower()
    assert "web" in web["message"].lower()
    assert mobile["message"] != web["message"]
    site_web = client.post("/api/v1/sessions", json={"path": "/web-app-development.html", "page_title": "Web"}).json()
    site_pricing = client.post("/api/v1/sessions", json={"path": "/pricing.html", "page_title": "Pricing"}).json()
    assert "web" in site_web["message"].lower()
    assert site_web["message"] != site_pricing["message"]


def _chip(label: str, field: str, value) -> dict:
    return {"label": label, "field": field, "value": value}


def _discover(client, session_id: str) -> None:
    steps = [
        ("Ops console for distributors to track orders and inventory alerts", None),
        ("Web", _chip("Web", "platforms", ["web"])),
        ("Internal team", _chip("Internal team", "users", "internal")),
        ("None yet", _chip("None yet", "integrations", ["none"])),
        ("1-3 months", _chip("1–3 months", "timeline", "1_3_months")),
        ("$40-80k", _chip("$40–80k", "budget_band", "40_80k")),
        ("I'm the founder", _chip("Founder / exec", "decision_role", "founder_or_exec")),
    ]
    for content, chip in steps:
        response = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content, "chip": chip})
        assert response.status_code == 200, response.text


def test_discovery_to_estimate_flow(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    body = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Show relevant work", "chip": _chip("Show relevant work", "show_portfolio", "yes")},
    )
    assert body.status_code == 200
    assert "$" in body.text or "event: cards" in body.text


def test_stage_progression_mvp_portfolio_contact(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    mvp = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Show MVP cut", "chip": _chip("Show MVP cut", "show_mvp", "yes")},
    )
    assert mvp.status_code == 200
    assert "mvp" in mvp.text.lower() or "event: cards" in mvp.text
    portfolio = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Show relevant work", "chip": _chip("Show relevant work", "show_portfolio", "yes")},
    )
    assert portfolio.status_code == 200
    contact = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Continue to contact", "chip": _chip("Continue to contact", "continue_contact", "yes")},
    )
    assert contact.status_code == 200
    email = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"})
    assert email.status_code == 200
    assert "event: meta" in email.text


def test_nda_required_before_booking(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    blocked = client.post(f"/api/v1/sessions/{session_id}/booking", json={"window": "next_week"})
    assert blocked.status_code == 400


def test_nda_then_booking_and_events(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    nda = client.post(f"/api/v1/sessions/{session_id}/nda")
    assert nda.status_code == 200
    assert nda.json()["nda_accepted"] is True
    booked = client.post(f"/api/v1/sessions/{session_id}/booking", json={"window": "this_week"})
    assert booked.status_code == 200
    body = booked.json()
    assert body["nda_accepted"] is True
    assert body["stage"] in {"handoff", "booking", "capture"}
    assert body.get("handoff_summary") or body["stage"] == "handoff" or "brief" in body["message"].lower() or "team" in body["message"].lower()
    booking = body.get("booking") or {}
    assert booking.get("slot_iso")
    assert str(booking.get("meet_url") or "").startswith("https://meet.devconsult.example/")
    ics = client.get(f"/api/v1/sessions/{session_id}/calendar.ics")
    assert ics.status_code == 200
    assert "BEGIN:VEVENT" in ics.text
    from sqlalchemy import select

    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import EventRow, LeadRow

    with SessionLocal() as db:
        lead = db.scalar(select(LeadRow).where(LeadRow.session_id == session_id))
        assert lead is not None
        assert lead.company == "Acme Ops"
        assert lead.crm_id.startswith("lead_devconsult_")
        kinds = set(db.scalars(select(EventRow.kind).where(EventRow.session_id == session_id)))
    assert {"crm", "calendar", "slack", "email", "visitor_follow_up"} <= kinds


def test_nda_then_document_upload(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    sample = Path("fixtures/sample-rfp.txt")
    assert sample.exists()
    denied = client.post(
        f"/api/v1/sessions/{session_id}/documents",
        files={"file": ("sample-rfp.txt", sample.read_bytes(), "text/plain")},
    )
    assert denied.status_code == 400
    assert client.post(f"/api/v1/sessions/{session_id}/nda").status_code == 200
    uploaded = client.post(
        f"/api/v1/sessions/{session_id}/documents",
        files={"file": ("sample-rfp.txt", sample.read_bytes(), "text/plain")},
        data={"nda_accepted": "true"},
    )
    assert uploaded.status_code == 200
    assert "event:" in uploaded.text


def test_admin_requires_password(client) -> None:
    assert client.get("/api/v1/admin/leads").status_code == 401
    assert client.get("/api/v1/admin/leads", auth=("admin", "test-admin")).status_code == 200


def test_disclaimer_comes_from_config() -> None:
    assert "indicative" in load_config().agency.disclaimer.lower()
