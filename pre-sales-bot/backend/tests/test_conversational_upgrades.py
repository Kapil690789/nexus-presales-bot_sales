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
