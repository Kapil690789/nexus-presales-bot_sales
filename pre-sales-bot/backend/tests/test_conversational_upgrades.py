from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.router import run_turn
from backend.app.models.db import SessionLocal
from backend.app.models.entities import SessionRow, TenantRow
from backend.app.tenants.loader import load_tenant


def test_close_out_chip():
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Northline")
        config = load_tenant("demo")
        session = SessionRow(tenant_id=tenant_row.id, stage="discovery")

        result = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text="",
            chip={"field": "close_out", "value": "yes"},
        )
        assert "Thanks for chatting with us" in result["message"]
        assert result["route"] == "discovery"
        assert any(c.get("field") == "booking_window" for c in result["chips"])


def test_natural_language_discovery_flow(monkeypatch):
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Northline")
        config = load_tenant("demo")
        session = SessionRow(tenant_id=tenant_row.id, stage="discovery")

        fake_extracted = {
            "service": "mobile_app",
            "platforms": ["ios", "android"],
            "goal": "Clinic management companion",
            "budget_band": "40_80k",
            "timeline": "1_3_months",
            "decision_role": "founder_or_exec",
            "is_question": False,
            "uncertain": False,
        }
        monkeypatch.setattr("backend.app.agents.router.extract_slots", lambda text, pending, brief: fake_extracted)

        result = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text="I am looking to build an iOS and Android app for clinic management, budget around 50k",
            chip=None,
        )

        assert result["route"] == "estimate"
        assert result["stage"] == "advising"
        assert "range_label" in (result.get("estimate") or {})


def test_session_expiry_endpoint(client):
    from datetime import datetime, timedelta, timezone
    from backend.app.models.entities import SessionRow, TenantRow
    from backend.app.models.db import SessionLocal

    with SessionLocal() as db:
        tenant = db.query(TenantRow).filter_by(slug="demo").first()
        expired_session = SessionRow(
            tenant_id=tenant.id,
            stage="discovery",
            expires_at=datetime.now(timezone.utc) - timedelta(days=1),
        )
        db.add(expired_session)
        db.commit()
        db.refresh(expired_session)
        expired_id = expired_session.id

    resp = client.post(f"/api/v1/sessions/{expired_id}/messages", json={"content": "Hello"})
    assert resp.status_code == 410
    assert "expired" in resp.json().get("detail", "").lower()


def test_off_topic_deflection_flow():
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Northline")
        config = load_tenant("demo")
        session = SessionRow(tenant_id=tenant_row.id, stage="discovery")

        result = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text="Who won the FIFA World Cup in 2022?",
            chip=None,
        )
        assert result["route"] in ("off_topic", "fallback", "faq")
        assert "software" in result["message"].lower() or "project" in result["message"].lower() or "custom" in result["message"].lower()
        assert not any(err in result["message"].lower() for err in ["traceback", "syntaxerror", "exception"])


def test_sarah_fintech_flow(monkeypatch):
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Northline")
        config = load_tenant("demo")
        session = SessionRow(tenant_id=tenant_row.id, stage="discovery")

        fake_extracted = {
            "service": "mobile_app",
            "platforms": ["ios", "android"],
            "goal": "Fintech app with AI chat",
            "budget_band": "15_40k",
            "timeline": "1_3_months",
            "decision_role": "founder_or_exec",
            "is_question": False,
            "is_off_topic": False,
            "uncertain": False,
        }
        monkeypatch.setattr("backend.app.agents.router.extract_slots", lambda text, pending, brief: fake_extracted)

        result = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text="Hi, I am Sarah, Founder at a Fintech startup. We urgently need a cross-platform mobile app for iOS & Android with AI chat, timeline is 2 months, and our budget is around $25k to $50k. Can we schedule a discussion?",
            chip=None,
        )

        assert result["route"] == "estimate"
        assert result["stage"] == "advising"
        assert result.get("estimate") is not None
        assert "cards" in result
        assert any(c["type"] == "estimate" for c in result["cards"])
