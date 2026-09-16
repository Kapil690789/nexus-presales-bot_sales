from __future__ import annotations

import argparse
from pathlib import Path

from sqlalchemy.orm import Session

from backend.app.config_loader.loader import AppConfig, get_config
from backend.app.core.settings import ROOT, get_settings
from backend.app.rag.chunker import config_documents, fixture_documents, website_documents
from backend.app.rag.content import CONTENT_SOURCE, ContentScan, scan_content
from backend.app.rag.store import Document, get_store

# Every source the chunker can emit. Listed explicitly so turning a source off in
# `rag.yaml` prunes its documents instead of leaving them behind.
KNOWLEDGE_SOURCES = (
    "portfolio",
    "services",
    "objections",
    "pages",
    "agency",
    "pricing",
    CONTENT_SOURCE,
    "fixtures",
    "website",
)

CONFIG_SOURCES = ("portfolio", "services", "objections", "pages", "agency", "pricing")

SOURCE_GROUPS = ("config", CONTENT_SOURCE, "fixtures", "website")


def website_dir(config: AppConfig) -> Path:
    raw = Path(config.rag.sources.website_dir)
    return raw if raw.is_absolute() else (ROOT / raw).resolve()


def content_dir(override: Path | str | None = None) -> Path:
    raw = Path(override) if override else Path(get_settings().content_dir)
    return raw if raw.is_absolute() else (ROOT / raw).resolve()


def build_documents(config: AppConfig | None = None) -> list[Document]:
    """Every document the enabled sources produce."""
    return collect_documents(config)[0]


def collect_documents(
    config: AppConfig | None = None,
    *,
    only: str | None = None,
    content_override: Path | str | None = None,
) -> tuple[list[Document], ContentScan | None]:
    """Collect documents, returning the content scan alongside them.

    The scan travels with the documents so the CLI can report on the library
    without reading every file a second time.
    """
    config = config or get_config()
    sources = config.rag.sources
    documents: list[Document] = []
    scan: ContentScan | None = None
    if sources.config and only in (None, "config"):
        documents += config_documents(config)
    if sources.content and only in (None, CONTENT_SOURCE):
        scan = scan_content(content_dir(content_override), set(config.services.in_scope))
        documents += scan.documents
    if sources.fixtures and only in (None, "fixtures"):
        documents += fixture_documents(ROOT / "fixtures")
    if sources.website and only in (None, "website"):
        documents += website_documents(website_dir(config))
    return documents, scan


def scan_summary(scan: ContentScan | None) -> dict | None:
    """JSON-safe view of a content scan, for API responses."""
    if scan is None:
        return None
    return {
        "files": scan.files,
        "indexed": scan.indexed,
        "skipped": scan.skipped,
        "errors": [str(finding) for finding in scan.errors],
        "warnings": [str(finding) for finding in scan.warnings],
    }


def _prunable(only: str | None) -> tuple[str, ...]:
    if only is None:
        return KNOWLEDGE_SOURCES
    if only == "config":
        return CONFIG_SOURCES
    return (only,)


def ingest(
    db: Session,
    config: AppConfig | None = None,
    *,
    only: str | None = None,
    prune: bool = True,
    content_override: Path | str | None = None,
) -> dict:
    """Rebuild the knowledge corpus. Idempotent: unchanged documents are not re-embedded."""
    config = config or get_config()
    if not get_settings().rag_enabled:
        return {"enabled": False, "documents": 0, "written": 0, "removed": 0, "backend": "disabled", "scan": None}
    documents, scan = collect_documents(config, only=only, content_override=content_override)
    keep: dict[str, set[str]] = {}
    for document in documents:
        keep.setdefault(document.source, set()).add(document.doc_id)
    store = get_store()
    written = store.upsert(db, documents)
    removed = 0
    if prune:
        removed = sum(store.delete_by_source(db, source, keep.get(source, set())) for source in _prunable(only))
    return {
        "enabled": True,
        "documents": len(documents),
        "written": written,
        "removed": removed,
        "backend": store.name,
        "scan": scan,
    }


def ingest_on_startup() -> dict:
    """Called from app startup. Never raises: an unreachable embedding API must not block boot."""
    from backend.app.models.db import SessionLocal

    try:
        with SessionLocal() as db:
            result = ingest(db)
            db.commit()
        return result
    except Exception as error:  # pragma: no cover - defensive
        return {"enabled": True, "error": str(error), "documents": 0, "written": 0, "removed": 0, "scan": None}


def _report(scan: ContentScan | None, *, verbose: bool) -> None:
    if scan is None:
        return
    print(f"\ncontent library: {scan.files} files, {scan.indexed} indexed, {scan.skipped} skipped")
    if verbose:
        by_doc: dict[str, int] = {}
        for document in scan.documents:
            by_doc[document.source_id] = by_doc.get(document.source_id, 0) + 1
        for source_id in sorted(by_doc):
            print(f"  {by_doc[source_id]:3} chunk(s)  {source_id}")
    findings = scan.findings if verbose else [f for f in scan.findings if f.level != "info"]
    if findings:
        print()
        for finding in findings:
            print(f"  {finding}")
    print(f"\n{len(scan.errors)} error(s), {len(scan.warnings)} warning(s)")


def main(argv: list[str] | None = None) -> int:
    parser = argparse.ArgumentParser(
        prog="python -m backend.app.rag.ingest",
        description="Index config/ and content/ into the RAG store.",
    )
    parser.add_argument("--dry-run", action="store_true", help="parse and validate without writing anything")
    parser.add_argument("--only", choices=SOURCE_GROUPS, help="index a single source group")
    parser.add_argument("--content-dir", help="override the content library location")
    parser.add_argument("--no-prune", action="store_true", help="keep chunks whose source file is gone")
    parser.add_argument("--verbose", "-v", action="store_true", help="list every document and every finding")
    args = parser.parse_args(argv)

    from backend.app.models.db import SessionLocal, init_db

    config = get_config()
    if args.dry_run:
        documents, scan = collect_documents(config, only=args.only, content_override=args.content_dir)
        print(f"dry run: {len(documents)} document chunk(s) would be indexed, nothing written")
        _report(scan, verbose=args.verbose)
        return 1 if scan and scan.errors else 0

    init_db()
    with SessionLocal() as db:
        result = ingest(
            db,
            config,
            only=args.only,
            prune=not args.no_prune,
            content_override=args.content_dir,
        )
        db.commit()
    print(
        f"backend={result['backend']} documents={result['documents']} "
        f"embedded={result['written']} pruned={result['removed']}"
    )
    _report(result.get("scan"), verbose=args.verbose)
    scan = result.get("scan")
    return 1 if scan and scan.errors else 0


if __name__ == "__main__":
    raise SystemExit(main())
