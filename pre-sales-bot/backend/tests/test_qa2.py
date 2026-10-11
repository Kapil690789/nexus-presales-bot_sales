import json
import re
from pathlib import Path

import pytest
from fastapi.testclient import TestClient

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.router import _platforms, recap_line_from_brief, run_turn
from backend.app.core.guard import sanitize_price_leaks
from backend.app.main import app
from backend.app.models.entities import SessionRow
from backend.app.screening.slots import (
    budget_label,
    display_platforms,
    goal_short,
    service_article,
    service_label_clean,
    timeline_label,
)
from backend.app.tenants.loader import load_tenant


@pytest.fixture
def config():
    return load_tenant("demo")


@pytest.fixture
def client():
    return TestClient(app)


def test_display_platforms_table():
    table = [
        (None, ""),
        ([], ""),
        (["ios"], "iOS"),
        (["android"], "Android"),
        (["ios", "android"], "iOS and Android"),
        (["both"], "iOS and Android"),
        (["web"], "web"),
        (["web", "ios"], "web and iOS"),
        (["web", "android"], "web and Android"),
        (["web", "ios", "android"], "web, iOS and Android"),
    ]
    for inp, expected in table:
        res = display_platforms(inp)
        assert res == expected
        assert "ios" not in res
        assert "android" not in res


def test_goal_short_10_sentences():
    cases = [
        (
            "I am building a sports clinic booking application for direct patients",
            "sports clinic booking application for direct patients",
        ),
        (
            "We are building a marketplace for local farmers and",
            "marketplace for local farmers",
        ),
        (
            "I'm looking to build an internal analytics dashboard for support",
            "internal analytics dashboard for support",
        ),
        (
            "We need to build a real-time dispatch system for urban deliveries and logistics",
            "real-time dispatch system for urban deliveries and logistics",
        ),
        (
            "Planning to build patient booking with",
            "patient booking",
        ),
        (
            "a mobile banking app for students",
            "mobile banking app for students",
        ),
        (
            "to build an AI document parser",
            "AI document parser",
        ),
        (
            "I am",
            None,
        ),
        (
            "direct cha:",
            "direct cha",
        ),
        (
            "We want a cross-platform fitness app for workouts and",
            "cross-platform fitness app for workouts",
        ),
    ]
    for inp, expected in cases:
        res = goal_short(inp)
        assert res == expected
        if res is not None:
            # Word boundary check - never ends on fragment
            last_word = res.split()[-1].lower()
            assert last_word not in {"and", "for", "to", "of", "with", "in", "on", "the", "a"}
            assert not res.endswith(":")


def test_service_article_and_clean(config):
    in_scope = config.services.in_scope if config.services else None
    assert service_article("mobile app") == "a"
    assert service_article("ai product") == "an"
    assert service_article("enterprise platform") == "an"
    assert service_article("web application") == "a"

    assert service_label_clean("mobile_app", in_scope) == "mobile app"
    assert service_label_clean("web_app", in_scope) == "web application"
    assert service_label_clean("ai_product", in_scope) == "ai product"
    assert service_label_clean("ui_ux", in_scope) == "ui/ux design"


def test_timeline_and_budget_labels():
    t_table = [
        ("asap", "as soon as possible"),
        ("1_3_months", "1 to 3 months"),
        ("3_6_months", "3 to 6 months"),
        ("flexible", "flexible timing"),
    ]
    for inp, exp in t_table:
        assert timeline_label(inp) == exp

    b_table = [
        ("under_15k", "under $15k"),
        ("15_40k", "$15k to $40k"),
        ("40_80k", "$40k to $80k"),
        ("80k_plus", "$80k or more"),
        ("exploring", "still exploring"),
    ]
    for inp, exp in b_table:
        assert budget_label(inp) == exp


def test_recap_with_0_to_6_features(config):
    for n in range(7):
        features = [f"feat_{i}" for i in range(1, n + 1)] if n > 0 else []
        brief = ProjectBrief(
            service="mobile_app",
            goal="Sports clinic booking application for direct patients",
            platforms=["ios", "android"],
            features=features,
            timeline="1_3_months",
            budget_band="15_40k",
            decision_role="founder_or_exec",
        )
        recap = recap_line_from_brief(config, brief)
        assert "Here's what I understood:" in recap
        assert "a mobile app for Sports clinic booking application for direct patients" in recap
        assert "on iOS and Android" in recap
        assert "aiming for 1 to 3 months with a budget of $15k to $40k" in recap

        if n == 0:
            assert "feat_" not in recap
        elif n == 1:
            assert "with feat_1" in recap
        elif n == 4:
            assert "with feat_1, feat_2, feat_3, feat_4" in recap
        elif n == 5:
            assert "with feat_1, feat_2, feat_3, feat_4, and 1 more" in recap
        elif n == 6:
            assert "with feat_1, feat_2, feat_3, feat_4, and 2 more" in recap

        for p in ["core features", "near-term target", "medium-term target", "growth tier", "scale tier"]:
            assert p not in recap


def test_no_placeholder_words_anywhere_in_backend_app():
    backend_app_dir = Path(__file__).resolve().parent.parent / "app"
    py_files = list(backend_app_dir.rglob("*.py"))
    assert len(py_files) > 0

    placeholders = [
        "core features",
        "near-term target",
        "medium-term target",
        "growth tier",
        "scale tier",
    ]
    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8").lower()
        for p in placeholders:
            assert p not in content, f"Placeholder phrase '{p}' found in {py_file}"


def test_no_problem_anywhere_in_backend_app():
    backend_app_dir = Path(__file__).resolve().parent.parent / "app"
    py_files = list(backend_app_dir.rglob("*.py"))
    assert len(py_files) > 0

    for py_file in py_files:
        content = py_file.read_text(encoding="utf-8").lower()
        assert "no problem" not in content, f"'No problem' found in {py_file}"


def test_web_and_mobile_platform_parsing():
    assert _platforms("Web and mobile") == ["web", "ios", "android"]
    assert _platforms("Mobile and web") == ["web", "ios", "android"]
    assert _platforms("web and mobile apps") == ["web", "ios", "android"]
    assert _platforms("iOS and Android") == ["ios", "android"]
    assert _platforms("iOS") == ["ios"]
    assert _platforms("Android") == ["android"]
    assert _platforms("Web") == ["web"]


def test_mobile_app_with_web_only_platforms_is_caught(client):
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]
    client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "service", "value": "mobile_app", "label": "Mobile app"}})
    client.post(f"/api/v1/sessions/{sid}/messages", json={"content": "Sports tracker app"})
    # Visitor selects web-only platform for mobile_app
    res = client.post(f"/api/v1/sessions/{sid}/messages", json={"chip": {"field": "platforms", "value": ["web"], "label": "Web"}}).json()
    assert "You mentioned a mobile app earlier, but web as the platform" in res["message"]
    assert any("mobile" in c["label"].lower() for c in res["chips"])
    assert any("web" in c["label"].lower() for c in res["chips"])


def test_budget_label_survives_price_guard():
    raw_15_40 = "Here's what I understood: a mobile app, aiming for 1 to 3 months with a budget of $15k to $40k."
    sanitized = sanitize_price_leaks(raw_15_40, visitor_budget="15_40k")
    assert "$15k to $40k" in sanitized
    assert "Exact pricing depends" not in sanitized

    raw_40_80 = "Here's what I understood: a web application, aiming for 3 to 6 months with a budget of $40k to $80k."
    sanitized_80 = sanitize_price_leaks(raw_40_80, visitor_budget="40_80k")
    assert "$40k to $80k" in sanitized_80
    assert "Exact pricing depends" not in sanitized_80


def test_out_of_order_s3_and_s8_scripts_reach_estimate(client):
    # S3 script: out-of-order free-text answers
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    turns = [
        {"chip": {"field": "ask", "value": "I have an app idea", "label": "I have an app idea"}},
        {"content": "A marketplace for local farmers"},
        {"content": "Web and mobile"},
        {"content": "Produce catalog, Stripe checkout, farmer payouts, direct chat"},
        {"content": "3 to 6 months"},
        {"content": "$40k to $80k"},
        {"content": "Product lead"},
    ]

    last_data = {}
    bot_messages = []
    for t in turns:
        res = client.post(f"/api/v1/sessions/{sid}/messages", json=t)
        assert res.status_code == 200
        last_data = res.json()
        bot_messages.append(last_data["message"])

    assert last_data["route"] == "estimate"
    assert any(c.get("type") == "estimate" for c in last_data.get("cards", []))

    # Assert no question repeated verbatim in consecutive turns
    for i in range(len(bot_messages) - 1):
        assert bot_messages[i] != bot_messages[i + 1]
