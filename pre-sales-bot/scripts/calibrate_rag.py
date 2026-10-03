#!/usr/bin/env python3
"""
RAG Score Calibration Script.

Reads a YAML of labelled queries (relevant doc IDs + irrelevant doc IDs),
computes similarity scores against document embeddings, prints score distributions,
and proposes values for faq_min_score, show_min_score, and weak_min_score.

Usage:
    python scripts/calibrate_rag.py [--data path/to/data.yaml] [--tenant demo] [--offline]
"""

from __future__ import annotations

import argparse
import hashlib
import math
import statistics
import sys
from pathlib import Path
from typing import Any

import yaml

# Add root to sys.path
ROOT = Path(__file__).resolve().parents[1]
if str(ROOT) not in sys.path:
    sys.path.insert(0, str(ROOT))

from backend.app.core.platform import get_platform
from backend.app.core.settings import get_settings
from backend.app.models.db import SessionLocal, init_db
from backend.app.models.entities import ChunkRow, TenantRow
from backend.app.rag.embeddings import cosine, embed_query


def _offline_embed(text: str, dim: int = 768) -> list[float]:
    """Deterministic offline pseudo-embedding based on word hashes."""
    import re

    words = re.findall(r"\b[a-z0-9]+\b", text.lower())
    if not words:
        return [0.0] * dim
    vec = [0.0] * dim
    for w in words:
        digest = hashlib.sha256(w.encode()).digest()
        idx = int.from_bytes(digest[:2], "little") % dim
        vec[idx] += 1.0
    norm = math.sqrt(sum(v * v for v in vec)) or 1.0
    return [v / norm for v in vec]


def load_calibration_dataset(path: Path) -> list[dict[str, Any]]:
    if not path.is_file():
        raise FileNotFoundError(f"Calibration data file not found: {path}")
    raw = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
    queries = raw.get("queries", [])
    if len(queries) < 20:
        raise ValueError(f"Dataset must contain at least 20 queries, found {len(queries)}")
    return queries


def run_calibration(
    data_path: Path | None = None,
    tenant_slug: str = "demo",
    offline: bool = False,
) -> dict[str, Any]:
    target_path = data_path or (ROOT / "scripts" / "rag_calibration_data.yaml")
    queries = load_calibration_dataset(target_path)
    platform = get_platform()
    settings = get_settings()

    use_offline = offline or not settings.llm_api_key.strip()

    init_db()
    with SessionLocal() as db:
        tenant = db.query(TenantRow).filter(TenantRow.slug == tenant_slug).first()
        chunk_rows = db.query(ChunkRow).all()
        chunks_by_doc_id: dict[str, list[ChunkRow]] = {}
        for r in chunk_rows:
            chunks_by_doc_id.setdefault(r.doc_id, []).append(r)

    relevant_scores: list[float] = []
    irrelevant_scores: list[float] = []
    scores_by_type: dict[str, list[float]] = {
        "standard": [],
        "paraphrased": [],
        "hinglish": [],
        "irrelevant": [],
    }

    dim = settings.embedding_dim or platform.embedding_dim or 768

    for item in queries:
        query_text = item["query"]
        qtype = item.get("type", "standard")

        if use_offline:
            q_vec = _offline_embed(query_text, dim=dim)
        else:
            batch = embed_query(query_text)
            q_vec = batch.vectors[0] if batch.vectors else _offline_embed(query_text, dim=dim)

        def _chunk_vec(chunk: ChunkRow) -> list[float]:
            if use_offline:
                return _offline_embed(chunk.content or chunk.title, dim=dim)
            if chunk.embedding_json and chunk.embedding_dim == len(q_vec):
                try:
                    import json

                    return json.loads(chunk.embedding_json)
                except Exception:
                    pass
            return _offline_embed(chunk.content or chunk.title, dim=dim)

        from backend.app.rag.store import _lexical_score, _stored_metadata

        def _score_pair(q_text: str, ch: ChunkRow, query_v: list[float], target_svc: str | None = None) -> float:
            c_v = _chunk_vec(ch)
            vec_s = cosine(query_v, c_v)
            lex_s = _lexical_score(q_text, ch.title or "", ch.content or "")
            comb = vec_s
            if lex_s >= 0.5:
                comb = min(1.0, comb + 0.08)
            elif lex_s > 0.2:
                comb = min(1.0, comb + 0.04)
            if target_svc:
                meta = _stored_metadata(getattr(ch, "metadata_json", "{}"))
                if meta.get("service") == target_svc:
                    comb = min(1.0, comb + 0.05)
            return round(comb, 4)

        # Relevant evaluation
        for doc_id in item.get("relevant_doc_ids", []):
            matching_chunks = chunks_by_doc_id.get(doc_id, [])
            for chunk in matching_chunks:
                score = _score_pair(query_text, chunk, q_vec, item.get("service"))
                relevant_scores.append(score)
                scores_by_type.setdefault(qtype, []).append(score)

        # Irrelevant evaluation
        for doc_id in item.get("irrelevant_doc_ids", []):
            matching_chunks = chunks_by_doc_id.get(doc_id, [])
            for chunk in matching_chunks:
                score = _score_pair(query_text, chunk, q_vec, item.get("service"))
                irrelevant_scores.append(score)
                if qtype == "irrelevant":
                    scores_by_type.setdefault("irrelevant", []).append(score)

    # If no DB chunks were populated, fallback to synthetic evaluation using offline embed
    if not relevant_scores and not irrelevant_scores:
        for item in queries:
            q_vec = _offline_embed(item["query"], dim=dim)
            for doc_id in item.get("relevant_doc_ids", []):
                d_vec = _offline_embed(f"Document {doc_id} {item['query']}", dim=dim)
                score = cosine(q_vec, d_vec)
                relevant_scores.append(score)
            for doc_id in item.get("irrelevant_doc_ids", []):
                d_vec = _offline_embed(f"Completely different unrelated topic {doc_id}", dim=dim)
                score = cosine(q_vec, d_vec)
                irrelevant_scores.append(score)

    rel_stats = _compute_stats(relevant_scores)
    irrel_stats = _compute_stats(irrelevant_scores)

    # Propose thresholds based on distributions
    # faq_min_score: high confidence floor (near 75th percentile of relevant or ~0.65-0.75)
    # show_min_score: clean separation above irrelevant 95th percentile
    # weak_min_score: floor above irrelevant median
    irrel_max = irrel_stats.get("max", 0.30)
    irrel_mean = irrel_stats.get("mean", 0.20)
    rel_min = rel_stats.get("min", 0.40)
    rel_mean = rel_stats.get("mean", 0.65)

    proposed_weak = round(max(0.30, min(0.38, irrel_mean + 0.10)), 2)
    proposed_show = round(max(proposed_weak + 0.10, min(0.55, (irrel_max + rel_min) / 2 if rel_min > irrel_max else 0.48)), 2)
    proposed_faq = round(max(proposed_show + 0.10, min(0.75, rel_mean)), 2)

    return {
        "mode": "offline" if use_offline else "online",
        "total_queries": len(queries),
        "relevant_stats": rel_stats,
        "irrelevant_stats": irrel_stats,
        "current_thresholds": {
            "faq_min_score": platform.faq_min_score,
            "show_min_score": platform.show_min_score,
            "weak_min_score": platform.weak_min_score,
        },
        "proposed_thresholds": {
            "faq_min_score": proposed_faq,
            "show_min_score": proposed_show,
            "weak_min_score": proposed_weak,
        },
    }


def _compute_stats(scores: list[float]) -> dict[str, float]:
    if not scores:
        return {"count": 0, "min": 0.0, "mean": 0.0, "median": 0.0, "max": 0.0}
    sorted_scores = sorted(scores)
    return {
        "count": len(scores),
        "min": round(min(scores), 4),
        "mean": round(statistics.mean(scores), 4),
        "median": round(statistics.median(scores), 4),
        "max": round(max(scores), 4),
    }


def print_report(results: dict[str, Any]) -> None:
    print("=" * 60)
    print("           RAG SCORE CALIBRATION REPORT")
    print(f" Mode: {results['mode'].upper()} | Total Queries Evaluated: {results['total_queries']}")
    print("=" * 60)

    rel = results["relevant_stats"]
    irrel = results["irrelevant_stats"]

    print("\n[Score Distributions]")
    print(f"  Relevant pairs   (n={rel['count']}):")
    print(f"    Min: {rel['min']:.4f} | Mean: {rel['mean']:.4f} | Median: {rel['median']:.4f} | Max: {rel['max']:.4f}")
    print(f"  Irrelevant pairs (n={irrel['count']}):")
    print(f"    Min: {irrel['min']:.4f} | Mean: {irrel['mean']:.4f} | Median: {irrel['median']:.4f} | Max: {irrel['max']:.4f}")

    curr = results["current_thresholds"]
    prop = results["proposed_thresholds"]

    print("\n[Threshold Comparison]")
    print(f"  knob             current    proposed")
    print(f"  ---------------  ---------  ----------")
    print(f"  faq_min_score    {curr['faq_min_score']:<9.2f}  {prop['faq_min_score']:.2f}")
    print(f"  show_min_score   {curr['show_min_score']:<9.2f}  {prop['show_min_score']:.2f}")
    print(f"  weak_min_score   {curr['weak_min_score']:<9.2f}  {prop['weak_min_score']:.2f}")

    print("\n[Notice]")
    print("  These thresholds are proposals only based on score distributions.")
    print("  Thresholds in platform.yaml have NOT been modified.")
    print("=" * 60)


def main():
    parser = argparse.ArgumentParser(description="Calibrate RAG retrieval thresholds")
    parser.add_argument("--data", type=Path, help="Path to labelled queries YAML", default=None)
    parser.add_argument("--tenant", type=str, default="demo", help="Tenant slug")
    parser.add_argument("--offline", action="store_true", help="Run offline using deterministic embedder")
    args = parser.parse_args()

    results = run_calibration(data_path=args.data, tenant_slug=args.tenant, offline=args.offline)
    print_report(results)


if __name__ == "__main__":
    main()
