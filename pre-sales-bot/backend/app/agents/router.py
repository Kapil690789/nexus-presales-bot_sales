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
ACTION = {"show_portfolio", "booking_window", "booking_slot", "nda", "close_out"}


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

    if field == "booking_slot":
        return _book(db, tenant, config, session, brief, contact, summary, str(value or ""))

    if field == "booking_window" or (text and not field and BOOK.search(text)):
        slots, live = list_slots(tenant)
        return _finish(
            session, brief, contact, summary,
            message="Here are a few times for a short discovery call with our team:",
            stage="booking",
            route="booking",
            chips=[{"label": slot["label"], "field": "booking_slot", "value": slot["slot_iso"]} for slot in slots],
            cards=[{"type": "booking", "title": "Pick a time", "live": live, "slots": slots}],
        )

    # Email capture (booking confirmation or lead capture)
    if found:
        email = contact["email"]
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
            if booked.get("meet_url"):
                reply += f" Google Meet link: {booked['meet_url']}."
            reply += " Our solutions engineering team is looking forward to the discussion!"

            post_chips = [
                {"label": "What is on the agenda?", "field": "ask", "value": "What is on the agenda for our discovery call?"},
                {"label": "Can I invite a colleague?", "field": "ask", "value": "Can I invite a colleague to the call?"},
                {"label": "Can I reschedule the time?", "field": "booking_window", "value": "reschedule"},
            ]
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="handoff",
                route="booking",
                chips=post_chips,
                cards=[{"type": "booking", "title": "Confirmed", **booked}],
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
            slots, live = list_slots(tenant)
            reply = f"Thank you! I've recorded your email ({email}) for the proposal. Here are a few times for a short discovery call with our team:"
            return _finish(
                session, brief, contact, summary,
                message=reply,
                stage="booking",
                route="booking",
                chips=[{"label": slot["label"], "field": "booking_slot", "value": slot["slot_iso"]} for slot in slots],
                cards=[{"type": "booking", "title": "Pick a time", "live": live, "slots": slots}],
                qualification=qual,
                estimate=estimate,
                handoff_summary=handoff,
            )

    # Post-booking specific questions (colleague, agenda)
    if session.booking_json and text:
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
            reply = (
                "Our 30-minute discovery call agenda covers:\n"
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
        return _finish(
            session, brief, contact, summary,
            message="Here are relevant case studies and similar projects from our past work:",
            stage=session.stage or "advising",
            route="portfolio",
            chips=[BOOK_CHIP],
            cards=[{"type": "portfolio", "title": "Similar work", "cases": cases}],
            portfolio=cases,
        )

    if field == "close_out":
        return _finish(
            session, brief, contact, summary,
            message="Thanks for chatting with us! If you'd like to talk through your project with our engineering team, feel free to book a short call anytime.",
            stage=session.stage or "discovery",
            route="discovery",
            chips=[BOOK_CHIP],
        )

    direct_objection = match_objection(text, config.objections) if (text and not field) else None
    if direct_objection:
        return _finish(
            session, brief, contact, summary,
            message=direct_objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=_next_chips(brief, has_booking=bool(session.booking_json)),
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
            # 1. Try LLM-assisted multi-slot extraction if not a simple FAQ question
            extracted = extract_slots(text, pending, brief)
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
                    )

    if filled or (field and field not in ACTION):
        return _after_brief(session, config, brief, contact, summary, user_text=text, history=history)

    semantic_objection = _objection(db, tenant, config, text, session.nda_accepted) if (text and not field) else None
    if semantic_objection:
        return _finish(
            session, brief, contact, summary,
            message=semantic_objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=_next_chips(brief, has_booking=bool(session.booking_json)),
        )

    raw_queries = lookup_queries(text, summary, previous[-3:]) or [text]
    queries = [rewrite_query_with_brief(q, brief) for q in raw_queries]
    filters = query_filters(text, service=brief.service, industry=brief.industry)
    faq_hits = _merge(db, tenant, queries, "faq", session.nda_accepted, filters)
    if faq_hits and faq_hits[0].score >= get_platform().faq_min_score:
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
        )

    hits = _merge(db, tenant, queries, "knowledge", session.nda_accepted, filters)
    decision, score = grade(queries[0], hits)
    strong = _strong_hits(hits)
    if decision == "show" and strong:
        message = grounded_answer(queries[0], strong)
        chunk_ids = [hit.id for hit in strong]
        route = "rag"
    else:
        estimate = estimate_project(brief, config.pricing) if brief_ready(brief) else None
        platform = get_platform()
        is_weak = decision == "weak" or (platform.weak_min_score <= score < platform.show_min_score)
        weak_notes = hits[:3] if is_weak and hits else None
        message = fallback_message(config, brief, estimate, query=queries[0], notes=weak_notes)
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
    )


def _book(db, tenant, config, session, brief, contact, summary, slot_iso: str) -> dict:
    email = contact.get("email") or ""
    booked = confirm_slot(
        tenant,
        slot_iso,
        f"Discovery call — {config.brand.name}",
        email,
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
    if booked.get("meet_url"):
        message += f" Meet link: {booked['meet_url']}"
    if not email:
        message += " Reply with your work email so the invite has somewhere to go."
    return _finish(
        session, brief, contact, summary,
        message=message,
        stage="handoff",
        route="booking",
        chips=[],
        cards=[{"type": "booking", "title": "Booked", **booked}],
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
        data = complete_json("You are an expert enterprise pre-sales software consultant. Output JSON only.", prompt)
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


def _after_brief(session, config, brief, contact, summary, user_text: str = "", history: list[dict] | None = None) -> dict:
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
        )
    if brief_ready(brief):
        return _estimate(session, config, brief, contact, summary, qual)
    field = next_discovery_field(brief)
    attempts = brief.field_attempts.get(field or "", 0)
    repeat = attempts >= 1
    if field:
        brief.field_attempts[field] = attempts + 1
    prompt_msg = prompt_for(brief, field, repeat=repeat) if repeat else synthesize_discovery_prompt(config, brief, field, user_text=user_text)
    chips = chips_for_field(field, brief, repeat=repeat) or ensure_chips(brief, prompt_msg)
    return _finish(
        session, brief, contact, summary,
        message=prompt_msg,
        stage="discovery",
        route="discovery",
        chips=chips,
        qualification=qual,
    )


def _estimate(session, config, brief, contact, summary, qual) -> dict:
    estimate = estimate_project(brief, config.pricing)
    architecture = recommend_architecture(brief, config.services)
    mvp = recommend_mvp(brief)
    cases = match_portfolio(brief, config.portfolio)
    message = _synthesize_estimate_message(config, brief, estimate)
    chips = [BOOK_CHIP, PORTFOLIO_CHIP]
    if not brief.company_size:
        message += "\n\n" + DISCOVERY_PROMPTS["company_size"]
        chips = chips_for_field("company_size") + chips
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
        {"type": "portfolio", "title": "Similar work", "cases": cases},
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
        brief.integrations = [part.strip() for part in cleaned.split(",") if part.strip()]
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
    if "ai" in lowered:
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
    if "asap" in lowered or "soon" in lowered or "next month" in lowered:
        return "asap"
    if "flex" in lowered or "no rush" in lowered:
        return "flexible"
    if "3" in lowered and "6" in lowered:
        return "3_6_months"
    if "1" in lowered or "quarter" in lowered or "month" in lowered:
        return "1_3_months"
    return None


def _budget(text: str) -> str | None:
    lowered = text.lower().replace(",", "")
    if "explor" in lowered or "not sure" in lowered:
        return "exploring"
    if "under" in lowered or "below" in lowered or "10k" in lowered or "8k" in lowered:
        return "under_15k"
    if "40" in lowered and "80" in lowered:
        return "40_80k"
    if "15" in lowered and "40" in lowered:
        return "15_40k"
    if "80" in lowered or "100k" in lowered or "100000" in lowered:
        return "80k_plus"
    if "40" in lowered:
        return "40_80k"
    if "15" in lowered:
        return "15_40k"
    return None


def _role(text: str) -> str | None:
    lowered = text.lower()
    if "intern" in lowered or "student" in lowered:
        if re.search(r"\b(my\s+cousin|his|her|their|friend|my\s+friend|our\s+intern|my\s+brother|my\s+sister)\b.{0,30}\b(student|intern|college)\b", lowered):
            return None
        return "intern_or_student"
    if "founder" in lowered or "ceo" in lowered or "exec" in lowered:
        return "founder_or_exec"
    if "product" in lowered or "ops" in lowered:
        return "product_or_ops_lead"
    if "agency" in lowered or "reseller" in lowered:
        return "agency_or_reseller"
    if "manager" in lowered:
        return "manager"
    return None


def _size(text: str) -> str | None:
    lowered = text.lower()
    if "enterprise" in lowered:
        return "enterprise"
    if "mid" in lowered:
        return "mid_market"
    if "smb" in lowered or "small" in lowered:
        return "smb"
    if "startup" in lowered:
        return "startup"
    return None


def _note_flags(brief: ProjectBrief) -> None:
    blob = " ".join([brief.goal or "", " ".join(brief.features or [])]).lower()
    if any(word in blob for word in ("login", "auth", "account")):
        brief.auth = True
    if "admin" in blob:
        brief.admin = True
    if "marketplace" in blob:
        brief.marketplace = True
    # Match "realtime", "real-time", and "real time"
    if "realtime" in blob or "real-time" in blob or "real time" in blob or "live chat" in blob or "live-chat" in blob:
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


def _merge(db, tenant, queries: list[str], kind: str, nda_accepted: bool, filters: dict | None = None):
    merged = {}
    for query in queries:
        if not query.strip():
            continue
        for hit in search(db, tenant, query, kind=kind, nda_accepted=nda_accepted, filters=filters):
            current = merged.get(hit.doc_id)
            if current is None or hit.score > current.score:
                merged[hit.doc_id] = hit
    return sorted(merged.values(), key=lambda item: item.score, reverse=True)


def rewrite_query_with_brief(query: str, brief: ProjectBrief | None) -> str:
    if not brief or not query:
        return query or ""
    cleaned = query.strip()
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
