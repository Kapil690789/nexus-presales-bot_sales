from datetime import datetime, timedelta

from sqlalchemy import select

from backend.app.config_loader.loader import load_config
from backend.app.models.db import SessionLocal
from backend.app.models.entities import EventRow, RagChunkRow, RagOutcomeRow, SessionRow
from backend.app.rag.learn import OUTCOME_PAGE, OUTCOME_PORTFOLIO, backfill, learning_threshold, win_rates
from backend.app.rag.redact import redact
from backend.app.services.sessions import loads
from backend.tests.test_api import _book_first_slot, _chip, _discover, accept_nda


def _lessons(db, session_id: str) -> list[RagChunkRow]:
    return list(
        db.scalars(select(RagChunkRow).where(RagChunkRow.kind == "lesson", RagChunkRow.source_id == session_id)).all()
    )


def _reach_handoff(client) -> str:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    assert accept_nda(client, session_id).status_code == 200
    assert _book_first_slot(client, session_id).status_code == 200
    return session_id


def test_redaction_strips_identifying_details() -> None:
    rules = load_config().rag.redaction
    cleaned = redact(
        "Reach me at Dana Whitfield <dana@northline-labs.com> or +1 (415) 555-0134, see https://northline-labs.com/brief",
        rules,
    )
    assert "dana@northline-labs.com" not in cleaned
    assert "555-0134" not in cleaned
    assert "northline-labs.com" not in cleaned
    assert "Dana Whitfield" not in cleaned


def test_discovery_only_session_is_not_learned_from(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "Just browsing for now"})
    with SessionLocal() as db:
        assert _lessons(db, session_id) == []


def test_disqualified_session_is_learned_from(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "It's for my university coursework", "chip": _chip("Student", "decision_role", "intern_or_student")},
    )
    with SessionLocal() as db:
        lessons = _lessons(db, session_id)
        assert len(lessons) == 1
        lesson = lessons[0]
        row = db.get(SessionRow, session_id)
        record = loads(row.learning_json, {})
    assert "Outcome: disqualified" in lesson.content
    assert "Tone to avoid:" in lesson.content
    assert "What to avoid:" in lesson.content
    assert record["outcome"] == "disqualified"
    assert record["tone_to_avoid"]


def test_successful_session_is_learned_exactly_once(client) -> None:
    session_id = _reach_handoff(client)
    with SessionLocal() as db:
        lessons = _lessons(db, session_id)
        assert len(lessons) == 1
        lesson = lessons[0]
    assert lesson.doc_id == f"session:{session_id}"
    assert "Situation:" in lesson.content
    assert "What worked:" in lesson.content
    assert "Outcome:" in lesson.content
    assert "Tone that worked:" in lesson.content
    assert "Client understanding:" in lesson.content
    # The transcript held a work email; nothing identifying may reach the corpus.
    assert "founder@acme.test" not in lesson.content
    assert "@" not in lesson.content
    with SessionLocal() as db:
        row = db.get(SessionRow, session_id)
        record = loads(row.learning_json, {})
    assert record["outcome"] == "handoff"
    assert record["tone_that_worked"]

    client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "One more question about the timeline"})
    with SessionLocal() as db:
        assert len(_lessons(db, session_id)) == 1
        kinds = list(db.scalars(select(EventRow.kind).where(EventRow.session_id == session_id)))
    assert kinds.count("rag_lesson") == 1
    assert "rag_exposure" in kinds
    assert "rag_conversion" in kinds


def test_lesson_is_upgraded_when_the_session_converts(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    _discover(client, session_id)
    client.post(
        f"/api/v1/sessions/{session_id}/messages",
        json={"content": "Mid-market, about 400 people", "chip": _chip("Mid-market", "company_size", "mid_market")},
    )
    with SessionLocal() as db:
        early = _lessons(db, session_id)
        assert len(early) == 1, "clearing the score gate should be learned from right away"
        assert "Outcome: qualified" in early[0].content

    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    assert accept_nda(client, session_id).status_code == 200
    assert _book_first_slot(client, session_id).status_code == 200

    with SessionLocal() as db:
        final = _lessons(db, session_id)
        assert len(final) == 1
        assert "Outcome: handoff" in final[0].content
        events = list(db.scalars(select(EventRow.kind).where(EventRow.session_id == session_id)))
    assert events.count("rag_lesson") == 1


def test_conversion_is_recorded_against_what_was_shown(client) -> None:
    session_id = _reach_handoff(client)
    with SessionLocal() as db:
        exposure = db.scalar(select(EventRow).where(EventRow.session_id == session_id, EventRow.kind == "rag_exposure"))
        assert exposure is not None
        pages = db.scalars(select(RagOutcomeRow).where(RagOutcomeRow.subject_kind == OUTCOME_PAGE)).all()
        assert any(row.subject_id == "/demo/web-app-development.html" and row.handoffs >= 1 for row in pages)
        cases = db.scalars(select(RagOutcomeRow).where(RagOutcomeRow.subject_kind == OUTCOME_PORTFOLIO)).all()
        assert cases
        assert all(row.sessions >= row.handoffs for row in cases)


def test_win_rate_smoothing_favours_a_track_record() -> None:
    with SessionLocal() as db:
        db.add_all(
            [
                RagOutcomeRow(subject_kind="test_subject", subject_id="lucky", sessions=1, handoffs=1),
                RagOutcomeRow(subject_kind="test_subject", subject_id="proven", sessions=10, handoffs=8),
            ]
        )
        db.commit()
        rates = win_rates(db, "test_subject", prior=3)
        assert rates["proven"] > rates["lucky"]
        assert rates["lucky"] < 1.0
        for row in db.scalars(select(RagOutcomeRow).where(RagOutcomeRow.subject_kind == "test_subject")).all():
            db.delete(row)
        db.commit()


def test_learning_gate_defaults_to_the_book_threshold() -> None:
    config = load_config()
    assert learning_threshold(config) == config.qualification.book_threshold


def _age_session(session_id: str, minutes: int = 31) -> None:
    with SessionLocal() as db:
        row = db.get(SessionRow, session_id)
        row.updated_at = datetime.utcnow() - timedelta(minutes=minutes)
        db.commit()


def test_abandoned_session_is_learned_from_on_backfill(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    for content in ("Just looking at options", "Not sure yet", "Maybe another time"):
        assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content}).status_code == 200
    with SessionLocal() as db:
        assert _lessons(db, session_id) == []
    _age_session(session_id)
    with SessionLocal() as db:
        result = backfill(db, load_config())
        db.commit()
        lessons = _lessons(db, session_id)
        record = loads(db.get(SessionRow, session_id).learning_json, {})
    assert result["written"] >= 1
    assert len(lessons) == 1
    assert "Outcome: abandoned" in lessons[0].content
    assert "Tone to avoid:" in lessons[0].content
    assert record["outcome"] == "abandoned"
    with SessionLocal() as db:
        again = backfill(db, load_config())
        db.commit()
        assert len(_lessons(db, session_id)) == 1
    assert again["written"] == 0


def test_abandoned_lesson_upgrades_when_the_session_converts(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    for content in ("Just looking at options", "Not sure yet", "Maybe another time"):
        assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content}).status_code == 200
    _age_session(session_id)
    with SessionLocal() as db:
        backfill(db, load_config())
        db.commit()
        assert "Outcome: abandoned" in _lessons(db, session_id)[0].content
    _discover(client, session_id)
    assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "founder@acme.test"}).status_code == 200
    assert accept_nda(client, session_id).status_code == 200
    assert _book_first_slot(client, session_id).status_code == 200
    with SessionLocal() as db:
        final = _lessons(db, session_id)
        record = loads(db.get(SessionRow, session_id).learning_json, {})
    assert len(final) == 1
    assert "Outcome: handoff" in final[0].content
    assert record["outcome"] == "handoff"
    assert "founder@acme.test" not in final[0].content


def test_objected_idle_session_is_learned_from_on_backfill(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    for content in ("A web ops console", "Still exploring", "This is way too expensive"):
        assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content}).status_code == 200
    with SessionLocal() as db:
        assert _lessons(db, session_id) == []
    _age_session(session_id)
    with SessionLocal() as db:
        backfill(db, load_config())
        db.commit()
        lessons = _lessons(db, session_id)
        record = loads(db.get(SessionRow, session_id).learning_json, {})
    assert len(lessons) == 1
    assert "Outcome: objected" in lessons[0].content
    assert record["outcome"] == "objected"


def test_short_idle_session_is_still_not_learned_from(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "Just browsing for now"})
    _age_session(session_id)
    with SessionLocal() as db:
        backfill(db, load_config())
        db.commit()
        assert _lessons(db, session_id) == []


def test_admin_backfill_indexes_past_sessions(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/demo/web-app-development.html"}).json()["session_id"]
    for content in ("Just looking at options", "Not sure yet", "Maybe another time"):
        assert client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": content}).status_code == 200
    _age_session(session_id)
    response = client.post("/api/v1/admin/rag/backfill", auth=("admin", "test-admin"))
    assert response.status_code == 200
    body = response.json()
    assert body["enabled"] is True
    assert body["written"] >= 1
    page = client.get("/admin/rag", auth=("admin", "test-admin"))
    assert page.status_code == 200
    assert "Learn from past sessions" in page.text
    with SessionLocal() as db:
        assert _lessons(db, session_id)
    brief = client.get(f"/admin/sessions/{session_id}", auth=("admin", "test-admin"))
    assert brief.status_code == 200
    assert "Learned from this conversation" in brief.text
    assert "abandoned" in brief.text
