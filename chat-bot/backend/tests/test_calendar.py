from datetime import datetime, timedelta, timezone

import pytest

from backend.app.engines.calendar import confirm_slot, slots_for
from backend.app.engines.google_client import CalendarError, set_google_client
from backend.app.models.db import SessionLocal
from backend.app.models.entities import CalendarCredentialRow
from backend.app.engines.google_client import credential_row


NOW = datetime(2026, 9, 21, 3, 0, tzinfo=timezone.utc)


class FakeGoogle:
    def __init__(self, busy=None):
        self.busy = list(busy or [])
        self.created = []

    def list_busy(self, calendar_id, time_min, time_max):
        return list(self.busy)

    def create_event(self, calendar_id, start, end, summary, description, email, timezone_name):
        self.created.append(
            {
                "calendar_id": calendar_id,
                "start": start,
                "end": end,
                "summary": summary,
                "email": email,
                "timezone_name": timezone_name,
            }
        )
        return {
            "event_id": "evt-1",
            "meet_url": "https://meet.google.com/abc-defg-hij",
            "html_link": "https://calendar.google.com/event?eid=1",
        }


@pytest.fixture(autouse=True)
def _reset_google():
    set_google_client(None)
    yield
    set_google_client(None)


def test_availability_endpoint_shape(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    body = client.get(f"/api/v1/sessions/{session_id}/availability", params={"window": "this_week"}).json()
    assert body["window"] == "this_week"
    assert body["duration_minutes"] == 45
    assert body["live"] is False
    assert len(body["slots"]) == 3
    assert body["days"]


def test_booking_requires_explicit_slot(client) -> None:
    from backend.tests.test_api import _discover, accept_nda

    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    assert accept_nda(client, session_id).status_code == 200
    blocked = client.post(f"/api/v1/sessions/{session_id}/booking", json={"window": "this_week"})
    assert blocked.status_code == 400
    assert "time" in blocked.json()["detail"].lower()


def test_empty_this_week_falls_through_to_next_week(monkeypatch) -> None:
    from backend.app.engines import calendar as cal

    real = cal.slots_for

    def fake(window="this_week", *, now=None, db=None):
        if window == "this_week":
            return []
        return real(window, now=now, db=db)

    monkeypatch.setattr(cal, "slots_for", fake)
    payload = cal.availability_payload("this_week")
    assert payload["window"] == "next_week"
    assert payload["slots"]
    assert payload["days"]
    card = cal.booking_card("this_week")
    assert card["window"] == "next_week"
    assert card["slots"]
    fake = FakeGoogle()
    set_google_client(fake)
    slots = slots_for("this_week", now=NOW)
    assert slots
    taken = datetime.fromisoformat(slots[0]["slot_iso"])
    fake.busy = [(taken, taken + timedelta(minutes=45))]
    remaining = slots_for("this_week", now=NOW)
    assert all(item["slot_iso"] != slots[0]["slot_iso"] for item in remaining)


def test_confirm_refuses_a_taken_slot() -> None:
    fake = FakeGoogle()
    set_google_client(fake)
    slots = slots_for("this_week", now=NOW)
    taken = datetime.fromisoformat(slots[0]["slot_iso"])
    fake.busy = [(taken, taken + timedelta(minutes=45))]
    with pytest.raises(CalendarError):
        confirm_slot("session-1", "this_week", slots[0]["slot_iso"], email="founder@acme.test", now=NOW)
    assert not fake.created


def test_confirm_creates_google_event() -> None:
    fake = FakeGoogle()
    set_google_client(fake)
    slots = slots_for("this_week", now=NOW)
    booked = confirm_slot("session-1", "this_week", slots[0]["slot_iso"], email="founder@acme.test", now=NOW)
    assert booked["status"] == "created"
    assert booked["meet_url"] == "https://meet.google.com/abc-defg-hij"
    assert booked["event_id"] == "evt-1"
    assert fake.created[0]["email"] == "founder@acme.test"


def test_oauth_callback_stores_refresh_token(client, monkeypatch) -> None:
    with SessionLocal() as db:
        row = credential_row(db)
        row.oauth_state = "xyz"
        db.commit()

    try:
        monkeypatch.setattr(
            "backend.app.engines.google_client.exchange_code",
            lambda code, code_verifier="": {
                "refresh_token": "rt-1",
                "access_token": "at-1",
                "email": "owner@example.com",
                "expiry": None,
                "scopes": "calendar",
                "token_uri": "https://oauth2.googleapis.com/token",
            },
        )
        response = client.get(
            "/admin/google/callback?code=abc&state=xyz",
            auth=("admin", "test-admin"),
            follow_redirects=False,
        )
        assert response.status_code == 303
        assert "connected=1" in response.headers["location"]
        with SessionLocal() as db:
            row = db.get(CalendarCredentialRow, "default")
            assert row is not None
            assert row.refresh_token == "rt-1"
            assert row.email == "owner@example.com"
    finally:
        with SessionLocal() as db:
            row = db.get(CalendarCredentialRow, "default")
            if row:
                db.delete(row)
                db.commit()


def test_oauth_callback_does_not_need_admin_auth(client, monkeypatch) -> None:
    with SessionLocal() as db:
        row = credential_row(db)
        row.oauth_state = "xyz"
        db.commit()
    monkeypatch.setattr(
        "backend.app.engines.google_client.exchange_code",
        lambda code, code_verifier="": {
            "refresh_token": "rt-2",
            "access_token": "at-2",
            "email": "owner@example.com",
            "expiry": None,
            "scopes": "calendar",
            "token_uri": "https://oauth2.googleapis.com/token",
        },
    )
    response = client.get("/admin/google/callback?code=abc&state=xyz", follow_redirects=False)
    assert response.status_code == 303
    assert "connected=1" in response.headers["location"]


def test_complete_oauth_passes_pkce_verifier(monkeypatch) -> None:
    from backend.app.engines.google_client import complete_oauth

    seen: dict[str, str] = {}

    def fake_exchange(code: str, code_verifier: str = "") -> dict:
        seen["code"] = code
        seen["verifier"] = code_verifier
        return {
            "refresh_token": "rt-1",
            "access_token": "at-1",
            "email": "owner@example.com",
            "expiry": None,
            "scopes": "calendar",
            "token_uri": "https://oauth2.googleapis.com/token",
        }

    monkeypatch.setattr("backend.app.engines.google_client.exchange_code", fake_exchange)
    with SessionLocal() as db:
        row = credential_row(db)
        row.oauth_state = "xyz"
        row.oauth_code_verifier = "pkce-secret"
        db.commit()
        complete_oauth(db, "abc", "xyz")
        db.commit()
        row = db.get(CalendarCredentialRow, "default")
        assert seen["code"] == "abc"
        assert seen["verifier"] == "pkce-secret"
        assert row is not None
        assert row.oauth_code_verifier == ""
        assert row.refresh_token == "rt-1"


def test_authorization_url_stores_pkce_verifier(monkeypatch) -> None:
    from backend.app.engines import google_client

    class FakeFlow:
        code_verifier = "verifier-from-google-flow"

        def authorization_url(self, **kwargs):
            return "https://accounts.google.com/o/oauth2/auth?x=1", "state-pkce"

    monkeypatch.setattr(google_client, "_flow", lambda code_verifier=None: FakeFlow())
    monkeypatch.setattr(google_client, "google_configured", lambda: True)
    with SessionLocal() as db:
        url = google_client.authorization_url(db)
        db.commit()
        row = db.get(CalendarCredentialRow, "default")
        assert "accounts.google.com" in url
        assert row is not None
        assert row.oauth_state == "state-pkce"
        assert row.oauth_code_verifier == "verifier-from-google-flow"
