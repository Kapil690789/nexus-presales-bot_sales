import re
from pathlib import Path
import pytest
from pydantic import ValidationError

from backend.app.tenants.schema import BrandConfig, PageHint, Starter, TenantConfig
from backend.app.tenants.loader import load_tenant, create_tenant_folder, clear_tenant_cache
from backend.app.core.settings import ROOT


def test_schema_defaults_load():
    brand = BrandConfig()
    assert brand.advisor_name == "Alex"
    assert brand.advisor_title == "AI project advisor"
    assert brand.advisor_avatar == ""
    assert brand.human_label == "Talk to a human"
    assert len(brand.starters) == 4
    assert brand.opening_variants == []
    assert brand.page_hints == []


def test_schema_advisor_title_without_ai_fails():
    with pytest.raises(ValidationError):
        BrandConfig(advisor_title="Senior Project Consultant")


def test_schema_advisor_avatar_http_fails():
    with pytest.raises(ValidationError):
        BrandConfig(advisor_avatar="http://example.com/avatar.png")


def test_schema_unknown_page_hint_service_fails(tmp_path):
    hint = PageHint(match="/mobile", service="nonexistent_service", question="Tell me about your mobile idea")
    brand = BrandConfig(page_hints=[hint])
    with pytest.raises(ValidationError):
        TenantConfig(
            brand=brand,
            services={"in_scope": {"web_app": {"label": "Web App"}}},
        )


def test_schema_unknown_keys_fail():
    with pytest.raises(ValidationError):
        BrandConfig(unknown_custom_field="not_allowed")

    with pytest.raises(ValidationError):
        Starter(label="Test", text="Test text", extra_key="fail")

    with pytest.raises(ValidationError):
        PageHint(match="/path", extra_key="fail")


def test_opener_word_count_and_content(client):
    res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert res.status_code == 200
    data = res.json()
    msg = data["message"]
    words = msg.split()
    assert len(words) <= 40, f"Opener has {len(words)} words, max is 40"
    assert "Alex" in msg
    assert "Nexus" in msg
    assert re.search(r"\bAI\b", msg)


def test_opener_custom_tenant_no_nexus(client, auth):
    created = client.post(
        "/admin/tenants",
        data={"slug": "acmetest", "name": "Acme", "logo_text": "Acme", "primary": "#112233"},
        auth=auth,
        follow_redirects=False,
    )
    assert created.status_code == 303
    try:
        session = client.post("/api/v1/sessions", json={"tenant": "acmetest"})
        assert session.status_code == 200
        msg = session.json()["message"]
        assert "Acme" in msg
        assert "Nexus" not in msg
        assert re.search(r"\bAI\b", msg)
    finally:
        import shutil
        tdir = ROOT / "tenants" / "acmetest"
        if tdir.exists():
            shutil.rmtree(tdir)
        clear_tenant_cache()


def test_opening_variants_deterministic_by_session_id(client, monkeypatch):
    from backend.app.tenants.loader import load_tenant
    config = load_tenant("demo")
    monkeypatch.setattr(
        config.brand,
        "opening_variants",
        [
            "What kind of product or application are you hoping to create?",
            "What are you looking to launch first?",
        ],
    )
    res1 = client.post("/api/v1/sessions", json={"tenant": "demo"})
    res2 = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert res1.status_code == 200
    assert res2.status_code == 200
    import hashlib
    s1_id = res1.json()["session_id"]
    idx1 = int(hashlib.md5(s1_id.encode()).hexdigest(), 16) % len(config.brand.opening_variants)
    expected_q1 = config.brand.opening_variants[idx1]
    assert expected_q1 in res1.json()["message"]


def test_opening_chips_include_starters_and_human(client):
    res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert res.status_code == 200
    chips = res.json()["chips"]
    fields = [c["field"] for c in chips]
    assert "booking_window" in fields
    assert "ask" in fields
    starter_labels = [c["label"] for c in chips if c["field"] == "ask"]
    assert "I have an app idea" in starter_labels
    assert "Talk to a human" in [c["label"] for c in chips if c["field"] == "booking_window"]


def test_starter_chip_sent_back_treated_as_free_text(client):
    res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    sid = res.json()["session_id"]
    reply = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "I have an app idea", "chip": {"label": "I have an app idea", "field": "ask", "value": "I have an app idea"}},
    )
    assert reply.status_code == 200
    body = reply.json()
    assert body["route"] in {"discovery", "consult", "fallback"}
    assert "message" in body


def test_human_chip_returns_booking_slots(client):
    res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    sid = res.json()["session_id"]
    reply = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "Talk to a human", "chip": {"label": "Talk to a human", "field": "booking_window", "value": "this_week"}},
    )
    assert reply.status_code == 200
    body = reply.json()
    assert body["route"] == "booking"
    assert any(c.get("type") == "booking" for c in body.get("cards", []))


def test_page_hint_matching(client, monkeypatch):
    from backend.app.tenants.loader import load_tenant
    config = load_tenant("demo")
    hint = PageHint(match="/mobile", service="mobile_app", question="Looks like you're exploring mobile apps. Tell me about your project.")
    monkeypatch.setattr(config.brand, "page_hints", [hint])

    # Path matching /mobile
    res = client.post("/api/v1/sessions", json={"tenant": "demo", "path": "/mobile?ref=twitter#section"})
    assert res.status_code == 200
    data = res.json()
    assert "Looks like you're exploring mobile apps" in data["message"]
    # Only human chip shown when page hint with service matched
    chips = data["chips"]
    assert len(chips) == 1
    assert chips[0]["field"] == "booking_window"

    # Unknown path gives default opener
    res_unknown = client.post("/api/v1/sessions", json={"tenant": "demo", "path": "/pricing"})
    assert res_unknown.status_code == 200
    assert "Tell me what you'd like to build" in res_unknown.json()["message"]
    assert any(c["field"] == "ask" for c in res_unknown.json()["chips"])


def test_public_config_exposes_advisor_fields(client):
    res = client.get("/api/v1/public-config?tenant=demo")
    assert res.status_code == 200
    brand = res.json()["brand"]
    assert brand["advisor_name"] == "Alex"
    assert "AI" in brand["advisor_title"]
    assert "advisor_avatar" in brand
    assert brand["human_label"] == "Talk to a human"
    # Ensure no secret / internal fields exposed
    for secret in ["database", "api_key", "secret", "token"]:
        assert secret not in brand


def test_widget_privacy_static_check():
    widget_path = Path("widget/consultant.js")
    content = widget_path.read_text(encoding="utf-8")
    assert "document.referrer" not in content
    assert "scrollDepth" not in content
    assert "dwellTime" not in content


def test_widget_files_identical():
    w1 = Path("widget/consultant.js").read_bytes()
    w2 = Path("public/widget/consultant.js").read_bytes()
    assert w1 == w2, "widget/consultant.js and public/widget/consultant.js must be byte-identical"


def test_widget_header_textContent_usage():
    content = Path("widget/consultant.js").read_text(encoding="utf-8")
    # Header title should be set via textContent
    assert "titleEl.textContent" in content
