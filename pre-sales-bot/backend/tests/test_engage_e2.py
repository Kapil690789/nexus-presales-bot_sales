import pytest
from pydantic import ValidationError
from fastapi.testclient import TestClient

from backend.app.main import app
from backend.app.agents.brief import ProjectBrief
from backend.app.agents.discovery_synth import (
    ack_from_brief,
    question_variant_for,
    validate_discovery_reply,
    deterministic_discovery_prompt,
    synthesize_discovery_prompt,
)
from backend.app.core.guard import sanitize_price_leaks
from backend.app.tenants.loader import load_tenant
from backend.app.tenants.schema import TenantConfig, VoiceConfig, BrandConfig

client = TestClient(app)


def test_same_session_and_field_give_same_variant():
    config = load_tenant("demo")
    voice = config.voice

    brief1 = ProjectBrief(platforms=["ios", "android"])
    brief2 = ProjectBrief(platforms=["ios", "android"])

    ack1 = ack_from_brief(brief1, ["platforms"], voice, session_id="fixed_session_123", attempt=0)
    ack2 = ack_from_brief(brief2, ["platforms"], voice, session_id="fixed_session_123", attempt=0)

    assert ack1 is not None
    assert ack1 == ack2


def test_no_ack_repeats_within_3_turns():
    config = load_tenant("demo")
    voice = config.voice

    brief = ProjectBrief(platforms=["ios", "android"])
    acks = []
    for turn in range(3):
        ack = ack_from_brief(brief, ["platforms"], voice, session_id="session_abc", attempt=turn)
        assert ack is not None
        acks.append(ack)

    # In voice.yaml for demo, platforms has 2 templates. Over 3 turns with recent_acks rotation,
    # the templates rotate so adjacent turns do not repeat the exact same ack id.
    assert len(brief.recent_acks) == 3
    assert acks[0] != acks[1]
    assert acks[1] != acks[2]


def test_ack_never_mentions_value_not_in_brief():
    config = load_tenant("demo")
    voice = config.voice

    # Brief has ONLY platforms; service, goal, features, timeline are None
    brief = ProjectBrief(platforms=["web"])
    ack = ack_from_brief(brief, ["platforms"], voice, session_id="sess_1")
    assert ack is not None
    assert "web" in ack.lower()
    assert "ios" not in ack.lower()
    assert "android" not in ack.lower()
    assert "week" not in ack.lower()
    assert "month" not in ack.lower()

    # Brief has ONLY features; platforms and goal are None
    brief2 = ProjectBrief(features=["user login", "activity feed"])
    ack2 = ack_from_brief(brief2, ["features"], voice, session_id="sess_2")
    assert ack2 is not None
    assert "user login" in ack2.lower()
    assert "web" not in ack2.lower()
    assert "ios" not in ack2.lower()


def test_scope_coach_trigger():
    config = load_tenant("demo")
    voice = config.voice

    # 5 features trigger scope coach
    five_features = ProjectBrief(features=["auth", "calendar", "push alerts", "payments", "analytics"])
    ack_5 = ack_from_brief(five_features, ["features"], voice, session_id="sess_5")
    assert ack_5 == voice.scope_coach
    assert "Core and Later" in ack_5

    # 3 features do NOT trigger scope coach
    three_features = ProjectBrief(features=["auth", "calendar", "push alerts"])
    ack_3 = ack_from_brief(three_features, ["features"], voice, session_id="sess_3")
    assert ack_3 != voice.scope_coach
    assert "auth, calendar, push alerts" in ack_3


def test_banned_phrases_never_appear_in_40_simulated_turns():
    config = load_tenant("demo")
    voice = config.voice
    banned = [p.lower() for p in voice.banned_phrases]

    fields = ["service", "goal", "platforms", "features", "timeline", "budget_band"]
    for i in range(40):
        field = fields[i % len(fields)]
        brief = ProjectBrief(
            service="web_app",
            goal="Operations portal",
            platforms=["web"],
            features=["auth", "billing"],
            timeline="1_3_months",
        )
        msg = deterministic_discovery_prompt(
            config,
            brief,
            field,
            changed_fields=[field],
            session_id=f"sess_sim_{i}",
            attempt=i % 2,
        )
        msg_lowered = msg.lower()
        for phrase in banned:
            assert phrase not in msg_lowered, f"Banned phrase '{phrase}' found in turn {i}: {msg}"


def test_message_over_320_chars_replaced_by_deterministic():
    config = load_tenant("demo")
    voice = config.voice

    fallback = "This is a safe fallback prompt."
    long_reply = "A" * 325

    validated = validate_discovery_reply(long_reply, voice, fallback)
    assert validated == fallback


def test_typo_in_voice_yaml_fails_loading():
    # 1. Unknown top-level key fails loading (extra="forbid")
    with pytest.raises(ValidationError):
        VoiceConfig.model_validate({"unknown_top_level_key": "invalid"})

    # 2. Unknown placeholder in ack template fails loading
    with pytest.raises(ValidationError):
        VoiceConfig.model_validate({
            "acks": {
                "goal": ["A {invalid_placeholder} for {goal_short}."]
            }
        })

    # 3. Question variant with currency symbols fails loading
    with pytest.raises(ValidationError):
        VoiceConfig.model_validate({
            "questions": {
                "service": [
                    "What would you like to build for $20,000?",
                    "What type of product are you building?"
                ]
            }
        })

    # 4. Question variant with digits + weeks fails loading
    with pytest.raises(ValidationError):
        VoiceConfig.model_validate({
            "questions": {
                "timeline": [
                    "Can you launch in 6 weeks?",
                    "What is your target launch milestone?"
                ]
            }
        })

    # 5. Question variant with >30 words fails loading
    long_question = " ".join(["word"] * 31)
    with pytest.raises(ValidationError):
        VoiceConfig.model_validate({
            "questions": {
                "service": [
                    long_question,
                    "What type of product are you building?"
                ]
            }
        })


def test_tenant_without_voice_yaml_still_works():
    # Fresh default VoiceConfig without voice.yaml
    default_voice = VoiceConfig()
    assert default_voice.max_chars == 320
    assert default_voice.emoji_max == 1

    # Fake tenant config without custom voice file
    brand = BrandConfig(name="Acme", slug="acme", primary="#123456", logo_text="Acme")
    tenant_cfg = TenantConfig(brand=brand)
    assert tenant_cfg.voice is not None
    assert tenant_cfg.voice.max_chars == 320

    # synthesize_discovery_prompt works with default voice config
    brief = ProjectBrief()
    prompt = synthesize_discovery_prompt(tenant_cfg, brief, "service", session_id="s1")
    assert prompt != ""
    assert "?" in prompt


def test_no_emoji_in_price_text():
    # Price guard sanitization must not add any emoji
    guarded = sanitize_price_leaks("This custom mobile application will cost $4,500 total.")
    emojis = [c for c in guarded if ord(c) > 0x1F000]
    assert len(emojis) == 0

    # Indicative estimate formatting must have no emoji
    config = load_tenant("demo")
    from backend.app.engines.pricing import estimate_project
    brief = ProjectBrief(
        service="web_app",
        platforms=["web"],
        timeline="1_3_months",
        features=["auth", "billing"],
    )
    est = estimate_project(brief, config.pricing)
    assert est is not None
    range_str = est["range_label"]
    emojis_range = [c for c in range_str if ord(c) > 0x1F000]
    assert len(emojis_range) == 0


def test_consultative_6_turn_scripted_dialogue():
    """Run 6 consultative scripted turns through the test client and inspect consultative transitions."""
    s = client.post("/api/v1/sessions", json={"tenant": "demo"}).json()
    sid = s["session_id"]

    turns_input = [
        {"content": "Web app", "chip": {"label": "Web app", "field": "service", "value": "web_app"}},
        {"content": "A client portal for real estate tax compliance"},
        {"content": "Web", "chip": {"label": "Web", "field": "platforms", "value": ["web"]}},
        {"content": "Client login, document upload, tax deadline reminders"},
        {"content": "1–3 months", "chip": {"label": "1–3 months", "field": "timeline", "value": "1_3_months"}},
        {"content": "$40–80k", "chip": {"label": "$40–80k", "field": "budget_band", "value": "40_80k"}},
    ]

    transcript = []
    for i, t in enumerate(turns_input):
        res = client.post(f"/api/v1/sessions/{sid}/messages", json=t)
        assert res.status_code == 200
        data = res.json()
        transcript.append({
            "turn": i + 1,
            "user": t["content"],
            "route": data["route"],
            "message": data["message"],
        })

    # Validate consultative flow
    assert len(transcript) == 6
    # Turn 2 acknowledged service and asked goal
    assert "web" in transcript[0]["message"].lower() or "problem" in transcript[0]["message"].lower() or "?" in transcript[0]["message"]
    # Turn 6 reached estimate or asking role/size
    assert transcript[-1]["route"] in ("estimate", "discovery")
