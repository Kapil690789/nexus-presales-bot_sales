#!/usr/bin/env python3
"""
Nexus Pre-Sales Consultant — Interactive & Step-by-Step Live Proposal Tester.

Usage:
    # 1. Guided Step-by-Step Walkthrough with Live Proposal (automatic or press enter):
    python scripts/interactive_chat.py --step

    # 2. Fully Interactive Chat (talk to the bot directly in your terminal):
    python scripts/interactive_chat.py --interactive

    # 3. Test against a running server (e.g., http://127.0.0.1:8000):
    python scripts/interactive_chat.py --url http://127.0.0.1:8000 --interactive
"""

import argparse
import json
import os
import sys
import time
from typing import Any

# Ensure project root is in sys.path
SCRIPT_DIR = os.path.dirname(os.path.abspath(__file__))
PROJECT_ROOT = os.path.dirname(SCRIPT_DIR)
if PROJECT_ROOT not in sys.path:
    sys.path.insert(0, PROJECT_ROOT)
os.chdir(PROJECT_ROOT)

# ANSI Colors
BOLD = "\033[1m"
DIM = "\033[2m"
CYAN = "\033[96m"
GREEN = "\033[92m"
YELLOW = "\033[93m"
BLUE = "\033[94m"
MAGENTA = "\033[95m"
RED = "\033[91m"
RESET = "\033[0m"


def print_banner():
    print(f"\n{BOLD}{CYAN}===================================================================={RESET}")
    print(f"{BOLD}{CYAN}      NEXUS PRE-SALES CONSULTANT — LIVE PROPOSAL TESTER            {RESET}")
    print(f"{BOLD}{CYAN}===================================================================={RESET}\n")


def render_card(card: dict[str, Any]):
    card_type = card.get("type")
    title = card.get("title") or card_type or "Details"

    if card_type == "estimate":
        print(f"\n{BOLD}{BLUE}┌─────────────────── 📄 LIVE PROPOSAL: ESTIMATE ───────────────────┐{RESET}")
        print(f"{BLUE}│{RESET} {BOLD}Title:{RESET} {title}")
        print(f"{BLUE}│{RESET} {BOLD}Indicative Range:{RESET} {GREEN}{card.get('range', 'N/A')}{RESET}")
        print(f"{BLUE}│{RESET} {BOLD}Target Timeline:{RESET}  {card.get('weeks', 'N/A')} weeks")
        print(f"{BLUE}│{RESET} {BOLD}Delivery Squad:{RESET}   {card.get('team', 'N/A')}")
        if card.get("inclusions"):
            print(f"{BLUE}│{RESET} {BOLD}Inclusions:{RESET}")
            for item in card["inclusions"]:
                print(f"{BLUE}│{RESET}   ✓ {item}")
        if card.get("assumptions"):
            print(f"{BLUE}│{RESET} {BOLD}Key Assumptions:{RESET}")
            for item in card["assumptions"]:
                print(f"{BLUE}│{RESET}   • {item}")
        if card.get("disclaimer"):
            print(f"{BLUE}│{RESET} {DIM}Note: {card['disclaimer']}{RESET}")
        print(f"{BOLD}{BLUE}└───────────────────────────────────────────────────────────────────┘{RESET}\n")

    elif card_type == "architecture":
        print(f"\n{BOLD}{MAGENTA}┌─────────────────── 🏗️ SYSTEM ARCHITECTURE ──────────────────────┐{RESET}")
        print(f"{MAGENTA}│{RESET} {BOLD}{title}{RESET}")
        if card.get("frontend"):
            print(f"{MAGENTA}│{RESET} {BOLD}Frontend:{RESET} {', '.join(card['frontend'])}")
        if card.get("backend"):
            print(f"{MAGENTA}│{RESET} {BOLD}Backend:{RESET}  {', '.join(card['backend'])}")
        if card.get("notes"):
            print(f"{MAGENTA}│{RESET} {BOLD}Architectural Highlights:{RESET}")
            for note in card["notes"]:
                print(f"{MAGENTA}│{RESET}   ⚙️ {note}")
        print(f"{BOLD}{MAGENTA}└───────────────────────────────────────────────────────────────────┘{RESET}\n")

    elif card_type == "mvp":
        print(f"\n{BOLD}{YELLOW}┌────────────────────── 🚀 MVP SCOPE BOUNDARY ──────────────────────┐{RESET}")
        print(f"{YELLOW}│{RESET} {BOLD}{title}{RESET}")
        if card.get("mvp"):
            print(f"{YELLOW}│{RESET} {BOLD}MVP Release 1 (Core):{RESET}")
            for item in card["mvp"]:
                print(f"{YELLOW}│{RESET}   ⭐ {item}")
        if card.get("later"):
            print(f"{YELLOW}│{RESET} {BOLD}Deferred / Phase 2:{RESET}")
            for item in card["later"]:
                print(f"{YELLOW}│{RESET}   ⏳ {item}")
        print(f"{BOLD}{YELLOW}└───────────────────────────────────────────────────────────────────┘{RESET}\n")

    elif card_type == "portfolio":
        badge = f"{YELLOW}[Sample project (demo data)]{RESET}" if card.get("is_sample") else ""
        print(f"\n{BOLD}{CYAN}┌─────────────────── 💼 CASE STUDIES & PORTFOLIO ───────────────────┐{RESET}")
        print(f"{CYAN}│{RESET} {BOLD}{title}{RESET} {badge}")
        for item in card.get("cases", []):
            item_badge = f"{YELLOW}[Sample project (demo data)]{RESET}" if item.get("is_sample") else ""
            print(f"{CYAN}│{RESET} • {BOLD}{item.get('title', 'Project')}{RESET} {item_badge}")
            if item.get("outcome"):
                print(f"{CYAN}│{RESET}   Impact: {item['outcome']}")
            if item.get("url"):
                print(f"{CYAN}│{RESET}   Link:   {item['url']}")
        print(f"{BOLD}{CYAN}└───────────────────────────────────────────────────────────────────┘{RESET}\n")

    elif card_type == "booking":
        print(f"\n{BOLD}{GREEN}┌───────────────────── 📅 CALENDAR BOOKING ────────────────────────┐{RESET}")
        print(f"{GREEN}│{RESET} {BOLD}{title}{RESET}")
        if card.get("label"):
            print(f"{GREEN}│{RESET} Slot: {card['label']}")
        if card.get("meet_url"):
            print(f"{GREEN}│{RESET} Meet Link: {CYAN}{card['meet_url']}{RESET}")
        if card.get("slots"):
            for s in card["slots"]:
                print(f"{GREEN}│{RESET} 🕒 {s.get('label')}")
        print(f"{BOLD}{GREEN}└───────────────────────────────────────────────────────────────────┘{RESET}\n")


def display_turn(bot_reply: dict[str, Any]):
    message = bot_reply.get("message", "")
    route = bot_reply.get("route", "")
    stage = bot_reply.get("stage", "")
    chips = bot_reply.get("chips", [])
    cards = bot_reply.get("cards", [])

    print(f"\n{BOLD}{GREEN}🤖 Nexus Consultant ({route} | {stage}):{RESET}")
    print(f"{message}\n")

    # Render Cards (e.g., Live Proposal!)
    if cards:
        for card in cards:
            render_card(card)

    # Render Suggestion Chips
    if chips:
        print(f"{BOLD}{YELLOW}💡 Suggestion Chips (Quick Options):{RESET}")
        for idx, chip in enumerate(chips, 1):
            label = chip.get("label") or chip.get("value")
            field = chip.get("field", "")
            print(f"  {YELLOW}[{idx}]{RESET} {label} {DIM}(field: {field}){RESET}")
        print()


class ChatClient:
    def __init__(self, base_url: str | None = None):
        self.base_url = base_url
        if base_url:
            import httpx
            self.client = httpx.Client(base_url=base_url, timeout=60.0)
            self.mode = "http"
        else:
            from starlette.testclient import TestClient
            from backend.app.main import create_app
            self.client = TestClient(create_app())
            self.mode = "in_memory"

    def create_session(self, tenant: str = "demo") -> str:
        res = self.client.post("/api/v1/sessions", json={"tenant": tenant})
        if res.status_code != 200:
            raise RuntimeError(f"Failed to create session: {res.text}")
        data = res.json()
        return data["session_id"], data

    def send_message(self, session_id: str, content: str = "", chip: dict | None = None) -> tuple[dict, str]:
        payload: dict[str, Any] = {"content": content}
        if chip:
            payload["chip"] = chip

        t0 = time.perf_counter()
        res = self.client.post(f"/api/v1/sessions/{session_id}/messages", json=payload)
        dur = (time.perf_counter() - t0) * 1000.0

        if res.status_code != 200:
            raise RuntimeError(f"Message failed ({res.status_code}): {res.text}")

        server_timing = res.headers.get("Server-Timing", f"client_roundtrip={dur:.1f}ms")
        return res.json(), server_timing


def run_guided_walkthrough(client: ChatClient):
    print_banner()
    print(f"{BOLD}Starting Guided Discovery Flow -> Generates Live Proposal & Estimates!{RESET}\n")

    session_id, initial = client.create_session("demo")
    print(f"{DIM}Session ID: {session_id} (Engine: {client.mode}){RESET}")
    display_turn(initial)

    # Scripted sequence demonstrating full discovery to Live Proposal
    script = [
        {
            "step": "Step 1: Choose Service",
            "user_say": "Web app",
            "chip": {"field": "service", "value": "web_app", "label": "Web app"},
            "explanation": "Select Web application using chip click (skips LLM extractor)."
        },
        {
            "step": "Step 2: Project Goal & Problem",
            "user_say": "We want to build a telemedicine platform connecting patients with specialized doctors for video appointments and e-prescriptions.",
            "chip": None,
            "explanation": "Free text scoping. Extractor analyzes domain and identifies healthcare SaaS."
        },
        {
            "step": "Step 3: Core Features",
            "user_say": "Patient booking, video consultation, and Stripe payments",
            "chip": None,
            "explanation": "Free text feature description."
        },
        {
            "step": "Step 4: Confirm Feature List",
            "user_say": "Ready with this list",
            "chip": {"field": "features_done", "value": "yes", "label": "Ready with this list"},
            "explanation": "Confirms the core feature set to proceed."
        },
        {
            "step": "Step 5: User Journey / Skip Flow",
            "user_say": "Skip for now",
            "chip": {"field": "user_flow", "value": "not_specified", "label": "Skip for now"},
            "explanation": "Skips optional user journey flow."
        },
        {
            "step": "Step 6: Target Platforms",
            "user_say": "Web",
            "chip": {"field": "platforms", "value": ["web"], "label": "Web"},
            "explanation": "Specifies responsive Web platform."
        },
        {
            "step": "Step 7: Target Users",
            "user_say": "Patients and healthcare providers",
            "chip": {"field": "users", "value": "consumers", "label": "Consumers & business"},
            "explanation": "Specifies user personas."
        },
        {
            "step": "Step 8: Integrations (Testing 'no')",
            "user_say": "no",
            "chip": None,
            "explanation": "Tests SHIP-2 rule: 'no' during discovery directly sets integrations to 'none'!"
        },
        {
            "step": "Step 9: Launch Timeline",
            "user_say": "1–3 months",
            "chip": {"field": "timeline", "value": "1_3_months", "label": "1–3 months"},
            "explanation": "Sizing sprint cycles and velocity."
        },
        {
            "step": "Step 10: Budget Range",
            "user_say": "$40–80k",
            "chip": {"field": "budget_band", "value": "40_80k", "label": "$40–80k"},
            "explanation": "Indicative budget band calibration."
        },
        {
            "step": "Step 11: Decision Role -> TRIGGERS LIVE PROPOSAL!",
            "user_say": "Founder / exec",
            "chip": {"field": "decision_role", "value": "founder_or_exec", "label": "Founder / exec"},
            "explanation": "Final engine parameter! The bot synthesizes the complete Live Proposal!"
        },
        {
            "step": "Step 12: Ask Domain Case Study Question",
            "user_say": "Do you have any past experience with clinic companions or patient scheduling?",
            "chip": None,
            "explanation": "Tests RAG retrieval against real clinic case studies (with 'Sample' badges)."
        },
        {
            "step": "Step 13: Handle Price Objection",
            "user_say": "That feels a bit expensive, can we phase it?",
            "chip": None,
            "explanation": "Demonstrates objection handling & modular MVP milestone phasing."
        },
        {
            "step": "Step 14: Book Discovery Call",
            "user_say": "Book a meeting",
            "chip": {"field": "booking_window", "value": "this_week", "label": "Book a meeting"},
            "explanation": "Presents live engineering calendar slots."
        },
    ]

    for item in script:
        step_title = item["step"]
        user_say = item["user_say"]
        chip = item["chip"]
        explanation = item["explanation"]

        print(f"\n{BOLD}{CYAN}--------------------------------------------------------------------{RESET}")
        print(f"{BOLD}▶ {step_title}{RESET}")
        print(f"{DIM}Rationale: {explanation}{RESET}")
        input(f"{DIM}Press [Enter] to send: \"{user_say}\"...{RESET}")

        print(f"\n{BOLD}👤 User:{RESET} {user_say} {'(Chip click)' if chip else ''}")
        reply, timing = client.send_message(session_id, content=user_say, chip=chip)
        display_turn(reply)
        print(f"{DIM}⏱️ Server-Timing: {timing}{RESET}")

    print(f"\n{BOLD}{GREEN}===================================================================={RESET}")
    print(f"{BOLD}{GREEN}✅ Walkthrough Complete! Live proposal, architecture, MVP & booking verified.{RESET}")
    print(f"{BOLD}{GREEN}===================================================================={RESET}\n")


def run_interactive_mode(client: ChatClient):
    print_banner()
    print(f"{BOLD}Interactive Chat Mode.{RESET} Type your messages or chip numbers. Type 'quit' to exit.\n")

    session_id, initial = client.create_session("demo")
    print(f"{DIM}Session ID: {session_id} (Engine: {client.mode}){RESET}")
    display_turn(initial)
    last_chips = initial.get("chips", [])

    while True:
        try:
            user_input = input(f"{BOLD}👤 You > {RESET}").strip()
        except (KeyboardInterrupt, EOFError):
            print("\nExiting chat. Bye!")
            break

        if not user_input:
            continue
        if user_input.lower() in ("exit", "quit", "q"):
            print("Chat session ended.")
            break

        # Check if user entered a number corresponding to a chip
        selected_chip = None
        content = user_input

        if user_input.isdigit() and last_chips:
            idx = int(user_input) - 1
            if 0 <= idx < len(last_chips):
                selected_chip = last_chips[idx]
                content = selected_chip.get("label") or str(selected_chip.get("value"))
                print(f"{DIM}[Selected Chip {user_input}: {content}]{RESET}")

        try:
            reply, timing = client.send_message(session_id, content=content, chip=selected_chip)
            display_turn(reply)
            last_chips = reply.get("chips", [])
            print(f"{DIM}⏱️ Timing: {timing}{RESET}")
        except Exception as exc:
            print(f"{RED}Error: {exc}{RESET}")


def main():
    parser = argparse.ArgumentParser(description="Nexus Pre-Sales Live Proposal Tester")
    parser.add_argument("--url", type=str, default=None, help="Connect to running server (e.g., http://127.0.0.1:8000)")
    parser.add_argument("--interactive", "-i", action="store_true", help="Run in free-form interactive terminal mode")
    parser.add_argument("--step", "-s", action="store_true", help="Run the step-by-step guided walkthrough")

    args = parser.parse_args()
    client = ChatClient(base_url=args.url)

    if args.interactive:
        run_interactive_mode(client)
    else:
        run_guided_walkthrough(client)


if __name__ == "__main__":
    main()
