from __future__ import annotations

import json
from pathlib import Path
from unittest.mock import patch

import pytest
from sqlalchemy import create_engine
from sqlalchemy.orm import Session, sessionmaker

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.fallback import fallback_recovery, fallback_recovery_message
from backend.app.agents.router import (
    budget_fit_line,
    recap_line_from_brief,
    run_turn,
)
from backend.app.core.platform import get_platform
from backend.app.models.entities import Base, SessionRow, TenantRow
from backend.app.tenants.loader import load_tenant


@pytest.fixture
def db():
    engine = create_engine("sqlite:///:memory:")
    Base.metadata.create_all(engine)
    session_factory = sessionmaker(bind=engine)
    sess = session_factory()
    yield sess
    sess.close()


@pytest.fixture
def tenant(db: Session):
    row = TenantRow(
        id="demo",
        slug="demo",
        name="Nexus",
    )
    db.add(row)
    db.commit()
    return row


@pytest.fixture
def config():
    return load_tenant("demo")


def test_recap_has_no_currency_or_duration(config):
    brief = ProjectBrief(
        service="web_app",
        goal="Build an internal analytics and billing portal for finance teams",
        platforms=["web"],
        features=["auth", "dashboard", "billing", "reports"],
        timeline="3_6_months",
        budget_band="40_80k",
        decision_role="founder_or_exec",
    )
    recap = recap_line_from_brief(config, brief)

    assert "\n" not in recap
    for sym in ["$", "€", "£", "₹", "USD"]:
        assert sym not in recap
    for dur in ["weeks", "week", "months", "month", "days", "day", "hours", "hour"]:
        assert f" {dur} " not in f" {recap.lower()} "

    assert "Web application" in recap
    assert "web" in recap
    assert "dashboard" in recap
    assert "Build an internal analytics and billing portal" in recap


def test_engine_range_appears_exactly_once_in_estimate_message(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    brief = ProjectBrief(
        service="web_app",
        goal="Build an internal analytics portal",
        platforms=["web"],
        features=["auth", "dashboard"],
        features_confirmed=True,
        timeline="1_3_months",
        budget_band="40_80k",
        decision_role="founder_or_exec",
        company_size="startup",
    )
    session.brief_json = brief.model_dump_json()

    res = run_turn(db, tenant, config, session, [], "", {"field": "decision_role", "value": "founder_or_exec"})
    assert res["route"] == "estimate"
    range_label = res["estimate"]["range_label"]
    assert res["message"].count(range_label) == 1
    assert "That's a first-pass range based on typical scope for this kind of project." in res["message"]
    assert any(c.get("type") == "estimate" and c.get("range") == range_label for c in res["cards"])


def test_budget_fit_line_cases(config):
    ranges = {
        "exploring": None,
        "under_15k": [0, 15000],
        "15_40k": [15000, 40000],
        "40_80k": [40000, 80000],
        "80k_plus": [80000, None],
    }
    estimate = {"low": 20000, "high": 35000, "range_label": "$20,000–$35,000"}

    # Below
    below_line = budget_fit_line("under_15k", estimate, ranges)
    assert below_line == "Your budget band sits below this first-pass range. The usual lever is a leaner scope; I can show a Core-only cut."

    # Overlap
    overlap_line = budget_fit_line("15_40k", estimate, ranges)
    assert overlap_line == "Your budget band overlaps this first-pass range."

    # Above
    above_line = budget_fit_line("80k_plus", estimate, ranges)
    assert above_line == "Your budget band is above this first-pass range, so there is room to add scope."

    # Exploring & missing
    assert budget_fit_line("exploring", estimate, ranges) == ""
    assert budget_fit_line(None, estimate, ranges) == ""
    assert budget_fit_line("unknown", estimate, ranges) == ""

    # Never uses forbidden words or prints currency figures
    for line in [below_line, overlap_line, above_line]:
        assert "realistic" not in line.lower()
        assert "guarantee" not in line.lower()
        assert "$" not in line


def test_budget_fit_below_produces_leaner_cut_chip(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    brief = ProjectBrief(
        service="web_app",
        goal="Build an internal analytics portal",
        platforms=["web"],
        features=["auth", "dashboard"],
        features_confirmed=True,
        timeline="1_3_months",
        budget_band="under_15k",
        decision_role="founder_or_exec",
        company_size="startup",
    )
    session.brief_json = brief.model_dump_json()

    res = run_turn(db, tenant, config, session, [], "", {"field": "budget_band", "value": "under_15k"})
    leaner_chips = [c for c in res["chips"] if c.get("field") == "view_mvp" and c.get("value") == "leaner_cut"]
    assert len(leaner_chips) == 1
    assert leaner_chips[0]["label"] == "Show a leaner cut"

    # Click leaner cut opens MVP
    mvp_res = run_turn(db, tenant, config, session, [], "", leaner_chips[0])
    assert mvp_res["route"] == "mvp"
    assert any(c.get("type") == "mvp" for c in mvp_res["cards"])


def test_shape_message_appears_once_and_before_timeline_question(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    # Step: set service
    run_turn(db, tenant, config, session, [], "", {"field": "service", "value": "web_app"})
    # Step: set goal
    run_turn(db, tenant, config, session, [], "Track company inventory metrics", None)
    # Step: set features
    run_turn(db, tenant, config, session, [], "", {"field": "features", "value": ["barcodes", "alerts"]})
    # Step: set platforms -> both platforms and features are now known
    res = run_turn(db, tenant, config, session, [], "", {"field": "platforms", "value": ["web"]})

    shape_cards = [c for c in res["cards"] if c.get("type") == "shape"]
    assert len(shape_cards) == 1
    assert "Channels and UX" in res["message"]
    assert "Core flow" in res["message"]
    assert "Backend and APIs" in res["message"]
    assert "$" not in res["message"]

    # Verify next turn does not re-show the shape card
    brief_after = ProjectBrief.model_validate_json(session.brief_json)
    assert brief_after.shape_shown is True

    next_res = run_turn(db, tenant, config, session, [], "", {"field": "users", "value": "internal_team"})
    next_shape_cards = [c for c in next_res["cards"] if c.get("type") == "shape"]
    assert len(next_shape_cards) == 0


def test_no_banned_strings_in_backend_app():
    backend_app_dir = Path(__file__).resolve().parent.parent / "app"
    py_files = list(backend_app_dir.rglob("*.py"))
    assert len(py_files) > 0

    banned = [
        "similar projects we've delivered",
        "usually respond within",
        "realistic",
    ]

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8").lower()
        for phrase in banned:
            assert phrase not in content, f"Banned phrase '{phrase}' found in {py_file}"


def test_email_instead_does_not_show_slots(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    db.add(session)
    db.commit()

    # Trigger booking window
    book_res = run_turn(db, tenant, config, session, [], "book a call", None)
    assert book_res["route"] == "booking"
    email_chips = [c for c in book_res["chips"] if c.get("field") == "email_instead"]
    assert len(email_chips) == 1
    assert email_chips[0]["label"] == "Email me instead"

    # Click 'Email me instead'
    ask_res = run_turn(db, tenant, config, session, [], "", email_chips[0])
    assert ask_res["route"] == "email_capture"
    assert "Sure. What's the best email?" in ask_res["message"]
    contact = json.loads(session.contact_json or "{}")
    assert contact.get("prefers_email") is True

    # Send email
    final_res = run_turn(db, tenant, config, session, [], "contact@mycompany.com", None)
    assert final_res["route"] == "email_capture"
    assert "Thanks, the team will email you the summary." in final_res["message"]
    assert not any(c.get("type") == "booking" for c in final_res.get("cards", []))
    assert not any(c.get("field") == "booking_slot" for c in final_res.get("chips", []))


def test_call_length_text_equals_config(db, tenant, config):
    session = SessionRow(tenant_id=tenant.id, stage="discovery")
    session.booking_json = json.dumps({"slot_iso": "2026-10-15T10:00:00Z", "label": "Thursday 10:00 AM"})
    db.add(session)
    db.commit()

    platform = get_platform()
    expected_duration = platform.calendar.duration_minutes

    res = run_turn(db, tenant, config, session, [], "what is on the agenda for the call?", None)
    assert f"{expected_duration}-minute discovery call agenda covers" in res["message"]


def test_widget_files_are_byte_identical():
    root = Path(__file__).resolve().parent.parent.parent
    widget_file = root / "widget" / "consultant.js"
    public_widget_file = root / "public" / "widget" / "consultant.js"

    assert widget_file.exists()
    assert public_widget_file.exists()
    assert widget_file.read_bytes() == public_widget_file.read_bytes()


def test_fallback_recovery_returns_expected_text_and_chips():
    text, chips = fallback_recovery()
    assert text == "That's outside what I have on hand right now. I can connect you with the team, or keep scoping your estimate."
    assert fallback_recovery_message() == text
    assert any(c.get("field") == "booking_window" for c in chips)
    assert any(c.get("field") == "continue_discovery" for c in chips)
