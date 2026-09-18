from backend.app.config_loader.loader import get_config, load_config


def test_config_loads_and_validates() -> None:
    config = load_config()
    assert config.agency.name == "DevConsult"
    assert config.agency.nda.version
    assert config.agency.nda.title
    assert "book a call" in config.agency.out_of_scope_close.lower()
    assert config.agency.out_of_scope_thanks.strip()
    assert config.calendar.timezone == "Asia/Kolkata"
    assert config.calendar.duration_minutes == 45
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
    service, opening, _ = config.page_for("/ui-ux-design.html")
    assert service == "ui_ux"
    assert "design" in opening.lower()
    service, _, _ = config.page_for("/staff-augmentation")
    assert service == "staff_augmentation"
    service, opening, _ = config.page_for("/work/harvest.html")
    assert service == "mobile_app"
    assert "harvest" in opening.lower()
    service, opening, _ = config.page_for("/work/atlas")
    assert service == "ai_product"
    assert "atlas" in opening.lower()
    service, opening, _ = config.page_for("/work.html")
    assert service is None
    assert "work" in opening.lower()
    service, opening, _ = config.page_for("/contact.html")
    assert service is None
    assert "build" in opening.lower() or "range" in opening.lower()


def test_enrichment_directory_loads() -> None:
    config = load_config()
    assert "acme.test" in config.enrichment.domains
    assert config.enrichment.domains["acme.test"]["company"] == "Acme Ops"
    assert config.handoff.notify.slack.get("enabled") is True
    assert config.handoff.notify.slack.get("channel") == "#inbound"
