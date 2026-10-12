#!/usr/bin/env python3
"""scripts/demo_transcripts.py - Runs demo scenarios S1 to S10 through the API and writes docs/DEMO_TRANSCRIPTS.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import statistics
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.core.llm import get_turn_llm_calls, reset_turn_llm_calls
from backend.app.core.settings import get_settings
from backend.app.engines.pricing import estimate_project
from backend.app.main import app
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import SessionRow
from backend.app.tenants.loader import load_tenant

BANNED_PHRASES = ["Love it", "Great idea", "Smart approach", "Awesome", "Exciting", "v1"]
PLACEHOLDERS = ["core features", "near-term target", "medium-term target", "growth tier", "scale tier"]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")

EXPECTED_BRIEFS = {
    "S1": {
        "platforms": ["ios", "android"],
        "features": ["login", "calendar booking", "push notifications"],
        "goal_contains": "sports clinic booking",
        "timeline": "1_3_months",
        "budget_band": "15_40k",
        "budget_text_contains": "$25k to $35k",
    },
    "S2": {
        "service": "mobile_app",
        "goal_contains": "field service",
        "platforms": ["ios", "android"],
        "features": ["offline data collection", "barcode scanning", "gps tracking"],
        "timeline": "1_3_months",
        "budget_band": "40_80k",
    },
    "S3": {
        "goal_contains": "marketplace for local farmers",
        "features": ["produce catalog", "stripe checkout", "farmer payouts", "direct chat"],
        "platforms": ["web", "ios", "android"],
        "timeline": "3_6_months",
        "budget_band": "40_80k",
    },
    "S4": {
        "service": "web_app",
        "goal_contains": "clinic management",
        "features_min_count": 7,
    },
    "S5": {
        "service": "mobile_app",
        "platforms": ["ios", "android"],
        "timeline": "1_3_months",
        "budget_band": "15_40k",
    },
    "S6": {
        "goal_contains": "fitness coaching",
        "features_contain": ["workout", "push notifications"],
        "platforms": ["ios", "android"],
    },
    "S7": {
        "service": "mobile_app",
        "goal_contains": "sports clinic booking",
        "platforms": ["ios", "android"],
        "features": ["user login & profiles"],
        "timeline": "1_3_months",
        "budget_band": "15_40k",
    },
    "S8": {
        "goal_contains": "marketplace for local farmers",
        "features": ["produce catalog", "stripe checkout", "farmer payouts", "direct chat"],
        "platforms": ["web", "ios", "android"],
        "timeline": "3_6_months",
        "budget_band": "40_80k",
    },
    "S9": {
        "service": "mobile_app",
        "budget_band": "40_80k",
        "budget_text_contains": "$40k to $80k",
        "platforms": ["ios", "android"],
        "timeline": "1_3_months",
        "decision_role": "founder_or_exec",
    },
    "S10": {
        "service": "mobile_app",
        "goal_contains": "barbers",
        "platforms": ["web", "ios", "android"],
        "features_min_count": 5,
        "timeline": "1_3_months",
        "budget_band": "15_40k",
        "decision_role": "founder_or_exec",
    },
}


def count_sentences(text: str) -> int:
    if not text.strip():
        return 0
    lines = [l.strip() for l in text.split("\n") if l.strip()]
    total = 0
    for line in lines:
        parts = [p.strip() for p in SENTENCE_SPLIT.split(line) if p.strip()]
        total += len(parts)
    return max(1, total)


def has_standalone_ai(text: str) -> bool:
    return bool(re.search(r"\bAI\b", text))


def check_banned_phrases(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for bp in BANNED_PHRASES:
        if re.search(r"\b" + re.escape(bp.lower()) + r"\b", lowered):
            found.append(bp)
    return found


def check_placeholders(text: str) -> list[str]:
    found = []
    lowered = text.lower()
    for p in PLACEHOLDERS:
        if p in lowered:
            found.append(p)
    return found


def check_platform_casing(text: str) -> list[str]:
    bad = []
    if re.search(r"\bios\b", text):
        bad.append("lowercase 'ios'")
    if re.search(r"\bandroid\b", text):
        bad.append("lowercase 'android'")
    return bad


def check_midword_cut(text: str) -> list[str]:
    bad = []
    if re.search(r"\b(cha|direct|appli|devel):\s*(that gives me|clear priority)", text, re.IGNORECASE):
        bad.append("mid-word truncation before punctuation")
    if re.search(r"\bagre\b", text, re.IGNORECASE):
        bad.append("mid-word truncation 'agre'")
    return bad


def check_banned_strings_qa3(text: str, has_estimate: bool) -> list[str]:
    bad = []
    if "for the Core flow" in text:
        bad.append("placeholder 'for the Core flow'")
    if re.search(r"\bno problem\b", text, re.IGNORECASE):
        bad.append("banned 'No problem'")
    if not has_estimate and "indicative range above" in text.lower():
        bad.append("'indicative range above' before estimate exists")
    if re.search(r"\byou mentioned (?:a )?web app earlier\b", text, re.IGNORECASE):
        bad.append("'You mentioned' without explicit source")
    return bad


def check_recap_repetitions(recap_text: str) -> list[str]:
    bad = []
    lowered = recap_text.lower()
    if len(re.findall(r"\bios\b", lowered)) > 1:
        bad.append("repeated platform 'iOS'")
    if len(re.findall(r"\bandroid\b", lowered)) > 1:
        bad.append("repeated platform 'Android'")
    if re.search(r"\bapp\s+for\s+application\b", lowered):
        bad.append("repeated 'app for application'")
    if re.search(r"\bmobile\s+app\s+for\s+mobile\s+app\b", lowered):
        bad.append("repeated 'mobile app for mobile app'")
    match_dup = re.search(r"\b([a-zA-Z]{4,})\s+\1\b", lowered)
    if match_dup and match_dup.group(1) not in {"that"}:
        bad.append(f"repeated consecutive word '{match_dup.group(1)}'")
    return bad


def check_brief_matches_expected(scenario_id: str, brief: dict | None) -> tuple[bool, str]:
    if not brief:
        return False, "Brief missing"
    exp = EXPECTED_BRIEFS.get(scenario_id)
    if not exp:
        return True, ""

    if "service" in exp and brief.get("service") != exp["service"]:
        return False, f"service exp {exp['service']} got {brief.get('service')}"
    if "goal_contains" in exp:
        g = (brief.get("goal") or "").lower()
        if exp["goal_contains"].lower() not in g:
            return False, f"goal exp contain {exp['goal_contains']!r} got {brief.get('goal')!r}"
    if "platforms" in exp:
        b_p = set(brief.get("platforms") or [])
        e_p = set(exp["platforms"])
        if b_p != e_p:
            return False, f"platforms exp {exp['platforms']} got {brief.get('platforms')}"
    if "features" in exp:
        b_f = [str(f).lower() for f in (brief.get("features") or [])]
        for ef in exp["features"]:
            if not any(ef.lower() in f for f in b_f):
                return False, f"feature {ef!r} not in {brief.get('features')}"
    if "features_contain" in exp:
        b_blob = " ".join([str(f).lower() for f in (brief.get("features") or [])])
        for ef in exp["features_contain"]:
            if ef.lower() not in b_blob:
                return False, f"feature cue {ef!r} not in {brief.get('features')}"
    if "features_min_count" in exp:
        cnt = len(brief.get("features") or [])
        if cnt < exp["features_min_count"]:
            return False, f"features count exp >= {exp['features_min_count']} got {cnt}"
    if "timeline" in exp and brief.get("timeline") != exp["timeline"]:
        return False, f"timeline exp {exp['timeline']} got {brief.get('timeline')}"
    if "budget_band" in exp and brief.get("budget_band") != exp["budget_band"]:
        return False, f"budget_band exp {exp['budget_band']} got {brief.get('budget_band')}"
    if "budget_text_contains" in exp:
        bt = (brief.get("budget_text") or "").lower()
        if exp["budget_text_contains"].lower() not in bt:
            return False, f"budget_text exp contain {exp['budget_text_contains']!r} got {brief.get('budget_text')!r}"
    if "decision_role" in exp and brief.get("decision_role") != exp["decision_role"]:
        return False, f"decision_role exp {exp['decision_role']} got {brief.get('decision_role')}"
    return True, ""


def check_recap_exact_slots(scenario_id: str, recap_text: str, brief: dict | None) -> tuple[bool, str]:
    if not recap_text:
        return False, "No recap line found"
    exp = EXPECTED_BRIEFS.get(scenario_id, {})
    lowered = recap_text.lower()

    if "Platforms:" not in recap_text:
        return False, "Recap missing Platforms:"
    if "Timeline:" not in recap_text and "timeline" not in lowered:
        return False, "Recap missing Timeline:"
    if "Budget:" not in recap_text:
        return False, "Recap missing Budget:"

    if "platforms" in exp:
        for p in exp["platforms"]:
            if p.lower() not in lowered:
                return False, f"platform {p} missing in recap"

    if exp.get("budget_text_contains"):
        if exp["budget_text_contains"].lower() not in lowered:
            return False, f"budget text {exp['budget_text_contains']} missing in recap"

    return True, ""


def extract_question(text: str) -> str:
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if "?" in sent:
            return sent.strip()
    return ""


def run_scenario(client: TestClient, scenario_id: str, title: str, turns: list[dict | str], is_live: bool = False) -> dict:
    reset_turn_llm_calls()
    t0 = time.perf_counter()
    init_res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    init_ms = (time.perf_counter() - t0) * 1000.0
    init_calls = get_turn_llm_calls()
    init_data = init_res.json()
    sid = init_data["session_id"]

    transcript_turns = []
    opener_msg = init_data.get("message", "")
    opener_chips = [c.get("label") for c in init_data.get("chips", [])]
    opener_cards = [c.get("type") for c in init_data.get("cards", [])]

    opener_turn = {
        "turn": 0,
        "visitor": "(Session Start)",
        "bot_message": opener_msg,
        "chips": opener_chips,
        "cards": opener_cards,
        "route": init_data.get("route", "opener"),
        "ms": round(init_ms, 1),
        "llm_calls": len(init_calls),
        "call_details": init_calls,
    }
    transcript_turns.append(opener_turn)

    recent_acks = []
    ack_repeats_found = 0
    banned_found = []
    placeholders_found = []
    casing_issues_found = []
    midword_cuts_found = []
    banned_strings_found = []
    recap_repetitions_found = []
    long_messages = []
    consecutive_bot_duplicates = 0
    objection_route_invalid = 0
    guard_before_estimate_found = 0
    bot_questions_count = 0
    turns_to_estimate = None
    final_brief = None
    estimate_card = None
    estimate_card_count = 0
    shape_cards_count = 0
    verbatim_repeats = 0
    estimate_split_valid = True
    full_recap_text = ""

    opener_has_ai = has_standalone_ai(opener_msg)
    opener_chips_valid = len(opener_chips) >= 5 and "Talk to a human" in opener_chips
    banned_in_opener = check_banned_phrases(opener_msg)
    if banned_in_opener:
        banned_found.extend(banned_in_opener)

    last_bot_msg = opener_msg
    turn_latencies_ms = []
    turn_llm_call_counts = []

    for idx, turn_input in enumerate(turns, start=1):
        is_obj_turn = False
        if isinstance(turn_input, str):
            payload = {"content": turn_input}
            visitor_label = turn_input
            if "guarantee 4 weeks" in turn_input.lower():
                is_obj_turn = True
        elif isinstance(turn_input, dict):
            payload = turn_input
            visitor_label = turn_input.get("content") or turn_input.get("chip", {}).get("label") or json.dumps(turn_input)
            is_obj_turn = bool(turn_input.get("is_objection"))
        else:
            payload = {"content": str(turn_input)}
            visitor_label = str(turn_input)

        reset_turn_llm_calls()
        t0 = time.perf_counter()
        res = client.post(f"/api/v1/sessions/{sid}/messages", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        calls = get_turn_llm_calls()
        data = res.json()

        turn_latencies_ms.append(elapsed_ms)
        turn_llm_call_counts.append(len(calls))

        bot_msg = data.get("message", "")
        chips = [c.get("label") for c in data.get("chips", [])]
        cards = data.get("cards", [])
        card_types = [c.get("type") for c in cards]
        route = data.get("route", "")

        # Check shape cards
        if "shape" in card_types:
            shape_cards_count += 1

        # Check estimate card
        for c in cards:
            if c.get("type") == "estimate":
                estimate_card_count += 1
                estimate_card = c
                if turns_to_estimate is None:
                    turns_to_estimate = idx

        # Route objection validity
        if route == "objection" and not is_obj_turn:
            objection_route_invalid += 1

        # Guard message before estimate
        if turns_to_estimate is None:
            if "indicative range above is the only figure" in bot_msg.lower() or "the indicative range above" in bot_msg.lower():
                guard_before_estimate_found += 1

        # Consecutive identical bot messages
        if bot_msg.strip() and bot_msg.strip() == last_bot_msg.strip():
            consecutive_bot_duplicates += 1

        # QA3 banned strings
        has_est_now = turns_to_estimate is not None
        bs = check_banned_strings_qa3(bot_msg, has_est_now)
        if bs:
            banned_strings_found.extend(bs)

        # Questions count before estimate
        if "?" in bot_msg and turns_to_estimate is None:
            bot_questions_count += 1

        banned = check_banned_phrases(bot_msg)
        if banned:
            banned_found.extend(banned)

        ph = check_placeholders(bot_msg)
        if ph:
            placeholders_found.extend(ph)

        cs = check_platform_casing(bot_msg)
        if cs:
            casing_issues_found.extend(cs)

        mc = check_midword_cut(bot_msg)
        if mc:
            midword_cuts_found.extend(mc)

        # Verbatim repeat question check
        curr_q = extract_question(bot_msg)
        last_q = extract_question(last_bot_msg)
        if curr_q and last_q and curr_q == last_q:
            verbatim_repeats += 1
        last_bot_msg = bot_msg

        # Sentence & character limit check
        if route != "estimate":
            sc = count_sentences(bot_msg)
            if len(bot_msg) > 320 or sc > 2:
                long_messages.append({"turn": idx, "length": len(bot_msg), "sentences": sc, "text": bot_msg})
        else:
            recap_present = "Here's what I understood:" in bot_msg and "If anything is off, tell me and I'll update the estimate." in bot_msg
            card_line_present = "indicative range for this scope is" in bot_msg
            honest_present = "first-pass range based on typical scope" in bot_msg or "typical scope" in bot_msg
            if not (recap_present and card_line_present and honest_present and estimate_card is not None):
                estimate_split_valid = False
            full_recap_text = bot_msg

            # Check repetitions in recap
            recap_reps = check_recap_repetitions(bot_msg)
            if recap_reps:
                recap_repetitions_found.extend(recap_reps)

        transcript_turns.append({
            "turn": idx,
            "visitor": visitor_label,
            "bot_message": bot_msg,
            "chips": chips,
            "cards": card_types,
            "route": route,
            "ms": round(elapsed_ms, 1),
            "llm_calls": len(calls),
            "call_details": calls,
        })

    # Retrieve final brief from database
    with SessionLocal() as db:
        s_row = db.get(SessionRow, sid)
        if s_row and s_row.brief_json:
            try:
                final_brief = json.loads(s_row.brief_json)
            except Exception:
                pass

    # Engine check
    engine_match = None
    if estimate_card and final_brief:
        config = load_tenant("demo")
        from backend.app.agents.brief import ProjectBrief
        pb = ProjectBrief(**final_brief)
        expected_est = estimate_project(pb, config.pricing)
        engine_match = (estimate_card.get("range") == expected_est.get("range_label"))

    shape_card_ok = (shape_cards_count == 1) if scenario_id == "S7" else True

    # Brief and recap strict checks
    brief_matches, brief_err = check_brief_matches_expected(scenario_id, final_brief)
    recap_exact, recap_err = check_recap_exact_slots(scenario_id, full_recap_text, final_brief) if turns_to_estimate is not None else (False, "No estimate turn")

    # Latency and call stats
    med_ms = statistics.median(turn_latencies_ms) if turn_latencies_ms else 0.0
    p95_ms = statistics.quantiles(turn_latencies_ms, n=20)[18] if len(turn_latencies_ms) >= 20 else max(turn_latencies_ms) if turn_latencies_ms else 0.0
    max_ms = max(turn_latencies_ms) if turn_latencies_ms else 0.0
    max_calls = max(turn_llm_call_counts) if turn_llm_call_counts else 0

    if is_live:
        latency_calls_ok = (med_ms <= 4000.0 and p95_ms <= 8000.0 and max_ms <= 12000.0 and max_calls <= 2)
    else:
        latency_calls_ok = True

    return {
        "id": scenario_id,
        "title": title,
        "turns": transcript_turns,
        "checks": {
            "first_has_ai": opener_has_ai,
            "opener_chips_valid": opener_chips_valid,
            "max_2_sentences_320_chars": len(long_messages) == 0,
            "no_placeholders": len(placeholders_found) == 0,
            "platform_casing": len(casing_issues_found) == 0,
            "no_midword_cut": len(midword_cuts_found) == 0,
            "no_verbatim_repeat": verbatim_repeats == 0,
            "no_banned_phrases": len(banned_found) == 0,
            "brief_matches_expected": brief_matches,
            "recap_exact_slots": recap_exact,
            "no_words_repeated_in_recap": len(recap_repetitions_found) == 0,
            "objection_route_valid": objection_route_invalid == 0,
            "no_guard_before_estimate": guard_before_estimate_found == 0,
            "no_duplicate_consecutive_messages": consecutive_bot_duplicates == 0,
            "estimate_appears_once": estimate_card_count <= 1,
            "no_banned_strings": len(banned_strings_found) == 0,
            "estimate_split_valid": estimate_split_valid,
            "estimate_matches_engine": engine_match if engine_match is not None else "N/A",
            "shape_card_ok": shape_card_ok,
            "latency_calls_ok": latency_calls_ok,
            "questions_before_estimate": bot_questions_count,
            "turns_to_estimate": turns_to_estimate if turns_to_estimate is not None else "N/A",
        },
        "stats": {
            "median_ms": round(med_ms, 1),
            "p95_ms": round(p95_ms, 1),
            "max_ms": round(max_ms, 1),
            "max_calls": max_calls,
        },
        "long_messages": long_messages,
        "banned_found": banned_found,
        "placeholders_found": placeholders_found,
        "casing_issues_found": casing_issues_found,
        "midword_cuts_found": midword_cuts_found,
        "banned_strings_found": banned_strings_found,
        "recap_repetitions_found": recap_repetitions_found,
        "brief_err": brief_err,
        "recap_err": recap_err,
    }


def get_scenarios() -> list[dict]:
    return [
        # S1: Long comprehensive initial message
        {
            "id": "S1",
            "title": "Long comprehensive initial message with platforms, features, budget, and timeline",
            "turns": [
                "We want it on both iOS and Android. For the first release we just need login, calendar booking, and push notifications. Budget around $25k to $35k, 2 to 3 months.",
                "I am building a sports clinic booking application for direct patients.",
                "I am the founder and technical decision maker.",
            ],
        },
        # S2: Starter chip 'I'm just exploring costs'
        {
            "id": "S2",
            "title": "Starter chip 'I'm just exploring costs'",
            "turns": [
                {"chip": {"field": "ask", "value": "I'm just exploring costs", "label": "I'm just exploring costs"}},
                "Mobile app",
                "Field service and asset tracking",
                "iOS and Android",
                "Offline data collection, barcode scanning, GPS tracking",
                "1 to 3 months",
                "$40k to $80k",
                "Founder",
            ],
        },
        # S3: Starter chip 'I have an app idea' -> 'A marketplace for local farmers'
        {
            "id": "S3",
            "title": "Starter chip 'I have an app idea' -> 'A marketplace for local farmers'",
            "turns": [
                {"chip": {"field": "ask", "value": "I have an app idea", "label": "I have an app idea"}},
                "A marketplace for local farmers",
                "Web and mobile",
                "Produce catalog, Stripe checkout, farmer payouts, direct chat",
                "3 to 6 months",
                "$40k to $80k",
                "Product lead",
            ],
        },
        # S4: Seven-feature list in one message
        {
            "id": "S4",
            "title": "Seven-feature list in one message (triggers Scope Coach)",
            "turns": [
                "I want a web app for clinic management. Features: patient booking, telemedicine video, prescriptions, billing, lab results, doctor scheduling, insurance verification.",
                "Web application",
                "1 to 3 months",
                "$40k to $80k",
                "Founder",
            ],
        },
        # S5: Hinglish scope message
        {
            "id": "S5",
            "title": "Hinglish: 'mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me'",
            "turns": [
                "mujhe ek delivery app chahiye, iOS aur Android dono, 3 mahine me",
                "Live order tracking, customer ratings, driver assignment",
                "$15k to $40k",
                "Founder",
            ],
        },
        # S6: Post-estimate technical questions, booking, and ack
        {
            "id": "S6",
            "title": "Post-estimate technical questions, calendar slot booking, and post-booking ack",
            "turns": [
                "We need a cross-platform mobile app for iOS and Android.",
                "Fitness coaching app with workout logger and push notifications.",
                "Workout tracking, user profiles, video demonstrations",
                "1 to 3 months",
                "$15k to $40k",
                "Founder",
                "Do you use Flutter?",
                "Which cloud do you use?",
                {"content": "Can you guarantee 4 weeks?", "is_objection": True},
                {"chip": {"field": "booking_slot", "value": "2026-10-16T15:00:00Z", "label": "Friday Oct 16, 3:00 PM UTC"}},
                "cool thanks",
            ],
        },
        # S7: Natural chip path
        {
            "id": "S7",
            "title": "Natural chip path: Mobile app, goal text, feature chips, platform chip, timeline chip, budget chip, role chip",
            "turns": [
                {"chip": {"field": "service", "value": "mobile_app", "label": "Mobile app"}},
                "A sports clinic booking application for direct patients",
                {"chip": {"field": "features", "value": ["User login & profiles"], "label": "User login & profiles"}},
                {"chip": {"field": "features_done", "value": "yes", "label": "Continue to next step →"}},
                {"chip": {"field": "platforms", "value": ["ios", "android"], "label": "iOS and Android"}},
                {"chip": {"field": "timeline", "value": "1_3_months", "label": "1–3 months"}},
                {"chip": {"field": "budget_band", "value": "15_40k", "label": "$15–40k"}},
                {"chip": {"field": "decision_role", "value": "founder_or_exec", "label": "Founder / exec"}},
            ],
        },
        # S8: Out-of-order answers (the old S3 script)
        {
            "id": "S8",
            "title": "Out-of-order answers (the old S3 script)",
            "turns": [
                {"chip": {"field": "ask", "value": "I have an app idea", "label": "I have an app idea"}},
                "A marketplace for local farmers",
                "Web and mobile",
                "Produce catalog, Stripe checkout, farmer payouts, direct chat",
                "3 to 6 months",
                "$40k to $80k",
                "Product lead",
            ],
        },
        # S9: First message is only a budget
        {
            "id": "S9",
            "title": "First message is only a budget: 'my budget is $40k to $80k'",
            "turns": [
                "my budget is $40k to $80k",
                "Mobile app",
                "An on-demand tutor marketplace",
                "iOS and Android",
                "Matching algorithm, in-app messaging, tutor reviews",
                "1 to 3 months",
                "Founder",
            ],
        },
        # S10: Starter chip 'I have an app idea' -> booking app for barbers
        {
            "id": "S10",
            "title": "Starter 'I have an app idea' -> 'a booking app for barbers' -> 'web and mobile'",
            "turns": [
                {"chip": {"field": "ask", "value": "I have an app idea", "label": "I have an app idea"}},
                "a booking app for barbers",
                "web and mobile",
                "Appointment scheduling, barber portfolio, customer SMS alerts, loyalty points, payment processing",
                {"chip": {"field": "timeline", "value": "1_3_months", "label": "1–3 months"}},
                {"chip": {"field": "budget_band", "value": "15_40k", "label": "$15–40k"}},
                {"chip": {"field": "decision_role", "value": "founder_or_exec", "label": "Founder / exec"}},
            ],
        },
    ]


def run_mode_scenarios(client: TestClient, is_live: bool, mode_title: str) -> tuple[list[str], list[dict]]:
    scenarios = get_scenarios()
    results = []
    print(f"\n--- Running scenarios for: {mode_title} ---")
    for sc in scenarios:
        print(f"  [{sc['id']}] {sc['title'][:65]}...")
        res = run_scenario(client, sc["id"], sc["title"], sc["turns"], is_live=is_live)
        results.append(res)

    md = [
        f"## {mode_title}\n",
        "### 1. QA Checks Summary Table (Complete QA-2 + QA-3 Validation)\n",
        "| Scenario | Title | Opener | Max 2Sent/320c | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Brief Match | Recap Exact | No Recap Reps | Objection Valid | No Guard Pre-Est | No Dup Bot | Est Once | Banned Strings | Latency & Calls | Turns to Est |",
        "|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        c = r["checks"]
        row = (
            f"| **{r['id']}** | {r['title'][:25]}... | "
            f"{'✓' if c['opener_chips_valid'] else '✗'} | "
            f"{'✓' if c['max_2_sentences_320_chars'] else '✗'} | "
            f"{'✓' if c['no_placeholders'] else '✗'} | "
            f"{'✓' if c['platform_casing'] else '✗'} | "
            f"{'✓' if c['no_midword_cut'] else '✗'} | "
            f"{'✓' if c['no_verbatim_repeat'] else '✗'} | "
            f"{'✓' if c['shape_card_ok'] else '✗'} | "
            f"{'✓' if c['brief_matches_expected'] else '✗'} | "
            f"{'✓' if c['recap_exact_slots'] else '✗'} | "
            f"{'✓' if c['no_words_repeated_in_recap'] else '✗'} | "
            f"{'✓' if c['objection_route_valid'] else '✗'} | "
            f"{'✓' if c['no_guard_before_estimate'] else '✗'} | "
            f"{'✓' if c['no_duplicate_consecutive_messages'] else '✗'} | "
            f"{'✓' if c['estimate_appears_once'] else '✗'} | "
            f"{'✓' if c['no_banned_strings'] else '✗'} | "
            f"{'✓' if c['latency_calls_ok'] else '✗'} | "
            f"{c['turns_to_estimate']} |"
        )
        md.append(row)

    md.append("\n### 2. Scenario Latency & Call Statistics\n")
    md.append("| Scenario | Turns | Median (s) | p95 (s) | Max (s) | Max Calls/Turn | Pass/Fail |")
    md.append("|---|---|---|---|---|---|---|")
    for r in results:
        st = r["stats"]
        status = "✓ PASS" if r["checks"]["latency_calls_ok"] else "✗ FAIL"
        md.append(f"| **{r['id']}** | {len(r['turns']) - 1} | {st['median_ms'] / 1000.0:.2f}s | {st['p95_ms'] / 1000.0:.2f}s | {st['max_ms'] / 1000.0:.2f}s | {st['max_calls']} | {status} |")

    md.append("\n### 3. Full Turn-by-Turn Transcripts & LLM Instrumentation\n")

    for r in results:
        md.append(f"#### Scenario {r['id']}: {r['title']}\n")
        md.append("| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) | LLM Calls |")
        md.append("|---|---|---|---|---|---|---|---|")
        for t in r["turns"]:
            bot_escaped = t["bot_message"].replace("\n", " ").replace("|", "\\|")
            vis_escaped = t["visitor"].replace("\n", " ").replace("|", "\\|")
            chips_str = ", ".join(t["chips"]) if t["chips"] else "-"
            cards_str = ", ".join(t["cards"]) if t["cards"] else "-"
            md.append(f"| {t['turn']} | {vis_escaped} | {bot_escaped} | {chips_str} | {cards_str} | {t['route']} | {t['ms']} | {t.get('llm_calls', 0)} |")

        # Call details table if calls were made
        has_calls = any(t.get("call_details") for t in r["turns"])
        if has_calls:
            md.append("\n*LLM Call Instrumentation (Turn, Purpose, Model, Wall ms, Thinking Tokens, Prompt Tokens, Output Tokens):*")
            md.append("| Turn | Purpose | Model | Wall ms | Thinking Tok | Prompt Tok | Output Tok |")
            md.append("|---|---|---|---|---|---|---|")
            for t in r["turns"]:
                for c in t.get("call_details", []):
                    md.append(f"| {t['turn']} | {c.get('purpose')} | {c.get('model')} | {c.get('wall_time_ms')} | {c.get('thinking_tokens')} | {c.get('prompt_tokens')} | {c.get('output_tokens')} |")
        md.append("")

    return md, results


def main():
    parser = argparse.ArgumentParser(description="Run demo transcripts.")
    parser.add_argument("--live", action="store_true", help="Run live LLM mode only.")
    parser.add_argument("--stub", action="store_true", help="Run stub mode only.")
    parser.add_argument("--flow", choices=["classic", "fast", "both"], default="both", help="Flow mode to evaluate (classic, fast, or both).")
    args = parser.parse_args()

    settings = get_settings()
    settings.message_rate_limit = 1000
    settings.llm_calls_per_ip_per_hour = 1000
    settings.llm_calls_per_session = 1000
    saved_key = settings.llm_api_key

    init_db()
    client = TestClient(app)

    sections = [
        "# DEMO TRANSCRIPTS & QA CHECKS (COMPLETE QA-2 + QA-3 + QA-4 VALIDATION)",
        f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"Primary model configured: `{settings.llm_model}` (thinkingLevel: `{settings.llm_thinking_level or 'low'}`)\n",
    ]
    live_sections = []

    run_classic = args.flow in ("classic", "both")
    run_fast = args.flow in ("fast", "both")

    # 1. Classic Flow Evaluation
    if run_classic:
        os.environ["ENABLE_FAST_FLOW"] = "false"
        if not args.live or args.stub:
            settings.llm_api_key = ""
            settings.embedding_backend = "hash"
            stub_c_md, stub_c_res = run_mode_scenarios(
                client, is_live=False, mode_title="Classic Flow: In-Process Deterministic Stub (Offline / Fallback)"
            )
            sections.extend(stub_c_md)

        if not args.stub and saved_key:
            settings.llm_api_key = saved_key
            settings.embedding_backend = "gemini"
            live_c_md, live_c_res = run_mode_scenarios(
                client, is_live=True, mode_title="Classic Flow: Live LLM Evaluation (Primary Provider: gemini-3.8-flash)"
            )
            sections.extend(live_c_md)
            live_sections.extend(live_c_md)

    # 2. Fast Flow Evaluation
    if run_fast:
        os.environ["ENABLE_FAST_FLOW"] = "true"
        if not args.live or args.stub:
            settings.llm_api_key = ""
            settings.embedding_backend = "hash"
            stub_f_md, stub_f_res = run_mode_scenarios(
                client, is_live=False, mode_title="Fast Flow: In-Process Deterministic Stub (Offline / Fallback)"
            )
            sections.extend(stub_f_md)

        if not args.stub and saved_key:
            settings.llm_api_key = saved_key
            settings.embedding_backend = "gemini"
            live_f_md, live_f_res = run_mode_scenarios(
                client, is_live=True, mode_title="Fast Flow: Live LLM Evaluation (Primary Provider: gemini-3.8-flash)"
            )
            sections.extend(live_f_md)
            live_sections.extend(live_f_md)

    # Restore default
    os.environ.pop("ENABLE_FAST_FLOW", None)
    settings.llm_api_key = saved_key

    out_path = ROOT / "docs" / "DEMO_TRANSCRIPTS.md"
    out_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nSuccessfully written {out_path.relative_to(ROOT)}.")

    if live_sections:
        live_header = [
            "# DEMO TRANSCRIPTS LIVE (UPLOAD-READY EVALUATION)",
            f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
            f"Primary model configured: `{settings.llm_model}` (thinkingLevel: `{settings.llm_thinking_level or 'low'}`)\n",
        ]
        out_live_path = ROOT / "docs" / "DEMO_TRANSCRIPTS_LIVE.md"
        out_live_path.write_text("\n".join(live_header + live_sections), encoding="utf-8")
        print(f"Successfully written upload-ready {out_live_path.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
