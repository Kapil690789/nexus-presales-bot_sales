from __future__ import annotations

import hashlib
import json
import logging
import re
from dataclasses import dataclass, field

from sqlalchemy import select, text
from sqlalchemy.orm import Session

from backend.app.core.platform import get_platform
from backend.app.models.db import pgvector_ready
from backend.app.models.entities import ChunkRow, TenantRow
from backend.app.rag.embeddings import (
    HASH_MODEL,
    EmbeddingError,
    active_embedding_version,
    cosine,
    embed_query,
    embed_texts,
    model_id_for,
    record_query_failure,
)

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
    source_id: str = ""
    metadata: dict = field(default_factory=dict)
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
        expected_dim = 384 if model == HASH_MODEL else get_platform().embedding_dim
        active_version = active_embedding_version(model, expected_dim)
        is_fresh = (
            row is not None
            and row.content_hash == digest
            and row.embedding_model == model
            and bool(row.embedding_json)
            and row.embedding_dim == expected_dim
            and getattr(row, "embedding_version", "") == active_version
        )
        if is_fresh:
            if _stored_metadata(row.metadata_json) == public:
                unchanged += 1
            else:
                row.metadata_json = _metadata_blob(public)
                metadata_updated += 1
            continue
        doc.metadata = {**public, "_hash": digest}
        pending.append(doc)
    embedded = 0
    failures = 0
    if pending:
        batch_size = 20
        for i in range(0, len(pending), batch_size):
            chunk_slice = pending[i : i + batch_size]
            texts = [d.embed_text or d.content for d in chunk_slice]
            try:
                batch = embed_texts(texts, model, mode="ingest")
                if len(batch.vectors) != len(chunk_slice):
                    raise EmbeddingError(f"Expected {len(chunk_slice)} vectors, got {len(batch.vectors)}")
                for doc, vector in zip(chunk_slice, batch.vectors):
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
                        "embedding_version": active_embedding_version(batch.model, batch.dim),
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
            except EmbeddingError as batch_exc:
                log.warning("Batch embedding failed for %d docs, falling back to 1-by-1: %s", len(chunk_slice), batch_exc)
                for doc in chunk_slice:
                    try:
                        single_batch = embed_texts([doc.embed_text or doc.content], model, mode="ingest")
                        if not single_batch.vectors:
                            raise EmbeddingError("No vectors returned")
                        vector = single_batch.vectors[0]
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
                            "embedding_model": single_batch.model,
                            "embedding_dim": single_batch.dim,
                            "embedding_version": active_embedding_version(single_batch.model, single_batch.dim),
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
                    except EmbeddingError as exc:
                        log.exception("Failed to embed document %s: %s", doc.doc_id, exc)
                        failures += 1
                        record_query_failure(exc)
                        continue
        if embedded > 0:
            db.commit()
            _write_pgvector(db, tenant.id, model)
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
        "failures": failures,
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


def _lexical_score(query: str, title: str, content: str) -> float:
    terms = [term for term in re.findall(r"\w+", query.lower()) if len(term) >= 2]
    if not terms:
        return 0.0
    text = f"{title}\n{content}".lower()
    score = 0.0
    cleaned_q = " ".join(terms)
    if cleaned_q in text:
        score += 0.5
    title_lower = (title or "").lower()
    content_lower = (content or "").lower()
    matched_terms = 0
    for term in terms:
        matched = False
        if term in title_lower:
            score += 0.3
            matched = True
        if term in content_lower:
            count = min(content_lower.count(term), 3)
            score += 0.15 * count
            matched = True
        if matched:
            matched_terms += 1
    coverage = matched_terms / len(terms)
    score *= (0.5 + 0.5 * coverage)
    return min(1.0, score)


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
    vector = None
    try:
        batch = embed_query(query, model)
        if batch and batch.vectors:
            vector = batch.vectors[0]
    except EmbeddingError as exc:
        status = getattr(exc, "status_code", None)
        status_msg = f" status={status}" if status else ""
        log.warning("Embedding query failed: %s%s", type(exc).__name__, status_msg)
        record_query_failure(exc)
        vector = None

    if vector and pgvector_ready():
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

    expected_dim = 384 if model == HASH_MODEL else platform.embedding_dim
    active_version = active_embedding_version(model, expected_dim)

    # Filter candidates by NDA, active filters, and chunk version/dim
    candidates: list[ChunkRow] = []
    for row in rows:
        if row.nda_only and not nda_accepted:
            continue
        if filters and not _metadata_matches(_stored_metadata(row.metadata_json), filters):
            continue
        if row.embedding_dim != expected_dim or getattr(row, "embedding_version", "") != active_version:
            continue
        candidates.append(row)

    if not candidates:
        return []

    # If vector embedding failed, fall back gracefully to pure lexical ranking
    if vector is None:
        scored = []
        for row in candidates:
            lex = _lexical_score(query, row.title or "", row.content or "")
            if lex > 0:
                scored.append(_hit(row, lex))
        scored.sort(key=lambda item: item.score, reverse=True)
        return _cap(scored, limit, platform.max_chunks_per_doc)

    # Hybrid Search: Dense Vector Similarity + Lexical Agreement & RRF Boost
    scored: list[Hit] = []
    target_service = filters.get("service") if filters else None
    for row in candidates:
        if not row.embedding_json:
            continue
        try:
            stored = json.loads(row.embedding_json)
        except json.JSONDecodeError:
            continue
        vec_score = cosine(vector, stored)
        lex_score = _lexical_score(query, row.title or "", row.content or "")

        combined_score = vec_score
        # Dual-match lexical agreement boost
        if lex_score >= 0.5:
            combined_score = min(1.0, combined_score + 0.08)
        elif lex_score > 0.2:
            combined_score = min(1.0, combined_score + 0.04)

        # Service metadata match boost
        if target_service:
            meta = _stored_metadata(row.metadata_json)
            if meta.get("service") == target_service:
                combined_score = min(1.0, combined_score + 0.05)

        scored.append(_hit(row, combined_score))

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
    platform = get_platform()
    expected_dim = 384 if model == HASH_MODEL else platform.embedding_dim
    active_version = active_embedding_version(model, expected_dim)
    for item in rows:
        row = db.get(ChunkRow, item["id"])
        if row is None:
            continue
        if row.embedding_dim != expected_dim or getattr(row, "embedding_version", "") != active_version:
            continue
        hits.append(_hit(row, float(item["score"] or 0)))
    return hits


def count_stale_chunks(db: Session, tenant: TenantRow | None = None) -> int:
    from backend.app.core.settings import get_settings

    model = model_id_for(tenant) if tenant else (get_settings().embedding_model.strip() or "gemini-embedding-001")
    expected_dim = 384 if model == HASH_MODEL else get_platform().embedding_dim
    active_version = active_embedding_version(model, expected_dim)

    query = select(ChunkRow)
    if tenant:
        query = query.where(ChunkRow.tenant_id == tenant.id)
    rows = db.scalars(query).all()
    stale = 0
    for row in rows:
        if (
            row.embedding_model != model
            or row.embedding_dim != expected_dim
            or getattr(row, "embedding_version", "") != active_version
        ):
            stale += 1
    return stale


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
        source_id=getattr(row, "source_id", "") or "",
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
