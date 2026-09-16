from __future__ import annotations

import json
from datetime import datetime

from sqlalchemy import select
from sqlalchemy.orm import Session

from backend.app.config_loader.loader import AppConfig
from backend.app.core.llm import complete_json, llm_available
from backend.app.core.settings import get_settings
from backend.app.models.entities import EventRow, MessageRow, RagOutcomeRow
from backend.app.rag.redact import redact
from backend.app.rag.store import Document, get_store

OUTCOME_PORTFOLIO = "portfolio_case"
OUTCOME_OBJECTION = "objection"
OUTCOME_PAGE = "page_opening"

EVENT_EXPOSURE = "rag_exposure"
EVENT_CONVERSION = "rag_conversion"
EVENT_LESSON = "rag_lesson"

MAX_TRANSCRIPT_CHARS = 4000


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


def learn_from_session(db: Session, row, turn, config: AppConfig) -> dict | None:
    """Record what this session exposed, and distill a lesson if it succeeded.

    Exposure is counted for every session that got far enough to show something,
    while lessons are gated on success — otherwise win rates would have no
    negatives to compare against and every subject would look like a winner.
    """
    if not learning_enabled(config):
        return None
    score = int((turn.qualification or {}).get("score") or 0)
    converted = bool(turn.handoff_summary)
    try:
        subjects = _record_exposure(db, row, turn)
        if converted:
            _record_conversion(db, row, subjects, score)
        if not (converted or score >= learning_threshold(config)):
            return None
        existing = _event(db, row.id, EVENT_LESSON)
        if existing is not None and not (converted and _payload(existing).get("outcome") != "handoff"):
            return None
        # A session that clears the score gate is learned from immediately, then
        # rewritten once it converts — the converting version is the useful one.
        return _write_lesson(db, row, turn, config, score=score, converted=converted, event=existing)
    except Exception:
        # Learning is a side effect. A failure here must never break the reply.
        return None


def _subjects(row, turn) -> list[list[str]]:
    subjects: list[list[str]] = []
    for case in turn.portfolio or []:
        case_id = case.get("id")
        if case_id:
            subjects.append([OUTCOME_PORTFOLIO, str(case_id)])
    objection_id = (turn.objection or {}).get("id")
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
    db: Session, row, turn, config: AppConfig, *, score: int, converted: bool, event: EventRow | None = None
) -> dict:
    transcript = _transcript(db, row.id, config)
    lesson = _distill_llm(transcript, turn, config) if llm_available() else None
    mode = "llm"
    if not lesson:
        lesson = _distill_heuristic(row, turn, config)
        mode = "heuristic"
    tags = sorted({str(tag).lower() for tag in lesson.get("tags") or [] if str(tag).strip()})
    outcome = "handoff" if converted else "qualified"
    content = "\n".join(
        [
            f"Situation: {lesson['situation']}",
            f"What worked: {lesson['what_worked']}",
            f"What to avoid: {lesson['what_to_avoid'] or 'nothing notable'}",
            f"Themes: {', '.join(tags) or 'general'}",
            f"Outcome: {outcome} (fit score {score})",
        ]
    )
    brief = turn.brief
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
    payload = json.dumps(
        {"status": "learned", "preview": lesson["situation"], "mode": mode, "outcome": outcome, "body": content}
    )
    if event is None:
        db.add(EventRow(session_id=row.id, kind=EVENT_LESSON, payload_json=payload))
    else:
        event.payload_json = payload
    db.flush()
    return {**metadata, "content": content}


def _transcript(db: Session, session_id: str, config: AppConfig) -> str:
    messages = db.scalars(
        select(MessageRow).where(MessageRow.session_id == session_id).order_by(MessageRow.created_at.asc())
    ).all()
    lines = [f"{message.role}: {message.content.strip()}" for message in messages if message.content.strip()]
    return redact("\n".join(lines), config.rag.redaction)[-MAX_TRANSCRIPT_CHARS:]


def _distill_llm(transcript: str, turn, config: AppConfig) -> dict | None:
    contract = (config.prompts.lesson_contract or "").strip()
    if not contract or not transcript:
        return None
    context = {
        "service": turn.brief.service,
        "industry": turn.brief.industry,
        "platforms": turn.brief.platforms,
        "stage": turn.stage,
        "band": (turn.qualification or {}).get("band"),
        "objection": (turn.objection or {}).get("id"),
    }
    try:
        data = complete_json(contract, f"Redacted transcript:\n{transcript}\n\nContext:\n{json.dumps(context, default=str)}")
    except Exception:
        return None
    situation = str(data.get("situation") or "").strip()
    worked = str(data.get("what_worked") or "").strip()
    if not situation or not worked:
        return None
    tags = data.get("tags")
    return {
        "situation": redact(situation, config.rag.redaction),
        "what_worked": redact(worked, config.rag.redaction),
        "what_to_avoid": redact(str(data.get("what_to_avoid") or "").strip(), config.rag.redaction),
        "tags": tags if isinstance(tags, list) else [],
    }


def _distill_heuristic(row, turn, config: AppConfig) -> dict:
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

    worked = [f"Discovery filled the brief from the {row.path} entry point"]
    if turn.estimate:
        worked.append(
            f"an indicative range of {turn.estimate['range_label']} over {turn.estimate['timeline_weeks']} weeks landed well"
        )
    if turn.portfolio:
        worked.append("showing " + " and ".join(item["title"] for item in turn.portfolio[:2]) + " as proof")
    if turn.booking and turn.booking.get("label"):
        worked.append(f"the visitor booked {turn.booking['label']}")

    avoid = ""
    objection_id = (turn.objection or {}).get("id")
    if objection_id:
        avoid = f"They raised the '{objection_id.replace('_', ' ')}' concern — get ahead of it before presenting the range."

    tags = [tag for tag in [brief.service, brief.industry, brief.budget_band, brief.timeline, objection_id] if tag]
    tags += brief.platforms + brief.ai_features
    return {"situation": situation, "what_worked": "; ".join(worked) + ".", "what_to_avoid": avoid, "tags": tags}
