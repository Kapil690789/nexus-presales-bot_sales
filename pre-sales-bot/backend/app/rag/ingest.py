from __future__ import annotations

from pathlib import Path

import yaml
from sqlalchemy.orm import Session

from backend.app.core.platform import get_platform
from backend.app.documents.extract import extract_text
from backend.app.models.entities import TenantRow
from backend.app.rag.chunker import chunk_text
from backend.app.rag.store import Document, upsert_documents
from backend.app.tenants.loader import list_tenant_slugs, load_tenant, tenant_dir
from backend.app.tenants.schema import TenantConfig

SOURCES = {"faq", "portfolio", "objection", "content"}
FOLDER_DOC_TYPES = {
    "case-studies": "case_study",
    "testimonials": "testimonial",
}


def _front_matter(text: str) -> tuple[dict, str]:
    if not text.startswith("---"):
        return {}, text
    parts = text.split("---", 2)
    if len(parts) < 3:
        return {}, text
    meta = yaml.safe_load(parts[1]) or {}
    return (meta if isinstance(meta, dict) else {}), parts[2]


def documents_for(config: TenantConfig) -> list[Document]:
    platform = get_platform()
    documents: list[Document] = []
    for faq in config.faqs:
        documents.append(
            Document(
                doc_id=f"faq:{faq.id}",
                title=faq.question,
                content=faq.answer.strip(),
                embed_text=faq.question.strip(),
                source="faq",
                source_id=faq.id,
                kind="faq",
                metadata={
                    "embeds_as": "question",
                    "doc_type": "faq",
                    "topic": faq.topic,
                    "tags": list(faq.tags),
                },
            )
        )
    for case in config.portfolio.cases:
        content = "\n".join(
            [
                f"Case study: {case.title}",
                f"Industry: {case.industry}",
                f"Service: {case.service}",
                f"Outcome: {case.outcome}",
            ]
        )
        documents.append(
            Document(
                doc_id=f"portfolio:{case.id}",
                title=case.title,
                content=content,
                source="portfolio",
                source_id=case.id,
                kind="knowledge",
                metadata={
                    "doc_type": "portfolio",
                    "case_id": case.id,
                    "service": case.service,
                    "industry": case.industry,
                    "platforms": list(case.platforms),
                    "stacks": list(case.stacks),
                    "tags": list(case.tags),
                    "is_sample": config.slug == "demo",
                },
            )
        )
    for key, item in config.objections.items.items():
        documents.append(
            Document(
                doc_id=f"objection:{key}",
                title=key,
                content=" ".join(item.reply.split()),
                embed_text=" ".join(item.triggers),
                source="objection",
                source_id=key,
                kind="objection",
                metadata={"doc_type": "objection", "objection_id": key, "topic": item.topic},
            )
        )
    folder = tenant_dir(config.slug) / "content"
    if config.slug != "demo":
        try:
            demo_folder = tenant_dir("demo") / "content"
            if folder.resolve() == demo_folder.resolve():
                raise RuntimeError(f"Non-demo tenant '{config.slug}' cannot ingest demo tenant content.")
        except LookupError:
            pass
    if folder.is_dir():
        for path in sorted(folder.rglob("*")):
            if not path.is_file():
                continue
            if path.suffix.lower() not in {".md", ".txt", ".pdf", ".docx"}:
                continue
            documents.extend(
                _file_documents(
                    config.slug,
                    folder,
                    path,
                    platform.chunk_tokens,
                    platform.chunk_overlap_tokens,
                    platform.semantic_break_similarity,
                    semantic_chunking=getattr(config, "semantic_chunking", False),
                )
            )
    return documents


def _file_documents(
    slug: str,
    root: Path,
    path: Path,
    chunk_tokens: int,
    overlap: int,
    break_similarity: float,
    semantic_chunking: bool = False,
) -> list[Document]:
    relative = path.relative_to(root).as_posix()
    if path.suffix.lower() in {".md", ".txt"}:
        meta, body = _front_matter(path.read_text(encoding="utf-8"))
    else:
        meta = {}
        body = extract_text(path.name, path.read_bytes(), sanitize=False)
    if str(meta.get("status") or "published").lower() == "draft":
        return []
    title = str(meta.get("title") or path.stem)
    nda_only = bool(meta.get("nda_only"))
    case_id = str(meta.get("case_id") or "")
    metadata = _content_metadata(slug, relative, meta, case_id)
    chunks = chunk_text(
        body,
        chunk_tokens=chunk_tokens,
        overlap_tokens=overlap,
        break_similarity=break_similarity,
        semantic_chunking=semantic_chunking,
    )
    documents: list[Document] = []
    for index, (_heading, piece) in enumerate(chunks):
        documents.append(
            Document(
                doc_id=f"content:{relative}#{index}",
                title=title,
                content=piece,
                source="content",
                source_id=relative,
                kind="knowledge",
                nda_only=nda_only,
                metadata=dict(metadata),
            )
        )
    return documents


def _content_metadata(slug: str, relative: str, meta: dict, case_id: str) -> dict:
    folder = relative.split("/", 1)[0]
    tags = meta.get("tags") or []
    if isinstance(tags, str):
        tags = [part.strip() for part in tags.split(",") if part.strip()]
    elif isinstance(tags, list):
        tags = [str(item) for item in tags if str(item).strip()]
    else:
        tags = []
    return {
        "doc_type": str(meta.get("doc_type") or FOLDER_DOC_TYPES.get(folder) or ""),
        "case_id": case_id,
        "path": relative,
        "tenant": slug,
        "topic": str(meta.get("topic") or ""),
        "industry": str(meta.get("industry") or ""),
        "service": str(meta.get("service") or ""),
        "role": str(meta.get("role") or ""),
        "tags": tags,
        "is_sample": slug == "demo",
    }


def ingest_tenant(db: Session, tenant: TenantRow) -> dict:
    config = load_tenant(tenant.slug)
    documents = documents_for(config)
    result = upsert_documents(db, tenant, documents, sources=SOURCES)
    result["documents"] = len(documents)
    result["tenant"] = tenant.slug
    return result


def ingest_all(db: Session) -> list[dict]:
    from backend.app.tenants.loader import ensure_tenant_row

    results = []
    for slug in list_tenant_slugs():
        row = ensure_tenant_row(db, slug)
        results.append(ingest_tenant(db, row))
    return results


def main() -> None:
    from backend.app.models.db import SessionLocal, init_db

    init_db()
    with SessionLocal() as db:
        for result in ingest_all(db):
            print(result)


if __name__ == "__main__":
    main()
