from __future__ import annotations

import hashlib
import json
from dataclasses import dataclass, field
from datetime import datetime
from threading import Lock
from typing import Protocol

import numpy as np
from sqlalchemy import func, select, text
from sqlalchemy.orm import Session

from backend.app.core.settings import get_settings
from backend.app.models.db import engine, vector_column_dim
from backend.app.models.entities import RagChunkRow
from backend.app.rag.embeddings import active_model, embed_texts


@dataclass
class Document:
    """A unit of retrievable text with a stable identity."""

    doc_id: str
    content: str
    title: str = ""
    kind: str = "knowledge"
    source: str = ""
    source_id: str = ""
    metadata: dict = field(default_factory=dict)
    # Optional text to embed instead of the title and content. Lets a document be
    # matched on one thing and shown as another, which matters where the stored text
    # is an answer but the query will always be the question.
    embed_text: str = ""

    def content_hash(self) -> str:
        payload = json.dumps(
            {
                "title": self.title,
                "content": self.content,
                "metadata": self.metadata,
                "embed_text": self.embed_text,
            },
            sort_keys=True,
            default=str,
        )
        return hashlib.sha256(payload.encode("utf-8")).hexdigest()


@dataclass
class Hit:
    doc_id: str
    title: str
    content: str
    kind: str
    source: str
    source_id: str
    metadata: dict
    score: float


class VectorStore(Protocol):
    name: str

    def upsert(self, db: Session, documents: list[Document]) -> int: ...

    def search(
        self,
        db: Session,
        query: str,
        *,
        k: int = 4,
        kind: str | None = None,
        sources: list[str] | None = None,
        min_score: float = 0.0,
    ) -> list[Hit]: ...

    def delete_by_source(self, db: Session, source: str, keep_doc_ids: set[str] | None = None) -> int: ...


class _BaseStore:
    """Shared write path. Only the similarity search differs between backends."""

    name = "base"

    def upsert(self, db: Session, documents: list[Document]) -> int:
        if not documents:
            return 0
        model, dim = active_model()
        by_id = {document.doc_id: document for document in documents}
        existing = {
            row.doc_id: row
            for row in db.scalars(select(RagChunkRow).where(RagChunkRow.doc_id.in_(list(by_id)))).all()
        }
        stale: list[Document] = []
        for doc_id, document in by_id.items():
            row = existing.get(doc_id)
            unchanged = (
                row is not None
                and row.content_hash == document.content_hash()
                and row.embedding_model == model
                and row.embedding_json
            )
            if not unchanged:
                stale.append(document)
        if not stale:
            return 0

        batch = embed_texts([_embed_text(document) for document in stale])
        for document, vector in zip(stale, batch.vectors):
            row = existing.get(document.doc_id)
            if row is None:
                row = RagChunkRow(doc_id=document.doc_id)
                db.add(row)
            row.kind = document.kind
            row.source = document.source
            row.source_id = document.source_id
            row.title = document.title
            row.content = document.content
            row.metadata_json = json.dumps(document.metadata, default=str)
            row.content_hash = document.content_hash()
            row.embedding_model = batch.model
            row.embedding_dim = batch.dim
            row.embedding_json = json.dumps([round(value, 6) for value in vector])
            row.updated_at = datetime.utcnow()
        db.flush()
        self._after_write(db, stale, batch.model, batch.dim)
        _invalidate_cache()
        return len(stale)

    def _after_write(self, db: Session, documents: list[Document], model: str, dim: int) -> None:
        return None

    def delete_by_source(self, db: Session, source: str, keep_doc_ids: set[str] | None = None) -> int:
        rows = db.scalars(select(RagChunkRow).where(RagChunkRow.source == source)).all()
        removed = 0
        for row in rows:
            if keep_doc_ids is not None and row.doc_id in keep_doc_ids:
                continue
            db.delete(row)
            removed += 1
        if removed:
            db.flush()
            _invalidate_cache()
        return removed

    def delete_doc(self, db: Session, doc_id: str) -> bool:
        row = db.scalar(select(RagChunkRow).where(RagChunkRow.doc_id == doc_id))
        if not row:
            return False
        db.delete(row)
        db.flush()
        _invalidate_cache()
        return True


class FallbackStore(_BaseStore):
    """In-process cosine search over a cached numpy matrix.

    Fine for a corpus of this size (hundreds of chunks) and keeps the SQLite demo
    working with no extra infrastructure.
    """

    name = "fallback"

    def search(
        self,
        db: Session,
        query: str,
        *,
        k: int = 4,
        kind: str | None = None,
        sources: list[str] | None = None,
        min_score: float = 0.0,
    ) -> list[Hit]:
        batch = embed_texts([query or ""])
        if not batch.vectors:
            return []
        matrix, rows = _corpus(db, batch.model, len(batch.vectors[0]))
        if matrix is None or not rows:
            return []
        scores = matrix @ np.asarray(batch.vectors[0], dtype=np.float32)
        order = np.argsort(-scores)
        hits: list[Hit] = []
        for index in order:
            row = rows[int(index)]
            score = float(scores[int(index)])
            if score < min_score:
                break
            if kind and row["kind"] != kind:
                continue
            if sources and row["source"] not in sources:
                continue
            hits.append(Hit(score=score, **{key: row[key] for key in _HIT_FIELDS}))
            if len(hits) >= k:
                break
        return hits


class PgVectorStore(_BaseStore):
    """Native pgvector search using the cosine distance operator."""

    name = "pgvector"

    def _after_write(self, db: Session, documents: list[Document], model: str, dim: int) -> None:
        # Mirror the portable JSON vectors into the native column used for search.
        for document in documents:
            db.execute(
                text(
                    "UPDATE rag_chunks SET embedding = CAST(embedding_json AS vector) "
                    "WHERE doc_id = :doc_id AND embedding_model = :model"
                ),
                {"doc_id": document.doc_id, "model": model},
            )

    def search(
        self,
        db: Session,
        query: str,
        *,
        k: int = 4,
        kind: str | None = None,
        sources: list[str] | None = None,
        min_score: float = 0.0,
    ) -> list[Hit]:
        batch = embed_texts([query or ""])
        if not batch.vectors:
            return []
        clauses = ["embedding IS NOT NULL", "embedding_model = :model"]
        params: dict[str, object] = {
            "model": batch.model,
            "q": json.dumps([round(value, 6) for value in batch.vectors[0]]),
            "k": max(1, k),
        }
        if kind:
            clauses.append("kind = :kind")
            params["kind"] = kind
        if sources:
            names = []
            for index, source in enumerate(sources):
                key = f"source_{index}"
                params[key] = source
                names.append(f":{key}")
            clauses.append(f"source IN ({', '.join(names)})")
        rows = db.execute(
            text(
                "SELECT doc_id, title, content, kind, source, source_id, metadata_json, "
                "1 - (embedding <=> CAST(:q AS vector)) AS score FROM rag_chunks "
                f"WHERE {' AND '.join(clauses)} ORDER BY embedding <=> CAST(:q AS vector) LIMIT :k"
            ),
            params,
        ).mappings()
        hits = []
        for row in rows:
            score = float(row["score"])
            if score < min_score:
                continue
            hits.append(
                Hit(
                    doc_id=row["doc_id"],
                    title=row["title"],
                    content=row["content"],
                    kind=row["kind"],
                    source=row["source"],
                    source_id=row["source_id"],
                    metadata=_loads(row["metadata_json"]),
                    score=score,
                )
            )
        return hits


_HIT_FIELDS = ("doc_id", "title", "content", "kind", "source", "source_id", "metadata")
_cache_lock = Lock()
_cache: dict[str, object] = {}


def _embed_text(document: Document) -> str:
    if document.embed_text.strip():
        return document.embed_text.strip()
    return f"{document.title}\n{document.content}".strip() if document.title else document.content


def _loads(raw: str) -> dict:
    try:
        value = json.loads(raw or "{}")
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}


def _invalidate_cache() -> None:
    with _cache_lock:
        _cache.clear()


def _corpus(db: Session, model: str, dim: int) -> tuple[np.ndarray | None, list[dict]]:
    """Cached matrix of every vector produced by ``model`` at ``dim`` dimensions."""
    signature = db.execute(
        select(func.count(RagChunkRow.id), func.max(RagChunkRow.updated_at)).where(RagChunkRow.embedding_model == model)
    ).one()
    key = (model, dim, signature[0], str(signature[1]))
    with _cache_lock:
        if _cache.get("key") == key:
            return _cache.get("matrix"), _cache.get("rows")  # type: ignore[return-value]
    rows: list[dict] = []
    vectors: list[list[float]] = []
    for row in db.scalars(
        select(RagChunkRow).where(RagChunkRow.embedding_model == model).order_by(RagChunkRow.doc_id.asc())
    ).all():
        try:
            vector = json.loads(row.embedding_json or "[]")
        except json.JSONDecodeError:
            continue
        # A length mismatch means the row predates a model change. Skipping keeps the
        # matrix rectangular; the next ingest re-embeds it.
        if not vector or len(vector) != dim:
            continue
        vectors.append(vector)
        rows.append(
            {
                "doc_id": row.doc_id,
                "title": row.title,
                "content": row.content,
                "kind": row.kind,
                "source": row.source,
                "source_id": row.source_id,
                "metadata": _loads(row.metadata_json),
            }
        )
    matrix = np.asarray(vectors, dtype=np.float32) if vectors else None
    with _cache_lock:
        _cache.update({"key": key, "matrix": matrix, "rows": rows})
    return matrix, rows


def get_store() -> VectorStore:
    """Pick a backend: pgvector when the native column exists, otherwise numpy."""
    backend = get_settings().rag_backend.strip().lower()
    if backend == "fallback":
        return FallbackStore()
    if backend == "pgvector":
        return PgVectorStore()
    if str(engine.url).startswith("postgresql") and vector_column_dim() == active_model()[1]:
        return PgVectorStore()
    return FallbackStore()


def corpus_stats(db: Session) -> dict:
    counts = db.execute(
        select(RagChunkRow.kind, RagChunkRow.source, func.count(RagChunkRow.id)).group_by(
            RagChunkRow.kind, RagChunkRow.source
        )
    ).all()
    models = db.scalars(select(RagChunkRow.embedding_model).distinct()).all()
    model, dim = active_model()
    return {
        "backend": get_store().name,
        "embedding_model": model,
        "embedding_dim": dim,
        "stored_models": sorted(name for name in models if name),
        "by_source": [{"kind": kind, "source": source, "count": count} for kind, source, count in counts],
        "total": sum(count for _, _, count in counts),
    }
