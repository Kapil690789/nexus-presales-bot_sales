from __future__ import annotations

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.extractor import apply_extracted_slots, extract_slots


def test_extractor_parses_natural_language(monkeypatch):
    fake_json = {
        "service": "mobile_app",
        "platforms": ["ios", "android"],
        "goal": "Clinic appointment booking application",
        "budget_band": "40_80k",
        "timeline": "1_3_months",
        "is_question": False,
        "uncertain": False,
    }
    monkeypatch.setattr("backend.app.agents.extractor.complete_json", lambda _sys, _user: fake_json)
    monkeypatch.setattr("backend.app.agents.extractor.llm_available", lambda: True)

    extracted = extract_slots("I want an iOS and Android app for clinic appointments around 50k in 2 months")
    assert extracted["service"] == "mobile_app"
    assert "ios" in extracted["platforms"]
    assert "android" in extracted["platforms"]

    brief = ProjectBrief()
    applied = apply_extracted_slots(brief, extracted)
    assert applied is True
    assert brief.service == "mobile_app"
    assert brief.platforms == ["ios", "android"]
    assert brief.budget_band == "40_80k"
    assert brief.timeline == "1_3_months"


def test_extractor_handles_uncertainty(monkeypatch):
    fake_json = {
        "service": None,
        "platforms": None,
        "goal": None,
        "budget_band": None,
        "timeline": None,
        "is_question": False,
        "uncertain": True,
    }
    monkeypatch.setattr("backend.app.agents.extractor.complete_json", lambda _sys, _user: fake_json)
    monkeypatch.setattr("backend.app.agents.extractor.llm_available", lambda: True)

    brief = ProjectBrief(service="mobile_app")
    extracted = extract_slots("I am not sure yet, give me an estimate", pending_field="budget_band", brief=brief)
    applied = apply_extracted_slots(brief, extracted, pending_field="budget_band")
    assert applied is True
    assert brief.budget_band == "15_40k"


def test_extractor_handles_out_of_scope(monkeypatch):
    fake_json = {
        "service": "out_of_scope",
        "is_question": False,
        "uncertain": False,
    }
    monkeypatch.setattr("backend.app.agents.extractor.complete_json", lambda _sys, _user: fake_json)
    monkeypatch.setattr("backend.app.agents.extractor.llm_available", lambda: True)

    brief = ProjectBrief()
    extracted = extract_slots("Can you do my crypto web3 homework?")
    applied = apply_extracted_slots(brief, extracted)
    assert applied is True
    assert brief.out_of_scope is not None
