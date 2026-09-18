from backend.app.agents import orchestrator
from backend.app.agents.brief import ProjectBrief, brief_ready
from backend.app.agents.chips import DISCOVERY_PROMPTS, chips_for_field
from backend.app.agents.extract import apply_brief_updates, capture_goal_reply, extract_from_text
from backend.app.agents.transcript import render_transcript
from backend.app.config_loader.loader import load_config


def test_extract_does_not_set_goal_from_smalltalk() -> None:
    brief = extract_from_text(ProjectBrief(), "Hello there, how is the weather in Berlin tomorrow?")
    assert brief.goal is None
    assert capture_goal_reply(ProjectBrief(), "hi").goal is None
    assert capture_goal_reply(ProjectBrief(), "thanks!").goal is None


def test_offline_goal_prompt_captures_a_real_answer() -> None:
    brief = ProjectBrief(service="web_app")
    brief = capture_goal_reply(brief, "Ops console for distributors to track orders")
    assert brief.goal and "distributors" in brief.goal


def test_apply_brief_updates_merges_and_rejects_invalid() -> None:
    config = load_config()
    brief = ProjectBrief(service="web_app", platforms=["web"])
    brief = apply_brief_updates(
        brief,
        {
            "goal": "Replace spreadsheets for dispatch",
            "service": "spaceship",
            "budget_band": "a million dollars",
            "timeline": "1_3_months",
            "decision_role": "founder_or_exec",
            "integrations": ["salesforce"],
            "price": 12,
            "unknown": "nope",
        },
        config,
    )
    assert brief.service == "web_app"
    assert brief.goal == "Replace spreadsheets for dispatch"
    assert brief.budget_band is None
    assert brief.timeline == "1_3_months"
    assert brief.decision_role == "founder_or_exec"
    assert "salesforce" in brief.integrations


def test_apply_brief_updates_does_not_blank_existing() -> None:
    config = load_config()
    brief = ProjectBrief(goal="Keep the first corridor", budget_band="40_80k")
    brief = apply_brief_updates(brief, {"goal": "", "budget_band": None, "timeline": "asap"}, config)
    assert brief.goal == "Keep the first corridor"
    assert brief.budget_band == "40_80k"
    assert brief.timeline == "asap"


def test_render_transcript_keeps_newest_turns() -> None:
    messages = [{"role": "user", "content": f"turn {i} " + ("x" * 200)} for i in range(40)]
    text = render_transcript(messages, max_turns=4, max_chars=800)
    assert "turn 39" in text
    assert "turn 0" not in text
    assert text.count("user:") <= 4


def test_llm_prompt_contains_transcript_and_page(monkeypatch) -> None:
    config = load_config()
    captured: dict[str, str] = {}

    def fake_complete_json(system: str, user: str) -> dict:
        captured["system"] = system
        captured["user"] = user
        return {
            "brief_updates": {"goal": "A driver app with live GPS"},
            "ask_field": "platforms",
            "message": "iOS first, or both platforms in v1?",
            "chips": [],
            "stage": "discovery",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(service="mobile_app"),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="We need a driver app with live GPS for our fleet.",
        chip=None,
        page_opening="Planning a mobile product?",
        extra_questions=["iOS, Android, or both?"],
        transcript="assistant: Planning a mobile product?\nuser: We need a driver app with live GPS for our fleet.",
        page_path="/mobile-app-development",
    )
    assert "Conversation so far:" in captured["user"]
    assert "driver app with live GPS" in captured["user"]
    assert "Planning a mobile product?" in captured["user"]
    assert "/mobile-app-development" in captured["user"]
    assert "Still needed before an estimate" in captured["user"]
    assert "brief_updates" in captured["system"]
    assert result.brief.goal and "GPS" in result.brief.goal
    assert result.message == "iOS first, or both platforms in v1?"


def test_ask_field_attaches_only_that_fields_chips(monkeypatch) -> None:
    config = load_config()

    def fake_complete_json(system: str, user: str) -> dict:
        return {
            "brief_updates": {"goal": "Marketplace for independent growers"},
            "ask_field": "budget_band",
            "message": "Which budget band should I estimate against?",
            "chips": [],
            "stage": "discovery",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(service="mobile_app", platforms=["ios"]),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="A two-sided marketplace for growers on iOS.",
        chip=None,
        page_opening="Planning a mobile product?",
        extra_questions=[],
        transcript="user: A two-sided marketplace for growers on iOS.",
        page_path="/mobile-app-development",
    )
    expected = {item["value"] for item in chips_for_field(result.brief, "budget_band")}
    assert result.chips
    assert {chip["field"] for chip in result.chips} == {"budget_band"}
    assert {chip["value"] for chip in result.chips} == expected


def test_invalid_llm_chips_are_dropped(monkeypatch) -> None:
    config = load_config()

    def fake_complete_json(system: str, user: str) -> dict:
        return {
            "brief_updates": {},
            "ask_field": None,
            "message": "Tell me a bit more about the first user.",
            "chips": [
                {"label": "Invented", "field": "budget_band", "value": "unlimited"},
                {"label": "Nope", "field": "not_a_field", "value": "x"},
            ],
            "stage": "discovery",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(service="web_app"),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="Internal ops tooling.",
        chip=None,
        page_opening="Building a web product?",
        extra_questions=[],
    )
    assert result.chips == []


def test_brief_updates_can_estimate_same_turn(monkeypatch) -> None:
    config = load_config()
    calls: list[str] = []

    def fake_complete_json(system: str, user: str) -> dict:
        calls.append(user)
        if "Approved frontend stacks" not in user:
            return {
                "brief_updates": {
                    "goal": "Ops console so distributors track orders in one place",
                    "platforms": ["web"],
                    "timeline": "1_3_months",
                    "budget_band": "40_80k",
                    "decision_role": "founder_or_exec",
                    "users": "internal",
                },
                "ask_field": "company_size",
                "message": "A couple of commercial details left.",
                "chips": [],
                "stage": "discovery",
            }
        label = "$40,000–$50,000 USD"
        marker = '"range_label": "'
        if marker in user:
            label = user.split(marker, 1)[1].split('"', 1)[0]
        return {
            "architecture": {"frontend": ["Next.js"], "backend": ["Node.js + PostgreSQL"], "notes": ["Admin belongs in v1."]},
            "mvp": {"mvp": ["Prove the distributor ops console", "One workflow end to end"], "later": ["Reporting suite"], "rationale": "Cut to the console."},
            "message": f"For this distributor console I'd start on Next.js. Indicative MVP sits around {label}.",
            "chips": [],
            "stage": "estimation",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(service="web_app"),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text=(
            "We're building a web ops console for distributors to track orders. "
            "We want it in the next quarter and the budget is around 60k."
        ),
        chip=None,
        page_opening="Building a web product or SaaS?",
        extra_questions=[],
        page_path="/web-app-development",
    )
    assert len(calls) == 2
    assert "Still needed before an estimate" in calls[0]
    assert "Approved frontend stacks" in calls[1]
    assert brief_ready(result.brief)
    assert result.estimate
    assert result.stage == "estimation"
    assert "$" in result.message
    assert DISCOVERY_PROMPTS["company_size"] not in result.message
    assert result.brief.goal and "distributors" in result.brief.goal
    assert any(card.get("type") == "estimate" for card in result.cards)


def test_llm_does_not_hijack_to_company_size_form(monkeypatch) -> None:
    config = load_config()

    def fake_complete_json(system: str, user: str) -> dict:
        return {
            "brief_updates": {},
            "ask_field": "users",
            "message": "Who is the first user of this console?",
            "chips": [{"label": "Internal team", "field": "users", "value": "internal"}],
            "stage": "discovery",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    brief = ProjectBrief(
        service="web_app",
        goal="Ops console for distributors",
        platforms=["web"],
        timeline="1_3_months",
        budget_band="40_80k",
    )
    result = orchestrator.run_turn(
        config=config,
        brief=brief,
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="I'm the founder",
        chip={"label": "Founder / exec", "field": "decision_role", "value": "founder_or_exec"},
        page_opening="Building a web product?",
        extra_questions=[],
    )
    assert result.message != DISCOVERY_PROMPTS["company_size"]
    assert "founder" in (result.brief.decision_role or "")


SCREENSHOT_MESSAGE = (
    "i want you to develop a website for me it will be a normal webpage to show some "
    "general info about me. can you give me a time estimate for that. my buget is $50k."
)


def test_personal_webpage_is_out_of_scope() -> None:
    brief = extract_from_text(ProjectBrief(), SCREENSHOT_MESSAGE)
    assert brief.out_of_scope == "pure_marketing_site"
    assert brief.budget_band == "40_80k"
    assert brief.goal
    config = load_config()
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text=SCREENSHOT_MESSAGE,
        chip=None,
        page_opening="What are you looking to build?",
        extra_questions=[],
    )
    assert result.stage == "disqualified"
    assert result.brief.out_of_scope == "pure_marketing_site"
    assert DISCOVERY_PROMPTS["service"] not in result.message
    assert {chip["label"] for chip in result.chips} == {"Book a call", "Thank you"}
    assert "book a call" in result.message.lower()
    assert "thank you" in result.message.lower()
    assert config.agency.out_of_scope_close.strip() in result.message or "outside" in result.message.lower()


def test_custom_web_ops_text_does_not_reask_service() -> None:
    text = "Web ops console for distributors, budget around 50k"
    brief = extract_from_text(ProjectBrief(), text)
    assert brief.service == "web_app"
    assert brief.budget_band == "40_80k"
    assert brief.goal
    result = orchestrator.run_turn(
        config=load_config(),
        brief=ProjectBrief(),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text=text,
        chip=None,
        page_opening="Building a web product?",
        extra_questions=[],
    )
    assert result.brief.service == "web_app"
    assert result.stage != "disqualified"
    assert DISCOVERY_PROMPTS["service"] not in result.message
    assert result.brief.goal


def test_mocked_llm_applies_custom_web_app_brief(monkeypatch) -> None:
    config = load_config()

    def fake_complete_json(system: str, user: str) -> dict:
        return {
            "brief_updates": {
                "service": "web_app",
                "goal": "Distributor ops console",
                "platforms": ["web"],
            },
            "ask_field": "users",
            "message": "Got it — an ops console for distributors. Who is the first user?",
            "chips": [{"label": "Internal team", "field": "users", "value": "internal"}],
            "stage": "discovery",
        }

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    result = orchestrator.run_turn(
        config=config,
        brief=ProjectBrief(),
        contact={},
        nda_accepted=False,
        booking=None,
        user_text="We need a custom web product so distributors can track orders in one place.",
        chip=None,
        page_opening="Building a web product?",
        extra_questions=[],
    )
    assert result.brief.service == "web_app"
    assert result.brief.goal and "distributor" in result.brief.goal.lower()
    assert DISCOVERY_PROMPTS["service"] not in result.message
    assert "ops console" in result.message.lower() or "user" in result.message.lower()


def _oos_turn(**kwargs):
    defaults = {
        "config": load_config(),
        "brief": ProjectBrief(),
        "contact": {},
        "nda_accepted": False,
        "booking": None,
        "user_text": "",
        "chip": None,
        "page_opening": "What are you looking to build?",
        "extra_questions": [],
    }
    defaults.update(kwargs)
    return orchestrator.run_turn(**defaults)


def test_out_of_scope_can_book_a_call() -> None:
    closed = _oos_turn(user_text=SCREENSHOT_MESSAGE)
    result = _oos_turn(
        brief=closed.brief,
        user_text="Book a call",
        chip={"label": "Book a call", "field": "booking_window", "value": "this_week"},
    )
    assert result.stage == "booking"
    assert any(card.get("type") == "booking" for card in result.cards)


def test_out_of_scope_thank_you_chip_closes() -> None:
    config = load_config()
    closed = _oos_turn(user_text=SCREENSHOT_MESSAGE, config=config)
    result = _oos_turn(
        config=config,
        brief=closed.brief,
        user_text="Thank you",
        chip={"label": "Thank you", "field": "close_out", "value": "thanks"},
    )
    assert result.stage == "disqualified"
    assert result.chips == []
    assert config.agency.out_of_scope_thanks.strip() in result.message


def test_out_of_scope_typed_thanks_closes() -> None:
    config = load_config()
    closed = _oos_turn(user_text=SCREENSHOT_MESSAGE, config=config)
    result = _oos_turn(config=config, brief=closed.brief, user_text="thank you")
    assert result.stage == "disqualified"
    assert result.chips == []
    assert config.agency.out_of_scope_thanks.strip() in result.message
