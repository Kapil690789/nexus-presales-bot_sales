import json
import uuid

import httpx
from sqlalchemy import select

from backend.app.core.settings import get_settings
from backend.app.models.db import SessionLocal
from backend.app.models.entities import EventRow
from backend.app.stubs.notify import booking_slack_text, notify_booking

BOOKING = {
    "window": "this_week",
    "slot_iso": "2026-09-21T11:00:00+00:00",
    "label": "Thu 11:00 UTC",
    "meet_url": "https://meet.google.com/abc-defg-hij",
    "html_link": "https://calendar.google.com/event?eid=abc",
    "event_id": "evt-1",
    "status": "created",
    "email": "founder@acme.test",
    "company": "Acme Ops",
}


def _events(session_id: str) -> list[tuple[str, dict]]:
    with SessionLocal() as db:
        rows = db.scalars(select(EventRow).where(EventRow.session_id == session_id).order_by(EventRow.created_at.asc())).all()
        return [(row.kind, json.loads(row.payload_json)) for row in rows]


def test_booking_slack_text_includes_admin_link(monkeypatch) -> None:
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com")
    get_settings.cache_clear()
    text = booking_slack_text(BOOKING, "sess-9")
    assert "New consultation booked" in text
    assert "When: Thu 11:00 UTC" in text
    assert "Email: founder@acme.test" in text
    assert "Company: Acme Ops" in text
    assert "Meet: https://meet.google.com/abc-defg-hij" in text
    assert "Calendar: https://calendar.google.com/event?eid=abc" in text
    assert "Session: https://bot.example.com/admin/sessions/sess-9" in text


def test_notify_booking_stubs_slack_without_webhook(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "")
    monkeypatch.setenv("PUBLIC_BASE_URL", "")
    get_settings.cache_clear()
    posted: list = []
    monkeypatch.setattr("backend.app.stubs.notify.httpx.post", lambda *a, **k: posted.append((a, k)))
    session_id = str(uuid.uuid4())
    with SessionLocal() as db:
        notify_booking(db, session_id, BOOKING)
        db.commit()
    assert posted == []
    events = _events(session_id)
    assert [kind for kind, _ in events] == ["calendar", "slack"]
    assert events[1][1]["status"] == "queued_stub"
    assert "founder@acme.test" in events[1][1]["text"]


def test_notify_booking_posts_webhook_once(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/XXX")
    monkeypatch.setenv("PUBLIC_BASE_URL", "https://bot.example.com")
    get_settings.cache_clear()
    posted: list[dict] = []

    class Resp:
        def raise_for_status(self) -> None:
            return None

    def fake_post(url, json=None, timeout=None):
        posted.append({"url": url, "json": json, "timeout": timeout})
        return Resp()

    monkeypatch.setattr("backend.app.stubs.notify.httpx.post", fake_post)
    session_id = str(uuid.uuid4())
    with SessionLocal() as db:
        notify_booking(db, session_id, BOOKING)
        notify_booking(db, session_id, BOOKING)
        db.commit()
    assert len(posted) == 1
    assert posted[0]["url"] == "https://hooks.slack.com/services/T/B/XXX"
    text = posted[0]["json"]["text"]
    assert "New consultation booked" in text
    assert "founder@acme.test" in text
    assert "Acme Ops" in text
    assert f"https://bot.example.com/admin/sessions/{session_id}" in text
    events = _events(session_id)
    assert [kind for kind, _ in events] == ["calendar", "slack"]
    assert events[1][1]["status"] == "sent"


def test_notify_booking_slack_failure_does_not_raise(monkeypatch) -> None:
    monkeypatch.setenv("SLACK_WEBHOOK_URL", "https://hooks.slack.com/services/T/B/XXX")
    get_settings.cache_clear()

    def boom(*_args, **_kwargs):
        raise httpx.ConnectError("offline")

    monkeypatch.setattr("backend.app.stubs.notify.httpx.post", boom)
    session_id = str(uuid.uuid4())
    with SessionLocal() as db:
        notify_booking(db, session_id, BOOKING)
        db.commit()
    events = _events(session_id)
    assert events[0][0] == "calendar"
    assert events[1][1]["status"] == "failed"
