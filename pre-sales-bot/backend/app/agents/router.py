from __future__ import annotations

from datetime import datetime, timezone
import json
import logging
import os
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

log = logging.getLogger(__name__) 


def _resolve_flow(config: TenantConfig) -> str:
    env_override = os.environ.get("ENABLE_FAST_FLOW")
    if env_override is not None:
        return "fast" if env_override.strip().lower() in ("true", "1", "yes") else "classic"
    if hasattr(config, "brand") and hasattr(config.brand, "flow") and config.brand.flow:
        return str(config.brand.flow).strip().lower()
    return "classic"

from backend.app.agents.brief import ProjectBrief, brief_ready, next_discovery_field, next_sharpen_field
from backend.app.agents.discovery_synth import synthesize_discovery_prompt
from backend.app.agents.extractor import apply_extracted_slots, extract_slots, is_product_idea
from backend.app.agents.fallback import fallback_message
from backend.app.agents.suggestions import ensure_chips
from backend.app.core.llm import LLMError, complete_json, llm_available
from backend.app.core.guard import OutputRails, sanitize_duration_leaks, sanitize_price_leaks
from backend.app.core.platform import get_platform
from backend.app.engines.architecture import recommend_architecture
from backend.app.engines.calendar import confirm_slot, list_slots
from backend.app.engines.mvp import recommend_mvp
from backend.app.engines.objections import match_objection
from backend.app.engines.portfolio import match_portfolio
from backend.app.engines.pricing import estimate_project
from backend.app.engines.qualification import qualify
from backend.app.engines.notify import company_from_email, format_bant_handoff_message, notify_slack
from backend.app.learning.pairs import save_booking_pairs
from backend.app.memory.rewrite import lookup_queries, rolling_summary
from backend.app.core.security import (
    check_booking_ip_limit,
    check_email_submission_limit,
    current_ip,
    record_booking_for_ip,
)
from backend.app.models.entities import LeadRow, SessionRow, TenantRow
from backend.app.rag.filters import query_filters
from backend.app.rag.grade import grade, grounded_answer
from backend.app.rag.store import search
from backend.app.screening.slots import BOOK_CHIP, DISCOVERY_PROMPTS, PORTFOLIO_CHIP, chips_for_field, prompt_for
from backend.app.tenants.schema import TenantConfig, VoiceConfig

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
OPEN = re.compile(r"\?|^(what|how|who|why|when|where|can|do|does|is|are|have)\b", re.IGNORECASE)
BOOK = re.compile(r"\b(book|schedule|reschedule)\b.{0,40}\b(call|meeting|consultation|time)\b|\breschedule\b", re.IGNORECASE)
OUT_OF_SCOPE = ("shopify", "crypto", "web3", "homework", "student project")
ACTION = {"show_portfolio", "booking_window", "booking_slot", "nda", "close_out", "view_mvp", "email_instead", "continue_discovery", "sharpen_estimate", "talk_human"}

_OBJECTION_CUES = re.compile(
    r"\b(expensive|cost|costly|price|pricing|cheaper|discount|afford|budget\s+is\s+tight|too\s+long|slow|faster|fixed\s+price|fixed\s+bid|lump\s+sum|offshore|outsourced|negotiate|guarantee)\b",
    re.IGNORECASE,
)
_PRESSURE_WORDS = re.compile(
    r"\b(expensive|cost|costly|price|pricing|cheaper|cheap|discount|afford|tight|rate|fee|budget|timeline|deadline|urgent|urgently|hurry|rush|slow|faster|delay|guarantee|weeks?|months?)\b",
    re.IGNORECASE,
)
_STARTER_TEXTS = frozenset({
    "i have an app idea", "i have an idea", "app idea", "i'm just exploring costs",
    "im just exploring costs", "just exploring costs", "explore costs", "i need a web platform",
    "add ai to my product", "i want to add ai to my product", "talk to a human", "i have a web idea",
})
_ACK_TEXTS = frozenset({
    "ok", "okay", "sounds good", "thanks", "thank you", "got it", "yes", "sure", "cool", "great", "perfect", "yep", "yup", "understood",
})
_SLOT_ANSWER_RE = re.compile(
    r"^(?:"
    r"(?:(?:my\s+)?budget\s+(?:is\s+)?|around\s+|under\s+|between\s+)?\$?\d+(?:,\d{3})*(?:k|K)?\s*(?:to|-|–)\s*\$?\d+(?:,\d{3})*(?:k|K)?|"
    r"under\s+\$?\d+(?:k|K)?|"
    r"\$?\d+k|"
    r"(?:\d+\s*(?:to|-|–)\s*\d+\s*(?:months?|weeks?))|(?:\d+\s*(?:months?|weeks?))|asap|flexible(?:\s+timing)?|"
    r"mobile\s+app|web\s+app|web\s+application|web\s+platform|web\s+and\s+mobile|mobile\s+and\s+web|ios\s+and\s+android|ios|android|web|"
    r"founder|founder\s+or\s+exec|product\s+lead|manager|student|intern|"
    r"startup|smb|mid-market|enterprise"
    r")$",
    re.IGNORECASE,
)


_HUMAN_CUES = re.compile(
    r"\b("
    r"talk\s+to\s+a?\s*(?:human|person|someone|team)|"
    r"speak\s+(?:to|with)\s+a?\s*(?:human|person|agent|representative|someone)|"
    r"connect\s+(?:me\s+)?(?:with|to)\s+a?\s*(?:human|person|real\s+person|someone)|"
    r"chat\s+with\s+a?\s*(?:human|person|someone)|"
    r"(?:don'?t|not)\s+want\s+to\s+chat\s+with\s+a?\s*bot|"
    r"stop\s+talking\s+to\s+a?\s*bot|"
    r"real\s+person|"
    r"human\s+agent"
    r")\b",
    re.IGNORECASE,
)


def _is_objection_eligible(text: str) -> bool:
    if not text:
        return False
    cleaned = text.strip().lower()
    if cleaned in _STARTER_TEXTS:
        return False
    if cleaned in _ACK_TEXTS:
        return False
    if _SLOT_ANSWER_RE.match(cleaned) and not _OBJECTION_CUES.search(text):
        return False
    words = cleaned.split()
    if len(words) <= 4 and not _OBJECTION_CUES.search(text):
        return False
    return True


def validate_single_email(raw: str) -> str | None:
    if not raw or not isinstance(raw, str):
        return None
    cleaned = raw.strip().rstrip(".")
    if len(cleaned) > 254:
        return None
    if any(c in cleaned for c in (" ", "\t", "\n", "\r", ",", ";")):
        return None
    if cleaned.count("@") != 1:
        return None
    m = re.match(r"^[a-zA-Z0-9_.+-]+@[a-zA-Z0-9-]+(?:\.[a-zA-Z0-9-]+)+$", cleaned)
    if not m:
        return None
    return cleaned.lower()


def extract_single_email(text: str) -> tuple[str | None, bool]:
    if not text:
        return None, False
    matches = EMAIL.findall(text)
    if len(matches) > 1 or ("," in text and "@" in text) or (";" in text and "@" in text):
        return None, True
    if len(matches) == 1:
        candidate = matches[0].rstrip(".")
        val = validate_single_email(candidate)
        return val, False
    return None, False

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
    "got", "it", "sure", "fine", "good", "sounds", "haan", "theek", "thik", "hai", "shukriya",
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
QUESTION_INQUIRY_PATTERNS = re.compile(
    r"\b("
    r"i\s+want\s+to\s+know|"
    r"i'?d\s+like\s+to\s+know|"
    r"i\s+would\s+like\s+to\s+know|"
    r"i\s+would\s+like\s+to\s+understand|"
    r"i'?d\s+like\s+to\s+understand|"
    r"want\s+to\s+understand|"
    r"wondering|"
    r"curious|"
    r"need\s+more\s+(info|information|details)|"
    r"looking\s+for\s+(info|information|details)|"
    r"more\s+about"
    r")\b",
    re.IGNORECASE,
)
YOUR_NOUN_PHRASE = re.compile(r"^\s*your\s+[a-z0-9_-]+(\s+[a-z0-9_-]+){0,4}\s*$", re.IGNORECASE)
KNOWN_CASE_STUDIES = {
    "zephyr", "harbor", "atlas", "ledgerly", "harvest", "northstar",
    "swiftdrop", "aura", "novapay", "kinetix", "omnicopilot",
    "taxpulse", "taxadvisor", "propadvisor", "lexilead",
    "talentflow", "claimscout", "drivepulse", "staywise",
}


def _is_question_like(text: str) -> bool:
    cleaned = (text or "").strip()
    if "?" in cleaned:
        return True
    if any(k in cleaned.lower() for k in KNOWN_CASE_STUDIES):
        return True
    if QUESTION_OR_COMMAND_START.match(cleaned):
        return True
    if QUESTION_INQUIRY_PATTERNS.search(cleaned):
        return True
    if YOUR_NOUN_PHRASE.match(cleaned):
        return True
    return False


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
    if text and "<" in text and ">" in text:
        text = re.sub(r"<[^>]+>", "", text).strip()
    session._latest_user_text = text
    chip = chip or {}
    field = str(chip.get("field") or "").strip()
    value = chip.get("value")
    if not text and value and field == "ask":
        text = str(value).strip()
    if field == "ask":
        field = ""
        value = None

    valid_brief_fields = set(ProjectBrief.model_fields.keys()) | {"confirm_role", "features_done"}
    if field and field not in valid_brief_fields and field not in ACTION:
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
    brief_track_fields = ("service", "goal", "platforms", "features", "timeline", "budget_band", "decision_role", "company_size", "integrations", "users")
    initial_brief_state = {f: getattr(brief, f) for f in brief_track_fields}
    initial_pending = _pending(brief)
    email_val, is_multi_email = extract_single_email(text)
    found = bool(email_val)
    if email_val:
        contact["email"] = email_val
    user_texts = [item["content"] for item in history if item.get("role") == "user" and item.get("content")]
    if text:
        user_texts.append(text)
    has_pending_discovery_init = (
        not brief_ready(brief)
        and not bool(session.estimate_json)
        and (session.stage not in ("advising", "handoff", "disqualified"))
    )
    if has_pending_discovery_init:
        summary = " | ".join(user_texts[-6:])[:800]
    else:
        summary = rolling_summary(session.summary or "", user_texts, get_platform().summary_every, history)
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
        flow = _resolve_flow(config)
        # Auto-skip optional fields that cause conversation loops when user clicks continue
        if brief.feature_detail is None:
            brief.feature_detail = "not_specified"
            brief.field_attempts["feature_detail"] = 99
        if brief.user_flow is None:
            brief.user_flow = "not_specified"
            brief.field_attempts["user_flow"] = 99
        if brief_ready(brief, flow=flow):
            s_field = next_sharpen_field(brief)
            if s_field:
                prompt_msg = prompt_for(brief, s_field, repeat=False)
                chips = chips_for_field(s_field, brief, repeat=False) or ensure_chips(brief, prompt_msg)
                return _finish(
                    session, brief, contact, summary,
                    message=prompt_msg,
                    stage="discovery",
                    route="discovery",
                    chips=chips,
                    cards=[],
                    timings=timings,
                )
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

    if is_multi_email:
        if session.stage in ("email_capture", "booking") or session.booking_json or contact.get("prefers_email") or "@" in text:
            return _finish(
                session, brief, contact, summary,
                message="Please provide a single valid email address (e.g. name@company.com).",
                stage=session.stage or "discovery",
                route="email_invalid",
                chips=[],
            )

    has_at = "@" in text
    if (has_at or session.stage == "email_capture") and not email_val and not is_chip_click and not field:
        target_msg = (
            "Please provide a single valid email address (e.g. name@company.com) so we can send your summary."
            if session.stage == "email_capture"
            else "Please provide a single valid email address (e.g. name@company.com) so we can send your calendar invitation."
        )
        return _finish(
            session, brief, contact, summary,
            message=target_msg,
            stage=session.stage or "discovery",
            route="email_invalid",
            chips=[],
        )

    if email_val:
        sub_cnt, sub_ok = check_email_submission_limit(session.id)
        if not sub_ok:
            return _finish(
                session, brief, contact, summary,
                message="You have reached the maximum number of email submissions for this session.",
                stage=session.stage or "discovery",
                route="email_capped",
                chips=[PORTFOLIO_CHIP],
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
                format_bant_handoff_message(
                    brand_name=config.brand.name,
                    brief=brief,
                    qual=qual,
                    contact=contact,
                    estimate=estimate,
                    booked=None,
                    session_id=session.id,
                    action_type="Lead email captured (prefers email)",
                ),
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

            # Check 1 active booking per email
            now_iso = datetime.now(timezone.utc).isoformat()
            rows = db.query(SessionRow).filter(SessionRow.booking_json != "").all()
            for r in rows:
                if r.id == session.id:
                    continue
                try:
                    b_prev = json.loads(r.booking_json)
                    if b_prev.get("attendee", "").lower() == email.lower() and (b_prev.get("slot_iso") or "") > now_iso:
                        return _finish(
                            session, brief, contact, summary,
                            message="You already have an active scheduled consultation with our team. Please check your calendar or contact us to reschedule.",
                            stage="handoff",
                            route="booking_blocked",
                            chips=[PORTFOLIO_CHIP],
                        )
                except Exception:
                    pass

            # Check 3 bookings per IP per 24h
            cip = current_ip()
            _, allowed = check_booking_ip_limit(cip)
            if not allowed:
                return _finish(
                    session, brief, contact, summary,
                    message="We have reached the maximum number of bookings allowed for today from your network. Please try again tomorrow or contact our team directly.",
                    stage="handoff",
                    route="booking_blocked",
                    chips=[PORTFOLIO_CHIP],
                )

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
            record_booking_for_ip(cip)

            qual = qualify(brief, config.qualification, config.services, has_email=True)
            estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
            handoff = _handoff(config, brief, contact, qual, estimate, booked)
            session.handoff_summary = handoff
            _lead(db, tenant, session, email, qual, estimate, handoff)
            notify_slack(
                db,
                session.id,
                tenant,
                format_bant_handoff_message(
                    brand_name=config.brand.name,
                    brief=brief,
                    qual=qual,
                    contact=contact,
                    estimate=estimate,
                    booked=booked,
                    session_id=session.id,
                    action_type="Booking invitation dispatched",
                ),
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
                format_bant_handoff_message(
                    brand_name=config.brand.name,
                    brief=brief,
                    qual=qual,
                    contact=contact,
                    estimate=estimate,
                    booked=None,
                    session_id=session.id,
                    action_type="Lead email captured",
                ),
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
            handoff = getattr(config.brand, "booking_handoff_text", "The team will see this whole conversation, so you won't need to repeat anything.")
            reply = f"You're all set for {booking_label}. {handoff}"
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

    is_portfolio_request = field == "show_portfolio" or bool(
        text and re.search(r"\b(show|see|any|have)\b.{0,30}\b(clients?|case\s+stud(?:y|ies)?|portfolio|examples?)\b|\b(client\s+in|case\s+stud(?:y|ies)?\s+in)\b", text, re.IGNORECASE)
    )
    if is_portfolio_request:
        brief_for_match = brief
        if not brief.industry and text:
            from backend.app.engines.domains import detect_domain
            detected = detect_domain(text=text, brief=brief)
            if detected:
                brief_for_match = brief.model_copy(update={"industry": detected})
            else:
                low_t = text.lower()
                if "health" in low_t:
                    brief_for_match = brief.model_copy(update={"industry": "health"})
                elif "fintech" in low_t or "finance" in low_t:
                    brief_for_match = brief.model_copy(update={"industry": "fintech"})
                elif "market" in low_t:
                    brief_for_match = brief.model_copy(update={"industry": "marketplace"})
        cases = match_portfolio(brief_for_match, config.portfolio)
        is_sample = getattr(config, "slug", "") == "demo" or tenant.slug == "demo"
        for c in cases:
            if is_sample or c.get("is_sample"):
                c["is_sample"] = True
        # Tailor message to what the client actually discussed!
        context_phrase = ""
        if brief.goal:
            clean_g = brief.goal.strip().rstrip(".")
            context_phrase = f" for {clean_g}"
        elif brief.service:
            s_name = brief.service.replace("_", " ")
            context_phrase = f" for your {s_name} project"

        if is_sample:
            reply_msg = f"Sample case study: Based on what you're building{context_phrase}, here is relevant work and similar projects from our portfolio:"
        else:
            reply_msg = f"Based on what you're building{context_phrase}, here are relevant case studies and similar projects from our past work:"

        portfolio_chips = [
            BOOK_CHIP,
            {"label": "Ask about tech stack", "field": "ask", "value": "What tech stack do you recommend for this?"},
            {"label": "Talk to a human", "field": "talk_human", "value": "human"},
        ]
        if session.estimate_json:
            portfolio_chips.append({"label": "Review estimate", "field": "sharpen_estimate", "value": "estimate"})
        elif brief.service:
            portfolio_chips.append({"label": "Continue in chat", "field": "continue_discovery", "value": "continue"})

        return _finish(
            session, brief, contact, summary,
            message=reply_msg,
            stage=session.stage or "advising",
            route="portfolio",
            chips=portfolio_chips,
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

    is_human_request = field == "talk_human" or bool(text and _HUMAN_CUES.search(text))
    if is_human_request:
        human_chips = [
            {"label": "Book a call", "field": "booking_window", "value": "this_week"},
            PORTFOLIO_CHIP,
        ]
        if not brief_ready(brief):
            human_chips.append({"label": "Continue in chat", "field": "continue_discovery", "value": "continue"})
        return _finish(
            session, brief, contact, summary,
            message="I'd be glad to connect you with our engineering team! You can schedule a direct discovery call below, or we can keep building your project scope and estimate right here in chat.",
            stage=session.stage or "discovery",
            route="human_escalation",
            chips=human_chips,
            timings=timings,
        )

    direct_objection = match_objection(text, config.objections) if (text and not field and _is_objection_eligible(text)) else None
    if direct_objection:
        objection_topic = direct_objection.get("topic") or ""
        if (brief_ready(brief) or session.estimate_json) and objection_topic == "pricing":
            objection_chips = [
                {"label": "💡 Show a leaner cut", "field": "view_mvp", "value": "leaner_cut"},
                {"label": "🗓️ Split into 2 phases", "field": "view_mvp", "value": "core_cut"},
                BOOK_CHIP,
                PORTFOLIO_CHIP,
            ]
        else:
            objection_chips = _next_chips(brief, has_booking=bool(session.booking_json))
        return _finish(
            session, brief, contact, summary,
            message=direct_objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=objection_chips,
            timings=timings,
        )

    filled = False
    extracted: dict = {}
    if field and field in valid_brief_fields and field not in ACTION and field != "ask":
        brief.apply_chip(field, value)
        _note_flags(brief)
        filled = True
    elif text or field == "ask":
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
            elif lowered_text in (
                "that's enough", "thats enough", "enough", "that's all", "thats all", "that is all",
                "skip", "skip this", "skip for now", "no more", "nothing else", "no need",
                "move on", "next", "continue", "done", "ready",
            ):
                if pending == "features":
                    brief.features_confirmed = True
                    if brief.features is None:
                        brief.features = []
                    filled = True
                elif pending == "feature_detail":
                    brief.feature_detail = "not_specified"
                    filled = True
                elif pending == "user_flow":
                    brief.user_flow = "not_specified"
                    filled = True
                elif pending == "integrations":
                    brief.integrations = ["none"]
                    filled = True

        if not filled and session.estimate_json and text:
            lt = text.lower().strip()
            if any(k in lt for k in ("founder", "ceo", "cto", "exec", "product lead", "manager", "product manager", "student", "intern")):
                brief.decision_role = "founder_or_exec" if any(k in lt for k in ("founder", "ceo", "cto", "exec")) else ("intern_or_student" if any(k in lt for k in ("student", "intern")) else "product_or_ops_lead")
                filled = True
            elif any(k in lt for k in ("startup", "enterprise", "scaleup")):
                brief.company_size = "startup" if "startup" in lt else ("enterprise" if "enterprise" in lt else "scaleup")
                filled = True
            else:
                is_tech_inquiry = any(k in lt for k in ("do you use", "can you use", "what tech", "what stack", "what framework", "how do you build", "tell me about"))
                if not is_tech_inquiry:
                    new_budget = _budget(text)
                    if new_budget and new_budget != brief.budget_band:
                        brief.budget_band = new_budget
                        if re.search(r"\d", text):
                            brief.budget_text = text.strip()[:40]
                        filled = True
                    new_timeline = _timeline(text)
                    if new_timeline and new_timeline != brief.timeline:
                        brief.timeline = new_timeline
                        filled = True
                    if not _is_question_like(text) or any(k in lt for k in ("switch", "change", "instead", "make it", "platforms")):
                        new_platforms = _platforms(text)
                        if new_platforms and set(new_platforms) != set(brief.platforms or []):
                            brief.platforms = new_platforms
                            filled = True

        if not filled:
            has_pending_discovery = (
                not brief_ready(brief)
                and not bool(session.estimate_json)
                and (session.stage not in ("advising", "handoff", "disqualified"))
            )
            # Skip LLM extractor for slot chip clicks and acknowledgements, or when booking exists and brief is ready, or when post-estimate question is asked
            is_ack = _is_ack(text, has_pending_discovery)
            if (is_chip_click and field != "ask") or is_ack or (bool(session.booking_json) and brief_ready(brief)):
                extracted = {}
            elif bool(session.estimate_json) and _is_question_like(text):
                extracted = {"is_question": True}
            elif (
                _is_question_like(text)
                and not is_product_idea(text)
                and not any(k in text.lower() for k in ("budget", "timeline", "dollar", "month", "week", "founder", "intern", "student", "startup", "enterprise", "chahiye"))
                and not re.search(r"\b\d+k\b", text.lower())
            ):
                extracted = {"is_question": True}
            else:
                t0_ext = time.perf_counter()
                try:
                    extracted = extract_slots(text, pending, brief, out_of_scope=config.services.out_of_scope)
                except TypeError:
                    extracted = extract_slots(text, pending, brief)
                timings["extractor"] += (time.perf_counter() - t0_ext) * 1000.0
            if extracted.get("is_off_topic"):
                _svc_label = (brief.service or "").replace("_", " ") or "custom software"
                _offtopic_msg = (
                    f"That's a bit outside my scope as {config.brand.name}'s project consultant — "
                    f"I'm focused on scoping, architecture, and estimation for {_svc_label} and digital products. "
                    f"Happy to keep building out your project estimate or answer any technical questions about what we can build for you."
                )
                return _finish(
                    session, brief, contact, summary,
                    message=_offtopic_msg,
                    stage=session.stage or "discovery",
                    route="off_topic",
                    chips=_next_chips(brief, has_booking=bool(session.booking_json)),
                    timings=timings,
                )
            if extracted and apply_extracted_slots(brief, extracted, pending, text=text):
                _note_flags(brief)
                if not extracted.get("is_question") or brief_ready(brief):
                    filled = True
            elif not extracted.get("is_question") and not _is_question_like(text) and not OPEN.search(text) and pending and _apply_free_text(brief, pending, text, out_of_scope=config.services.out_of_scope):
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

            if not filled and not brief.goal and (not field or field == "ask") and text:
                t_clean = text.strip()
                if re.match(r"^(i'?m\s+)?(just\s+)?explor(ing)?\s+costs?$", t_clean, re.IGNORECASE):
                    service_chips = [
                        {"label": "Mobile app", "field": "service", "value": "mobile_app"},
                        {"label": "Web platform", "field": "service", "value": "web_app"},
                        {"label": "AI product", "field": "service", "value": "ai_product"},
                        {"label": "UI/UX design", "field": "service", "value": "ui_ux"},
                    ]
                    return _finish(
                        session, brief, contact, summary,
                        message="Happy to help you explore costs. What are you thinking of building: a mobile app, a web platform, AI, or design?",
                        stage="discovery",
                        route="discovery",
                        chips=service_chips,
                        timings=timings,
                    )
                if re.match(r"^(i\s+have\s+an?\s+(?:app|web|software|product)?\s*idea|app\s+idea)$", t_clean, re.IGNORECASE):
                    service_chips = [
                        {"label": "Mobile app", "field": "service", "value": "mobile_app"},
                        {"label": "Web platform", "field": "service", "value": "web_app"},
                        {"label": "AI product", "field": "service", "value": "ai_product"},
                        {"label": "UI/UX design", "field": "service", "value": "ui_ux"},
                    ]
                    return _finish(
                        session, brief, contact, summary,
                        message="Tell me what your app does in a sentence or two — who is it for and what's the core workflow?",
                        stage="discovery",
                        route="discovery",
                        chips=service_chips,
                        timings=timings,
                    )
                if re.match(r"^(i\s+want\s+to\s+add\s+ai\s+to\s+my\s+product|add\s+ai\s+to\s+my\s+product)$", t_clean, re.IGNORECASE):
                    brief.service = "ai_product"
                    brief.service_source = "explicit"
                    ai_chips = [
                        {"label": "AI chat / Assistant", "field": "features", "value": ["AI chat"]},
                        {"label": "Document processing", "field": "features", "value": ["Document processing"]},
                        {"label": "Workflow automation", "field": "features", "value": ["Workflow automation"]},
                    ]
                    return _finish(
                        session, brief, contact, summary,
                        message="Tell me a bit about your current product and what AI capability you want to add — e.g. customer support chat, document search, or workflow automation?",
                        stage="discovery",
                        route="discovery",
                        chips=ai_chips,
                        timings=timings,
                    )
                if re.match(r"^(i\s+need\s+a\s+web\s+platform|i\s+need\s+a\s+web\s+app)$", t_clean, re.IGNORECASE):
                    brief.service = "web_app"
                    brief.service_source = "explicit"
                    web_chips = [
                        {"label": "B2B SaaS portal", "field": "goal", "value": "B2B SaaS portal"},
                        {"label": "Customer dashboard", "field": "goal", "value": "Customer dashboard"},
                        {"label": "Online marketplace", "field": "goal", "value": "Online marketplace"},
                    ]
                    return _finish(
                        session, brief, contact, summary,
                        message="What will your web platform do — who is it for and what's the primary workflow users will complete?",
                        stage="discovery",
                        route="discovery",
                        chips=web_chips,
                        timings=timings,
                    )



    if filled or (field and field not in ACTION and field != "ask"):
        changed_fields = [f for f in brief_track_fields if getattr(brief, f) != initial_brief_state[f] and getattr(brief, f)]
        if changed_fields and any(f in changed_fields for f in ("platforms", "timeline", "budget_band", "decision_role")):
            if brief.feature_detail is None:
                brief.feature_detail = "not_specified"
            if brief.user_flow is None:
                brief.user_flow = "not_specified"
        # Auto-skip feature_detail and user_flow for ai_product service
        # AI product features (AI chat, Document processing) are self-explanatory — no detail needed
        if (field == "features_done" or (field == "features" and brief.features_confirmed)) and brief.service == "ai_product":
            if brief.feature_detail is None:
                brief.feature_detail = "not_specified"
                brief.field_attempts["feature_detail"] = 99
            if brief.user_flow is None:
                brief.user_flow = "not_specified"
                brief.field_attempts["user_flow"] = 99
        # Auto-skip user_flow when feature_detail is standard or skipped
        if (field == "feature_detail" or getattr(brief, "feature_detail", None) == "not_specified") and getattr(brief, "user_flow", None) is None:
            if brief.feature_detail == "not_specified" or "standard" in (brief.feature_detail or "").lower():
                brief.user_flow = "not_specified"
                brief.field_attempts["user_flow"] = 99
        return _after_brief(
            session, config, brief, contact, summary,
            user_text=text, history=history, timings=timings,
            changed_fields=changed_fields, prev_pending=initial_pending,
            extracted_ack=extracted.get("acknowledgement") if isinstance(extracted, dict) else None,
            is_chip_click=is_chip_click,
        )

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
            reply_msg = "Sounds good. When you're ready, book a call and the team will take it from here."
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
        greetings = ("hello", "hi", "hey", "umm", "thanks", "ok", "cool", "good morning", "good evening")
        is_filler = any(text.lower().strip().startswith(g) for g in greetings) or len(text.split()) < 3
        if not changed_fields and not brief.goal and not is_filler and is_product_idea(text):
            from backend.app.screening.slots import goal_short as _clean_goal
            cleaned_g = _clean_goal(text) or text.strip()[:120]
            brief.goal = cleaned_g
            changed_fields = ["goal"]
        if changed_fields and any(f in changed_fields for f in ("platforms", "timeline", "budget_band", "decision_role")):
            if brief.feature_detail is None:
                brief.feature_detail = "not_specified"
            if brief.user_flow is None:
                brief.user_flow = "not_specified"
        return _after_brief(
            session, config, brief, contact, summary,
            user_text=text, history=history, timings=timings,
            changed_fields=changed_fields, prev_pending=initial_pending,
            extracted_ack=extracted.get("acknowledgement") if isinstance(extracted, dict) else None,
            is_chip_click=is_chip_click,
        )

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

            # QA-3 Item 8: Deduplicate consecutive FAQ replies
            last_bot_msg = ""
            for item in reversed(history or []):
                if item.get("role") == "assistant" and item.get("content"):
                    last_bot_msg = str(item.get("content")).strip()
                    break

            hit = faq_hits[0]
            if last_bot_msg and hit.content.strip() in last_bot_msg:
                if len(faq_hits) > 1 and faq_hits[1].content.strip() not in last_bot_msg:
                    hit = faq_hits[1]
                else:
                    return _finish(
                        session, brief, contact, summary,
                        message="Our team can go into detail on a call.",
                        stage="advising" if brief_ready(brief) else "discovery",
                        route="faq",
                        chips=[BOOK_CHIP, PORTFOLIO_CHIP],
                        timings=timings,
                    )

            # If this is a tech stack FAQ hit and the client has a scoped project, provide tailored architecture
            is_stack_hit = getattr(hit, "id", "") == "stack" or getattr(hit, "topic", "") == "stack" or bool(TECH_STACK_INQUIRY_RE.search(text))
            if is_stack_hit and (brief.service or brief.goal):
                arch = recommend_architecture(brief, config.services)
                mvp_res = recommend_mvp(brief)
                message = _tailored_architecture_advisory(config, brief, text)
                extra = _continuation(brief, history) if not brief_ready(brief) else None
                if extra:
                    message = f"{message}\n\n{extra[0]}"
                    chips = list(extra[1])
                else:
                    chips = [
                        {"label": "Book a call", "field": "booking_window", "value": "this_week"},
                        {"label": "See sample projects", "field": "show_portfolio", "value": "yes"},
                        {"label": "Talk to a human", "field": "talk_human", "value": "human"},
                    ] if (brief_ready(brief) or session.estimate_json) else _next_chips(brief)

                cards = [build_shape_card(arch, mvp_res)]
                return _finish(
                    session, brief, contact, summary,
                    message=message,
                    stage=session.stage or ("advising" if brief_ready(brief) else "discovery"),
                    route="faq",
                    chips=chips,
                    cards=cards,
                    passages=[hit.content],
                    chunk_ids=[hit.id],
                    query=queries[0],
                    score=hit.score,
                    timings=timings,
                )

            message = hit.content
            # Enrich security FAQ with domain compliance context when active
            if getattr(hit, "id", "") == "security" or getattr(hit, "topic", "") == "security":
                from backend.app.engines.domains import detect_domain, get_domain_blueprint
                dom_id = detect_domain(brief=brief)
                bp_dom = get_domain_blueprint(dom_id) if dom_id else None
                if bp_dom and bp_dom.compliance:
                    message = f"{message} For {bp_dom.label}, we enforce {bp_dom.compliance}."
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
    estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
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
        platform = get_platform()
        is_weak = decision == "weak" or (platform.weak_min_score <= score < platform.show_min_score)
        weak_notes = hits[:3] if is_weak and hits else None

        is_stack_fallback = bool(TECH_STACK_INQUIRY_RE.search(text)) and (brief.service or brief.goal) and not weak_notes
        if is_stack_fallback:
            arch = recommend_architecture(brief, config.services)
            mvp_res = recommend_mvp(brief)
            message = _tailored_architecture_advisory(config, brief, text)
            extra = _continuation(brief, history) if not brief_ready(brief) else None
            if extra:
                message = f"{message}\n\n{extra[0]}"
                chips = list(extra[1])
            else:
                chips = [
                    {"label": "Book a call", "field": "booking_window", "value": "this_week"},
                    {"label": "See sample projects", "field": "show_portfolio", "value": "yes"},
                    {"label": "Talk to a human", "field": "talk_human", "value": "human"},
                ] if (brief_ready(brief) or session.estimate_json) else _next_chips(brief)
            cards = [build_shape_card(arch, mvp_res)]
            return _finish(
                session, brief, contact, summary,
                message=message,
                stage=session.stage or ("advising" if brief_ready(brief) else "discovery"),
                route="faq",
                chips=chips,
                cards=cards,
                timings=timings,
            )

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
        from backend.app.agents.suggestions import ensure_chips
        chips = ensure_chips(brief, message, [h.content for h in strong] if (decision == "show" and strong) else None)

    last_assistant_msg = ""
    for item in reversed(history or []):
        if item.get("role") == "assistant" and item.get("content"):
            last_assistant_msg = str(item.get("content")).strip()
            break
    if last_assistant_msg and message.strip() == last_assistant_msg:
        if brief_ready(brief):
            message = "We can dive deeper into that architecture and technical setup during a quick discovery call."
        else:
            message = "Our team can go into detail on those specific points on a call."

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
        estimate=estimate,
        timings=timings,
    )


def _book(db, tenant, config, session, brief, contact, summary, slot_iso: str) -> dict:
    email = contact.get("email") or ""
    cip = current_ip()
    if email:
        now_iso = datetime.now(timezone.utc).isoformat()
        rows = db.query(SessionRow).filter(SessionRow.booking_json != "").all()
        for r in rows:
            if r.id == session.id:
                continue
            try:
                b_prev = json.loads(r.booking_json)
                if b_prev.get("attendee", "").lower() == email.lower() and (b_prev.get("slot_iso") or "") > now_iso:
                    return _finish(
                        session, brief, contact, summary,
                        message="You already have an active scheduled consultation with our team. Please check your calendar or contact us to reschedule.",
                        stage="handoff",
                        route="booking_blocked",
                        chips=[PORTFOLIO_CHIP],
                    )
            except Exception:
                pass

    _, allowed = check_booking_ip_limit(cip)
    if not allowed:
        return _finish(
            session, brief, contact, summary,
            message="We have reached the maximum number of bookings allowed for today from your network. Please try again tomorrow or contact our team directly.",
            stage="handoff",
            route="booking_blocked",
            chips=[PORTFOLIO_CHIP],
        )

    tz_name = getattr(config.brand, "timezone", "") or "Asia/Kolkata"
    booked = confirm_slot(
        tenant,
        slot_iso,
        f"Discovery call — {config.brand.name}",
        email,
        tz_name=tz_name,
    )
    if email:
        record_booking_for_ip(cip)
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
        format_bant_handoff_message(
            brand_name=config.brand.name,
            brief=brief,
            qual=qual,
            contact=contact,
            estimate=estimate,
            booked=booked,
            session_id=session.id,
            action_type=f"Booking for {config.brand.name}: {booked.get('label') or slot_iso} ({email or 'no email yet'})",
        ),
    )
    if email:
        _lead(db, tenant, session, email, qual, estimate, handoff)
    if not booked.get("live"):
        message = f"You're booked for {booked.get('label') or slot_iso} — Demo booking: no calendar invite is sent until Google Calendar is connected."
    else:
        message = f"You're booked for {booked.get('label') or slot_iso}."
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
        chips=_next_chips(brief, has_booking=True),
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


def _truncate_word_boundary(text: str, max_len: int = 35) -> str:
    cleaned = text.strip()
    if len(cleaned) <= max_len:
        return cleaned
    cut = cleaned[:max_len]
    if " " in cut:
        cut = cut.rsplit(" ", 1)[0]
    return cut.rstrip(" .,!?:;")


def format_shape_message(arch: dict, mvp_res: dict) -> str:
    channels = (arch.get("frontend") or ["Web / Mobile"])[0]
    all_mvp = list(mvp_res.get("mvp") or [])
    core_items = [it for it in all_mvp if re.match(r"^core:\s*", str(it), flags=re.IGNORECASE)]
    raw_mvp = core_items[:3] if core_items else all_mvp[:3]
    clean_mvp = []
    for item in raw_mvp:
        it = re.sub(r"^(Prove this outcome:\s*|Core:\s*)", "", str(item).strip(), flags=re.IGNORECASE).strip()
        it = _truncate_word_boundary(it, 35)
        if it:
            clean_mvp.append(it)
    backend = (arch.get("backend") or ["API + Database"])[0]
    if clean_mvp:
        mvp_str = ", ".join(clean_mvp)
        return f"Channels and UX: {channels}. Core flow: {mvp_str}. Backend and APIs: {backend}."
    return f"Channels and UX: {channels}. Backend and APIs: {backend}."


def build_shape_card(arch: dict, mvp_res: dict) -> dict:
    clean_flow = []
    for item in (mvp_res.get("mvp") or [])[:3]:
        cleaned = re.sub(r"^(Prove this outcome:\s*|Core:\s*)", "", str(item).strip(), flags=re.IGNORECASE).strip()
        cleaned = cleaned.replace("_", " ")
        if cleaned:
            clean_flow.append(cleaned)
    return {
        "type": "shape",
        "title": "Channels, core flow, and architecture",
        "channels_ux": list(arch.get("frontend") or []),
        "core_flow": clean_flow,
        "backend_apis": list(arch.get("backend") or []),
    }


TECH_STACK_INQUIRY_RE = re.compile(
    r"\b(what|which|recommend|suggest|explain|tell\s+me\s+about)\b.{0,35}\b(tech\s+stack|technology\s+stack|stack|architecture|database|db|framework|frameworks|backend|frontend|technologies)\b"
    r"|\b(tech\s+stack|recommended\s+stack|recommend\s+a\s+stack|suggest\s+a\s+stack|which\s+database|what\s+database|why\s+next\.?js|why\s+fastapi|why\s+python|why\s+postgres)\b",
    re.IGNORECASE,
)


def _tailored_architecture_advisory(config: TenantConfig, brief: ProjectBrief, user_query: str) -> str:
    """Generate an authoritative, domain-tailored technical architecture recommendation."""
    from backend.app.engines.architecture import recommend_architecture
    from backend.app.engines.domains import detect_domain, get_domain_blueprint

    arch = recommend_architecture(brief, config.services)
    domain_id = detect_domain(text=user_query, brief=brief)
    bp = get_domain_blueprint(domain_id) if domain_id else None

    frontend_str = ", ".join(arch.get("frontend") or ["Next.js (Web)"])
    backend_str = ", ".join(arch.get("backend") or ["FastAPI + PostgreSQL"])
    notes_list = arch.get("notes") or []
    notes_str = "\n".join(f"• {n}" for n in notes_list[:3])

    domain_label = bp.label if bp else (arch.get("label") or brief.service or "custom software")
    project_label = brief.goal or domain_label

    fallback_lines = [
        f"For your {domain_label} build ({project_label}), here is our recommended production stack based on our engineering blueprints:",
        f"• **Frontend & Channels:** {frontend_str}",
        f"• **Backend & APIs:** {backend_str}",
    ]
    if notes_list:
        fallback_lines.append(f"• **Key Architectural Pillars:**\n{notes_str}")
    fallback_lines.append(
        "We assert this stack because it guarantees requisite data security, sub-second query performance, and clean scalability without premature operational overhead."
    )
    fallback = "\n\n".join(fallback_lines)

    if not llm_available():
        return fallback

    brand_name = getattr(config.brand, "name", "Nexus")
    prompt = (
        f"You are Mike, senior solutions architect and technical advisor at {brand_name}. "
        f"A prospective client is scoping a project:\n"
        f"- Goal: '{brief.goal or 'Custom solution'}'\n"
        f"- Domain: '{domain_label}'\n"
        f"- Platforms: {', '.join(brief.platforms) if brief.platforms else 'Web / Mobile'}\n"
        f"- Integrations: {', '.join(brief.integrations) if brief.integrations else 'Standard'}\n"
        f"- Recommended Frontend: {frontend_str}\n"
        f"- Recommended Backend: {backend_str}\n"
        f"- Architecture Pillars: {'; '.join(notes_list[:3])}\n"
        f"Client question: '{user_query}'\n\n"
        f"Explain authoritatively why this specific architecture and stack is optimal for their requirements. "
        f"Highlight data security, database performance, and developer velocity. "
        f"Never ask the client to choose frameworks or databases—assert the architectural decision with confidence. "
        f"Keep the tone consultative, senior, and concise (under 160 words). "
        f'Return JSON {{"message": "..."}}.'
    )
    try:
        data = complete_json(SOLUTION_SYSTEM_PROMPT, prompt, mode="request")
        msg = str(data.get("message") or "").strip()
        if msg:
            return msg
    except Exception:
        pass
    return fallback


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
    from backend.app.screening.slots import (
        budget_label,
        display_platforms,
        service_article,
        service_label_clean,
        timeline_label,
    )

    s_clean = service_label_clean(brief.service, config.services.in_scope if config.services else None)
    art = service_article(s_clean)

    g_phrase = ""
    if brief.goal:
        g = brief.goal.strip()
        g = re.sub(
            r"^(i\s+am\s+building|i'?m\s+building|we\s+are\s+building|we'?re\s+building|"
            r"i\s+want\s+a|i\s+want\s+to\s+build|i\s+want|we\s+want\s+a|we\s+want|"
            r"i\s+need\s+a|i\s+need\s+to\s+build|i\s+need|we\s+need\s+a|we\s+need|"
            r"looking\s+to\s+build|planning\s+to\s+build)\b\s*",
            "",
            g,
            flags=re.IGNORECASE,
        ).strip()
        g = re.sub(r"^(a|an|the)\b\s*", "", g, flags=re.IGNORECASE).strip()
        p_words = r",?\s*\b(for\s+ios\s+(?:&|and|aur)\s+android(?:\s+dono)?|ios\s+(?:&|and|aur)\s+android(?:\s+dono)?|cross-platform\s+mobile\s+app|mobile\s+app|web\s+app|web\s+application|on\s+ios\s+and\s+android|on\s+web|\bios\b|\bandroid\b)\b"
        t_words = r",?\s*\b\d+\s*(?:months?|mahine(?:\s+me)?|weeks?)\b"
        g = re.sub(p_words, "", g, flags=re.IGNORECASE).strip()
        g = re.sub(t_words, "", g, flags=re.IGNORECASE).strip()
        g = re.sub(r"\s+", " ", g).strip(" ,.-")
        if g and len(g) > 90:
            g = g[:90].rsplit(" ", 1)[0].strip()
        if g.lower().strip() in {
            "develop an app idea", "develop an app", "build an app", "app idea",
            "software idea", "my app", "an idea", "custom software", "idea", "an app",
            "develop app idea", "build app", "create an app", "create an app idea",
            "new app", "mobile app", "web app", "new project", "an application",
            "an app project", "software project",
        }:
            g = ""
        g_phrase = g

    service_goal = f"{art} {s_clean.lower()}"
    if g_phrase:
        clean_gp = g_phrase.replace("_", " ")
        service_goal += f" - {clean_gp}"

    lines = [f"Here's what I understood: {service_goal}."]

    plats = display_platforms(brief.platforms)
    if plats:
        lines.append(f"Platforms: {plats}.")

    if brief.features:
        named = [str(f).strip() for f in brief.features if str(f).strip()]
        if len(named) > 4:
            lines.append(f"Features: {', '.join(named[:4])}, and {len(named) - 4} more.")
        elif named:
            lines.append(f"Features: {', '.join(named)}.")

    t_lbl = timeline_label(brief.timeline)
    if t_lbl:
        lines.append(f"Timeline: {t_lbl}.")

    b_val = getattr(brief, "budget_text", None) or budget_label(brief.budget_band)
    if b_val:
        lines.append(f"Budget: {b_val}.")

    return " ".join(lines)


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
    prev_pending: str | None = None,
    extracted_ack: str | None = None,
    is_chip_click: bool = False,
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

    # QA-3 Item 8.a: After the estimate, role or company-size answers get a short acknowledgement and next-step chips; estimate block is never sent twice
    if session.estimate_json:
        role_label = getattr(brief, "decision_role", None)
        size_label = getattr(brief, "company_size", None)
        ack_parts = []
        if changed_fields and "decision_role" in changed_fields and role_label:
            ack_parts.append(f"Noted — having the {role_label.replace('_', ' ')} perspective helps keep delivery aligned.")
        elif changed_fields and "company_size" in changed_fields and size_label:
            ack_parts.append(f"Noted — designing for {size_label.replace('_', ' ')} scale helps calibrate our squad and architecture.")
        else:
            ack_parts.append("Noted, I have updated your project brief.")
        reply_msg = f"{' '.join(ack_parts)} What would you like to explore next?"
        next_chips = [
            {"label": "Book a call", "field": "booking_window", "value": "this_week"},
            {"label": "See the MVP", "field": "view_mvp", "value": "mvp"},
            {"label": "See sample projects", "field": "show_portfolio", "value": "yes"},
            {"label": "Talk to a human", "field": "talk_human", "value": "human"},
        ]
        return _finish(
            session, brief, contact, summary,
            message=reply_msg,
            stage="advising",
            route="discovery",
            chips=next_chips,
            timings=timings,
        )

    # Check consistency between service and platforms (Rule 4e / QA-3 Item 5.b)
    if brief.service == "mobile_app" and brief.platforms and ("web" in brief.platforms) and not any(p in ("ios", "android") for p in brief.platforms):
        if getattr(brief, "service_source", "guess") in ("chip", "explicit"):
            if not brief.platform_service_clarified:
                brief.platform_service_clarified = True
                return _finish(
                    session, brief, contact, summary,
                    message="You mentioned a mobile app earlier, but web as the platform. Should we build this as a mobile app (iOS/Android), a web app, or both?",
                    stage="discovery",
                    route="discovery",
                    chips=[
                        {"label": "Mobile app", "field": "platforms", "value": ["ios", "android"]},
                        {"label": "Web app", "field": "service", "value": "web_app"},
                        {"label": "Both web & mobile", "field": "platforms", "value": ["web", "ios", "android"]},
                    ],
                    qualification=qual,
                    timings=timings,
                )
        else:
            brief.service = "web_app"
            brief.service_source = "explicit"
    elif brief.service == "web_app" and brief.platforms and any(p in ("ios", "android") for p in brief.platforms) and "web" not in [p.lower() for p in brief.platforms]:
        if getattr(brief, "service_source", "guess") in ("chip", "explicit"):
            if not brief.platform_service_clarified:
                brief.platform_service_clarified = True
                return _finish(
                    session, brief, contact, summary,
                    message="You mentioned a web app earlier, but mobile as the platform. Should we target web, mobile, or both?",
                    stage="discovery",
                    route="discovery",
                    chips=[
                        {"label": "Web app", "field": "platforms", "value": ["web"]},
                        {"label": "Mobile app", "field": "service", "value": "mobile_app"},
                        {"label": "Both web & mobile", "field": "platforms", "value": ["web", "ios", "android"]},
                    ],
                    qualification=qual,
                    timings=timings,
                )
        else:
            brief.service = "mobile_app"
            brief.service_source = "explicit"

    if changed_fields and prev_pending and prev_pending not in changed_fields:
        # Rule 4c: If something was captured but not the pending field,
        # acknowledge what was captured and ask the next missing field;
        # never repeat the pending question as if nothing happened.
        if prev_pending in ("feature_detail", "user_flow"):
            setattr(brief, prev_pending, "not_specified")
            brief.field_attempts[prev_pending] = 99
        elif prev_pending in {"users", "integrations", "company_size"}:
            defaults = {"users": "business", "integrations": ["none"], "company_size": "startup"}
            if not getattr(brief, prev_pending):
                setattr(brief, prev_pending, defaults.get(prev_pending, "not_specified"))
            brief.field_attempts[prev_pending] = 99
        elif prev_pending == "service":
            if not brief.service:
                brief.service = "mobile_app" if (brief.platforms and any(p in ("ios", "android") for p in brief.platforms)) else "web_app"

    flow = _resolve_flow(config)
    for _ in range(15):
        if brief_ready(brief, flow=flow):
            return _estimate(session, config, brief, contact, summary, qual, timings=timings)
        field = next_discovery_field(brief, flow=flow)
        if not field:
            break
        attempts = brief.field_attempts.get(field, 0)
        max_att = 1 if field in ("feature_detail", "user_flow") else (3 if (field == "features" and brief and brief.features) else 2)
        if attempts >= max_att:
            # The same field is asked at most twice (Rule 4d).
            # On third time, leave slot unknown and move on.
            if field == "features":
                brief.features = brief.features or []
                brief.features_confirmed = True
            elif field == "feature_detail":
                brief.feature_detail = "not_specified"
            elif field == "user_flow":
                brief.user_flow = "not_specified"
            elif field in {"timeline", "budget_band", "decision_role", "company_size", "users", "platforms"}:
                defaults = {
                    "timeline": "flexible",
                    "budget_band": "exploring",
                    "decision_role": "founder_or_exec",
                    "company_size": "startup",
                    "users": "business",
                    "platforms": ["web"],
                }
                if not getattr(brief, field):
                    setattr(brief, field, defaults.get(field, "unknown"))
            elif field == "goal":
                if not brief.goal:
                    brief.goal = "Custom software project"
            elif field == "service":
                if not brief.service:
                    brief.service = "mobile_app" if (brief.platforms and any(p in ("ios", "android") for p in brief.platforms)) else "web_app"
            brief.field_attempts[field] = 99
            continue
        break

    if brief_ready(brief, flow=flow):
        return _estimate(session, config, brief, contact, summary, qual, timings=timings)

    attempts = brief.field_attempts.get(field or "", 0)
    repeat = attempts >= 1
    if field:
        if changed_fields and field not in changed_fields:
            brief.field_attempts[field] = 1
            repeat = False
        else:
            brief.field_attempts[field] = attempts + 1
    t0_ans = time.perf_counter()
    from backend.app.agents.discovery_synth import (
        deterministic_discovery_prompt,
        question_variant_for,
        validate_discovery_reply,
    )
    voice = getattr(config, "voice", None) or VoiceConfig()
    deterministic_msg = deterministic_discovery_prompt(
        config,
        brief,
        field,
        changed_fields=changed_fields,
        session_id=str(session.id or ""),
        attempt=attempts,
    )
    if repeat or is_chip_click or not user_text:
        prompt_msg = prompt_for(brief, field, repeat=repeat) if repeat else deterministic_msg
    else:
        ext_ack = (extracted_ack or "").strip()
        if ext_ack and len(ext_ack) <= voice.max_chars and not any(p.lower() in ext_ack.lower() for p in voice.banned_phrases):
            q_var = question_variant_for(config, brief, field, session_id=str(session.id or ""), attempt=attempts)
            combined = f"{ext_ack} {q_var}".strip()
            prompt_msg = validate_discovery_reply(combined, voice, deterministic_msg)
        else:
            prompt_msg = deterministic_msg
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
        prompt_q = prompt_for(brief, field, repeat=repeat)
        prompt_msg = f"{shape_text} {prompt_q}"

    progress_val = None
    if _resolve_flow(config) == "fast":
        fast_fields = ["service", "goal", "platforms", "timeline", "budget_band"]
        filled_count = sum(1 for f in fast_fields if getattr(brief, f))
        progress_val = f"{min(5, filled_count + 1)} of 5"

    return _finish(
        session, brief, contact, summary,
        message=prompt_msg,
        stage="discovery",
        route="discovery",
        chips=chips,
        cards=cards,
        progress=progress_val,
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

    features_count = len(brief.features or [])
    base_val = 0.0
    if config.pricing and hasattr(config.pricing, "bases") and config.pricing.bases:
        base_val = float(config.pricing.bases.get(brief.service) or config.pricing.bases.get("unknown") or 0.0)
    has_scope_caution = bool(features_count >= 5 and estimate.get("low", 0) <= base_val)

    if has_scope_caution and "room to add scope" in fit_line:
        fit_line = ""

    parts = [
        f"{recap} If anything is off, tell me and I'll update the estimate.",
        f"A first-pass indicative range for this scope is **{estimate['range_label']}** over about **{estimate['timeline_weeks']} weeks**.\n*{config.brand.disclaimer}*",
        "That's a first-pass range based on typical scope for this kind of project.",
    ]
    if has_scope_caution:
        parts.append("This range assumes the Core scope; a list this long will likely need more, and the team can size it precisely.")
    if fit_line:
        parts.append(fit_line)
        if "leaner scope" in fit_line and mvp and mvp.get("mvp"):
            BOILERPLATE_MVP = ("primary user journey", "operational workflow", "problem framing", "component foundations", "named specialist")
            clean_mvp = [
                re.sub(r"^(Prove this outcome:\s*|Core:\s*)", "", str(it).strip(), flags=re.IGNORECASE).strip().replace("_", " ")
                for it in (mvp.get("mvp") or [])
                if it and not any(term in str(it).lower() for term in BOILERPLATE_MVP)
            ][:3]
            clean_later = [
                re.sub(r"^(Prove this outcome:\s*|Core:\s*)", "", str(it).strip(), flags=re.IGNORECASE).strip().replace("_", " ")
                for it in (mvp.get("later") or [])
                if it and not any(term in str(it).lower() for term in BOILERPLATE_MVP)
            ][:2]
            core_items = ", ".join(clean_mvp)
            deferred_items = ", ".join(clean_later)
            if deferred_items:
                parts.append(
                    f"💡 **Consultant Recommendation**: To align with your timeline and investment, we recommend staging a **Phased MVP Sprint**:\n"
                    f"• **Phase 1 Launch**: Prioritize {core_items} to launch lean and fast.\n"
                    f"• **Phase 2 Expansion**: Introduce {deferred_items} once initial traction is validated."
                )

    message = "\n\n".join(parts)

    chips = []
    if has_scope_caution:
        chips.append({"label": "Show the Core cut", "field": "view_mvp", "value": "core_cut"})
    elif "leaner scope" in fit_line:
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
        return [BOOK_CHIP, PORTFOLIO_CHIP]
    field = next_discovery_field(brief)
    return chips_for_field(field or "service", brief)


def _pending(brief: ProjectBrief) -> str | None:
    if not brief_ready(brief):
        return next_discovery_field(brief)
    return None


def _apply_free_text(brief: ProjectBrief, field: str, text: str, out_of_scope: list[str] | None = None) -> bool:
    cleaned = text.strip()
    if not cleaned:
        return False
    if field == "service":
        mapped = _service(cleaned, out_of_scope=out_of_scope)
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
        if re.search(r"\d", cleaned):
            brief.budget_text = cleaned[:40]
        elif getattr(brief, "budget_text", None) in ("just exploring costs", "exploring", "still exploring"):
            brief.budget_text = None
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
        p_mapped = _platforms(cleaned)
        if p_mapped or cleaned.lower().strip() in ("ios and android", "ios", "android", "web", "mobile", "web and mobile"):
            brief.platforms = p_mapped or (["web", "ios", "android"] if "web" in cleaned.lower() else ["ios", "android"])
            return True
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


def _service(text: str, out_of_scope: list[str] | None = None) -> str | None:
    lowered = text.lower()
    tokens = (
        OUT_OF_SCOPE
        if out_of_scope is None
        else tuple(t.lower().strip() for t in out_of_scope if t and t.strip())
    )
    if any(token in lowered for token in tokens):
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
    has_web = "web" in lowered or "browser" in lowered
    has_ios = "ios" in lowered or "iphone" in lowered or "ipad" in lowered
    has_android = "android" in lowered
    has_mobile = "mobile" in lowered or "both" in lowered or "phone" in lowered or ("app" in lowered and "web and app" in lowered)

    if (has_web and (has_mobile or (has_ios and has_android))) or ("web and mobile" in lowered or "mobile and web" in lowered):
        return ["web", "ios", "android"]
    if has_web and has_ios:
        return ["web", "ios"]
    if has_web and has_android:
        return ["web", "android"]
    if (has_ios and has_android) or has_mobile:
        return ["ios", "android"]
    if has_ios:
        return ["ios"]
    if has_android:
        return ["android"]
    if has_web:
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
    if re.search(r"\bunder\b", lowered):
        upper = upper - 1.0
    if upper <= 15000:
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


_OBJECTION_KEYWORDS = re.compile(
    r"\b(expensive|cheaper|cheap|too\s+much|reduce|cost|rates?|budget|too\s+long|faster|hurry|slow|timeline|rush|fixed\s+price|fixed\s+bid|lump\s+sum|offshore|outsourced|guarantee|discount|hourly|retainer)\b",
    re.IGNORECASE,
)


def _objection(db, tenant, config, text, nda_accepted: bool):
    found = match_objection(text, config.objections)
    if found or not text:
        return found
    if len(text.split()) > 20:
        return None
    hits = search(db, tenant, text, kind="objection", k=1, nda_accepted=nda_accepted)
    if hits:
        has_keywords = bool(_OBJECTION_KEYWORDS.search(text))
        min_score = get_platform().faq_min_score if has_keywords else 0.76
        if hits[0].score >= min_score:
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


def compute_discovery_progress(brief: Any, stage: str, route: str) -> str | None:
    """Compute the 4-step consultative progress indicator for the chat widget."""
    if stage in ("booking", "handoff", "contact") or route in ("booking", "contact", "email_capture"):
        return None
    if stage in ("pricing", "estimate", "scoping") or route in ("estimate", "scoping"):
        return "4 of 4"
    has_scope = bool(getattr(brief, "service", None) or getattr(brief, "goal", None))
    has_features = bool(getattr(brief, "features", None) or getattr(brief, "platforms", None))
    has_commercials = bool(getattr(brief, "budget_band", None) or getattr(brief, "timeline", None))

    if not has_scope:
        step = 1
    elif not has_features:
        step = 2
    elif not has_commercials:
        step = 3
    else:
        step = 4
    return f"{step} of 4"


def _handoff(config, brief, contact, qual, estimate, booked) -> str:
    lines = [
        f"# Discovery summary — {config.brand.name}",
        f"Email: {contact.get('email') or 'not captured'}",
        f"Service: {brief.service or 'unspecified'}",
        f"Goal: {brief.goal or '—'}",
        f"Score: {qual.get('score')} ({qual.get('band')})",
    ]
    bant = qual.get("bant")
    if bant and isinstance(bant, dict):
        b = bant.get("budget", {}).get("value") or getattr(brief, "budget_band", None) or "exploring"
        a = bant.get("authority", {}).get("value") or getattr(brief, "decision_role", None) or "unknown"
        t = bant.get("timing", {}).get("value") or getattr(brief, "timeline", None) or "flexible"
        lines.append(f"BANT: Budget={b} | Authority={a} | Timing={t}")
    from backend.app.engines.domains import detect_domain, get_domain_blueprint
    dom = detect_domain(brief=brief)
    if dom:
        bp = get_domain_blueprint(dom)
        if bp:
            lines.append(f"Domain: {bp.label} (Compliance: {bp.compliance})")
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
    try:
        from backend.app.agents.brief import ProjectBrief
        brief_obj = ProjectBrief.model_validate_json(session.brief_json or "{}")
    except Exception:
        brief_obj = None
    try:
        from backend.app.engines.notify import sync_crm_lead
        sync_crm_lead(db, session.id, tenant, email, qual, brief_obj, estimate, handoff)
    except Exception:
        pass


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
    if not chips and payload.get("route") != "email_capture" and payload.get("stage") != "email_capture":
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
    has_session_estimate = bool(payload.get("estimate") or session.estimate_json or estimate_ctx)
    vis_budget = getattr(brief, "budget_text", None) or getattr(brief, "budget_band", None)
    sanitized_message = sanitize_price_leaks(
        raw_message,
        estimate_ctx,
        visitor_budget=vis_budget,
        session_has_estimate=has_session_estimate,
    )
    if not sanitized_message.strip():
        sanitized_message = "Let's continue shaping your project."
    passages = list(payload.get("passages") or [])
    route = payload.get("route") or "discovery"
    if not passages and route != "faq":
        engine_weeks = None
        if estimate_ctx and isinstance(estimate_ctx, dict):
            try:
                engine_weeks = int(estimate_ctx.get("timeline_weeks"))
            except (TypeError, ValueError):
                engine_weeks = None
        visitor_text = payload.get("visitor_text") or getattr(session, "_latest_user_text", "") or ""
        sanitized_message = sanitize_duration_leaks(sanitized_message, engine_weeks=engine_weeks, visitor_message=visitor_text)
    visitor_text = payload.get("visitor_text") or getattr(session, "_latest_user_text", "") or ""
    if visitor_text and route in ("fallback", "rag", "objection", "faq") and not payload.get("cards"):
        try:
            from backend.app.agents.critic import verify_and_refine_turn
            sanitized_message, chips = verify_and_refine_turn(
                user_text=visitor_text,
                draft_message=sanitized_message,
                draft_chips=chips,
                brief=brief,
                config=payload.get("config"),
                route=route,
                passages=passages,
            )
        except Exception:
            pass
    sanitized_message = OutputRails.scrub_tokens(sanitized_message)
    progress_val = payload.get("progress")
    if progress_val is None:
        progress_val = compute_discovery_progress(
            brief,
            payload.get("stage") or session.stage,
            payload.get("route") or "discovery",
        )
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
        "progress": progress_val,
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
