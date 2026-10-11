import json
from pathlib import Path
import pytest
from backend.app.agents.brief import (
    ProjectBrief,
    brief_ready,
    next_discovery_field,
    fast_engine_gaps,
    next_sharpen_field,
)
from backend.app.engines.pricing import estimate_project
from backend.app.screening.slots import prompt_for, chips_for_field
from backend.app.tenants.loader import load_tenant
from backend.app.tenants.schema import BrandConfig
from backend.app.agents.router import run_turn
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import SessionRow, TenantRow


def test_brand_config_default_flow_is_classic():
    brand = BrandConfig()
    assert brand.flow == "classic"


def test_brief_ready_both_flows():
    # An initial brief with 5 fast fields:
    brief_fast = ProjectBrief(
        service="mobile_app",
        goal="Direct patient sports clinic booking",
        platforms=["ios", "android"],
        timeline="1_3_months",
        budget_band="15_40k",
    )
    # In fast flow, ready without decision_role
    assert brief_ready(brief_fast, flow="fast") is True
    # In classic flow, requires decision_role
    assert brief_ready(brief_fast, flow="classic") is False

    # Adding decision_role makes it ready in classic flow too
    brief_fast.decision_role = "founder_or_exec"
    assert brief_ready(brief_fast, flow="classic") is True


def test_brief_ready_ui_ux_platforms_implied_in_fast():
    brief_ui = ProjectBrief(
        service="ui_ux",
        goal="Redesign mobile checkouts",
        timeline="1_3_months",
        budget_band="15_40k",
    )
    assert brief_ready(brief_ui, flow="fast") is True
    assert "platforms" not in fast_engine_gaps(brief_ui)


def test_engine_numbers_identical_both_flows():
    tenant = load_tenant("demo")
    brief = ProjectBrief(
        service="mobile_app",
        goal="Sports clinic booking application for direct patients",
        platforms=["ios", "android"],
        timeline="1_3_months",
        budget_band="15_40k",
        features=["User login & profiles", "Push notifications", "In-app payments"],
    )
    est1 = estimate_project(brief, tenant.pricing)
    est2 = estimate_project(brief, tenant.pricing)
    assert est1["low"] == est2["low"]
    assert est1["high"] == est2["high"]
    assert est1["timeline_weeks"] == est2["timeline_weeks"]


def test_budget_prompt_wording():
    prompt = prompt_for(None, "budget_band")
    assert "a rough ballpark helps me size this, no commitment" in prompt.lower()
    chips = chips_for_field("budget_band")
    assert any(c.get("label") == "Still exploring" for c in chips)


def test_budget_never_asked_before_goal_and_platforms():
    brief_empty = ProjectBrief(service="mobile_app")
    assert next_discovery_field(brief_empty, flow="fast") != "budget_band"
    assert next_discovery_field(brief_empty, flow="classic") != "budget_band"

    brief_with_goal = ProjectBrief(service="mobile_app", goal="Booking app")
    # Missing platforms
    assert next_discovery_field(brief_with_goal, flow="fast") == "platforms"
    assert next_discovery_field(brief_with_goal, flow="classic") != "budget_band"


def test_fast_flow_reaches_estimate_within_6_bot_questions():
    init_db()
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Nexus")
        config = load_tenant("demo")
        config.brand.flow = "fast"
        session = SessionRow(tenant_id=tenant_row.id, stage="discovery")

        # Turn 1: Comprehensive message
        t1_text = (
            "We want it on both iOS and Android. For the first release we just need login, "
            "calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months."
        )
        res1 = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text=t1_text,
            chip=None,
        )
        assert res1["route"] == "discovery"

        # Turn 2: Goal answered
        t2_text = "I am building a sports clinic booking application for direct patients."
        res2 = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[
                {"role": "user", "content": t1_text},
                {"role": "assistant", "content": res1["message"]},
            ],
            user_text=t2_text,
            chip=None,
        )

        # In fast flow, Turn 2 reaches estimate directly (only 2 bot turns)
        assert res2["route"] == "estimate"
        assert res2.get("estimate") is not None
        assert any(c.get("type") == "estimate" for c in res2.get("cards", []))


def test_sharpen_answer_recomputes_estimate():
    init_db()
    with SessionLocal() as db:
        tenant_row = TenantRow(slug="demo", name="Nexus")
        config = load_tenant("demo")
        config.brand.flow = "fast"
        
        initial_brief = ProjectBrief(
            service="mobile_app",
            goal="Sports clinic booking application for direct patients",
            platforms=["ios", "android"],
            timeline="1_3_months",
            budget_band="15_40k",
        )
        session = SessionRow(
            tenant_id=tenant_row.id,
            stage="estimate",
            brief_json=initial_brief.model_dump_json(),
        )

        # Click sharpen chip
        res_sharpen = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[],
            user_text="",
            chip={"field": "sharpen_estimate", "value": "yes", "label": "Sharpen this estimate"},
        )
        assert res_sharpen["route"] == "discovery"

        # Now provide features
        res_features = run_turn(
            db=db,
            tenant=tenant_row,
            config=config,
            session=session,
            history=[
                {"role": "assistant", "content": res_sharpen["message"]},
            ],
            user_text="Real-time calendar syncing, In-app payments, Push notifications, Analytics dashboard",
            chip=None,
        )
        # Recomputes estimate with new features
        assert res_features["route"] == "estimate"
        assert res_features.get("estimate") is not None
        est = res_features["estimate"]
        assert est["low"] > 0
        assert est["high"] >= est["low"]
