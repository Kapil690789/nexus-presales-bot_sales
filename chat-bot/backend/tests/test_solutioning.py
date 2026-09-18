from backend.app.agents import orchestrator
from backend.app.agents.brief import ProjectBrief
from backend.app.agents.chips import DISCOVERY_PROMPTS
from backend.app.agents.extract import apply_architecture, apply_mvp
from backend.app.config_loader.loader import load_config
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.pricing import estimate_project
from backend.app.models.db import SessionLocal
from backend.app.rag.ingest import ingest


READY_WEB = ProjectBrief(
    service="web_app",
    goal="Ops console so distributors track orders in one place",
    platforms=["web"],
    timeline="1_3_months",
    budget_band="40_80k",
    decision_role="founder_or_exec",
    users="internal",
    admin=True,
)


def _ingested():
    db = SessionLocal()
    ingest(db)
    db.commit()
    return db


def test_unapproved_stack_is_dropped() -> None:
    config = load_config()
    engine = recommend_architecture(ProjectBrief(service="mobile_app", platforms=["both"]), config.services)
    merged = apply_architecture(
        engine,
        {"frontend": ["Flutter", "Laravel"], "backend": ["Firebase"], "notes": ["Shared codebase for both stores."]},
        config,
        "mobile_app",
    )
    assert "Laravel" not in merged["frontend"]
    assert "Flutter" in merged["frontend"]
    assert set(merged["frontend"]).issubset(set(config.services.in_scope["mobile_app"].stacks) | set(engine["frontend"]))


def test_empty_architecture_overlay_keeps_engine() -> None:
    config = load_config()
    engine = recommend_architecture(ProjectBrief(service="web_app", platforms=["web"], admin=True), config.services)
    merged = apply_architecture(engine, {}, config, "web_app")
    assert merged["frontend"] == engine["frontend"]
    assert apply_mvp({"mvp": ["A"], "later": ["B"], "rationale": "x"}, {})["mvp"] == ["A"]


def test_offline_estimate_includes_assumptions() -> None:
    config = load_config()
    result = estimate_project(
        ProjectBrief(service="mobile_app", platforms=["both"], goal="Marketplace for growers", marketplace=True),
        config.pricing,
    )
    assert result["assumptions"]
    assert any("iOS and Android" in item for item in result["assumptions"])
    assert any("marketplace" in item.lower() for item in result["assumptions"])


def test_offline_mvp_stays_template_with_goal_first() -> None:
    rec = recommend_mvp(ProjectBrief(service="web_app", goal="Cut close time in half"))
    assert rec["mvp"][0].endswith("Cut close time in half")


def test_tight_budget_moves_items_to_later() -> None:
    roomy = recommend_mvp(ProjectBrief(service="web_app", goal="Ops console", budget_band="80k_plus"))
    tight = recommend_mvp(ProjectBrief(service="web_app", goal="Ops console", budget_band="under_15k"))
    assert len(tight["mvp"]) <= 3
    assert len(tight["later"]) >= len(roomy["later"])


def test_health_brief_adds_privacy_note() -> None:
    config = load_config()
    rec = recommend_architecture(
        ProjectBrief(service="mobile_app", platforms=["ios"], industry="health", constraints=["Must-have HIPAA controls."]),
        config.services,
    )
    blob = " ".join(rec["notes"]).lower()
    assert "privacy" in blob or "hipaa" in blob or "constraint" in blob


def test_same_turn_solutioning_sees_range_and_approved_stacks(monkeypatch) -> None:
    config = load_config()
    calls: list[str] = []

    def fake_complete_json(system: str, user: str) -> dict:
        calls.append(user)
        if "Approved frontend stacks" not in user:
            return {
                "brief_updates": {
                    "goal": "A patient companion on iOS",
                    "platforms": ["ios"],
                    "timeline": "1_3_months",
                    "budget_band": "40_80k",
                    "decision_role": "founder_or_exec",
                },
                "message": "Noted.",
                "chips": [],
                "stage": "discovery",
            }
        assert "range_label" in user
        assert "Still needed before an estimate" not in user
        return {
            "architecture": {"frontend": ["Flutter"], "notes": ["One platform first."]},
            "mvp": {"mvp": ["Prove this outcome: A patient companion on iOS"], "later": ["Android"], "rationale": "iOS first."},
            "message": "I would keep v1 to iOS. Indicative MVP sits around $1.",
            "chips": [],
            "stage": "estimation",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    db = _ingested()
    try:
        result = orchestrator.run_turn(
            config=config,
            brief=ProjectBrief(service="mobile_app"),
            contact={},
            nda_accepted=False,
            booking=None,
            user_text="Building an iOS patient companion, 1-3 months, budget around 50k.",
            chip=None,
            page_opening="Planning a mobile product?",
            extra_questions=[],
            db=db,
            page_path="/mobile-app-development",
        )
    finally:
        db.close()
    assert len(calls) == 2
    assert "Approved frontend stacks" in calls[1]
    assert result.estimate
    assert result.estimate["range_label"] in result.message
    assert DISCOVERY_PROMPTS["company_size"] not in result.message
    assert any(card.get("assumptions") for card in result.cards if card.get("type") == "estimate")


def test_solutioning_message_without_range_is_stitched(monkeypatch) -> None:
    config = load_config()

    def fake_complete_json(system: str, user: str) -> dict:
        return {
            "architecture": {"frontend": ["Next.js"], "notes": ["Admin in v1 for distributors."]},
            "mvp": {"mvp": ["One distributor workflow"], "later": ["Exports"], "rationale": "Thin first release."},
            "message": "I would protect the distributor workflow and leave reporting for later.",
            "chips": [],
            "stage": "estimation",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=READY_WEB.model_copy(deep=True),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="What stack would you use?",
        chip=None,
        page_opening="Building a web product?",
        extra_questions=[],
    )
    assert result.estimate
    assert result.estimate["range_label"] in result.message
    assert "distributor" in result.message.lower()
    assert result.architecture
    assert "Next.js" in (result.architecture.get("frontend") or [])
    assert result.mvp and result.mvp["mvp"][0].startswith("One distributor")
