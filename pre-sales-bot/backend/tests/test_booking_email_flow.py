import json
from backend.app.models.db import SessionLocal
from backend.app.models.entities import LeadRow, SessionRow


def test_booking_email_capture_and_inquiries(client):
    """Test full booking lifecycle:
    1. Select slot -> bot prompts for work email
    2. Provide email -> bot confirms invitation dispatch and records lead
    3. Ask post-booking questions (agenda, colleague, reschedule) -> answered accurately
    """
    # 1. Create session
    resp = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert resp.status_code == 200
    session_id = resp.json()["session_id"]

    # 2. Book a slot via chip
    slot_iso = "2026-10-05T15:00:00Z"
    r_book = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "", "chip": {"field": "booking_slot", "value": slot_iso, "label": "Mon Oct 05, 15:00 UTC"}},
    )
    assert r_book.status_code == 200
    data_book = r_book.json()
    assert "Reply with your work email" in data_book["message"]

    # 3. User responds with email and natural language: "kapil19092003@gmail.com here is my mail"
    r_email = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "kapil19092003@gmail.com here is my mail"},
    )
    assert r_email.status_code == 200
    data_email = r_email.json()
    msg = data_email["message"]

    # Assert invitation dispatch confirmation
    assert "kapil19092003@gmail.com" in msg
    assert "invitation" in msg.lower() or "dispatched" in msg.lower()
    assert data_email["stage"] == "handoff"
    assert data_email["route"] == "booking"
    assert "BrowserStack" not in msg

    # Verify DB lead record was created/updated
    with SessionLocal() as db:
        lead = db.query(LeadRow).filter(LeadRow.session_id == session_id).first()
        assert lead is not None
        assert lead.email == "kapil19092003@gmail.com"

        session_row = db.get(SessionRow, session_id)
        assert session_row.booking_json
        booked = json.loads(session_row.booking_json)
        assert booked.get("attendee") == "kapil19092003@gmail.com"

    # 4. User asks post-booking question: "What is on the agenda?"
    r_agenda = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "What is on the agenda?"},
    )
    assert r_agenda.status_code == 200
    agenda_msg = r_agenda.json()["message"]
    assert "agenda" in agenda_msg.lower() or "discovery" in agenda_msg.lower()
    assert "BrowserStack" not in agenda_msg

    # 5. User asks: "Can I invite a colleague?"
    r_colleague = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Can I invite a colleague?"},
    )
    assert r_colleague.status_code == 200
    colleague_msg = r_colleague.json()["message"]
    assert "colleague" in colleague_msg.lower() or "team members" in colleague_msg.lower() or "forward" in colleague_msg.lower()

    # 6. User asks: "Can I reschedule the time?"
    r_resched = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Can I reschedule the time?"},
    )
    assert r_resched.status_code == 200
    resched_data = r_resched.json()
    assert resched_data["stage"] == "booking"
    assert any(c.get("field") == "booking_slot" for c in resched_data.get("chips", []))
