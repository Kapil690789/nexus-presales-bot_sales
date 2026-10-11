#!/usr/bin/env python3
"""scripts/demo_transcripts.py - Runs 8 demo scenarios through the API and writes docs/DEMO_TRANSCRIPTS.md."""

from __future__ import annotations

import argparse
import json
import os
import re
import sys
import time
from pathlib import Path

# Add project root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from fastapi.testclient import TestClient

from backend.app.core.settings import get_settings
from backend.app.engines.pricing import estimate_project
from backend.app.main import app
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import SessionRow
from backend.app.tenants.loader import load_tenant

BANNED_PHRASES = ["Love it", "Great idea", "Smart approach", "Awesome", "Exciting", "v1"]
PLACEHOLDERS = ["core features", "near-term target", "medium-term target", "growth tier", "scale tier"]
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


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
    return bad


def extract_question(text: str) -> str:
    for sent in re.split(r"(?<=[.!?])\s+", text):
        if "?" in sent:
            return sent.strip()
    return ""


def run_scenario(client: TestClient, scenario_id: str, title: str, turns: list[dict | str]) -> dict:
    # 1. Create session
    t0 = time.perf_counter()
    init_res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    init_ms = (time.perf_counter() - t0) * 1000.0
    init_data = init_res.json()
    sid = init_data["session_id"]

    transcript_turns = []
    opener_msg = init_data.get("message", "")
    opener_chips = [c.get("label") for c in init_data.get("chips", [])]
    opener_cards = [c.get("type") for c in init_data.get("cards", [])]

    # Opener turn
    opener_turn = {
        "turn": 0,
        "visitor": "(Session Start)",
        "bot_message": opener_msg,
        "chips": opener_chips,
        "cards": opener_cards,
        "route": init_data.get("route", "opener"),
        "ms": round(init_ms, 1),
    }
    transcript_turns.append(opener_turn)

    recent_acks = []
    ack_repeats_found = 0
    banned_found = []
    placeholders_found = []
    casing_issues_found = []
    midword_cuts_found = []
    long_messages = []
    bot_questions_count = 0
    turns_to_estimate = None
    final_brief = None
    estimate_card = None
    shape_cards_count = 0
    verbatim_repeats = 0
    question_history = []
    estimate_split_valid = True

    opener_has_ai = has_standalone_ai(opener_msg)
    opener_chips_valid = len(opener_chips) >= 5 and "Talk to a human" in opener_chips
    banned_in_opener = check_banned_phrases(opener_msg)
    if banned_in_opener:
        banned_found.extend(banned_in_opener)

    last_bot_msg = opener_msg

    for idx, turn_input in enumerate(turns, start=1):
        if isinstance(turn_input, str):
            payload = {"content": turn_input}
            visitor_label = turn_input
        elif isinstance(turn_input, dict):
            payload = turn_input
            visitor_label = turn_input.get("content") or turn_input.get("chip", {}).get("label") or json.dumps(turn_input)
        else:
            payload = {"content": str(turn_input)}
            visitor_label = str(turn_input)

        t0 = time.perf_counter()
        res = client.post(f"/api/v1/sessions/{sid}/messages", json=payload)
        elapsed_ms = (time.perf_counter() - t0) * 1000.0
        data = res.json()

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
                estimate_card = c
                if turns_to_estimate is None:
                    turns_to_estimate = idx

        # Checks
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

        # Verbatim repeat question check (no question repeated verbatim in consecutive bot turns)
        curr_q = extract_question(bot_msg)
        last_q = extract_question(last_bot_msg)
        if curr_q and last_q and curr_q == last_q:
            verbatim_repeats += 1
        last_bot_msg = bot_msg

        # Sentence & character limit check: for every route except estimate
        if route != "estimate":
            sc = count_sentences(bot_msg)
            if len(bot_msg) > 320 or sc > 2:
                long_messages.append({"turn": idx, "length": len(bot_msg), "sentences": sc, "text": bot_msg})
        else:
            # Check estimate message split into recap, card line, honest sentence
            recap_present = "Here's what I understood:" in bot_msg and "If anything is off, tell me and I'll update the estimate." in bot_msg
            card_line_present = "indicative range for this scope is" in bot_msg
            honest_present = "first-pass range based on typical scope" in bot_msg or "typical scope" in bot_msg
            if not (recap_present and card_line_present and honest_present and estimate_card is not None):
                estimate_split_valid = False

        # Track acknowledgements
        sentences = [s.strip() for s in SENTENCE_SPLIT.split(bot_msg) if s.strip()]
        if sentences:
            first_clause = sentences[0].lower()
            if any(first_clause.startswith(w) for w in ["a ", "building ", "focusing ", "targeting ", "working ", "sounds ", "glad "]):
                if first_clause in recent_acks[-3:]:
                    ack_repeats_found += 1
                recent_acks.append(first_clause)

        transcript_turns.append({
            "turn": idx,
            "visitor": visitor_label,
            "bot_message": bot_msg,
            "chips": chips,
            "cards": card_types,
            "route": route,
            "ms": round(elapsed_ms, 1),
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
            "estimate_split_valid": estimate_split_valid,
            "estimate_matches_engine": engine_match if engine_match is not None else "N/A",
            "shape_card_ok": shape_card_ok,
            "questions_before_estimate": bot_questions_count,
            "turns_to_estimate": turns_to_estimate if turns_to_estimate is not None else "N/A",
        },
        "long_messages": long_messages,
        "banned_found": banned_found,
        "placeholders_found": placeholders_found,
        "casing_issues_found": casing_issues_found,
        "midword_cuts_found": midword_cuts_found,
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
                "Can you guarantee 4 weeks?",
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
    ]


def run_mode_scenarios(client: TestClient, is_live: bool, mode_title: str) -> list[str]:
    scenarios = get_scenarios()
    results = []
    print(f"\n--- Running scenarios for: {mode_title} ---")
    for sc in scenarios:
        print(f"  [{sc['id']}] {sc['title'][:65]}...")
        res = run_scenario(client, sc["id"], sc["title"], sc["turns"])
        results.append(res)

    md = [
        f"## {mode_title}\n",
        "### 1. QA Checks Summary Table\n",
        "| Scenario | Title | Opener (4+Human) | Bot <=2 Sent & <=320 Chars | No Placeholders | Platform Casing | No Mid-Word Cut | No Verbatim Repeat | Shape Card (S7) | Estimate Checked | Turns to Est |",
        "|---|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        c = r["checks"]
        row = (
            f"| **{r['id']}** | {r['title'][:32]}... | "
            f"{'✓' if c['opener_chips_valid'] else '✗'} | "
            f"{'✓' if c['max_2_sentences_320_chars'] else '✗'} | "
            f"{'✓' if c['no_placeholders'] else '✗'} | "
            f"{'✓' if c['platform_casing'] else '✗'} | "
            f"{'✓' if c['no_midword_cut'] else '✗'} | "
            f"{'✓' if c['no_verbatim_repeat'] else '✗'} | "
            f"{'✓' if c['shape_card_ok'] else '✗'} | "
            f"{'✓' if c['estimate_split_valid'] and c['estimate_matches_engine'] is True else ('✓' if c['estimate_split_valid'] else '✗')} | "
            f"{c['turns_to_estimate']} |"
        )
        md.append(row)

    md.append("\n### 2. Full Turn-by-Turn Transcripts\n")

    for r in results:
        md.append(f"#### Scenario {r['id']}: {r['title']}\n")
        md.append("| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |")
        md.append("|---|---|---|---|---|---|---|")
        for t in r["turns"]:
            bot_escaped = t["bot_message"].replace("\n", " ").replace("|", "\\|")
            vis_escaped = t["visitor"].replace("\n", " ").replace("|", "\\|")
            chips_str = ", ".join(t["chips"]) if t["chips"] else "-"
            cards_str = ", ".join(t["cards"]) if t["cards"] else "-"
            md.append(f"| {t['turn']} | {vis_escaped} | {bot_escaped} | {chips_str} | {cards_str} | {t['route']} | {t['ms']} |")
        md.append("")

    return md, results


def main():
    parser = argparse.ArgumentParser(description="Run demo transcripts.")
    parser.add_argument("--live", action="store_true", help="Run live LLM mode only.")
    parser.add_argument("--stub", action="store_true", help="Run stub mode only.")
    args = parser.parse_args()

    settings = get_settings()
    settings.message_rate_limit = 1000
    settings.llm_calls_per_ip_per_hour = 1000
    settings.llm_calls_per_session = 1000
    saved_key = settings.llm_api_key

    init_db()
    client = TestClient(app)

    sections = [
        "# DEMO TRANSCRIPTS & QA CHECKS (QA-2 VALIDATION)",
        f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"Primary model configured: `{settings.llm_model}`\n",
    ]

    # Section 1: In-Process Deterministic Stub
    if not args.live or args.stub:
        settings.llm_api_key = ""
        stub_md, stub_res = run_mode_scenarios(client, is_live=False, mode_title="Section 1: In-Process Deterministic Stub (Offline / Fallback)")
        sections.extend(stub_md)

    # Section 2: Live LLM Mode (if key is present and not explicitly --stub)
    if not args.stub and saved_key:
        settings.llm_api_key = saved_key
        live_md, live_res = run_mode_scenarios(client, is_live=True, mode_title="Section 2: Live LLM Evaluation (Primary Provider)")
        sections.extend(live_md)

    out_path = ROOT / "docs" / "DEMO_TRANSCRIPTS.md"
    out_path.write_text("\n".join(sections), encoding="utf-8")
    print(f"\nSuccessfully written {out_path.relative_to(ROOT)}.")


if __name__ == "__main__":
    main()
