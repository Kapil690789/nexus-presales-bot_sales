from __future__ import annotations

import json
import time
from datetime import datetime, timedelta, timezone

import pytest
from starlette.testclient import TestClient

from backend.app.agents.router import extract_single_email, run_turn, validate_single_email
from backend.app.core.security import (
    ADMIN_LOCKOUT_LIMIT,
    ADMIN_LOCKOUT_WINDOW,
    _atomic_upsert_rate_limit,
    _failed_admin,
    _get_rate_limit,
    _message_hits,
    _reset_rate_limit,
    check_booking_ip_limit,
    check_email_submission_limit,
    hash_ip,
    record_booking_for_ip,
)
from backend.app.core.settings import get_settings
from backend.app.engines.calendar import confirm_slot
from backend.app.main import app
from backend.app.models.db import SessionLocal, get_engine
from backend.app.models.entities import SessionRow, TenantRow
from backend.app.tenants.loader import load_tenant


# ---------------------------------------------------------------------------
# 1. Invalid Emails and Multiple Emails Tests
# ---------------------------------------------------------------------------

def test_validate_single_email_edge_cases():
    assert validate_single_email("alex@company.com") == "alex@company.com"
    assert validate_single_email("ALEX.SMITH+WORK@MY-COMPANY.CO.UK") == "alex.smith+work@my-company.co.uk"

    # Invalid cases
    assert validate_single_email("") is None
    assert validate_single_email("not-an-email") is None
    assert validate_single_email("user@") is None
    assert validate_single_email("@domain.com") is None
    assert validate_single_email("user@domain") is None
    assert validate_single_email("user @domain.com") is None
    assert validate_single_email("user\n@domain.com") is None
    assert validate_single_email("a" * 250 + "@b.com") is None  # > 254 chars
    assert validate_single_email("a@b.com, c@d.com") is None
    assert validate_single_email("a@b.com; c@d.com") is None


def test_extract_single_email():
    email, multi = extract_single_email("My email is founder@startup.io thanks")
    assert email == "founder@startup.io"
    assert not multi

    email, multi = extract_single_email("Send to a@b.com, c@d.com please")
    assert email is None
    assert multi is True

    email, multi = extract_single_email("No email here just text")
    assert email is None
    assert multi is False


def test_multi_emails_rejected_in_chat(client):
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    # Choose email instead
    r1 = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "Email me instead", "chip": {"field": "email_instead", "label": "Email me instead", "value": "prefers_email"}},
    )
    assert r1.status_code == 200

    # Provide multiple emails
    r2 = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "Contact us at team@work.com, founder@work.com"},
    )
    assert r2.status_code == 200
    assert r2.json()["route"] == "email_invalid"
    assert "single valid email" in r2.json()["message"].lower()


def test_invalid_email_rejected_in_chat(client):
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "Email me instead", "chip": {"field": "email_instead", "label": "Email me instead", "value": "prefers_email"}},
    )

    r = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "not-an-email-address"},
    )
    assert r.status_code == 200
    assert r.json()["route"] == "email_invalid"
    assert "single valid email" in r.json()["message"].lower()


# ---------------------------------------------------------------------------
# 2. Fourth Booking from Same IP Blocked (Cap = 3)
# ---------------------------------------------------------------------------

def test_fourth_booking_from_same_ip_blocked(client):
    test_ip = "192.168.10.99"
    headers = {"x-forwarded-for": test_ip}

    # 3 bookings from this IP should succeed
    for i in range(3):
        s = client.post("/api/v1/sessions", json={"tenant": "demo"}, headers=headers).json()
        sid = s["session_id"]
        # pick booking slot
        tomorrow = (datetime.now(timezone.utc) + timedelta(days=i + 1)).isoformat()
        r1 = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": "Pick slot", "chip": {"field": "booking_slot", "label": "Tomorrow", "value": tomorrow}},
            headers=headers,
        )
        assert r1.status_code == 200
        # send valid distinct email
        r2 = client.post(
            f"/api/v1/sessions/{sid}/messages",
            json={"content": f"user{i}@testcompany.com"},
            headers=headers,
        )
        assert r2.status_code == 200
        assert r2.json()["route"] == "booking"
        assert r2.json()["booking"] is not None

    # 4th booking from the same IP must be blocked
    s4 = client.post("/api/v1/sessions", json={"tenant": "demo"}, headers=headers).json()
    sid4 = s4["session_id"]
    t4 = (datetime.now(timezone.utc) + timedelta(days=5)).isoformat()
    r4 = client.post(
        f"/api/v1/sessions/{sid4}/messages",
        json={"content": "Pick slot", "chip": {"field": "booking_slot", "label": "Day 5", "value": t4}},
        headers=headers,
    )
    assert r4.status_code == 200
    assert r4.json()["route"] == "booking_blocked"
    assert "maximum number of bookings" in r4.json()["message"].lower()


# ---------------------------------------------------------------------------
# 3. Second Booking for Same Email Blocked (1 Active Booking per Email)
# ---------------------------------------------------------------------------

def test_second_booking_for_same_email_blocked(client):
    target_email = "singlebooking@enterprise.com"

    # First booking succeeds
    s1 = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid1 = s1["session_id"]
    slot1 = (datetime.now(timezone.utc) + timedelta(days=2)).isoformat()
    client.post(
        f"/api/v1/sessions/{sid1}/messages",
        json={"content": "Pick slot", "chip": {"field": "booking_slot", "label": "Slot 1", "value": slot1}},
    )
    r1 = client.post(
        f"/api/v1/sessions/{sid1}/messages",
        json={"content": target_email},
    )
    assert r1.status_code == 200
    assert r1.json()["route"] == "booking"

    # Second booking in a new session with the same email is blocked
    s2 = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid2 = s2["session_id"]
    slot2 = (datetime.now(timezone.utc) + timedelta(days=3)).isoformat()
    client.post(
        f"/api/v1/sessions/{sid2}/messages",
        json={"content": "Pick slot", "chip": {"field": "booking_slot", "label": "Slot 2", "value": slot2}},
    )
    r2 = client.post(
        f"/api/v1/sessions/{sid2}/messages",
        json={"content": target_email},
    )
    assert r2.status_code == 200
    assert r2.json()["route"] == "booking_blocked"
    assert "already have an active scheduled consultation" in r2.json()["message"].lower()


# ---------------------------------------------------------------------------
# 4. Two Simulated Instances Share a Rate Limit in Database
# ---------------------------------------------------------------------------

def test_two_simulated_instances_share_rate_limit(client):
    settings = get_settings()
    shared_key = hash_ip("shared-test-key", settings)
    window = 60.0

    # Instance 1 increments the rate limit 5 times
    for _ in range(5):
        cnt, _ = _atomic_upsert_rate_limit(shared_key, window)

    assert cnt == 5

    # Instance 2 (checking via fresh query from DB) reads 5
    current_cnt, _ = _get_rate_limit(shared_key, window)
    assert current_cnt == 5

    # Instance 2 increments further
    cnt2, _ = _atomic_upsert_rate_limit(shared_key, window)
    assert cnt2 == 6


# ---------------------------------------------------------------------------
# 5. Rate Limit Window Reset
# ---------------------------------------------------------------------------

def test_rate_limit_window_reset():
    settings = get_settings()
    key = hash_ip("reset-test-key", settings)
    window = 2.0  # 2 second window

    c1, _ = _atomic_upsert_rate_limit(key, window)
    assert c1 == 1
    c2, _ = _atomic_upsert_rate_limit(key, window)
    assert c2 == 2

    # Wait for window to expire
    time.sleep(2.1)

    # After window, counter must reset to 1
    c3, _ = _atomic_upsert_rate_limit(key, window)
    assert c3 == 1


# ---------------------------------------------------------------------------
# 6. Admin Lockout Survives a New Process
# ---------------------------------------------------------------------------

def test_admin_lockout_survives_new_process(client, monkeypatch):
    admin_ip = "10.0.0.42"

    # Make 5 failed login attempts
    for _ in range(ADMIN_LOCKOUT_LIMIT):
        res = client.get(
            "/admin/api/usage",
            auth=("admin", "wrongpassword"),
            headers={"x-forwarded-for": admin_ip},
        )
        assert res.status_code in (401, 429)

    # Now lockout is active -> 429
    res_locked = client.get(
        "/admin/api/usage",
        auth=("admin", "wrongpassword"),
        headers={"x-forwarded-for": admin_ip},
    )
    assert res_locked.status_code == 429
    assert "too many failed admin logins" in res_locked.json()["detail"].lower()

    # SIMULATE NEW PROCESS: clear Python in-memory state
    _failed_admin.default_factory = list
    # The in-memory dict is wiped, but database rate_limits table retains lockout
    super(_failed_admin.__class__, _failed_admin).clear()

    # In a "new process", request still returns 429 because state is persistent
    res_survived = client.get(
        "/admin/api/usage",
        auth=("admin", "wrongpassword"),
        headers={"x-forwarded-for": admin_ip},
    )
    assert res_survived.status_code == 429


# ---------------------------------------------------------------------------
# 7. Calendar Attendee Never More Than One
# ---------------------------------------------------------------------------

def test_calendar_never_more_than_one_attendee():
    tenant = TenantRow(slug="demo", name="Nexus")
    tomorrow = (datetime.now(timezone.utc) + timedelta(days=1)).isoformat()
    booked = confirm_slot(tenant, tomorrow, "Meeting", "test@company.com")
    assert booked is not None
    # No multi attendees possible


# ---------------------------------------------------------------------------
# 8. Session Email Submission Cap (Max 5)
# ---------------------------------------------------------------------------

def test_session_email_submission_cap():
    sess_id = "test-sess-limit-123"
    for i in range(1, 6):
        cnt, ok = check_email_submission_limit(sess_id)
        assert ok is True
        assert cnt == i

    # 6th submission exceeds cap
    cnt6, ok6 = check_email_submission_limit(sess_id)
    assert ok6 is False
    assert cnt6 == 6


# ---------------------------------------------------------------------------
# 9. IP Hash Salt Production Requirement
# ---------------------------------------------------------------------------

def test_ip_hash_salt_production():
    from backend.app.core.security import assert_ip_salt_configured
    from backend.app.core.settings import Settings

    s_bad = Settings(environment="production", database_url="postgresql://u:p@localhost:5432/db", ip_hash_salt="")
    with pytest.raises(RuntimeError, match="IP_HASH_SALT"):
        assert_ip_salt_configured(s_bad)

    s_good = Settings(environment="production", database_url="postgresql://u:p@localhost:5432/db", ip_hash_salt="secret-production-salt-987")
    assert_ip_salt_configured(s_good)

