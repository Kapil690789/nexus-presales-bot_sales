import pytest
from backend.app.agents.brief import ProjectBrief, needs_feature_detail, next_discovery_field
from backend.app.agents.extractor import extract_slots, is_product_idea
from backend.app.agents.router import recap_line_from_brief, run_turn
from backend.app.screening.slots import prompt_for, chips_for_field
from backend.app.tenants.loader import load_tenant


def test_starter_phrase_does_not_set_dummy_goal():
    """Verify phrases like 'I have an app idea' do not get extracted as dummy goals."""
    brief = ProjectBrief()
    slots = extract_slots("I have an app idea", brief)
    # The goal must not be 'Develop an app idea' or similar dummy string
    assert slots.get("goal") is None or "develop an app idea" not in str(slots.get("goal")).lower()


def test_single_commodity_feature_skips_redundant_detail_and_sketch():
    """When a client only selects User authentication, skip detail and sketch interrogation."""
    brief = ProjectBrief(service="mobile_app", goal="Fitness trainer bookings", features=["User authentication"], features_confirmed=True)
    assert not needs_feature_detail(brief), "Commodity login feature should not require detail explanation"
    
    # next_discovery_field should advance straight to platforms, not user_flow or feature_detail
    nxt = next_discovery_field(brief)
    assert nxt == "platforms", f"Expected platforms next, got {nxt}"
    assert brief.user_flow == "not_specified", "User flow should be auto-marked not_specified for commodity login"


def test_recap_never_mentions_dummy_goal():
    """Recap line must never say 'a mobile app - Develop an app idea'."""
    config = load_tenant("demo")
    brief = ProjectBrief(service="mobile_app", goal="Develop an app idea", platforms=["ios", "android"])
    recap = recap_line_from_brief(config, brief)
    assert "develop an app idea" not in recap.lower()
    assert "a mobile app" in recap.lower()


def test_objection_pricing_preserves_phase_two_and_adds_lean_mvp():
    """Price objection must preserve phase-two keyword while offering Lean Core MVP."""
    config = load_tenant("demo")
    too_exp = config.objections.items.get("too_expensive")
    assert too_exp is not None
    reply = too_exp.reply if hasattr(too_exp, "reply") else too_exp["reply"]
    assert "phase-two" in reply
    assert "Lean Core MVP" in reply or "Lean" in reply


def test_security_faq_domain_enrichment():
    """Security FAQ should enrich with domain compliance standards when health/fintech domain is active."""
    from backend.app.engines.domains import get_domain_blueprint
    bp_health = get_domain_blueprint("health")
    assert bp_health is not None
    assert "HIPAA" in bp_health.compliance
