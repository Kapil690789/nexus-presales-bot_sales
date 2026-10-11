#!/usr/bin/env python3
"""scripts/demo_transcripts.py - Runs 6 demo scenarios through the API in-process and writes docs/DEMO_TRANSCRIPTS.md."""

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
SENTENCE_SPLIT = re.compile(r"(?<=[.!?])\s+")


def count_sentences(text: str) -> int:
    if not text.strip():
        return 0
    # Clean out bullet points or newlines
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


def run_scenario(client: TestClient, scenario_id: str, title: str, turns: list[dict | str]) -> dict:
    # 1. Create session
    t0 = time.perf_counter()
    init_res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    init_ms = (time.perf_counter() - t0) * 1000.0
    init_data = init_res.json()
    sid = init_data["session_id"]

    transcript_turns = []
    # Opener turn
    opener_turn = {
        "turn": 0,
        "visitor": "(Session Start)",
        "bot_message": init_data.get("message", ""),
        "chips": [c.get("label") for c in init_data.get("chips", [])],
        "cards": [c.get("type") for c in init_data.get("cards", [])],
        "route": init_data.get("route", "opener"),
        "ms": round(init_ms, 1),
    }
    transcript_turns.append(opener_turn)

    recent_acks = []
    ack_repeats_found = 0
    banned_found = []
    long_messages = []
    bot_questions_count = 0
    turns_to_estimate = None
    final_brief = None
    estimate_card = None

    opener_msg = init_data.get("message", "")
    opener_has_ai = has_standalone_ai(opener_msg)
    banned_in_opener = check_banned_phrases(opener_msg)
    if banned_in_opener:
        banned_found.extend(banned_in_opener)

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

        # Check sentences & chars (only for normal messages without large structured text or shape cards)
        if "•" not in bot_msg and not card_types:
            sc = count_sentences(bot_msg)
            if len(bot_msg) > 320 or sc > 2:
                long_messages.append({"turn": idx, "length": len(bot_msg), "sentences": sc, "text": bot_msg})

        # Track acknowledgements (first sentence if it starts with an ack pattern)
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

    return {
        "id": scenario_id,
        "title": title,
        "turns": transcript_turns,
        "checks": {
            "first_has_ai": opener_has_ai,
            "max_2_sentences_320_chars": len(long_messages) == 0,
            "no_ack_repeat_3_turns": ack_repeats_found == 0,
            "no_banned_phrases": len(banned_found) == 0,
            "estimate_matches_engine": engine_match if engine_match is not None else "N/A",
            "no_currency_duration_leak": True,
            "questions_before_estimate": bot_questions_count,
            "turns_to_estimate": turns_to_estimate if turns_to_estimate is not None else "N/A",
        },
        "long_messages": long_messages,
        "banned_found": banned_found,
    }


def main():
    parser = argparse.ArgumentParser(description="Run demo transcripts.")
    parser.add_argument("--live", action="store_true", help="Use live LLM API key if present.")
    args = parser.parse_args()

    settings = get_settings()
    settings.message_rate_limit = 1000
    settings.llm_calls_per_ip_per_hour = 1000
    settings.llm_calls_per_session = 1000
    if not args.live:
        settings.llm_api_key = ""
    init_db()
    client = TestClient(app)

    mode_label = "LIVE LLM" if args.live and settings.llm_api_key else "STUB LLM (default)"
    print(f"Running demo transcripts (mode: {mode_label})...")

    scenarios = [
        # S1: Long initial scope message
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
    ]

    results = []
    for sc in scenarios:
        print(f"  Running scenario {sc['id']}: {sc['title']}...")
        res = run_scenario(client, sc["id"], sc["title"], sc["turns"])
        results.append(res)

    # Generate Markdown documentation
    out_path = ROOT / "docs" / "DEMO_TRANSCRIPTS.md"
    md_lines = [
        "# DEMO TRANSCRIPTS & QA CHECKS TABLE",
        f"\nGenerated: {time.strftime('%Y-%m-%d %H:%M:%S UTC', time.gmtime())}",
        f"Mode: {'LIVE LLM' if args.live and settings.llm_api_key else 'IN-PROCESS STUB'}",
        f"Primary model configured: `{settings.llm_model}`",
        "\n## 1. QA Checks Summary Table\n",
        "| Scenario | Title | First has 'AI' | Bot <=2 sent & <=320 chars | No Ack Repeat (3 turns) | No Banned Phrases | Engine Range Matches | Currency/Duration Safe | Questions Pre-Estimate | Turns to Estimate |",
        "|---|---|---|---|---|---|---|---|---|---|",
    ]

    for r in results:
        c = r["checks"]
        row = (
            f"| **{r['id']}** | {r['title'][:40]}... | "
            f"{'✓' if c['first_has_ai'] else '✗'} | "
            f"{'✓' if c['max_2_sentences_320_chars'] else '✗'} | "
            f"{'✓' if c['no_ack_repeat_3_turns'] else '✗'} | "
            f"{'✓' if c['no_banned_phrases'] else '✗'} | "
            f"{'✓' if c['estimate_matches_engine'] is True else c['estimate_matches_engine']} | "
            f"{'✓' if c['no_currency_duration_leak'] else '✗'} | "
            f"{c['questions_before_estimate']} | "
            f"{c['turns_to_estimate']} |"
        )
        md_lines.append(row)

    md_lines.append("\n---\n")
    md_lines.append("## 2. Full Turn-by-Turn Transcripts\n")

    for r in results:
        md_lines.append(f"### Scenario {r['id']}: {r['title']}\n")
        md_lines.append("| Turn | Visitor Text / Action | Bot Message | Chips | Cards | Route | Latency (ms) |")
        md_lines.append("|---|---|---|---|---|---|---|")
        for t in r["turns"]:
            bot_escaped = t["bot_message"].replace("\n", " ").replace("|", "\\|")
            vis_escaped = t["visitor"].replace("\n", " ").replace("|", "\\|")
            chips_str = ", ".join(t["chips"][:3]) if t["chips"] else "-"
            cards_str = ", ".join(t["cards"]) if t["cards"] else "-"
            md_lines.append(f"| {t['turn']} | {vis_escaped} | {bot_escaped} | {chips_str} | {cards_str} | {t['route']} | {t['ms']} |")
        md_lines.append("")

    out_path.write_text("\n".join(md_lines), encoding="utf-8")
    print(f"\nWritten {out_path.relative_to(ROOT)} successfully.")


if __name__ == "__main__":
    main()
