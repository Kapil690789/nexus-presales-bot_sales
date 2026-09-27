from __future__ import annotations

import hashlib
import json
import logging
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.core.platform import get_platform
from backend.app.models.db import pgvector_ready
from backend.app.models.entities import ChunkRow, TenantRow
from backend.app.rag.embeddings import cosine, embed_texts, model_id_for

log = logging.getLogger(__name__)


@dataclass
class Document:
    doc_id: str
    title: str
    content: str
    source: str
    source_id: str = ""
    kind: str = "knowledge"
    embed_text: str = ""
    metadata: dict = field(default_factory=dict)
    nda_only: bool = False


@dataclass
class Hit:
    id: str
    doc_id: str
    title: str
    content: str
    score: float
    source: str
    metadata: dict
    nda_only: bool = False


FILTER_KEYS = ("doc_type", "topic", "industry", "service", "role")


def _doc_key(doc_id: str) -> str:
    return doc_id.split("#", 1)[0]


def _public_metadata(metadata: dict) -> dict:
    clean = {}
    for key, value in metadata.items():
        if key == "_hash" or value in ("", None, []):
            continue
        clean[key] = value
    return clean


def _metadata_blob(metadata: dict) -> str:
    return json.dumps(_public_metadata(metadata), sort_keys=True, separators=(",", ":"))


def _stored_metadata(raw: str) -> dict:
    try:
        data = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return data if isinstance(data, dict) else {}


def _clean_filters(filters: dict | None) -> dict[str, str]:
    cleaned: dict[str, str] = {}
    for key, value in (filters or {}).items():
        if key not in FILTER_KEYS or value in (None, ""):
            continue
        cleaned[key] = str(value)
    return cleaned


def _metadata_matches(metadata: dict, filters: dict[str, str]) -> bool:
    for key, expected in filters.items():
        value = metadata.get(key)
        if isinstance(value, list):
            if expected.lower() not in {str(item).lower() for item in value}:
                return False
        elif str(value or "").lower() != expected.lower():
            return False
    return True


def upsert_documents(db: Session, tenant: TenantRow, documents: list[Document], *, sources: set[str] | None = None) -> dict:
    model = model_id_for(tenant)
    existing = {
        row.doc_id: row
        for row in db.scalars(select(ChunkRow).where(ChunkRow.tenant_id == tenant.id)).all()
    }
    pending: list[Document] = []
    keep_ids: set[str] = set()
    unchanged = 0
    metadata_updated = 0
    for doc in documents:
        digest = hashlib.sha256(f"{doc.embed_text}\n{doc.content}".encode()).hexdigest()
        row = existing.get(doc.doc_id)
        keep_ids.add(doc.doc_id)
        public = _public_metadata(doc.metadata)
        if row and row.content_hash == digest and row.embedding_model == model and row.embedding_json:
            if _stored_metadata(row.metadata_json) == public:
                unchanged += 1
            else:
                row.metadata_json = _metadata_blob(public)
                metadata_updated += 1
            continue
        doc.metadata = {**public, "_hash": digest}
        pending.append(doc)
    embedded = 0
    if pending:
        batch = embed_texts([doc.embed_text or doc.content for doc in pending], model)
        for doc, vector in zip(pending, batch.vectors):
            digest = doc.metadata.get("_hash", "")
            row = existing.get(doc.doc_id)
            payload = {
                "title": doc.title,
                "content": doc.content,
                "source": doc.source,
                "source_id": doc.source_id,
                "kind": doc.kind,
                "metadata_json": _metadata_blob(doc.metadata),
                "content_hash": digest,
                "embedding_model": batch.model,
                "embedding_dim": batch.dim,
                "embedding_json": json.dumps(vector),
                "nda_only": doc.nda_only,
                "collection": tenant.collection or tenant.slug,
            }
            if row is None:
                row = ChunkRow(tenant_id=tenant.id, doc_id=doc.doc_id, **payload)
                db.add(row)
            else:
                for key, value in payload.items():
                    setattr(row, key, value)
            embedded += 1
        db.commit()
        _write_pgvector(db, tenant.id, batch.model)
    elif metadata_updated:
        db.commit()
    pruned = 0
    if sources:
        rows = db.scalars(
            select(ChunkRow).where(ChunkRow.tenant_id == tenant.id, ChunkRow.source.in_(sources))
        ).all()
        for row in rows:
            if row.doc_id not in keep_ids:
                db.delete(row)
                pruned += 1
        db.commit()
    return {
        "embedded": embedded,
        "unchanged": unchanged,
        "metadata_updated": metadata_updated,
        "pruned": pruned,
        "model": model,
    }


def _write_pgvector(db: Session, tenant_id: str, model: str) -> None:
    if not pgvector_ready():
        return
    rows = db.scalars(
        select(ChunkRow).where(ChunkRow.tenant_id == tenant_id, ChunkRow.embedding_model == model)
    ).all()
    for row in rows:
        if not row.embedding_json:
            continue
        try:
            db.execute(
                text("UPDATE rag_chunks SET embedding = CAST(:vec AS vector) WHERE id = :id"),
                {"vec": row.embedding_json, "id": row.id},
            )
        except Exception:
            log.exception("Could not write pgvector column for %s", row.id)
            return
    db.commit()


def search(
    db: Session,
    tenant: TenantRow,
    query: str,
    *,
    kind: str,
    k: int | None = None,
    nda_accepted: bool = False,
    filters: dict | None = None,
) -> list[Hit]:
    active = _clean_filters(filters)
    hits = _search_once(db, tenant, query, kind=kind, k=k, nda_accepted=nda_accepted, filters=active)
    if active and not hits:
        hits = _search_once(db, tenant, query, kind=kind, k=k, nda_accepted=nda_accepted, filters={})
    return hits


def _search_once(
    db: Session,
    tenant: TenantRow,
    query: str,
    *,
    kind: str,
    k: int | None,
    nda_accepted: bool,
    filters: dict[str, str],
) -> list[Hit]:
    platform = get_platform()
    limit = k or platform.top_k
    model = model_id_for(tenant)
    batch = embed_texts([query], model)
    if not batch.vectors:
        return []
    vector = batch.vectors[0]
    if pgvector_ready():
        try:
            hits = _pg_search(db, tenant, kind, model, vector, limit * 4, nda_accepted, filters)
            if hits:
                return _cap(hits, limit, platform.max_chunks_per_doc)
        except Exception:
            log.exception("pgvector search failed; using local cosine")
    rows = db.scalars(
        select(ChunkRow).where(
            ChunkRow.tenant_id == tenant.id,
            ChunkRow.collection == (tenant.collection or tenant.slug),
            ChunkRow.kind == kind,
            ChunkRow.embedding_model == model,
        )
    ).all()
    scored: list[Hit] = []
    for row in rows:
        if row.nda_only and not nda_accepted:
            continue
        if filters and not _metadata_matches(_stored_metadata(row.metadata_json), filters):
            continue
        if not row.embedding_json:
            continue
        try:
            stored = json.loads(row.embedding_json)
        except json.JSONDecodeError:
            continue
        scored.append(_hit(row, cosine(vector, stored)))
    scored.sort(key=lambda item: item.score, reverse=True)
    return _cap(scored, limit, platform.max_chunks_per_doc)


def _pg_search(db, tenant, kind, model, vector, limit, nda_accepted, filters: dict[str, str]) -> list[Hit]:
    literal = json.dumps(vector)
    params = {
        "q": literal,
        "tenant": tenant.id,
        "collection": tenant.collection or tenant.slug,
        "kind": kind,
        "model": model,
        "nda": nda_accepted,
        "limit": limit,
    }
    clauses = []
    for key, value in filters.items():
        param = f"meta_{key}"
        clauses.append(f"AND lower(metadata_json::jsonb ->> '{key}') = :{param}")
        params[param] = value.lower()
    extra = "\n              ".join(clauses)
    rows = db.execute(
        text(
            f"""
            SELECT id, (1 - (embedding <=> CAST(:q AS vector))) AS score
            FROM rag_chunks
            WHERE tenant_id = :tenant
              AND collection = :collection
              AND kind = :kind
              AND embedding_model = :model
              AND embedding IS NOT NULL
              AND (:nda OR nda_only = false)
              {extra}
            ORDER BY embedding <=> CAST(:q AS vector)
            LIMIT :limit
            """
        ),
        params,
    ).mappings().all()
    hits: list[Hit] = []
    for item in rows:
        row = db.get(ChunkRow, item["id"])
        if row is None:
            continue
        hits.append(_hit(row, float(item["score"] or 0)))
    return hits


def _hit(row: ChunkRow, score: float) -> Hit:
    try:
        metadata = json.loads(row.metadata_json or "{}")
    except json.JSONDecodeError:
        metadata = {}
    return Hit(
        id=row.id,
        doc_id=row.doc_id,
        title=row.title,
        content=row.content,
        score=score,
        source=row.source,
        metadata=metadata if isinstance(metadata, dict) else {},
        nda_only=row.nda_only,
    )


def _cap(hits: list[Hit], k: int, per_doc: int) -> list[Hit]:
    chosen: list[Hit] = []
    counts: dict[str, int] = {}
    for hit in hits:
        key = _doc_key(hit.doc_id)
        if counts.get(key, 0) >= per_doc:
            continue
        counts[key] = counts.get(key, 0) + 1
        chosen.append(hit)
        if len(chosen) >= k:
            break
    return chosen
