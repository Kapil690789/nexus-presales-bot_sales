from __future__ import annotations

import argparse
import json
from datetime import datetime, timedelta
from types import SimpleNamespace

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.config_loader.loader import AppConfig, get_config
from backend.app.core.llm import complete_json, llm_available
from backend.app.core.settings import get_settings
from backend.app.models.entities import EventRow, MessageRow, RagOutcomeRow, SessionRow
from backend.app.rag.redact import redact
from backend.app.rag.store import Document, get_store
from backend.app.services.sessions import brief_of, loads

OUTCOME_PORTFOLIO = "portfolio_case"
OUTCOME_OBJECTION = "objection"
OUTCOME_PAGE = "page_opening"

EVENT_EXPOSURE = "rag_exposure"
EVENT_CONVERSION = "rag_conversion"
EVENT_LESSON = "rag_lesson"

MAX_TRANSCRIPT_CHARS = 4000

SUCCESS_OUTCOMES = frozenset({"handoff", "qualified"})
AVOID_OUTCOMES = frozenset({"abandoned", "disqualified", "objected"})
OUTCOME_RANK = {
    "abandoned": 1,
    "objected": 2,
    "disqualified": 3,
    "qualified": 4,
    "handoff": 5,
}
LESSON_TEXT_KEYS = (
    "situation",
    "what_worked",
    "what_to_avoid",
    "tone_that_worked",
    "tone_to_avoid",
    "client_understanding",
    "what_they_liked",
)


def learning_enabled(config: AppConfig) -> bool:
    settings = get_settings()
    return bool(settings.rag_enabled and settings.learning_enabled and config.rag.learning.enabled)


def learning_threshold(config: AppConfig) -> int:
    override = config.rag.learning.min_score
    return int(override) if override is not None else int(config.qualification.book_threshold)


def win_rates(db: Session, subject_kind: str, prior: int = 3) -> dict[str, float]:
    """Smoothed conversion rate per subject.

    Dividing by ``sessions + prior`` keeps a single lucky conversation from
    outranking a case study with a real track record.
    """
    rows = db.scalars(select(RagOutcomeRow).where(RagOutcomeRow.subject_kind == subject_kind)).all()
    return {row.subject_id: row.handoffs / (row.sessions + max(prior, 0)) for row in rows if row.sessions}


def learn_from_session(
    db: Session,
    row,
    turn,
    config: AppConfig,
    *,
    abandoned: bool = False,
    force: bool = False,
) -> dict | None:
    """Record what this session exposed, and distill a lesson when it qualifies.

    Exposure is counted for every session that got far enough to show something.
    Lessons used to be success-only so win rates had negatives to compare against;
    failed chats now become avoid-lessons without incrementing handoffs.
    """
    if not learning_enabled(config):
        return None
    score = int((turn.qualification or {}).get("score") or 0)
    converted = bool(turn.handoff_summary)
    try:
        subjects = _record_exposure(db, row, turn)
        if converted:
            _record_conversion(db, row, subjects, score)
        outcome = _classify_outcome(db, row, turn, config, abandoned=abandoned)
        if outcome is None:
            return None
        existing = _event(db, row.id, EVENT_LESSON)
        existing_outcome = _payload(existing).get("outcome") if existing is not None else None
        if existing is not None and not force and not _is_upgrade(existing_outcome, outcome):
            return None
        return _write_lesson(db, row, turn, config, score=score, outcome=outcome, event=existing)
    except Exception:
        # Learning is a side effect. A failure here must never break the reply.
        return None


def stored_turn(db: Session, row: SessionRow):
    """Rebuild a turn-like object from what persist_turn already saved."""
    payload = _last_assistant_payload(db, row.id)
    objection = payload.get("objection")
    if not isinstance(objection, dict) or not objection:
        objection = None
    estimate = loads(row.estimate_json, None)
    return SimpleNamespace(
        brief=brief_of(row),
        qualification=loads(row.qualification_json, None) or {},
        estimate=estimate if isinstance(estimate, dict) else None,
        architecture=loads(row.architecture_json, None) or None,
        mvp=loads(row.mvp_json, None) or None,
        portfolio=loads(row.portfolio_json, None) or [],
        contact=loads(row.contact_json, None) or {},
        nda_accepted=bool(row.nda_accepted),
        booking=loads(row.booking_json, None) or None,
        handoff_summary=row.handoff_summary or None,
        stage=row.stage,
        objection=objection,
    )


def learn_from_row(
    db: Session,
    row: SessionRow,
    config: AppConfig,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> dict | None:
    """Learn from a stored session (backfill). Respects the same gates as live turns."""
    return learn_from_session(
        db,
        row,
        stored_turn(db, row),
        config,
        abandoned=_is_abandoned(row, config, now=now),
        force=force,
    )


def backfill(
    db: Session,
    config: AppConfig | None = None,
    *,
    now: datetime | None = None,
    force: bool = False,
) -> dict:
    """Distill lessons from sessions already in the database. Idempotent."""
    config = config or get_config()
    if not learning_enabled(config):
        return {"enabled": False, "scanned": 0, "written": 0, "skipped": 0}
    rows = db.scalars(select(SessionRow)).all()
    written = 0
    skipped = 0
    for row in rows:
        if learn_from_row(db, row, config, now=now, force=force):
            written += 1
        else:
            skipped += 1
    return {"enabled": True, "scanned": len(rows), "written": written, "skipped": skipped}


def forget_lesson(db: Session, session_id: str) -> int:
    deleted = get_store().delete_doc(db, f"session:{session_id}")
    row = db.get(SessionRow, session_id)
    if row is not None:
        row.learning_json = ""
        db.flush()
    return deleted


def _classify_outcome(db: Session, row, turn, config: AppConfig, *, abandoned: bool) -> str | None:
    if turn.handoff_summary:
        return "handoff"
    score = int((turn.qualification or {}).get("score") or 0)
    if score >= learning_threshold(config):
        return "qualified"
    if not config.rag.learning.include_failed:
        return None
    stage = str(getattr(turn, "stage", None) or row.stage or "").strip().lower()
    if stage == "disqualified":
        return "disqualified"
    if not abandoned:
        return None
    if _visitor_message_count(db, row.id) < max(1, int(config.rag.learning.min_visitor_messages)):
        return None
    objection = getattr(turn, "objection", None) or {}
    if (isinstance(objection, dict) and objection.get("id")) or stage == "objections":
        return "objected"
    return "abandoned"


def _is_upgrade(existing: str | None, new: str) -> bool:
    return OUTCOME_RANK.get(new, 0) > OUTCOME_RANK.get(existing or "", 0)


def _is_abandoned(row: SessionRow, config: AppConfig, *, now: datetime | None = None) -> bool:
    if row.handoff_summary:
        return False
    stage = (row.stage or "").strip().lower()
    if stage in {"handoff", "disqualified"}:
        return False
    stamp = row.updated_at or row.created_at or datetime.utcnow()
    idle = (now or datetime.utcnow()) - stamp
    return idle >= timedelta(minutes=max(0, int(config.rag.learning.abandon_after_minutes)))


def _visitor_message_count(db: Session, session_id: str) -> int:
    count = db.scalar(
        select(func.count()).select_from(MessageRow).where(MessageRow.session_id == session_id, MessageRow.role == "user")
    )
    return int(count or 0)


def _last_assistant_payload(db: Session, session_id: str) -> dict:
    messages = db.scalars(
        select(MessageRow)
        .where(MessageRow.session_id == session_id, MessageRow.role == "assistant")
        .order_by(MessageRow.created_at.desc())
    ).all()
    for message in messages:
        payload = loads(message.payload_json, {})
        if isinstance(payload, dict) and payload:
            return payload
    return {}


def _subjects(row, turn) -> list[list[str]]:
    subjects: list[list[str]] = []
    for case in turn.portfolio or []:
        case_id = case.get("id")
        if case_id:
            subjects.append([OUTCOME_PORTFOLIO, str(case_id)])
    objection = getattr(turn, "objection", None) or {}
    objection_id = objection.get("id") if isinstance(objection, dict) else None
    if objection_id:
        subjects.append([OUTCOME_OBJECTION, str(objection_id)])
    if row.path:
        subjects.append([OUTCOME_PAGE, str(row.path)])
    return subjects


def _record_exposure(db: Session, row, turn) -> list[list[str]]:
    """Count each subject once per session, accumulating as the conversation reveals more.

    Case studies only appear several turns in, so a one-shot snapshot on the first
    turn would only ever credit the entry page.
    """
    event = _event(db, row.id, EVENT_EXPOSURE)
    known: list[list[str]] = (_payload(event).get("subjects") or []) if event else []
    seen = {tuple(subject) for subject in known}
    fresh = [subject for subject in _subjects(row, turn) if tuple(subject) not in seen]
    if not fresh:
        return known
    for kind, subject_id in fresh:
        _bump(db, kind, subject_id, sessions=1)
    merged = known + fresh
    payload = json.dumps({"subjects": merged, "status": "recorded", "preview": f"{len(merged)} subjects tracked"})
    if event is None:
        db.add(EventRow(session_id=row.id, kind=EVENT_EXPOSURE, payload_json=payload))
    else:
        event.payload_json = payload
    db.flush()
    return merged


def _record_conversion(db: Session, row, subjects: list[list[str]], score: int) -> None:
    if _event(db, row.id, EVENT_CONVERSION) is not None or not subjects:
        return
    for kind, subject_id in subjects:
        _bump(db, kind, subject_id, handoffs=1, score_sum=score)
    db.add(
        EventRow(
            session_id=row.id,
            kind=EVENT_CONVERSION,
            payload_json=json.dumps(
                {"subjects": subjects, "score": score, "status": "recorded", "preview": f"converted at score {score}"}
            ),
        )
    )
    db.flush()


def _bump(db: Session, subject_kind: str, subject_id: str, *, sessions: int = 0, handoffs: int = 0, score_sum: int = 0) -> None:
    row = db.scalar(
        select(RagOutcomeRow).where(RagOutcomeRow.subject_kind == subject_kind, RagOutcomeRow.subject_id == subject_id)
    )
    if row is None:
        row = RagOutcomeRow(subject_kind=subject_kind, subject_id=subject_id)
        db.add(row)
    row.sessions = (row.sessions or 0) + sessions
    row.handoffs = (row.handoffs or 0) + handoffs
    row.score_sum = (row.score_sum or 0) + score_sum
    row.updated_at = datetime.utcnow()
    db.flush()


def _event(db: Session, session_id: str, kind: str) -> EventRow | None:
    return db.scalar(select(EventRow).where(EventRow.session_id == session_id, EventRow.kind == kind))


def _payload(event: EventRow) -> dict:
    try:
        value = json.loads(event.payload_json or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _write_lesson(
    db: Session, row, turn, config: AppConfig, *, score: int, outcome: str, event: EventRow | None = None
) -> dict:
    transcript = _transcript(db, row.id, config)
    lesson = _distill_llm(transcript, turn, config, outcome=outcome) if llm_available() else None
    mode = "llm"
    fallback = _distill_heuristic(row, turn, config, outcome)
    if not lesson:
        lesson = fallback
        mode = "heuristic"
    else:
        for key in LESSON_TEXT_KEYS:
            if not str(lesson.get(key) or "").strip():
                lesson[key] = fallback.get(key) or ""
        if not lesson.get("tags"):
            lesson["tags"] = fallback.get("tags") or []
    tags = sorted({str(tag).lower() for tag in lesson.get("tags") or [] if str(tag).strip()})
    lesson["tags"] = tags
    content = _lesson_content(lesson, outcome, score)
    brief = turn.brief
    record = {
        "outcome": outcome,
        "situation": lesson.get("situation") or "",
        "tone_that_worked": lesson.get("tone_that_worked") or "",
        "tone_to_avoid": lesson.get("tone_to_avoid") or "",
        "client_understanding": lesson.get("client_understanding") or "",
        "what_they_liked": lesson.get("what_they_liked") or "",
        "what_worked": lesson.get("what_worked") or "",
        "what_to_avoid": lesson.get("what_to_avoid") or "",
        "tags": tags,
        "score": score,
        "mode": mode,
    }
    metadata = {
        "session_id": row.id,
        "score": score,
        "band": (turn.qualification or {}).get("band") or "",
        "service": brief.service,
        "industry": brief.industry,
        "platforms": brief.platforms,
        "tags": tags,
        "outcome": outcome,
        "mode": mode,
        "tone_that_worked": record["tone_that_worked"],
        "client_understanding": record["client_understanding"],
        "what_they_liked": record["what_they_liked"],
    }
    get_store().upsert(
        db,
        [
            Document(
                doc_id=f"session:{row.id}",
                title=f"Lesson: {lesson['situation'][:120]}",
                content=content,
                kind="lesson",
                source="session",
                source_id=row.id,
                metadata=metadata,
            )
        ],
    )
    row.learning_json = json.dumps(record, default=str)
    payload = json.dumps(
        {
            "status": "learned",
            "preview": lesson["situation"],
            "mode": mode,
            "outcome": outcome,
            "body": content,
            "record": record,
        }
    )
    if event is None:
        db.add(EventRow(session_id=row.id, kind=EVENT_LESSON, payload_json=payload))
    else:
        event.payload_json = payload
    db.flush()
    return {**metadata, "content": content, "record": record}


def _lesson_content(lesson: dict, outcome: str, score: int) -> str:
    tags = [str(tag) for tag in lesson.get("tags") or [] if str(tag).strip()]
    return "\n".join(
        [
            f"Outcome: {outcome} (fit score {score})",
            f"Situation: {lesson.get('situation') or 'not recorded'}",
            f"Tone that worked: {lesson.get('tone_that_worked') or 'not recorded'}",
            f"Tone to avoid: {lesson.get('tone_to_avoid') or 'not recorded'}",
            f"Client understanding: {lesson.get('client_understanding') or 'not recorded'}",
            f"What they liked: {lesson.get('what_they_liked') or 'not recorded'}",
            f"What worked: {lesson.get('what_worked') or 'not recorded'}",
            f"What to avoid: {lesson.get('what_to_avoid') or 'nothing notable'}",
            f"Themes: {', '.join(tags) or 'general'}",
        ]
    )


def _transcript(db: Session, session_id: str, config: AppConfig) -> str:
    messages = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.created_at.asc())
    ).all()
    lines = [f"{message.role}: {message.content.strip()}" for message in messages if message.content.strip()]
    return redact("\n".join(lines), config.rag.redaction)[-MAX_TRANSCRIPT_CHARS:]


def _distill_llm(transcript: str, turn, config: AppConfig, *, outcome: str) -> dict | None:
    contract = (config.prompts.lesson_contract or "").strip()
    if not contract or not transcript:
        return None
    context = {
        "service": turn.brief.service,
        "industry": turn.brief.industry,
        "platforms": turn.brief.platforms,
        "stage": turn.stage,
        "band": (turn.qualification or {}).get("band"),
        "objection": (turn.objection or {}).get("id") if isinstance(turn.objection, dict) else None,
        "outcome": outcome,
    }
    try:
        data = complete_json(contract, f"Redacted transcript:\n{transcript}\n\nContext:\n{json.dumps(context, default=str)}")
    except Exception:
        return None
    situation = str(data.get("situation") or "").strip()
    worked = str(data.get("what_worked") or "").strip()
    avoid = str(data.get("what_to_avoid") or "").strip()
    if not situation or not (worked or avoid):
        return None
    tags = data.get("tags")
    rules = config.rag.redaction
    return {
        "situation": redact(situation, rules),
        "what_worked": redact(worked, rules),
        "what_to_avoid": redact(avoid, rules),
        "tone_that_worked": redact(str(data.get("tone_that_worked") or "").strip(), rules),
        "tone_to_avoid": redact(str(data.get("tone_to_avoid") or "").strip(), rules),
        "client_understanding": redact(str(data.get("client_understanding") or "").strip(), rules),
        "what_they_liked": redact(str(data.get("what_they_liked") or "").strip(), rules),
        "tags": tags if isinstance(tags, list) else [],
    }


def _distill_heuristic(row, turn, config: AppConfig, outcome: str) -> dict:
    """Template lesson so the offline demo still produces something inspectable."""
    brief = turn.brief
    rules = config.rag.redaction
    goal = redact(brief.goal or "an unspecified goal", rules)
    role = (brief.decision_role or "visitor of unknown role").replace("_", " ")
    platforms = ", ".join(brief.platforms) or "unspecified platforms"
    audience = f"A {role}"
    if brief.company_size:
        audience += f" at a {brief.company_size.replace('_', ' ')} company"
    situation = f"{audience} wanted {goal} ({brief.service or 'unspecified service'} on {platforms})."
    objection = getattr(turn, "objection", None) or {}
    objection_id = objection.get("id") if isinstance(objection, dict) else None

    if outcome in AVOID_OUTCOMES:
        tone_that_worked = "Short, plain language; admit misfit or pause quickly."
        tone_to_avoid = (
            "Long capability dumps, repeating commercial detail, or walking discovery like a form after they stalled."
        )
        if outcome == "disqualified":
            client_understanding = "They understood this was not a fit, or the brief was out of scope."
            liked = ""
            worked = "Closed politely rather than pushing an estimate."
            avoid = "Do not estimate or upsell once the brief is out of scope or below the floor."
        elif outcome == "objected":
            client_understanding = "They pushed back and did not get a clear answer to the concern."
            liked = ""
            worked = "Named the concern instead of talking past it."
            label = (objection_id or "unknown").replace("_", " ")
            avoid = f"They raised the '{label}' concern — address it before presenting more commercial detail."
        else:
            client_understanding = (
                "They left before the brief was complete, which often means the last question felt like a form "
                "or the reply was too long."
            )
            liked = "Short replies and chips when they were used."
            worked = "Chips and a single question keep momentum better than a paragraph of options."
            avoid = "Do not stack questions or re-ask something already in the transcript."
        tags = [tag for tag in [brief.service, brief.industry, outcome, objection_id] if tag]
        tags += list(brief.platforms)
        return {
            "situation": situation,
            "what_worked": worked,
            "what_to_avoid": avoid,
            "tone_that_worked": tone_that_worked,
            "tone_to_avoid": tone_to_avoid,
            "client_understanding": client_understanding,
            "what_they_liked": liked,
            "tags": tags,
        }

    worked_bits = [f"Discovery filled the brief from the {row.path} entry point"]
    liked_bits: list[str] = []
    if turn.estimate:
        worked_bits.append("an indicative range and timeline landed well")
        liked_bits.append("a single indicative range rather than a feature catalogue")
    if turn.portfolio:
        titles = " and ".join(redact(str(item.get("title") or ""), rules) for item in turn.portfolio[:2])
        worked_bits.append(f"showing {titles} as proof")
        liked_bits.append("named case studies as proof")
    if turn.booking and turn.booking.get("label"):
        worked_bits.append("the visitor booked a consultation")
    avoid = ""
    if objection_id:
        avoid = (
            f"They raised the '{objection_id.replace('_', ' ')}' concern — get ahead of it before presenting the range."
        )
    tags = [tag for tag in [brief.service, brief.industry, brief.budget_band, brief.timeline, objection_id] if tag]
    tags += list(brief.platforms) + list(brief.ai_features)
    return {
        "situation": situation,
        "what_worked": "; ".join(worked_bits) + ".",
        "what_to_avoid": avoid,
        "tone_that_worked": "Calm, specific, one question at a time.",
        "tone_to_avoid": "Repeating the price or walking discovery like a form after the brief is full.",
        "client_understanding": (
            "They followed the indicative range versus a contractual quote, and the MVP versus later cut."
        ),
        "what_they_liked": "; ".join(liked_bits),
        "tags": tags,
    }


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.app.rag.learn",
        description="Distill lessons from stored sessions into the RAG store.",
    )
    parser.add_argument("--backfill", action="store_true", help="learn from sessions already in the database")
    parser.add_argument("--force", action="store_true", help="rewrite existing lessons even without an outcome upgrade")
    args = parser.parse_args(argv)
    if not args.backfill:
        parser.error("pass --backfill to learn from stored sessions")

    from backend.app.models.db import SessionLocal, init_db

    init_db()
    config = get_config()
    with SessionLocal() as db:
        result = backfill(db, config, force=args.force)
        db.commit()
    print(f"scanned={result['scanned']} written={result['written']} skipped={result['skipped']}")
    return 0


if __name__ == "__main__":
    raise SystemExit(main())
