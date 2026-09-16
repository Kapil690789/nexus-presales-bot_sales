from sqlalchemy import select

from backend.app.config_loader.loader import load_config
from backend.app.models.db import SessionLocal
from backend.app.models.entities import RagChunkRow
from backend.app.rag.chunker import chunk_text
from backend.app.rag.ingest import build_documents, ingest


def test_ingest_is_idempotent() -> None:
    with SessionLocal() as db:
        first = ingest(db)
        db.commit()
        assert first["documents"] > 0
        second = ingest(db)
        db.commit()
        assert second["written"] == 0
        assert second["removed"] == 0
        assert second["documents"] == first["documents"]


def test_every_config_entity_is_addressable() -> None:
    config = load_config()
    doc_ids = {document.doc_id for document in build_documents(config)}
    for case in config.portfolio.cases:
        assert f"portfolio:{case.id}" in doc_ids
    for key in config.services.in_scope:
        assert f"services:{key}" in doc_ids
    for key in config.objections.items:
        assert f"objections:{key}" in doc_ids
    assert {"agency:overview", "agency:disclaimer", "agency:nda", "pricing:inclusions", "pricing:exclusions"} <= doc_ids
    assert any(doc_id.startswith("fixture:sample-rfp") for doc_id in doc_ids)


def test_pricing_internals_are_never_indexed() -> None:
    config = load_config()
    corpus = "\n".join(document.content for document in build_documents(config))
    for base in config.pricing.bases.values():
        assert str(base) not in corpus
    assert str(config.pricing.low_side_factor) not in corpus
    assert "multiplier" not in corpus.lower()
    # The never-say list must not be echoed back to the model as reference material.
    for phrase in config.agency.never_say:
        assert phrase not in corpus


def test_stale_documents_are_pruned() -> None:
    with SessionLocal() as db:
        ingest(db)
        db.add(
            RagChunkRow(
                doc_id="portfolio:retired-case",
                kind="knowledge",
                source="portfolio",
                source_id="retired-case",
                content="A case study that was removed from portfolio.yaml.",
                embedding_model="hash-256",
                embedding_dim=256,
                embedding_json="[]",
            )
        )
        db.commit()
        result = ingest(db)
        db.commit()
        assert result["removed"] == 1
        assert db.scalar(select(RagChunkRow).where(RagChunkRow.doc_id == "portfolio:retired-case")) is None


def test_lessons_survive_a_knowledge_reindex() -> None:
    with SessionLocal() as db:
        db.add(
            RagChunkRow(
                doc_id="session:keep-me",
                kind="lesson",
                source="session",
                source_id="keep-me",
                content="Situation: a founder wanted an ops console.",
                embedding_model="hash-256",
                embedding_dim=256,
                embedding_json="[]",
            )
        )
        db.commit()
        ingest(db)
        db.commit()
        assert db.scalar(select(RagChunkRow).where(RagChunkRow.doc_id == "session:keep-me")) is not None
        db.delete(db.scalar(select(RagChunkRow).where(RagChunkRow.doc_id == "session:keep-me")))
        db.commit()


def test_chunk_text_packs_paragraphs_within_the_limit() -> None:
    body = "\n\n".join(f"Paragraph number {index} with some filler words." * 3 for index in range(12))
    chunks = chunk_text(body, max_chars=300, overlap=40)
    assert len(chunks) > 1
    assert all(len(chunk) <= 300 for chunk in chunks)
    assert chunk_text("") == []
    assert chunk_text("short") == ["short"]
