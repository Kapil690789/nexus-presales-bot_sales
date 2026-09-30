from __future__ import annotations

import hashlib
import math
import os
import re
from functools import lru_cache
from typing import NamedTuple

from backend.app.core.platform import get_platform
from backend.app.core.settings import ROOT, get_settings
from backend.app.models.entities import TenantRow

HASH_MODEL = "hash-v1-384"
BASE_MODEL = "BAAI/bge-small-en-v1.5"
_TOKEN = re.compile(r"[a-z0-9]+")
STOPWORDS = frozenset(
    """
    a about all also am an and any are as at be been being but by can cannot could did do does
    doing done for from get got had has have having he her here hers him his how i if in into is
    it its just me more most my no nor not of off on once only or other our out over own same she
    should so some such than that the their them then there these they this those to too us very
    was we were what when where which while who whom why will with would you your yours
    """.split()
)


class EmbeddingBatch(NamedTuple):
    model: str
    dim: int
    vectors: list[list[float]]


def embedding_backend() -> str:
    choice = get_settings().embedding_backend.strip().lower() or "auto"
    if os.environ.get("VERCEL") and choice != "gemini":
        return "hash"
    if choice == "gemini":
        return "gemini"
    if choice == "hash":
        return "hash"
    if choice == "sentence-transformers":
        return "sentence-transformers"
    if get_settings().llm_api_key.strip():
        return "gemini"
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return "hash"
    return "sentence-transformers"


def model_id_for(tenant: TenantRow | None) -> str:
    backend = embedding_backend()
    if backend == "gemini":
        return get_settings().embedding_model.strip() or "gemini-embedding-001"
    if backend == "hash":
        return HASH_MODEL
    custom = (tenant.embedding_model if tenant else "").strip()
    if custom.startswith("finetuned:"):
        return custom
    return get_settings().embedding_model.strip() or get_platform().embedding_model or BASE_MODEL


def model_source(model_id: str) -> str:
    if model_id.startswith("finetuned:"):
        slug = model_id.split(":", 1)[1]
        path = ROOT / "models" / slug
        if path.is_dir():
            return str(path)
    return model_id if model_id != HASH_MODEL else BASE_MODEL


def embed_texts(texts: list[str], model_id: str | None = None) -> EmbeddingBatch:
    backend = embedding_backend()
    model = model_id or (HASH_MODEL if backend == "hash" else model_id_for(None))
    if backend == "gemini" or (model and "gemini" in model):
        vectors = _gemini_embed(texts, model)
        dim = len(vectors[0]) if vectors else 3072
        return EmbeddingBatch(model, dim, vectors)
    if backend == "hash" or model == HASH_MODEL:
        vectors = [_hash_embed(text) for text in texts]
        return EmbeddingBatch(HASH_MODEL, len(vectors[0]) if vectors else 384, vectors)
    encoder = _sentence_model(model_source(model))
    raw = encoder.encode(list(texts), normalize_embeddings=True)
    vectors = [list(map(float, row)) for row in raw]
    dim = len(vectors[0]) if vectors else 0
    return EmbeddingBatch(model, dim, vectors)


def _gemini_embed(texts: list[str], model_id: str = "gemini-embedding-001") -> list[list[float]]:
    import httpx
    import time

    key = get_settings().llm_api_key.strip()
    if not key or not texts:
        return [_hash_embed(text) for text in texts]

    target_model = model_id or "gemini-embedding-001"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:batchEmbedContents?key={key}"
    batch_size = 50
    all_vectors: list[list[float]] = []

    try:
        with httpx.Client(timeout=30.0) as client:
            for i in range(0, len(texts), batch_size):
                chunk = texts[i : i + batch_size]
                requests = [
                    {"model": f"models/{target_model}", "content": {"parts": [{"text": t or " "}]}}
                    for t in chunk
                ]
                success = False
                for attempt in range(3):
                    resp = client.post(url, json={"requests": requests})
                    if resp.status_code == 200:
                        data = resp.json()
                        raw_embeddings = data.get("embeddings", [])
                        for item in raw_embeddings:
                            values = [float(v) for v in item.get("values", [])]
                            all_vectors.append(values)
                        success = True
                        break
                    elif resp.status_code == 429:
                        time.sleep(2.5 * (attempt + 1))
                    else:
                        break
                if not success:
                    return [_hash_embed(text) for text in texts]
        if len(all_vectors) == len(texts):
            return all_vectors
    except Exception:
        pass
    return [_hash_embed(text) for text in texts]


def _hash_embed(text: str, dim: int = 384) -> list[float]:
    tokens = [token for token in _TOKEN.findall((text or "").lower()) if token not in STOPWORDS]
    grams = tokens + [f"{left}_{right}" for left, right in zip(tokens, tokens[1:])]
    vec = [0.0] * dim
    for gram in grams:
        digest = hashlib.sha256(gram.encode()).digest()
        bucket = int.from_bytes(digest[:4], "little") % dim
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vec[bucket] += sign
    norm = math.sqrt(sum(value * value for value in vec)) or 1.0
    return [value / norm for value in vec]


@lru_cache
def _sentence_model(name: str):
    from sentence_transformers import SentenceTransformer

    return SentenceTransformer(name)


def cosine(left: list[float], right: list[float]) -> float:
    if not left or not right or len(left) != len(right):
        return 0.0
    dot = sum(a * b for a, b in zip(left, right))
    left_norm = math.sqrt(sum(a * a for a in left))
    right_norm = math.sqrt(sum(b * b for b in right))
    if left_norm == 0 or right_norm == 0:
        return 0.0
    return dot / (left_norm * right_norm)
