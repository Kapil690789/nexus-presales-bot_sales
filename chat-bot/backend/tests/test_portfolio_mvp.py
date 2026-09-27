from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.portfolio import match_portfolio


def test_architecture_stays_on_approved_stacks() -> None:
    config = load_config()
    rec = recommend_architecture(ProjectBrief(service="mobile_app", platforms=["both"], auth=True), config.services)
    assert set(rec["frontend"]).issubset(set(config.services.in_scope["mobile_app"].stacks))


def test_mvp_puts_goal_first() -> None:
    rec = recommend_mvp(ProjectBrief(service="web_app", goal="Cut close time in half"))
    assert rec["mvp"][0].endswith("Cut close time in half")


def test_mvp_includes_named_features() -> None:
    rec = recommend_mvp(
        ProjectBrief(service="web_app", goal="Cut close time in half", features=["Payments", "Admin"])
    )
    blob = " ".join(rec["mvp"])
    assert "Payments" in blob
    assert "Admin" in blob


def test_portfolio_prefers_matching_service() -> None:
    config = load_config()
    matches = match_portfolio(ProjectBrief(service="ai_product", industry="professional_services", ai_features=["rfp"]), config.portfolio)
    assert matches[0]["title"].startswith("Atlas")
