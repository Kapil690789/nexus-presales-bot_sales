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
    service, opening, extras = config.page_for("/mobile-app-development.html")
    assert service == "mobile_app"
    assert any("android" in item.lower() for item in extras)
    service, opening, extras = config.page_for("/ai-development")
    assert service == "ai_product"
    assert extras


def test_unmapped_site_pages_have_distinct_openings() -> None:
    config = get_config()
    _, home, _ = config.page_for("/")
    service, about, _ = config.page_for("/about.html")
    assert service is None
    assert about != home
    assert "consult" in about.lower()
    service, process, _ = config.page_for("/process.html")
    _, pricing, _ = config.page_for("/pricing.html")
    assert service is None
    assert process != pricing
    assert "engagement" in process.lower() or "discovery" in process.lower()
    service, careers, extras = config.page_for("/careers")
    assert service is None
    assert "role" in careers.lower()
    assert extras and "role" in extras[0].lower()
    service, insights, _ = config.page_for("/insights.html")
    assert service is None
    assert "mvp" in insights.lower() or "notes" in insights.lower() or "range" in insights.lower()
    service, grounding, extras = config.page_for("/insights/grounding-ai.html")
    assert service == "ai_product"
    assert "ground" in grounding.lower() or "assistant" in grounding.lower() or "corpus" in grounding.lower()
    assert extras
    service, mvp, _ = config.page_for("/insights/mvp-first")
    assert service is None
    assert "user" in mvp.lower() or "journey" in mvp.lower()
    service, ranges, _ = config.page_for("/insights/indicative-ranges.html")
    assert service is None
    assert "indicative" in ranges.lower() or "stakeholders" in ranges.lower()
    service, privacy, _ = config.page_for("/privacy.html")
    assert service is None
    assert "legal" in privacy.lower()
    service, terms, _ = config.page_for("/terms")
    assert service is None
    assert "legal" in terms.lower() or "contract" in terms.lower()
    assert privacy != terms
    assert about != process
    assert careers != home


def test_enrichment_directory_loads() -> None:
    config = load_config()
    assert "acme.test" in config.enrichment.domains
    assert config.enrichment.domains["acme.test"]["company"] == "Acme Ops"
    assert config.handoff.notify.slack.get("enabled") is True
    assert config.handoff.notify.slack.get("channel") == "#inbound"
