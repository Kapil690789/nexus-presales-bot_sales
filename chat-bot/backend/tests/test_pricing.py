from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.app.engines.pricing import estimate_project


def test_estimate_is_low_side_range() -> None:
    config = load_config()
    result = estimate_project(ProjectBrief(service="mobile_app", platforms=["both"], goal="Marketplace for growers"), config.pricing)
    assert result["low"] < result["raw"]
    assert abs(result["low"] / result["raw"] - config.pricing.low_side_factor) < 0.08
    assert result["high"] > result["low"]
    assert result["team"]


def test_changing_yaml_factor_changes_number() -> None:
    config = load_config()
    brief = ProjectBrief(service="web_app", platforms=["web"])
    normal = estimate_project(brief, config.pricing)
    config.pricing.low_side_factor = 0.5
    cheaper = estimate_project(brief, config.pricing)
    assert cheaper["low"] < normal["low"]
