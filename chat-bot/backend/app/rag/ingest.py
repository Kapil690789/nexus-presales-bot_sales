from __future__ import annotations

from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.config_loader.loader import AppConfig, get_config
from backend.app.core.settings import ROOT, get_settings
from backend.app.rag.chunker import config_documents, fixture_documents, website_documents
from backend.app.rag.store import Document, get_store

# Every source the chunker can emit. Listed explicitly so turning a source off in
# `rag.yaml` prunes its documents instead of leaving them behind.
KNOWLEDGE_SOURCES = ("portfolio", "services", "objections", "pages", "agency", "pricing", "fixtures", "website")


def website_dir(config: AppConfig) -> Path:
    raw = Path(config.rag.sources.website_dir)
    return raw if raw.is_absolute() else (ROOT / raw).resolve()


def build_documents(config: AppConfig | None = None) -> list[Document]:
    config = config or get_config()
    sources = config.rag.sources
    documents: list[Document] = []
    if sources.config:
        documents += config_documents(config)
    if sources.fixtures:
        documents += fixture_documents(ROOT / "fixtures")
    if sources.website:
        documents += website_documents(website_dir(config))
    return documents


def ingest(db: Session, config: AppConfig | None = None) -> dict:
    """Rebuild the knowledge corpus. Idempotent: unchanged documents are not re-embedded."""
    config = config or get_config()
    if not get_settings().rag_enabled:
        return {"enabled": False, "documents": 0, "written": 0, "removed": 0, "backend": "disabled"}
    documents = build_documents(config)
    keep: dict[str, set[str]] = {}
    for document in documents:
        keep.setdefault(document.source, set()).add(document.doc_id)
    store = get_store()
    written = store.upsert(db, documents)
    removed = sum(store.delete_by_source(db, source, keep.get(source, set())) for source in KNOWLEDGE_SOURCES)
    return {"enabled": True, "documents": len(documents), "written": written, "removed": removed, "backend": store.name}


def ingest_on_startup() -> dict:
    """Called from app startup. Never raises: an unreachable embedding API must not block boot."""
    from backend.app.models.db import SessionLocal

    try:
        with SessionLocal() as db:
            result = ingest(db)
            db.commit()
        return result
    except Exception as error:  # pragma: no cover - defensive
        return {"enabled": True, "error": str(error), "documents": 0, "written": 0, "removed": 0}


def main() -> None:
    from backend.app.models.db import SessionLocal, init_db

    init_db()
    with SessionLocal() as db:
        result = ingest(db)
        db.commit()
    print(
        f"backend={result['backend']} documents={result['documents']} "
        f"embedded={result['written']} pruned={result['removed']}"
    )


if __name__ == "__main__":
    main()
