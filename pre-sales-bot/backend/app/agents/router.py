from __future__ import annotations

import json
import re

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.agents.brief import ProjectBrief, brief_ready, next_discovery_field
from backend.app.agents.extractor import apply_extracted_slots, extract_slots
from backend.app.agents.fallback import fallback_message
from backend.app.agents.suggestions import ensure_chips
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
BOOK = re.compile(r"\b(book|schedule)\b.{0,40}\b(call|meeting|consultation|time)\b", re.IGNORECASE)
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
        contact["email"] = found.group(0)
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
            message="Thanks. I can use confidential project notes in this chat now.",
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
            message="Here are a few times for a short call.",
            stage="booking",
            route="booking",
            chips=[{"label": slot["label"], "field": "booking_slot", "value": slot["slot_iso"]} for slot in slots],
            cards=[{"type": "booking", "title": "Pick a time", "live": live, "slots": slots}],
        )

    if field == "show_portfolio":
        cases = match_portfolio(brief, config.portfolio)
        return _finish(
            session, brief, contact, summary,
            message="These are the closest projects we can talk about from the structured portfolio.",
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

    objection = None if field else _objection(db, tenant, config, text, session.nda_accepted)
    if objection:
        return _finish(
            session, brief, contact, summary,
            message=objection["reply"],
            stage=session.stage or "discovery",
            route="objection",
            chips=_next_chips(brief) or [BOOK_CHIP],
        )

    filled = False
    if field and field not in ACTION:
        brief.apply_chip(field, value)
        _note_flags(brief)
        filled = True
    elif text:
        pending = _pending(brief)
        # 1. Try LLM-assisted multi-slot extraction if not a simple FAQ question
        extracted = extract_slots(text, pending, brief)
        if extracted and apply_extracted_slots(brief, extracted, pending):
            _note_flags(brief)
            filled = True
        elif not OPEN.search(text) and pending and _apply_free_text(brief, pending, text):
            # 2. Fallback to deterministic regex matching
            _note_flags(brief)
            filled = True

    if filled or (field and field not in ACTION):
        return _after_brief(session, config, brief, contact, summary)

    queries = lookup_queries(text, summary, previous[-3:]) or [text]
    filters = query_filters(text, service=brief.service, industry=brief.industry)
    faq_hits = _merge(db, tenant, queries, "faq", session.nda_accepted, filters)
    if faq_hits and faq_hits[0].score >= get_platform().faq_min_score:
        hit = faq_hits[0]
        message = hit.content
        extra = _continuation(brief)
        if extra:
            message = f"{message}\n\n{extra[0]}"
            chips = list(extra[1])
        else:
            chips = [BOOK_CHIP, PORTFOLIO_CHIP]
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
        message = fallback_message(config, brief, estimate)
        chunk_ids = []
        route = "fallback"
    extra = _continuation(brief)
    if extra:
        message = f"{message}\n\n{extra[0]}"
        chips = list(extra[1])
    elif brief_ready(brief):
        chips = [BOOK_CHIP, PORTFOLIO_CHIP]
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


def _after_brief(session, config, brief, contact, summary) -> dict:
    qual = qualify(brief, config.qualification, config.services, has_email=bool(contact.get("email")))
    if qual["band"] == "disqualify":
        return _finish(
            session, brief, contact, summary,
            message=qual["reasons"][0],
            stage="disqualified",
            route="discovery",
            chips=[BOOK_CHIP],
            qualification=qual,
        )
    if brief_ready(brief):
        return _estimate(session, config, brief, contact, summary, qual)
    field = next_discovery_field(brief)
    return _finish(
        session, brief, contact, summary,
        message=prompt_for(brief, field),
        stage="discovery",
        route="discovery",
        chips=chips_for_field(field or "", brief),
        qualification=qual,
    )


def _estimate(session, config, brief, contact, summary, qual) -> dict:
    estimate = estimate_project(brief, config.pricing)
    architecture = recommend_architecture(brief, config.services)
    mvp = recommend_mvp(brief)
    cases = match_portfolio(brief, config.portfolio)
    message = (
        f"A first-pass range for this is {estimate['range_label']} over about {estimate['timeline_weeks']} weeks. "
        f"{config.brand.disclaimer}"
    )
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


def _continuation(brief: ProjectBrief) -> tuple[str, list[dict]] | None:
    if brief_ready(brief):
        return None
    field = next_discovery_field(brief)
    if not field or field == "company_size":
        return None
    return prompt_for(brief, field), chips_for_field(field, brief)


def _next_chips(brief: ProjectBrief) -> list[dict]:
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
        brief.decision_role = mapped
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
    if "realtime" in blob or "live chat" in blob:
        brief.realtime = True


def _objection(db, tenant, config, text, nda_accepted: bool):
    found = match_objection(text, config.objections)
    if found or not text:
        return found
    hits = search(db, tenant, text, kind="objection", k=1, nda_accepted=nda_accepted)
    if hits and hits[0].score >= get_platform().faq_min_score:
        return {"id": hits[0].source_id, "reply": hits[0].content, "match": "semantic"}
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
    result = {
        "message": payload.get("message") or "",
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
