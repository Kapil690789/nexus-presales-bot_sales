from __future__ import annotations

import hashlib
import math
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
    if choice == "hash":
        return "hash"
    if choice == "sentence-transformers":
        return "sentence-transformers"
    try:
        import sentence_transformers  # noqa: F401
    except Exception:
        return "hash"
    return "sentence-transformers"


def model_id_for(tenant: TenantRow | None) -> str:
    if embedding_backend() == "hash":
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
    model = model_id or (HASH_MODEL if embedding_backend() == "hash" else model_id_for(None))
    if embedding_backend() == "hash" or model == HASH_MODEL:
        vectors = [_hash_embed(text) for text in texts]
        return EmbeddingBatch(HASH_MODEL, len(vectors[0]) if vectors else 384, vectors)
    encoder = _sentence_model(model_source(model))
    raw = encoder.encode(list(texts), normalize_embeddings=True)
    vectors = [list(map(float, row)) for row in raw]
    dim = len(vectors[0]) if vectors else 0
    return EmbeddingBatch(model, dim, vectors)


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
