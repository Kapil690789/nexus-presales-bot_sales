from sqlalchemy import select

from backend.app.agents import orchestrator
from backend.app.agents.brief import ProjectBrief
from backend.app.config_loader.loader import load_config
from backend.app.core.settings import get_settings
from backend.app.engines.objections import match_objection
from backend.app.engines.portfolio import match_portfolio
from backend.app.models.db import SessionLocal
from backend.app.models.entities import RagOutcomeRow
from backend.app.rag.ingest import ingest
from backend.app.rag.learn import OUTCOME_PORTFOLIO
from backend.app.rag.retrieve import render_snippets, retrieve_knowledge, retrieve_lessons

AI_BRIEF = ProjectBrief(
    service="ai_product",
    goal="An assistant that drafts RFP responses from our document library",
    platforms=["web"],
    industry="professional_services",
    ai_features=["rag"],
)


def _ingested():
    db = SessionLocal()
    ingest(db)
    db.commit()
    return db


def test_retrieval_finds_the_relevant_case_and_service() -> None:
    config = load_config()
    db = _ingested()
    try:
        hits = retrieve_knowledge(db, "what have you built with RAG before?", AI_BRIEF, config.rag, k=5)
        doc_ids = [hit.doc_id for hit in hits]
        assert "portfolio:atlas-ai" in doc_ids
        assert doc_ids.index("portfolio:atlas-ai") == 0
        assert "services:ai_product" in doc_ids
    finally:
        db.close()


def test_retrieval_returns_nothing_for_an_unrelated_question() -> None:
    config = load_config()
    db = _ingested()
    try:
        assert retrieve_knowledge(db, "what is the weather in Berlin tomorrow", ProjectBrief(), config.rag) == []
    finally:
        db.close()


def test_retrieved_context_reaches_the_model_prompt(monkeypatch) -> None:
    config = load_config()
    captured: dict[str, str] = {}

    def fake_complete_json(system: str, user: str) -> dict:
        captured["system"] = system
        captured["user"] = user
        return {"message": "Here is how I would approach it.", "chips": [], "stage": "estimation"}

    monkeypatch.setattr(orchestrator, "llm_available", lambda: True)
    monkeypatch.setattr(orchestrator, "complete_json", fake_complete_json)
    db = _ingested()
    try:
        result = orchestrator.run_turn(
            config=config,
            brief=AI_BRIEF.model_copy(deep=True),
            contact={},
            nda_accepted=False,
            booking=None,
            user_text="what have you built with RAG before?",
            chip=None,
            page_opening="Exploring an AI product?",
            extra_questions=[],
            db=db,
        )
    finally:
        db.close()
    assert result.message == "Here is how I would approach it."
    assert "Reference knowledge" in captured["user"]
    assert "Lessons from past conversations" in captured["user"]
    assert "Atlas" in captured["user"], "the matched case study should be grounded in the prompt"
    assert "Engine JSON" in captured["user"]
    # The guard rules travel with the retrieved context.
    assert "reference knowledge is internal source material" in captured["system"].lower()


def test_retrieval_is_a_no_op_without_a_session() -> None:
    config = load_config()
    assert retrieve_knowledge(None, "anything", AI_BRIEF, config.rag) == []
    assert retrieve_lessons(None, AI_BRIEF, "estimation", config.rag) == []
    assert render_snippets([], config.rag.max_snippet_chars) == "(none)"


def test_snippets_are_truncated_for_the_prompt() -> None:
    config = load_config()
    db = _ingested()
    try:
        hits = retrieve_knowledge(db, "confidentiality and document uploads", AI_BRIEF, config.rag, k=2)
        assert hits
        assert all(len(hit.content) > 40 for hit in hits)
        rendered = render_snippets(hits, 40)
        assert rendered.count("…") == len(hits)
        assert len(rendered) < sum(len(hit.content) for hit in hits)
    finally:
        db.close()


def test_track_record_can_reorder_portfolio_matches() -> None:
    config = load_config()
    db = _ingested()
    try:
        brief = ProjectBrief(service="mobile_app", goal="A booking app for clinics", platforms=["ios", "android"])
        baseline = match_portfolio(brief, config.portfolio, limit=5, db=db, rag=config.rag)
        underdog = baseline[-1]["id"]
        # Flushed, never committed: the rollback below leaves no trace for other tests.
        record = db.scalar(
            select(RagOutcomeRow).where(
                RagOutcomeRow.subject_kind == OUTCOME_PORTFOLIO, RagOutcomeRow.subject_id == underdog
            )
        )
        if record is None:
            record = RagOutcomeRow(subject_kind=OUTCOME_PORTFOLIO, subject_id=underdog)
            db.add(record)
        record.sessions, record.handoffs = 6, 6
        db.flush()
        # A deliberately large boost proves the wiring; the shipped default only breaks ties.
        loud = config.rag.model_copy(update={"learning": config.rag.learning.model_copy(update={"outcome_boost": 50.0})})
        promoted = match_portfolio(brief, config.portfolio, limit=5, db=db, rag=loud)
        assert promoted[0]["id"] == underdog
        assert promoted[0]["win_rate"] > 0
        assert promoted[0]["keyword_score"] == next(case["keyword_score"] for case in baseline if case["id"] == underdog)
    finally:
        db.rollback()
        db.close()


def test_portfolio_matching_is_unchanged_without_a_session() -> None:
    config = load_config()
    matches = match_portfolio(
        ProjectBrief(service="ai_product", industry="professional_services", ai_features=["rfp"]), config.portfolio
    )
    assert matches[0]["title"].startswith("Atlas")
    assert matches[0]["win_rate"] == 0


def test_disabling_rag_restores_keyword_only_behaviour(monkeypatch) -> None:
    config = load_config()
    db = _ingested()
    try:
        monkeypatch.setattr(get_settings(), "rag_enabled", False)
        brief = ProjectBrief(service="mobile_app", goal="A booking app for clinics", platforms=["ios", "android"])
        with_session = match_portfolio(brief, config.portfolio, limit=5, db=db, rag=config.rag)
        without_session = match_portfolio(brief, config.portfolio, limit=5)
        assert [case["id"] for case in with_session] == [case["id"] for case in without_session]
        assert all(case["score"] == case["keyword_score"] for case in with_session)
        assert retrieve_knowledge(db, "what have you built with RAG before?", AI_BRIEF, config.rag) == []
        assert match_objection("your price is a bigger number than we set aside", config.objections, db=db, rag=config.rag) is None
    finally:
        db.close()


def test_objection_triggers_still_win_outright() -> None:
    config = load_config()
    db = _ingested()
    try:
        hit = match_objection("This is way too expensive", config.objections, db=db, rag=config.rag)
        assert hit is not None
        assert hit["id"] == "too_expensive"
        assert hit["match"] == "trigger"
    finally:
        db.close()


def test_semantic_fallback_catches_an_unlisted_phrasing() -> None:
    config = load_config()
    db = _ingested()
    try:
        text = "your price is a bigger number than the budget we set aside"
        assert match_objection(text, config.objections) is None
        hit = match_objection(text, config.objections, db=db, rag=config.rag)
        assert hit is not None
        assert hit["id"] == "too_expensive"
        assert hit["match"] == "semantic"
        # The reply is the approved copy from config, never the indexed text.
        assert hit["reply"] == config.objections.items["too_expensive"].reply.strip()
    finally:
        db.close()


def test_unrelated_message_is_still_not_an_objection() -> None:
    config = load_config()
    db = _ingested()
    try:
        assert match_objection("We need appointment reminders", config.objections, db=db, rag=config.rag) is None
    finally:
        db.close()
