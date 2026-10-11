import os
from pathlib import Path
from fastapi.testclient import TestClient
from backend.app.main import app
from backend.app.models.db import init_db
from backend.app.core.settings import get_settings


ROOT = Path(__file__).resolve().parent.parent.parent


def test_widget_files_byte_identical():
    src = (ROOT / "widget" / "consultant.js").read_bytes()
    dst = (ROOT / "public" / "widget" / "consultant.js").read_bytes()
    assert src == dst, "widget/consultant.js and public/widget/consultant.js must be byte-identical"


def test_widget_contains_e6_features():
    content = (ROOT / "widget" / "consultant.js").read_text(encoding="utf-8")
    
    # 1. Typing indicator min-delay logic
    assert "waitStartTime" in content
    assert "elapsed < 400" in content
    assert "600 - elapsed" in content
    assert "aria-live" in content
    assert "polite" in content
    assert "prefers-reduced-motion" in content

    # 2. Chips wrapping on small screens
    assert ".ps-chips{flex-wrap:wrap" in content or "flex-wrap:wrap" in content

    # 3. Progress hint pill
    assert "ps-progress-pill" in content
    assert "payload.progress" in content

    # 4. Your brief compact card with helper formatting
    assert "renderBriefCard" in content
    assert "ps-brief-card" in content
    assert "ps-brief-toggle" in content
    assert "displayPlatforms" in content
    assert "timelineLabel" in content
    assert "budgetLabel" in content
    assert "iOS and Android" in content

    # 5. Teaser bubble desktop only, dismissible, sessionStorage
    assert "initTeaserBubble" in content
    assert "ps-teaser-bubble" in content
    assert "ps-teaser-close" in content
    assert "teaser_delay_ms" in content
    assert "sessionStorage" in content
    assert "ps_teaser_dismissed" in content
    assert "window.innerWidth >= 768" in content


def test_studio_html_contains_e6_platform_formatter():
    content = (ROOT / "public" / "studio.html").read_text(encoding="utf-8")
    assert "formatPlatforms" in content
    assert "iOS and Android" in content


def test_api_session_returns_progress_field():
    init_db()
    client = TestClient(app)
    res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert res.status_code == 200
    data = res.json()
    assert "progress" in data
