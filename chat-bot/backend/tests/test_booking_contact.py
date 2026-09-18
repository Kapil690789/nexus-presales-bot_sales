import json

from backend.app.agents import orchestrator
from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.tests.test_api import _chip, _discover, _book_first_slot, accept_nda


READY = ProjectBrief(
    service="web_app",
    goal="Ops console so distributors track orders in one place",
    platforms=["web"],
    timeline="1_3_months",
    budget_band="40_80k",
    decision_role="founder_or_exec",
    users="internal",
    integrations=["none"],
)


def _sse(text: str) -> dict:
    cards: list = []
    chips: list = []
    meta: dict = {}
    tokens: list[str] = []
    event = None
    for line in text.splitlines():
        if line.startswith("event:"):
            event = line.split(":", 1)[1].strip()
        elif line.startswith("data:") and event:
            data = json.loads(line.split(":", 1)[1].strip() or "{}")
            if event == "token":
                tokens.append(str(data.get("text") or ""))
            elif event == "cards":
                cards = data.get("cards") or []
            elif event == "chips":
                chips = data.get("chips") or []
            elif event == "meta":
                meta = data
            event = None
    return {"message": "".join(tokens), "cards": cards, "chips": chips, **meta}


def _turn(**kwargs):
    defaults = {
        "config": load_config(),
        "brief": READY.model_copy(deep=True),
        "contact": {},
        "nda_accepted": False,
        "booking": None,
        "user_text": "",
        "chip": None,
        "page_opening": "Building a web product?",
        "extra_questions": [],
        "existing_estimate": {"range_label": "$19,000–$24,000 USD"},
    }
    defaults.update(kwargs)
    return orchestrator.run_turn(**defaults)


def test_continue_contact_asks_email_without_estimate_card() -> None:
    result = _turn(
        user_text="Continue to contact",
        chip={"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
    )
    assert result.stage == "capture"
    assert "email" in result.message.lower()
    assert "$19,000" not in result.message
    assert all(card.get("type") != "estimate" for card in result.cards)


def test_typed_book_a_call_does_not_replay_estimate() -> None:
    result = _turn(user_text="book a call for me")
    assert result.stage == "capture"
    assert "email" in result.message.lower()
    assert "happy to book" in result.message.lower()
    assert all(card.get("type") != "estimate" for card in result.cards)
    assert all(card.get("type") != "booking" for card in result.cards)


def test_email_then_continue_contact_shows_slots_when_nda_accepted() -> None:
    result = _turn(
        contact={"email": "founder@acme.test"},
        nda_accepted=True,
        user_text="Continue to contact",
        chip={"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
    )
    assert result.stage == "booking"
    assert "email" not in result.message.lower() or "work email" not in result.message.lower()
    assert any(card.get("type") == "booking" for card in result.cards)
    booking = next(card for card in result.cards if card.get("type") == "booking")
    assert booking.get("slots") or booking.get("days")
    assert all(card.get("type") != "estimate" for card in result.cards)


def test_continue_contact_with_email_does_not_reask_email() -> None:
    result = _turn(
        contact={"email": "founder@acme.test"},
        nda_accepted=False,
        user_text="Continue to contact",
        chip={"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
    )
    assert result.stage == "capture"
    assert "what work email" not in result.message.lower()
    assert "confidential" in result.message.lower()
    assert all(card.get("type") != "estimate" for card in result.cards)


def test_email_on_capture_advances_to_nda_or_booking() -> None:
    result = _turn(user_text="founder@acme.test")
    assert result.contact.get("email") == "founder@acme.test"
    assert result.stage == "capture"
    assert "confidential" in result.message.lower()
    assert "what work email" not in result.message.lower()
    booked = _turn(
        contact={"email": "founder@acme.test"},
        nda_accepted=True,
        user_text="I accept the confidentiality notice.",
        chip={"field": "nda", "value": True},
    )
    assert booked.stage == "booking"
    assert any(card.get("type") == "booking" for card in booked.cards)


def test_confirmed_slot_handoff_has_label_not_estimate() -> None:
    result = _turn(
        contact={"email": "founder@acme.test"},
        nda_accepted=True,
        booking={
            "window": "this_week",
            "slot_iso": "2026-09-22T05:00:00+00:00",
            "label": "Tue 22 Sep, 10:30",
            "meet_url": "https://meet.devconsult.example/abc",
        },
        user_text="ok",
    )
    assert result.stage == "handoff"
    assert "Tue 22 Sep, 10:30" in result.message
    assert all(card.get("type") != "estimate" for card in result.cards)
    assert any(card.get("type") == "booking_confirm" for card in result.cards)


def test_duplicate_contact_prompt_is_rewritten() -> None:
    first = _turn(
        user_text="Continue to contact",
        chip={"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
    )
    second = _turn(
        user_text="Continue to contact",
        chip={"label": "Continue to contact", "field": "continue_contact", "value": "yes"},
        last_assistant=first.message,
    )
    assert second.message.strip() != first.message.strip()
    assert "email" in second.message.lower()


def test_api_continue_contact_then_email_then_slots(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    contact = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Continue to contact", "chip": _chip("Continue to contact", "continue_contact", "yes")},
    )
    assert contact.status_code == 200
    payload = _sse(contact.text)
    assert payload.get("stage") == "capture"
    assert "email" in payload["message"].lower()
    assert all(card.get("type") != "estimate" for card in payload["cards"])

    typed = client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "book a call for me"},
    )
    assert typed.status_code == 200
    again = _sse(typed.text)
    assert again["message"].strip() != payload["message"].strip()
    assert all(card.get("type") != "estimate" for card in again["cards"])

    email = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"})
    assert email.status_code == 200
    after_email = _sse(email.text)
    assert "what work email" not in after_email["message"].lower()

    nda = accept_nda(client, session_id)
    assert nda.status_code == 200
    body = nda.json()
    assert body["stage"] == "booking"
    assert any(card.get("type") == "booking" for card in body.get("cards") or [])
    assert all(card.get("type") != "estimate" for card in body.get("cards") or [])
    slots = next(card for card in body["cards"] if card["type"] == "booking")
    assert slots.get("slots") or slots.get("days")

    booked = _book_first_slot(client, session_id, window=slots.get("window") or "this_week")
    assert booked.status_code == 200
    done = booked.json()
    assert done["stage"] == "handoff"
    assert done.get("booking", {}).get("slot_iso")
    assert done["booking"]["label"] in done["message"]
    assert all(card.get("type") != "estimate" for card in done.get("cards") or [])
    assert any(card.get("type") == "booking_confirm" for card in done.get("cards") or [])
