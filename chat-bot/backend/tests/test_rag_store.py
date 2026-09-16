import pytest
from sqlalchemy import select

from backend.app.core.settings import get_settings
from backend.app.models.db import SessionLocal
from backend.app.models.entities import RagChunkRow
from backend.app.rag.embeddings import FALLBACK_DIM, FALLBACK_MODEL, active_model, embed_texts
from backend.app.rag.store import Document, FallbackStore, PgVectorStore, corpus_stats, get_store

SOURCE = "test_store"

DOCS = [
    Document(
        doc_id="test:mobile",
        title="Flutter marketplace app",
        content="A two-sided marketplace built with Flutter for ios and android buyers and sellers.",
        source=SOURCE,
        source_id="mobile",
        metadata={"service": "mobile_app", "platforms": ["ios", "android"]},
    ),
    Document(
        doc_id="test:finance",
        title="Accounting console",
        content="A multi-entity finance operations console for accountants closing the books.",
        source=SOURCE,
        source_id="finance",
        metadata={"service": "web_app", "platforms": ["web"]},
    ),
]


@pytest.fixture
def store():
    instance = FallbackStore()
    yield instance
    with SessionLocal() as db:
        instance.delete_by_source(db, SOURCE)
        db.commit()


def test_local_embedder_is_used_without_an_api_key() -> None:
    assert active_model() == (FALLBACK_MODEL, FALLBACK_DIM)


def test_hash_embedding_is_deterministic_and_unit_length() -> None:
    first = embed_texts(["a marketplace for farm produce"])
    second = embed_texts(["a marketplace for farm produce"])
    assert first.vectors == second.vectors
    assert len(first.vectors[0]) == FALLBACK_DIM
    assert abs(sum(value * value for value in first.vectors[0]) - 1.0) < 1e-6


def test_fallback_store_ranks_by_similarity(store) -> None:
    with SessionLocal() as db:
        assert store.upsert(db, DOCS) == 2
        db.commit()
        hits = store.search(db, "flutter marketplace for ios and android", k=2, kind="knowledge", sources=[SOURCE])
        assert hits
        assert hits[0].doc_id == "test:mobile"
        assert hits[0].score > 0
        assert hits[0].metadata["service"] == "mobile_app"


def test_unchanged_documents_are_not_re_embedded(store) -> None:
    with SessionLocal() as db:
        store.upsert(db, DOCS)
        db.commit()
        assert store.upsert(db, DOCS) == 0
        edited = Document(**{**DOCS[0].__dict__, "content": DOCS[0].content + " Now with in-app payments."})
        assert store.upsert(db, [edited]) == 1
        db.commit()
        row = db.scalar(select(RagChunkRow).where(RagChunkRow.doc_id == "test:mobile"))
        assert "payments" in row.content


def test_vectors_of_the_wrong_shape_are_never_compared(store) -> None:
    """Rows from another model, or from before a model change, must be skipped."""
    with SessionLocal() as db:
        store.upsert(db, DOCS)
        db.add_all(
            [
                RagChunkRow(
                    doc_id="test:alien",
                    kind="knowledge",
                    source=SOURCE,
                    source_id="alien",
                    content="flutter marketplace for ios and android",
                    embedding_model="some-other-model",
                    embedding_dim=3,
                    embedding_json="[1.0, 0.0, 0.0]",
                ),
                # Same model name, stale dimension: this is what would make the
                # numpy matrix ragged if it were not filtered out.
                RagChunkRow(
                    doc_id="test:stale-dim",
                    kind="knowledge",
                    source=SOURCE,
                    source_id="stale",
                    content="flutter marketplace for ios and android",
                    embedding_model=FALLBACK_MODEL,
                    embedding_dim=3,
                    embedding_json="[1.0, 0.0, 0.0]",
                ),
            ]
        )
        db.commit()
        hits = store.search(db, "flutter marketplace for ios and android", k=5, kind="knowledge", sources=[SOURCE])
        assert hits
        assert hits[0].doc_id == "test:mobile"
        assert {hit.doc_id for hit in hits}.isdisjoint({"test:alien", "test:stale-dim"})


def test_delete_by_source_can_keep_documents(store) -> None:
    with SessionLocal() as db:
        store.upsert(db, DOCS)
        db.commit()
        assert store.delete_by_source(db, SOURCE, {"test:mobile"}) == 1
        db.commit()
        remaining = db.scalars(select(RagChunkRow.doc_id).where(RagChunkRow.source == SOURCE)).all()
        assert remaining == ["test:mobile"]


def test_backend_selection_follows_the_setting(monkeypatch) -> None:
    settings = get_settings()
    assert isinstance(get_store(), FallbackStore), "SQLite has no vector column, so auto must fall back"
    monkeypatch.setattr(settings, "rag_backend", "pgvector")
    assert isinstance(get_store(), PgVectorStore)
    monkeypatch.setattr(settings, "rag_backend", "fallback")
    assert isinstance(get_store(), FallbackStore)


def test_corpus_stats_reports_the_active_backend() -> None:
    with SessionLocal() as db:
        stats = corpus_stats(db)
    assert stats["backend"] == "fallback"
    assert stats["embedding_model"] == FALLBACK_MODEL
    assert stats["embedding_dim"] == FALLBACK_DIM
