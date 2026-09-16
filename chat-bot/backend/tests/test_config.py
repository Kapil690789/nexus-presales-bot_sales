from backend.app.config_loader.loader import get_config, load_config


def test_config_loads_and_validates() -> None:
    config = load_config()
    assert config.agency.name == "DevConsult"
    assert config.pricing.low_side_factor == 0.80
    assert "mobile_app" in config.services.in_scope


def test_page_context_is_path_aware() -> None:
    config = get_config()
    service, opening, _ = config.page_for("/demo/mobile-app-development.html")
    assert service == "mobile_app"
    assert "mobile" in opening.lower()
    service, opening, _ = config.page_for("/demo/web-app-development")
    assert service == "web_app"
    assert "web" in opening.lower()
    service, _, _ = config.page_for("/demo/ai-development.html")
    assert service == "ai_product"
    service, _, _ = config.page_for("/demo/")
    assert service is None
    service, opening, _ = config.page_for("/web-app-development.html")
    assert service == "web_app"
    assert "web" in opening.lower()
    service, opening, _ = config.page_for("/pricing")
    assert service is None
    assert "price" in opening.lower() or "range" in opening.lower()
    service, _, _ = config.page_for("/")
    assert service is None


def test_enrichment_directory_loads() -> None:
    config = load_config()
    assert "acme.test" in config.enrichment.domains
    assert config.enrichment.domains["acme.test"]["company"] == "Acme Ops"
