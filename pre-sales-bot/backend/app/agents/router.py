from __future__ import annotations

import json
import logging
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__)

from backend.app.agents.brief import ProjectBrief, brief_ready, next_discovery_field
from backend.app.agents.discovery_synth import synthesize_discovery_prompt
from backend.app.agents.extractor import apply_extracted_slots, extract_slots
from backend.app.agents.fallback import fallback_message
from backend.app.agents.suggestions import ensure_chips
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.core.guard import sanitize_price_leaks
from backend.app.core.platform import get_platform
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.calendar import confirm_slot, list_slots
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.objections import match_objection
from backend.app.engines.portfolio import match_portfolio
from backend.app.engines.pricing import estimate_project
from backend.app.engines.qualification import qualify
from backend.app.engines.notify import company_from_email, notify_slack
from backend.app.learning.pairs import save_booking_pairs
from backend.app.memory.rewrite import lookup_queries, rolling_summary
from backend.app.models.entities import LeadRow, SessionRow, TenantRow
from backend.app.rag.filters import query_filters
from backend.app.rag.grade import grade, grounded_answer
from backend.app.rag.store import search
from backend.app.screening.slots import BOOK_CHIP, DISCOVERY_PROMPTS, PORTFOLIO_CHIP, chips_for_field, prompt_for
from backend.app.tenants.schema import TenantConfig

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
OPEN = re.compile(r"\?|^(what|how|who|why|when|where|can|do|does|is|are|have)\b", re.IGNORECASE)
BOOK = re.compile(r"\b(book|schedule|reschedule)\b.{0,40}\b(call|meeting|consultation|time)\b|\breschedule\b", re.IGNORECASE)
OUT_OF_SCOPE = ("shopify", "crypto", "web3", "homework", "student project")
ACTION = {"show_portfolio", "booking_window", "booking_slot", "nda", "close_out", "view_mvp", "email_instead", "continue_discovery", "sharpen_estimate"}

import time
from backend.app.rag.embeddings import query_embedding_duration_ms

GROUNDING_LINE = (
    "Answer only from the engine data and the provided notes. If the notes do not contain the answer, "
    "say you are not sure and offer to connect the team. Never invent clients, case studies, guarantees, "
    "delivery dates or prices."
)
SOLUTION_SYSTEM_PROMPT = (
    "You are an expert enterprise pre-sales software consultant and principal solutions architect. Output JSON only. "
    + GROUNDING_LINE
)
ACK_VOCAB = {
    "cool", "thanks", "thank", "you", "ok", "okay", "great", "nice", "awesome", "perfect",
    "got", "it", "sure", "fine", "good", "haan", "theek", "thik", "hai", "shukriya",
    "dhanyavad", "so", "much", "very", "a", "lot", "hi", "hello", "hey", "yes", "no",
}
CONDITIONAL_ACK_WORDS = {"yes", "no", "ok", "okay", "haan", "theek", "thik"}


def _is_ack(text: str, has_pending_discovery: bool = False) -> bool:
    cleaned = (text or "").lower()
    words = [w.strip(".,!?:;\"'()[]{}~`") for w in cleaned.split()]
    words = [w for w in words if w]
    if not words or len(words) > 5:
        return False
    if not all(w in ACK_VOCAB for w in words):
        return False
    if has_pending_discovery and all(w in CONDITIONAL_ACK_WORDS for w in words):
        return False
    return True


QUESTION_OR_COMMAND_START = re.compile(
    r"^\s*(what|how|who|why|when|where|can|do|does|is|are|have|will|should|tell|show|explain|describe|list|give|share)\b",
    re.IGNORECASE,
)
KNOWN_CASE_STUDIES = {"zephyr", "harbor", "atlas", "ledgerly", "harvest", "northstar"}


def _is_question_like(text: str) -> bool:
    cleaned = (text or "").strip()
    if "?" in cleaned:
        return True
    if any(k in cleaned.lower() for k in KNOWN_CASE_STUDIES):
        return True
    return bool(QUESTION_OR_COMMAND_START.match(cleaned))


def _last_question_sentence(msg: str) -> str:
    if not msg:
        return ""
    q_idx = msg.rfind("?")
    if q_idx == -1:
        return ""
    before_q = msg[:q_idx]
    parts = re.split(r"[.\n!]", before_q)
    last_part = parts[-1] if parts else before_q
    return (last_part + "?").strip().lower()


def run_turn(
    db: Session,
    tenant: TenantRow,
    config: TenantConfig,
    session: SessionRow,
    history: list[dict],
    user_text: str,
    chip: dict | None,
) -> dict:
    brief = _brief(session)
    contact = _json(session.contact_json)
    text = (user_text or "").strip()
    chip = chip or {}
    field = str(chip.get("field") or "").strip()
    value = chip.get("value")
    if field == "ask":
        field = ""
        value = None

    timings = {
        "extractor": 0.0,
        "query_embedding": 0.0,
        "retrieval_db": 0.0,
        "answer_llm": 0.0,
        "db_writes": 0.0,
    }
    is_chip_click = bool(field or value)
    brief_track_fields = ("service", "goal", "platforms", "features", "timeline", "budget_band", "decision_role", "company_size", "integrations")
    initial_brief_state = {f: getattr(brief, f) for f in brief_track_fields}
    found = EMAIL.search(text)
    if found:
        contact["email"] = found.group(0).rstrip(".")
    user_texts = [item["content"] for item in history if item.get("role") == "user" and item.get("content")]
    if text:
        user_texts.append(text)
    summary = rolling_summary(session.summary or "", user_texts, get_platform().summary_every)
    previous = [item["content"] for item in history if item.get("role") == "user" and item.get("content")]

    if field == "nda":
        if str(value) == config.brand.nda_version or value is True or str(value).lower() in {"yes", "true", "1"}:
            session.nda_accepted = True
            session.nda_version = config.brand.nda_version
        return _finish(
            session, brief, contact, summary,
            message="Thanks! NDA acknowledged. I can now share detailed architectures and relevant case study metrics in this chat.",
            stage="discovery",
            route="nda",
            chips=_next_chips(brief),
        )

    if field == "view_mvp":
        mvp_res = recommend_mvp(brief)
        cards = [
            {
                "type": "mvp",
                "title": "MVP breakdown",
                "mvp": mvp_res["mvp"],
                "later": mvp_res["later"],
                "rationale": mvp_res["rationale"],
            }
        ]
        msg = f"Here is how we recommend staging the MVP release to keep initial timeline and budget focused: {mvp_res['rationale']}"
        chips = [
            {"label": "Book a call", "field": "booking_window", "value": "this_week"},
            {"label": "See sample projects", "field": "show_portfolio", "value": "yes"},
        ]
        return _finish(
            session, brief, contact, summary,
            message=msg,
            stage="advising",
            route="mvp",
            chips=chips,
            cards=cards,
            mvp=mvp_res,
        )

    if field in ("continue_discovery", "sharpen_estimate"):
        return _after_brief(session, config, brief, contact, summary, user_text=text, history=history, timings=timings)

    if field == "email_instead":
        contact["prefers_email"] = True
        session.contact_json = json.dumps(contact)
        return _finish(
            session, brief, contact, summary,
            message="Sure. What's the best email?",
            stage="email_capture",
            route="email_capture",
            chips=[],
        )

    if field == "booking_slot":
        return _book(db, tenant, config, session, brief, contact, summary, str(value or ""))

    if field == "booking_window" or (text and not field and BOOK.search(text)):
        tz_name = getattr(config.brand, "timezone", "") or "Asia/Kolkata"
        slots, live = list_slots(tenant, tz_name=tz_name)
        duration_min = get_platform().calendar.duration_minutes
        handoff_text = getattr(config.brand, "booking_handoff_text", None) or "The team will see this whole conversation, so you won't need to repeat anything."
        pick_card = {"type": "booking", "title": "Pick a time", "live": live, "slots": slots}
        if not live:
            pick_card["disclaimer"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
            pick_card["note"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
        chips = [{"label": slot["label"], "field": "booking_slot", "value": slot["slot_iso"]} for slot in slots]
        chips.append({"label": "Email me instead", "field": "email_instead", "value": "prefers_email"})
        return _finish(
            session, brief, contact, summary,
            message=f"Here are a few times for a short {duration_min}-minute discovery call with our team. {handoff_text}",
            stage="booking",
            route="booking",
            chips=chips,
            cards=[pick_card],
        )

    if found:
        email = contact["email"]
        if contact.get("prefers_email"):
            qual = qualify(brief, config.qualification, config.services, has_email=True)
            estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
            handoff = _handoff(config, brief, contact, qual, estimate, None)
            session.handoff_summary = handoff
            _lead(db, tenant, session, email, qual, estimate, handoff)
            notify_slack(
                db,
                session.id,
                tenant,
                f"Lead email captured (prefers email) for {config.brand.name}: {email}",
            )
            return _finish(
                session, brief, contact, summary,
                message="Thanks, the team will email you the summary.",
                stage="handoff",
                route="email_capture",
                chips=[PORTFOLIO_CHIP],
                qualification=qual,
                estimate=estimate,
                handoff_summary=handoff,
            )
        if session.booking_json:
            try:
                booked = json.loads(session.booking_json)
            except Exception:
                booked = {}
            slot_iso = booked.get("slot_iso") or ""
            if slot_iso:
                try:
                    updated_booked = confirm_slot(
                        tenant,
                        slot_iso,
                        f"Discovery call — {config.brand.name}",
                        email,
                        event_id=booked.get("event_id"),
                        tz_name=getattr(config.brand, "timezone", "") or "Asia/Kolkata",
                    )
                    if updated_booked:
                        booked.update(updated_booked)
                except Exception as exc:
                    log.warning("Failed to update slot with email: %s", exc)
            booked["attendee"] = email
            session.booking_json = json.dumps(booked)

            qual = qualify(brief, config.qualification, config.services, has_email=True)
            estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
            handoff = _handoff(config, brief, contact, qual, estimate, booked)
            session.handoff_summary = handoff
            _lead(db, tenant, session, email, qual, estimate, handoff)
            notify_slack(
                db,
                session.id,
                tenant,
                f"Booking invitation dispatched for {config.brand.name}: {booked.get('label') or slot_iso} -> {email}",
            )
            slot_label = booked.get("label") or slot_iso or "your scheduled discovery session"
            reply = f"Thank you! Your calendar invitation for **{slot_label}** has been dispatched to **{email}**."
            if not booked.get("live"):
                reply += " Demo booking: no calendar invite is sent until Google Calendar is connected."
            elif booked.get("meet_url"):
                reply += f" Google Meet link: {booked['meet_url']}."
            reply += " Our solutions engineering team is looking forward to the discussion!"

            post_chips = [
                {"label": "What is on the agenda?", "field": "ask", "value": "What is on the agenda for our discovery call?"},
                {"label": "Can I invite a colleague?", "field": "ask", "value": "Can I invite a colleague to the call?"},
                {"label": "Can I reschedule the time?", "field": "booking_window", "value": "reschedule"},
            ]
            confirm_card = {"type": "booking", "title": "Confirmed", **booked}
            if not booked.get("live"):
                confirm_card["disclaimer"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
                confirm_card["note"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="handoff",
                route="booking",
                chips=post_chips,
                cards=[confirm_card],
                qualification=qual,
                estimate=estimate,
                booking=booked,
                handoff_summary=handoff,
            )

        if session.stage in ("handoff", "booking") or brief_ready(brief):
            qual = qualify(brief, config.qualification, config.services, has_email=True)
            estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
            handoff = _handoff(config, brief, contact, qual, estimate, None)
            session.handoff_summary = handoff
            _lead(db, tenant, session, email, qual, estimate, handoff)
            notify_slack(
                db,
                session.id,
                tenant,
                f"Lead email captured for {config.brand.name}: {email}",
            )
            tz_name = getattr(config.brand, "timezone", "") or "Asia/Kolkata"
            slots, live = list_slots(tenant, tz_name=tz_name)
            pick_card = {"type": "booking", "title": "Pick a time", "live": live, "slots": slots}
            if not live:
                pick_card["disclaimer"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
                pick_card["note"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
            reply = f"Thank you! I've recorded your email ({email}) for the proposal. Here are a few times for a short discovery call with our team:"
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="booking",
                route="booking",
                chips=[{"label": slot["label"], "field": "booking_slot", "value": slot["slot_iso"]} for slot in slots],
                cards=[pick_card],
                qualification=qual,
                estimate=estimate,
                handoff_summary=handoff,
            )

    # Post-booking specific questions (colleague, agenda, or chit-chat ack)
    if session.booking_json and text:
        if _is_ack(text):
            try:
                booked = json.loads(session.booking_json)
            except Exception:
                booked = {}
            booking_label = booked.get("label") or booked.get("slot_iso") or "your scheduled session"
            reply = f"You're welcome! You're all set for {booking_label}. I can share the agenda or help you reschedule."
            post_chips = [
                {"label": "What is on the agenda?", "field": "ask", "value": "What is on the agenda for our discovery call?"},
                {"label": "Can I reschedule the time?", "field": "booking_window", "value": "reschedule"},
            ]
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage=session.stage or "handoff",
                route="ack",
                chips=post_chips,
                timings=timings,
            )
        if re.search(r"\b(colleague|coworker|team member|partner|invite)\b", text.lower()):
            reply = (
                "Yes, absolutely! Feel free to forward the calendar invitation or invite any team members, "
                "technical leads, or stakeholders to the call. Having key collaborators present makes the "
                "scoping session even more productive."
            )
            post_chips = [
                {"label": "What is on the agenda?", "field": "ask", "value": "What is on the agenda for our discovery call?"},
                {"label": "Can I reschedule the time?", "field": "booking_window", "value": "reschedule"},
            ]
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="handoff",
                route="booking_faq",
                chips=post_chips,
            )
        if re.search(r"\b(agenda|what to expect|discuss on the call|happen on the call)\b", text.lower()):
            duration_min = get_platform().calendar.duration_minutes
            reply = (
                f"Our {duration_min}-minute discovery call agenda covers:\n"
                "1. **Requirements & Scope**: Deep-dive into your core user workflows and product goals.\n"
                "2. **Technical Architecture**: Aligning on stack, security, APIs, and key integrations.\n"
                "3. **Delivery & Team Sizing**: Reviewing sprint roadmap, squad composition, and MVP boundaries.\n"
                "4. **Timeline & Budget**: Sign-off on budget bands and engineering kickoff steps."
            )
            post_chips = [
                {"label": "Can I invite a colleague?", "field": "ask", "value": "Can I invite a colleague to the call?"},
                {"label": "Can I reschedule the time?", "field": "booking_window", "value": "reschedule"},
            ]
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="handoff",
                route="booking_faq",
                chips=post_chips,
            )

    if field == "show_portfolio":
        cases = match_portfolio(brief, config.portfolio)
        is_sample = getattr(config, "slug", "") == "demo" or tenant.slug == "demo"
        for c in cases:
            if is_sample or c.get("is_sample"):
                c["is_sample"] = True
        return _finish(
            session, brief, contact, summary,
            message="Here are relevant sample case studies and similar projects from our past work:" if is_sample else "Here are relevant case studies and similar projects from our past work:",
            stage=session.stage or "advising",
            route="portfolio",
            chips=[BOOK_CHIP],
            cards=[{"type": "portfolio", "title": "Similar work", "cases": cases, "is_sample": is_sample}],
            portfolio=cases,
            timings=timings,
        )

    if field == "close_out":
        return _finish(
            session, brief, contact, summary,
            message="Thanks for chatting with us! If you'd like to talk through your project with our engineering team, feel free to book a short call anytime.",
            stage=session.stage or "discovery",
            route="discovery",
            chips=[BOOK_CHIP],
            timings=timings,
        )

    direct_objection = match_objection(text, config.objections) if (text and not field) else None
    if direct_objection:
        return _finish(
            session, brief, contact, summary,
            message=direct_objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=_next_chips(brief, has_booking=bool(session.booking_json)),
            timings=timings,
        )

    filled = False
    if field and field not in ACTION:
        brief.apply_chip(field, value)
        _note_flags(brief)
        filled = True
    elif text:
        if brief.role_unconfirmed:
            lowered = text.lower()
            if any(w in lowered for w in ("study", "practice", "college", "homework", "student", "class", "course", "academic")):
                brief.decision_role = "intern_or_student"
                brief.role_unconfirmed = False
                filled = True
            elif any(w in lowered for w in ("live", "company", "client", "business", "work", "commercial", "startup", "founder", "team", "production")):
                brief.decision_role = None
                brief.role_unconfirmed = False
                filled = True
        if not filled:
            pending = _pending(brief)
            last_assistant_msg = ""
            for item in reversed(history):
                if item.get("role") == "assistant" and item.get("content"):
                    last_assistant_msg = str(item.get("content"))
                    break

            last_q = _last_question_sentence(last_assistant_msg)
            lowered_text = text.lower().strip()
            # Handle direct yes/no answers to specific discovery questions
            # Use only the last question sentence of that message when it contains "integration" or "admin"
            is_integration_q = "integration" in last_q or (pending == "integrations" and not last_q)
            is_admin_q = "admin" in last_q or (pending == "admin" and not last_q)

            if is_integration_q and lowered_text in (
                "no", "none", "nope", "nah", "no integrations", "none needed", "not needed", "no need", "none on day one"
            ):
                brief.integrations = ["none"]
                _note_flags(brief)
                filled = True
            elif is_admin_q and lowered_text in (
                "yes", "yep", "yeah", "sure", "true", "1"
            ):
                brief.admin = True
                _note_flags(brief)
                filled = True
            elif is_admin_q and lowered_text in (
                "no", "nope", "nah", "false", "0"
            ):
                brief.admin = False
                filled = True

        if not filled:
            has_pending_discovery = (
                not brief_ready(brief)
                and not bool(session.estimate_json)
                and (session.stage not in ("advising", "handoff", "disqualified"))
            )
            # Skip LLM extractor for chip clicks and acknowledgements, or when booking exists and brief is ready
            is_ack = _is_ack(text, has_pending_discovery)
            if is_chip_click or is_ack or (bool(session.booking_json) and brief_ready(brief)):
                extracted = {}
            else:
                t0_ext = time.perf_counter()
                extracted = extract_slots(text, pending, brief)
                timings["extractor"] += (time.perf_counter() - t0_ext) * 1000.0
            if extracted.get("is_off_topic"):
                return _finish(
                    session, brief, contact, summary,
                    message=(
                        f"I'm {config.brand.name}'s project consultant, specializing in custom software scoping, "
                        f"architecture, and estimation for web and mobile applications. "
                        f"While I can't assist with general trivia or standalone coding questions, I'd love to help if you're exploring "
                        f"building a digital product or application! What type of project are you considering?"
                    ),
                    stage=session.stage or "discovery",
                    route="off_topic",
                    chips=_next_chips(brief, has_booking=bool(session.booking_json)),
                    timings=timings,
                )
            if extracted and not extracted.get("is_question") and apply_extracted_slots(brief, extracted, pending):
                _note_flags(brief)
                filled = True
            elif not OPEN.search(text) and pending and _apply_free_text(brief, pending, text):
                # 2. Fallback to deterministic regex matching
                _note_flags(brief)
                filled = True
            elif re.search(r"\b(student|intern)\b", text.lower()) and not brief.decision_role:
                brief.role_unconfirmed = True
                filled = True
            elif found and not brief_ready(brief):
                pending = _pending(brief)
                if pending:
                    p_text = prompt_for(brief, pending)
                    return _finish(
                        session, brief, contact, summary,
                        message=f"Thank you, saved your email ({contact['email']})! Now, to help size your project: {p_text}",
                        stage="discovery",
                        route="discovery",
                        chips=chips_for_field(pending, brief),
                        timings=timings,
                    )

    if filled or (field and field not in ACTION):
        changed_fields = [f for f in brief_track_fields if getattr(brief, f) != initial_brief_state[f] and getattr(brief, f)]
        return _after_brief(session, config, brief, contact, summary, user_text=text, history=history, timings=timings, changed_fields=changed_fields)

    # Skip embedding and retrieval for pure acknowledgements
    has_pending_discovery = (
        not brief_ready(brief)
        and not bool(session.estimate_json)
        and (session.stage not in ("advising", "handoff", "disqualified"))
    )
    is_ack = _is_ack(text, has_pending_discovery)
    if not is_chip_click and is_ack:
        estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
        if brief and brief_ready(brief):
            reply_msg = (
                f"Glad that aligns! If you'd like to talk through the technical architecture, team setup, or confirm the timeline, "
                f"feel free to schedule a short discovery call with our team anytime."
            )
        else:
            reply_msg = fallback_message(config, brief, estimate, query=text)
        extra = _continuation(brief, history)
        if extra:
            reply_msg = f"{reply_msg}\n\n{extra[0]}"
            chips = list(extra[1])
        else:
            chips = [
                {"label": "Can I reschedule?", "field": "booking_window", "value": "reschedule"},
                PORTFOLIO_CHIP,
            ] if session.booking_json else ([BOOK_CHIP, PORTFOLIO_CHIP] if brief_ready(brief) else _next_chips(brief))
        return _finish(
            session, brief, contact, summary,
            message=reply_msg,
            stage="advising" if brief_ready(brief) else "discovery",
            route="fallback",
            chips=chips,
            passages=[],
            chunk_ids=[],
            query="",
            score=0.0,
            estimate=estimate,
            timings=timings,
        )

    semantic_objection = _objection(db, tenant, config, text, session.nda_accepted) if (text and not field) else None
    if semantic_objection:
        return _finish(
            session, brief, contact, summary,
            message=semantic_objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=_next_chips(brief, has_booking=bool(session.booking_json)),
        )

    if has_pending_discovery and text and not _is_question_like(text):
        changed_fields = [f for f in brief_track_fields if getattr(brief, f) != initial_brief_state[f] and getattr(brief, f)]
        return _after_brief(session, config, brief, contact, summary, user_text=text, history=history, timings=timings, changed_fields=changed_fields)

    raw_queries = lookup_queries(text, summary, previous[-3:]) or [text]
    queries = [rewrite_query_with_brief(q, brief) for q in raw_queries]
    filters = query_filters(text, service=brief.service, industry=brief.industry)

    query_embedding_duration_ms.set(0.0)
    t_ret_start = time.perf_counter()
    try:
        faq_hits = _merge(db, tenant, queries, "faq", session.nda_accepted, filters)
        is_faq_eligible = False
        if faq_hits and faq_hits[0].score >= get_platform().faq_min_score:
            top_hit = faq_hits[0]
            msg_tokens = [w.strip("?,.!;:\"'()[]{}~`").lower() for w in text.split()]
            msg_tokens = [w for w in msg_tokens if w]
            is_q_or_long = bool(OPEN.search(text) or "?" in text or len(msg_tokens) >= 5)
            if is_q_or_long:
                if top_hit.score >= 0.80:
                    is_faq_eligible = True
                else:
                    content_tokens_orig = {t for t in msg_tokens if t not in ROUTER_STOPWORDS and len(t) >= 2}
                    faq_raw = f"{getattr(top_hit, 'title', '')} {top_hit.content}".lower()
                    faq_tokens = set(re.findall(r"\b[a-z0-9]+\b", faq_raw))
                    if bool(content_tokens_orig & faq_tokens):
                        is_faq_eligible = True

        if is_faq_eligible:
            t_ret_total = (time.perf_counter() - t_ret_start) * 1000.0
            timings["query_embedding"] = query_embedding_duration_ms.get()
            timings["retrieval_db"] = max(0.0, t_ret_total - timings["query_embedding"])
            hit = faq_hits[0]
            message = hit.content
            extra = _continuation(brief, history)
            if extra:
                message = f"{message}\n\n{extra[0]}"
                chips = list(extra[1])
            else:
                chips = [
                    {"label": "Can I reschedule?", "field": "booking_window", "value": "reschedule"},
                    PORTFOLIO_CHIP,
                ] if session.booking_json else [BOOK_CHIP, PORTFOLIO_CHIP]
            return _finish(
                session, brief, contact, summary,
                message=message,
                stage="discovery" if not brief_ready(brief) else "advising",
                route="faq",
                chips=chips,
                passages=[hit.content],
                chunk_ids=[hit.id],
                query=queries[0],
                score=hit.score,
                timings=timings,
            )

        hits = _merge(db, tenant, queries, "knowledge", session.nda_accepted, filters)
    finally:
        t_ret_total = (time.perf_counter() - t_ret_start) * 1000.0
        timings["query_embedding"] = query_embedding_duration_ms.get()
        timings["retrieval_db"] = max(0.0, t_ret_total - timings["query_embedding"])

    decision, score = grade(queries[0], hits)
    strong = _strong_hits(hits)
    if decision == "show" and strong:
        t0_ans = time.perf_counter()
        message = grounded_answer(queries[0], strong)
        timings["answer_llm"] += (time.perf_counter() - t0_ans) * 1000.0
        chunk_ids = [hit.id for hit in strong]
        route = "rag"
        has_sample = any(hit.metadata.get("is_sample") or (getattr(hit, "source_id", "") and "case" in getattr(hit, "source_id", "").lower()) for hit in strong) or (tenant.slug == "demo" and any("case" in (hit.source or "").lower() or "portfolio" in (hit.source or "").lower() for hit in strong))
        if has_sample and "sample" not in message.lower():
            message = f"Sample case study: {message}"
    else:
        estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
        platform = get_platform()
        is_weak = decision == "weak" or (platform.weak_min_score <= score < platform.show_min_score)
        weak_notes = hits[:3] if is_weak and hits else None
        t0_ans = time.perf_counter()
        message = fallback_message(config, brief, estimate, query=queries[0], notes=weak_notes)
        timings["answer_llm"] += (time.perf_counter() - t0_ans) * 1000.0
        chunk_ids = []
        route = "fallback"
    extra = _continuation(brief, history)
    if extra:
        field_target = next_discovery_field(brief) or ""
        repeat = brief.field_attempts.get(field_target, 0) > 1
        if repeat:
            message = f"{message}\n\n{extra[0]}"
        elif not message.strip().endswith("?") and not any(phrase in message.lower() for phrase in ["looking to build", "what kind of product", "what are you looking", "what should this"]):
            message = f"{message}\n\n{extra[0]}"
        chips = list(extra[1])
    elif brief_ready(brief):
        chips = [
            {"label": "Can I reschedule?", "field": "booking_window", "value": "reschedule"},
            PORTFOLIO_CHIP,
        ] if session.booking_json else [BOOK_CHIP, PORTFOLIO_CHIP]
    else:
        chips = []
    return _finish(
        session, brief, contact, summary,
        message=message,
        stage="advising" if brief_ready(brief) else "discovery",
        route=route,
        chips=chips,
        passages=[hit.content for hit in strong] if route == "rag" else [],
        chunk_ids=chunk_ids,
        query=queries[0] if text else "",
        score=score,
        estimate=estimate_project(brief, config.pricing) if brief_ready(brief) else None,
        timings=timings,
    )


def _book(db, tenant, config, session, brief, contact, summary, slot_iso: str) -> dict:
    email = contact.get("email") or ""
    tz_name = getattr(config.brand, "timezone", "") or "Asia/Kolkata"
    booked = confirm_slot(
        tenant,
        slot_iso,
        f"Discovery call — {config.brand.name}",
        email,
        tz_name=tz_name,
    )
    qual = qualify(brief, config.qualification, config.services, has_email=bool(email))
    estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
    handoff = _handoff(config, brief, contact, qual, estimate, booked)
    session.booking_json = json.dumps(booked)
    session.handoff_summary = handoff
    save_booking_pairs(db, tenant.id, session.id)
    notify_slack(
        db,
        session.id,
        tenant,
        f"Booking for {config.brand.name}: {booked.get('label') or slot_iso} ({email or 'no email yet'})",
    )
    if email:
        _lead(db, tenant, session, email, qual, estimate, handoff)
    message = f"You're booked for {booked.get('label') or slot_iso}."
    if not booked.get("live"):
        message += " Demo booking: no calendar invite is sent until Google Calendar is connected."
    if booked.get("meet_url"):
        message += f" Meet link: {booked['meet_url']}"
    if not email:
        message += " Reply with your work email so the invite has somewhere to go."
    card = {"type": "booking", "title": "Booked", **booked}
    if not booked.get("live"):
        card["disclaimer"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
        card["note"] = "Demo booking: no calendar invite is sent until Google Calendar is connected."
    return _finish(
        session, brief, contact, summary,
        message=message,
        stage="handoff",
        route="booking",
        chips=[],
        cards=[card],
        qualification=qual,
        estimate=estimate,
        booking=booked,
        handoff_summary=handoff,
    )


def _synthesize_estimate_message(config: TenantConfig, brief: ProjectBrief, estimate: dict) -> str:
    brand_name = config.brand.name
    fallback = (
        f"A first-pass range for this is **{estimate['range_label']}** over about **{estimate['timeline_weeks']} weeks**.\n"
        f"*{config.brand.disclaimer}*"
    )
    if not llm_available():
        return fallback

    role = f"as a {brief.decision_role}" if brief.decision_role else ""
    goal = brief.goal or brief.service or "custom software project"
    platforms = ", ".join(brief.platforms) if brief.platforms else "agreed platforms"
    timeline = f"targeted for {brief.timeline}" if brief.timeline else ""

    prompt = (
        f"You are the senior enterprise pre-sales software consultant at {brand_name}. "
        f"We are scoping: Goal: '{goal}', Platforms: '{platforms}', Role: '{role}', Timeline: '{timeline}', Budget: '{brief.budget_band}'. "
        f"The calculated indicative engineering estimate is {estimate['range_label']} over ~{estimate['timeline_weeks']} weeks. "
        f"Write a concise, polished executive summary (2-3 sentences max) tailored to the visitor's goal and role. "
        f"Acknowledge their objective, highlight how an MVP release is structured, and clearly state the indicative range {estimate['range_label']} and {estimate['timeline_weeks']} weeks timeline. "
        f"Include a note that this is an indicative estimate, not a fixed quote. "
        f'Return JSON {{"message": "..."}}.'
    )
    try:
        data = complete_json(SOLUTION_SYSTEM_PROMPT, prompt, mode="request")
        msg = str(data.get("message") or "").strip()
        if msg:
            return msg
    except LLMError:
        pass
    return fallback


def _field_asked_count(history: list[dict], field: str | None) -> int:
    if not history or not field:
        return 0
    from backend.app.screening.slots import DISCOVERY_PROMPTS, REPHRASED_PROMPTS

    prompt_snippet = DISCOVERY_PROMPTS.get(field, "").lower()[:25]
    rephrased_snippet = REPHRASED_PROMPTS.get(field, "").lower()[:25]
    count = 0
    for item in history:
        if item.get("role") != "assistant":
            continue
        content = item.get("content", "").lower()
        if (prompt_snippet and prompt_snippet in content) or (rephrased_snippet and rephrased_snippet in content):
            count += 1
    return count


def format_shape_message(arch: dict, mvp_res: dict) -> str:
    channels = ", ".join(arch.get("frontend") or ["Web / Mobile"])
    flow = "; ".join((mvp_res.get("mvp") or [])[:3])
    backend = ", ".join(arch.get("backend") or ["API + Database"])
    lines = [
        "Here is the architectural shape based on what you've shared:",
        f"• Channels and UX: {channels}",
        f"• Core flow: {flow}",
        f"• Backend and APIs: {backend}",
    ]
    return "\n".join(lines)


def build_shape_card(arch: dict, mvp_res: dict) -> dict:
    return {
        "type": "shape",
        "title": "Channels, core flow, and architecture",
        "channels_ux": list(arch.get("frontend") or []),
        "core_flow": list((mvp_res.get("mvp") or [])[:3]),
        "backend_apis": list(arch.get("backend") or []),
    }


def budget_fit_line(
    band: str | None,
    estimate: dict | None,
    ranges: dict | None,
) -> str:
    if not band or not ranges or not estimate:
        return ""
    if band == "exploring" or band not in ranges:
        return ""
    band_range = ranges.get(band)
    if not band_range or not isinstance(band_range, (list, tuple)) or len(band_range) < 2:
        return ""

    band_min, band_max = band_range[0], band_range[1]
    est_low = estimate.get("low")
    est_high = estimate.get("high")

    if est_low is None or est_high is None:
        nums = [int(n.replace(",", "")) for n in re.findall(r"([0-9,]+)", estimate.get("range_label", ""))]
        if len(nums) >= 2:
            est_low, est_high = nums[0], nums[1]
        elif len(nums) == 1:
            est_low = est_high = nums[0]
        else:
            return ""

    if band_max is not None and band_max < est_low:
        return "Your budget band sits below this first-pass range. The usual lever is a leaner scope; I can show a Core-only cut."
    if band_min is not None and band_min > est_high:
        return "Your budget band is above this first-pass range, so there is room to add scope."
    return "Your budget band overlaps this first-pass range."


def recap_line_from_brief(config: TenantConfig, brief: ProjectBrief) -> str:
    service_label = ""
    if brief.service and config.services and brief.service in config.services.in_scope:
        service_label = config.services.in_scope[brief.service].label
    elif brief.service:
        service_label = brief.service.replace("_", " ").title()
    else:
        service_label = "Custom Software"

    platforms_str = ", ".join(brief.platforms) if brief.platforms else "Web"
    features_list = (brief.features or [])[:4]
    features_str = ", ".join(features_list) if features_list else "core features"

    # Format timeline without duration numbers or weeks/months
    t_clean = (brief.timeline or "flexible").lower()
    if "asap" in t_clean:
        timeline_str = "ASAP launch"
    elif "flexible" in t_clean or "unknown" in t_clean:
        timeline_str = "flexible target"
    elif "1_3" in t_clean:
        timeline_str = "near-term target"
    elif "3_6" in t_clean:
        timeline_str = "medium-term target"
    else:
        timeline_str = re.sub(r"[\$€£₹]|USD|\b(weeks?|months?|days?|\d+)\b", "", t_clean).strip() or "target milestone"

    # Format budget band without currency symbols
    b_clean = (brief.budget_band or "exploring").lower()
    if "under_15" in b_clean:
        budget_str = "starter tier"
    elif "15_40" in b_clean:
        budget_str = "growth tier"
    elif "40_80" in b_clean:
        budget_str = "scale tier"
    elif "80k_plus" in b_clean or "80k" in b_clean:
        budget_str = "enterprise tier"
    elif "exploring" in b_clean:
        budget_str = "exploring budget"
    else:
        budget_str = re.sub(r"[\$€£₹]|USD|\d+", "", b_clean).strip() or "exploring budget"

    goal_str = (brief.goal or "core project")[:120].replace("\n", " ").strip()

    return f"{service_label}, {platforms_str}, {features_str}, {timeline_str}, {budget_str}, {goal_str}"


def _after_brief(
    session,
    config,
    brief,
    contact,
    summary,
    user_text: str = "",
    history: list[dict] | None = None,
    timings: dict | None = None,
    changed_fields: list[str] | None = None,
) -> dict:
    timings = timings or {}
    qual = qualify(brief, config.qualification, config.services, has_email=bool(contact.get("email")))
    if brief.role_unconfirmed:
        return _finish(
            session, brief, contact, summary,
            message="Could you confirm your role and whether you're building a live project for a company, or is this primarily for study or practice?",
            stage="discovery",
            route="discovery",
            chips=[
                {"label": "Live project at a company", "field": "confirm_role", "value": "company_project"},
                {"label": "Study or practice", "field": "confirm_role", "value": "study_or_practice"},
            ],
            qualification=qual,
            timings=timings,
        )
    if qual["band"] == "disqualify":
        if brief.out_of_scope:
            msg = (
                f"{config.brand.name} specializes in bespoke web platforms, cross-platform mobile apps (iOS & Android), "
                f"AI integrations, and dedicated engineering pods. We don't take on this category of work, "
                f"but if you have a custom software product or platform in mind, we'd be delighted to explore it."
            )
        else:
            msg = f"{qual['reasons'][0]} If your project scope evolves or you'd like to consult with our technical leadership, feel free to schedule a short call."
        return _finish(
            session, brief, contact, summary,
            message=msg,
            stage="disqualified",
            route="discovery",
            chips=[BOOK_CHIP],
            qualification=qual,
            timings=timings,
        )
    if brief_ready(brief):
        return _estimate(session, config, brief, contact, summary, qual, timings=timings)
    field = next_discovery_field(brief)
    attempts = brief.field_attempts.get(field or "", 0)
    repeat = attempts >= 1
    if field:
        brief.field_attempts[field] = attempts + 1
    t0_ans = time.perf_counter()
    prompt_msg = (
        prompt_for(brief, field, repeat=repeat)
        if repeat
        else synthesize_discovery_prompt(
            config,
            brief,
            field,
            user_text=user_text,
            session_id=str(session.id or ""),
            changed_fields=changed_fields,
            attempt=attempts,
        )
    )
    if not repeat:
        timings["answer_llm"] = timings.get("answer_llm", 0.0) + (time.perf_counter() - t0_ans) * 1000.0
    chips = chips_for_field(field, brief, repeat=repeat) or ensure_chips(brief, prompt_msg)
    cards = []
    if (
        brief.platforms
        and (brief.features or brief.features_confirmed)
        and not getattr(brief, "shape_shown", False)
    ):
        brief.shape_shown = True
        arch = recommend_architecture(brief, config.services)
        mvp_res = recommend_mvp(brief)
        cards.append(build_shape_card(arch, mvp_res))
        shape_text = format_shape_message(arch, mvp_res)
        prompt_msg = f"{shape_text}\n\n{prompt_msg}"

    return _finish(
        session, brief, contact, summary,
        message=prompt_msg,
        stage="discovery",
        route="discovery",
        chips=chips,
        cards=cards,
        qualification=qual,
        timings=timings,
    )


def _estimate(session, config, brief, contact, summary, qual, timings: dict | None = None) -> dict:
    timings = timings or {}
    estimate = estimate_project(brief, config.pricing)
    architecture = recommend_architecture(brief, config.services)
    mvp = recommend_mvp(brief)
    cases = match_portfolio(brief, config.portfolio)
    is_sample = getattr(config, "slug", "") == "demo"
    for c in cases:
        if is_sample or c.get("is_sample"):
            c["is_sample"] = True

    recap = recap_line_from_brief(config, brief)
    fit_line = budget_fit_line(brief.budget_band, estimate, config.qualification.budget_band_ranges_usd)

    parts = [
        f"{recap}. If anything is off, tell me and I'll update the estimate.",
        f"A first-pass indicative range for this scope is **{estimate['range_label']}** over about **{estimate['timeline_weeks']} weeks**.\n*{config.brand.disclaimer}*",
        "That's a first-pass range based on typical scope for this kind of project.",
    ]
    if fit_line:
        parts.append(fit_line)
    if not brief.company_size:
        parts.append(DISCOVERY_PROMPTS["company_size"])

    message = "\n\n".join(parts)

    chips = []
    if "leaner scope" in fit_line:
        chips.append({"label": "Show a leaner cut", "field": "view_mvp", "value": "leaner_cut"})
    chips.extend([
        {"label": "Sharpen this estimate", "field": "sharpen_estimate", "value": "sharpen"},
        {"label": "See the MVP", "field": "view_mvp", "value": "mvp"},
        {"label": "See sample projects", "field": "show_portfolio", "value": "yes"},
        {"label": "Book a call", "field": "booking_window", "value": "this_week"},
        {"label": "Talk to a human", "field": "talk_human", "value": "human"},
    ])

    cards = [
        {
            "type": "estimate",
            "title": "Indicative range",
            "range": estimate["range_label"],
            "weeks": estimate["timeline_weeks"],
            "team": estimate["team"],
            "inclusions": estimate["inclusions"],
            "exclusions": estimate["exclusions"],
            "assumptions": estimate["assumptions"],
            "disclaimer": config.brand.disclaimer,
        },
        {
            "type": "architecture",
            "title": "Architecture",
            "frontend": architecture["frontend"],
            "backend": architecture["backend"],
            "notes": architecture["notes"],
        },
        {"type": "mvp", "title": "MVP", "mvp": mvp["mvp"], "later": mvp["later"]},
        {"type": "portfolio", "title": "Similar work", "cases": cases, "is_sample": is_sample},
    ]
    return _finish(
        session, brief, contact, summary,
        message=message,
        stage="advising",
        route="estimate",
        chips=chips,
        cards=cards,
        qualification=qual,
        estimate=estimate,
        architecture=architecture,
        mvp=mvp,
        portfolio=cases,
        timings=timings,
    )


def _continuation(brief: ProjectBrief, history: list[dict] | None = None) -> tuple[str, list[dict]] | None:
    if brief_ready(brief):
        return None
    field = next_discovery_field(brief)
    if not field or field == "company_size":
        return None
    attempts = brief.field_attempts.get(field, 0)
    repeat = attempts >= 1
    brief.field_attempts[field] = attempts + 1
    return prompt_for(brief, field, repeat=repeat), chips_for_field(field, brief, repeat=repeat)


def _next_chips(brief: ProjectBrief, has_booking: bool = False) -> list[dict]:
    if has_booking:
        return [
            {"label": "Can I reschedule?", "field": "booking_window", "value": "reschedule"},
            PORTFOLIO_CHIP,
        ]
    if brief_ready(brief):
        chips = [BOOK_CHIP, PORTFOLIO_CHIP]
        if not brief.company_size:
            return chips_for_field("company_size") + chips
        return chips
    field = next_discovery_field(brief)
    return chips_for_field(field or "service", brief)


def _pending(brief: ProjectBrief) -> str | None:
    if not brief_ready(brief):
        field = next_discovery_field(brief)
        if field and field != "company_size":
            return field
        return field
    if not brief.company_size:
        return "company_size"
    return None


def _apply_free_text(brief: ProjectBrief, field: str, text: str) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if field == "service":
        mapped = _service(cleaned)
        if mapped == "out":
            brief.out_of_scope = cleaned
            return True
        if not mapped:
            return False
        brief.service = mapped
        return True
    if field == "platforms":
        mapped = _platforms(cleaned)
        if not mapped:
            return False
        brief.platforms = mapped
        return True
    if field == "timeline":
        mapped = _timeline(cleaned)
        if not mapped:
            return False
        brief.timeline = mapped
        return True
    if field == "budget_band":
        mapped = _budget(cleaned)
        if not mapped:
            return False
        brief.budget_band = mapped
        return True
    if field == "decision_role":
        mapped = _role(cleaned)
        if not mapped:
            return False
        if mapped == "intern_or_student":
            brief.role_unconfirmed = True
            return True
        brief.decision_role = mapped
        brief.role_unconfirmed = False
        return True
    if field == "company_size":
        mapped = _size(cleaned)
        brief.company_size = mapped or cleaned[:80]
        return True
    if field == "features":
        brief.features = [part.strip() for part in cleaned.split(",") if part.strip()]
        brief.features_confirmed = True
        return True
    if field == "feature_detail":
        brief.feature_detail = cleaned
        return True
    if field == "integrations":
        lowered = cleaned.lower()
        if lowered in ("no", "none", "nope", "nah", "no integrations", "none needed", "not needed", "no need", "none on day one"):
            brief.integrations = ["none"]
            return True
        brief.integrations = [part.strip() for part in cleaned.split(",") if part.strip()]
        return True
    if field == "admin":
        brief.admin = cleaned.lower() in ("yes", "true", "yep", "sure", "1", "yeah")
        return True
    if field in brief.model_fields:
        setattr(brief, field, cleaned)
        return True
    return False


def _service(text: str) -> str | None:
    lowered = text.lower()
    if any(token in lowered for token in OUT_OF_SCOPE):
        return "out"
    if "mobile" in lowered:
        return "mobile_app"
    if "staff" in lowered or "augment" in lowered:
        return "staff_augmentation"
    if "design" in lowered or "ui/ux" in lowered or lowered.strip() in {"ui", "ux"}:
        return "ui_ux"
    if re.search(r"\b(ai|llm|gpt|chatgpt|openai|chatbot|machine\s+learning)\b", lowered):
        return "ai_product"
    if "web" in lowered or "saas" in lowered:
        return "web_app"
    return None


def _platforms(text: str) -> list[str] | None:
    lowered = text.lower()
    if "ios" in lowered and "android" in lowered or "both" in lowered:
        return ["ios", "android"]
    if "ios" in lowered or "iphone" in lowered:
        return ["ios"]
    if "android" in lowered:
        return ["android"]
    if "web" in lowered:
        return ["web"]
    return None


def _timeline(text: str) -> str | None:
    lowered = text.lower()
    if "asap" in lowered or "soon" in lowered:
        return "asap"
    if "flex" in lowered or "no rush" in lowered:
        return "flexible"

    month_match = re.search(r"(\d+)\s*(?:-\s*(\d+)|\s+to\s+(\d+))?\s*months?\b", lowered)
    if month_match:
        upper = month_match.group(3) or month_match.group(2) or month_match.group(1)
        n = int(upper)
        if n <= 3:
            return "1_3_months"
        elif 4 <= n <= 6:
            return "3_6_months"
        else:
            return "flexible"

    word_map = {"one": 1, "two": 2, "three": 3, "four": 4, "five": 5, "six": 6, "seven": 7, "eight": 8, "nine": 9, "ten": 10, "twelve": 12}
    word_match = re.search(r"\b(one|two|three|four|five|six|seven|eight|nine|ten|twelve)\s+months?\b", lowered)
    if word_match:
        n = word_map[word_match.group(1)]
        if n <= 3:
            return "1_3_months"
        elif 4 <= n <= 6:
            return "3_6_months"
        else:
            return "flexible"

    if "quarter" in lowered or "next month" in lowered or "1 month" in lowered:
        return "1_3_months"
    if "3_6" in lowered or "3 to 6" in lowered:
        return "3_6_months"
    if "1_3" in lowered or "1 to 3" in lowered:
        return "1_3_months"
    return None


def _budget(text: str) -> str | None:
    lowered = text.lower().replace(",", "")
    if "explor" in lowered or "not sure" in lowered:
        return "exploring"

    if not re.search(r"(\$|usd|dollars?|\b\d+k\b)", lowered):
        return None

    vals = []
    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*k\b", lowered):
        vals.append(float(m.group(1)) * 1000.0)

    for m in re.finditer(r"(?:\$|usd\s*)\s*(\d+(?:\.\d+)?)\s*(k)?\b", lowered):
        mult = 1000.0 if m.group(2) else 1.0
        vals.append(float(m.group(1)) * mult)

    for m in re.finditer(r"\b(\d+(?:\.\d+)?)\s*(?:dollars?|usd)\b", lowered):
        vals.append(float(m.group(1)))

    if not vals:
        return None

    upper = max(vals)
    if upper < 15000:
        return "under_15k"
    elif upper < 40000:
        return "15_40k"
    elif upper < 80000:
        return "40_80k"
    else:
        return "80k_plus"


def _role(text: str) -> str | None:
    lowered = text.lower()
    if "intern" in lowered or "student" in lowered:
        if re.search(r"\b(my\s+cousin|his|her|their|friend|my\s+friend|our\s+intern|my\s+brother|my\s+sister)\b.{0,30}\b(student|intern|college)\b", lowered):
            return None
        return "intern_or_student"
    if re.search(r"\b(founder|ceo|exec|executive|cto|co-founder)\b", lowered):
        return "founder_or_exec"
    if re.search(r"\bproduct\s+(lead|manager|owner|head|director)\b|\b(lead|manager|owner)\s+of\s+product\b|\bops\b|\boperations\b", lowered):
        return "product_or_ops_lead"
    if re.search(r"\b(agency|reseller)\b", lowered):
        return "agency_or_reseller"
    if re.search(r"\bmanager\b", lowered):
        return "manager"
    return None


def _size(text: str) -> str | None:
    lowered = text.lower()
    if re.search(r"\benterprise\b", lowered):
        return "enterprise"
    if re.search(r"\bmid\b|\bmid[- ]market\b", lowered):
        return "mid_market"
    if re.search(r"\b(smb|small)\b", lowered):
        return "smb"
    if re.search(r"\bstartup\b", lowered):
        return "startup"
    return None


def _note_flags(brief: ProjectBrief) -> None:
    blob = " ".join([brief.goal or "", " ".join(brief.features or [])]).lower()
    if re.search(r"\b(login|log in|sign[ -]?in|sign[ -]?up|authentication|user accounts?)\b", blob):
        brief.auth = True
    if re.search(r"\badmin\b", blob):
        brief.admin = True
    if re.search(r"\bmarketplace\b", blob):
        brief.marketplace = True
    if re.search(r"\b(realtime|real[- ]time|live[- ]chat)\b", blob):
        brief.realtime = True


def _objection(db, tenant, config, text, nda_accepted: bool):
    found = match_objection(text, config.objections)
    if found or not text:
        return found
    if len(text.split()) > 20:
        return None
    hits = search(db, tenant, text, kind="objection", k=1, nda_accepted=nda_accepted)
    if hits and hits[0].score >= get_platform().faq_min_score:
        return {"id": getattr(hits[0], "source_id", "") or hits[0].id, "reply": hits[0].content, "match": "semantic"}
    return None


def _strong_hits(hits: list) -> list:
    if not hits:
        return []
    floor = get_platform().show_min_score
    top = hits[0].score
    return [hit for hit in hits if hit.score >= floor and hit.score >= top - 0.12]


ROUTER_STOPWORDS = frozenset(
    """
    a about all also am an and any are as at be been being but by can cannot could did do does
    doing done for from get got had has have having he her here hers him his how i if in into is
    it its just me more most my no nor not of off on once only or other our out over own same she
    should so some such than that the their them then there these they this those to too us very
    was we were what when where which while who whom why will with would you your yours during
    """.split()
)


def _merge(db, tenant, queries: list[str], kind: str, nda_accepted: bool, filters: dict | None = None):
    merged = {}
    for query in queries:
        if not query.strip():
            continue
        for hit in search(db, tenant, query, kind=kind, nda_accepted=nda_accepted, filters=filters):
            score = hit.score
            if kind == "faq":
                q_words = [w.strip("?,.!;:\"'()[]{}~`").lower() for w in query.split()]
                q_words = [w for w in q_words if w and w not in ROUTER_STOPWORDS and len(w) >= 3]
                if q_words:
                    text_blob = f"{getattr(hit, 'title', '')} {hit.content}".lower()
                    overlap_ratio = sum(1 for w in q_words if w in text_blob) / len(q_words)
                    if overlap_ratio >= 0.6:
                        score = max(score, 0.82)
            current = merged.get(hit.doc_id)
            if current is None or score > current.score:
                hit.score = score
                merged[hit.doc_id] = hit
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)



def rewrite_query_with_brief(query: str, brief: ProjectBrief | None) -> str:
    if not brief or not query:
        return query or ""
    if _is_ack(query):
        return query
    cleaned = query.strip()
    is_question_like = bool(OPEN.search(cleaned) or "?" in cleaned)
    if not is_question_like:
        return cleaned

    tokens = [w.strip("?,.!;:\"'()[]{}~`").lower() for w in cleaned.split()]
    tokens = [w for w in tokens if w]
    rewrite_stopwords = frozenset({"a", "about", "an", "and", "are", "as", "at", "be", "by", "for", "from", "in", "is", "it", "of", "on", "or", "that", "the", "this", "to", "was", "with"})
    non_stopwords = [t for t in tokens if t not in rewrite_stopwords]
    if len(non_stopwords) < 3:
        return cleaned

    words = cleaned.split()
    known_tech = {"web", "mobile", "ios", "android", "ai", "flutter", "react", "python", "ledgerly", "harvest", "atlas", "zephyr"}
    has_specific_tech = any(w.strip("?,.!").lower() in known_tech for w in words)
    if not has_specific_tech and len(words) <= 6:
        enrichment = []
        if brief.service:
            service_label = brief.service.replace("_", " ")
            if service_label not in cleaned.lower():
                enrichment.append(service_label)
        if brief.platforms:
            for p in brief.platforms:
                if str(p).lower() not in cleaned.lower():
                    enrichment.append(str(p))
        if enrichment:
            return f"{cleaned} {' '.join(enrichment)}".strip()
    return cleaned


def _handoff(config, brief, contact, qual, estimate, booked) -> str:
    lines = [
        f"# Discovery summary — {config.brand.name}",
        f"Email: {contact.get('email') or 'not captured'}",
        f"Service: {brief.service or 'unspecified'}",
        f"Goal: {brief.goal or '—'}",
        f"Score: {qual.get('score')} ({qual.get('band')})",
    ]
    if estimate:
        lines.append(f"Range: {estimate['range_label']} / {estimate['timeline_weeks']} weeks")
    if booked:
        lines.append(f"Booking: {booked.get('label') or booked.get('slot_iso')}")
    return "\n".join(lines)


def _lead(db, tenant, session, email, qual, estimate, handoff) -> None:
    row = db.scalar(select(LeadRow).where(LeadRow.session_id == session.id))
    if row is None:
        row = LeadRow(session_id=session.id, tenant_id=tenant.id)
        db.add(row)
    row.email = email
    row.company = company_from_email(email)
    row.score = int(qual.get("score") or 0)
    row.band = qual.get("band") or ""
    row.estimate_snapshot = json.dumps(estimate or {})
    row.handoff_summary = handoff


def _finish(session, brief, contact, summary, **payload) -> dict:
    session.brief_json = brief.model_dump_json()
    session.contact_json = json.dumps(contact)
    session.summary = summary or ""
    session.stage = payload.get("stage") or session.stage
    if payload.get("qualification") is not None:
        session.qualification_json = json.dumps(payload["qualification"])
    if payload.get("estimate") is not None:
        session.estimate_json = json.dumps(payload["estimate"])
    if payload.get("architecture") is not None:
        session.architecture_json = json.dumps(payload["architecture"])
    if payload.get("mvp") is not None:
        session.mvp_json = json.dumps(payload["mvp"])
    if payload.get("portfolio") is not None:
        session.portfolio_json = json.dumps(payload["portfolio"])
    if payload.get("handoff_summary"):
        session.handoff_summary = payload["handoff_summary"]
    chips = list(payload.get("chips") or [])
    if not chips:
        chips = ensure_chips(
            brief,
            str(payload.get("message") or ""),
            list(payload.get("passages") or []),
        )
    raw_message = str(payload.get("message") or "")
    estimate_ctx = payload.get("estimate")
    if not estimate_ctx and session.estimate_json:
        try:
            estimate_ctx = json.loads(session.estimate_json)
        except Exception:
            estimate_ctx = None
    sanitized_message = sanitize_price_leaks(raw_message, estimate_ctx, visitor_budget=getattr(brief, "budget_band", None))
    result = {
        "message": sanitized_message,
        "stage": payload.get("stage") or "discovery",
        "chips": chips,
        "cards": payload.get("cards") or [],
        "route": payload.get("route") or "discovery",
        "chunk_ids": payload.get("chunk_ids") or [],
        "query": payload.get("query") or "",
        "score": payload.get("score") or 0,
        "qualification": payload.get("qualification"),
        "estimate": payload.get("estimate"),
        "booking": payload.get("booking"),
        "summary": summary,
        "contact": contact,
        "handoff_summary": payload.get("handoff_summary") or session.handoff_summary or "",
        "_timings": payload.get("timings") or {},
    }
    return result


def _brief(session: SessionRow) -> ProjectBrief:
    try:
        return ProjectBrief.model_validate_json(session.brief_json or "{}")
    except Exception:
        return ProjectBrief()


def _json(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}
