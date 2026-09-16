from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.app.engines.qualification import qualify


def _ready(**kwargs) -> ProjectBrief:
    data = {
        "service": "web_app",
        "goal": "Ops console for accountants",
        "platforms": ["web"],
        "users": "internal",
        "integrations": ["none"],
        "timeline": "1_3_months",
        "budget_band": "40_80k",
        "decision_role": "founder_or_exec",
        "company_size": "smb",
    }
    data.update(kwargs)
    return ProjectBrief(**data)


def test_strong_lead_is_hot_and_can_estimate() -> None:
    config = load_config()
    result = qualify(_ready(), config.qualification, config.services, has_email=True)
    assert result["band"] == "hot"
    assert result["can_estimate"] is True
    assert result["can_book"] is True


def test_intern_is_disqualified_without_estimate() -> None:
    config = load_config()
    result = qualify(_ready(decision_role="intern_or_student"), config.qualification, config.services)
    assert result["band"] == "disqualify"
    assert result["can_estimate"] is False


def test_out_of_scope_disqualifies() -> None:
    config = load_config()
    result = qualify(_ready(service="crypto_web3", out_of_scope="crypto_web3"), config.qualification, config.services)
    assert result["band"] == "disqualify"
