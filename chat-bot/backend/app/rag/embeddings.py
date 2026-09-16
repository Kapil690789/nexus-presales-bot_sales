from __future__ import annotations

import hashlib
import math
import re
from functools import lru_cache
from typing import NamedTuple

from backend.app.core.settings import get_settings

FALLBACK_MODEL = "hash-256"
FALLBACK_DIM = 256

# Anthropic has no embeddings endpoint, so that provider uses the local embedder.
PROVIDER_MODELS: dict[str, str] = {
    "openai": "text-embedding-3-small",
    "gemini": "text-embedding-004",
}

KNOWN_DIMS: dict[str, int] = {
    "text-embedding-3-small": 1536,
    "text-embedding-3-large": 3072,
    "text-embedding-ada-002": 1536,
    "text-embedding-004": 768,
    "embedding-001": 768,
    FALLBACK_MODEL: FALLBACK_DIM,
}

_TOKEN = re.compile(r"[a-z0-9]+")


class EmbeddingBatch(NamedTuple):
    """Vectors plus the model that actually produced them.

    The model is carried alongside the vectors because a remote failure falls back
    to the local embedder, and vectors from different models must never be compared.
    """

    model: str
    dim: int
    vectors: list[list[float]]


def embeddings_provider() -> str:
    settings = get_settings()
    if not settings.llm_api_key.strip():
        return "local"
    provider = settings.llm_provider.strip().lower()
    return provider if provider in PROVIDER_MODELS else "local"


@lru_cache
def active_model() -> tuple[str, int]:
    """The model this deployment intends to use, and its dimension."""
    provider = embeddings_provider()
    if provider == "local":
        return FALLBACK_MODEL, FALLBACK_DIM
    override = get_settings().embedding_model.strip()
    model = override or PROVIDER_MODELS[provider]
    dim = KNOWN_DIMS.get(model, 0)
    if not dim:
        try:
            dim = len(_remote(provider, model, ["dimension probe"])[0])
        except Exception:
            return FALLBACK_MODEL, FALLBACK_DIM
        KNOWN_DIMS[model] = dim
    return model, dim


def embed_texts(texts: list[str]) -> EmbeddingBatch:
    if not texts:
        model, dim = active_model()
        return EmbeddingBatch(model, dim, [])
    provider = embeddings_provider()
    model, dim = active_model()
    if provider != "local" and model != FALLBACK_MODEL:
        try:
            vectors = _remote(provider, model, [text[:8000] for text in texts])
            if len(vectors) == len(texts) and all(len(vector) == dim for vector in vectors):
                return EmbeddingBatch(model, dim, [_normalize(vector) for vector in vectors])
        except Exception:
            pass
    return EmbeddingBatch(FALLBACK_MODEL, FALLBACK_DIM, [_hash_embed(text) for text in texts])


def embed_query(text: str) -> EmbeddingBatch:
    return embed_texts([text or ""])


def _remote(provider: str, model: str, texts: list[str]) -> list[list[float]]:
    if provider == "gemini":
        return _gemini(model, texts)
    return _openai(model, texts)


def _openai(model: str, texts: list[str]) -> list[list[float]]:
    from openai import OpenAI

    settings = get_settings()
    kwargs: dict[str, object] = {"api_key": settings.llm_api_key}
    if settings.llm_base_url.strip():
        kwargs["base_url"] = settings.llm_base_url.strip()
    response = OpenAI(**kwargs).embeddings.create(model=model, input=texts)
    return [item.embedding for item in response.data]


def _gemini(model: str, texts: list[str]) -> list[list[float]]:
    import google.generativeai as genai

    genai.configure(api_key=get_settings().llm_api_key)
    name = model if model.startswith("models/") else f"models/{model}"
    vectors: list[list[float]] = []
    for text in texts:
        result = genai.embed_content(model=name, content=text)
        vectors.append(list(result["embedding"]))
    return vectors


def _hash_embed(text: str) -> list[float]:
    """Deterministic signed hashing embedder over unigrams and bigrams.

    Bigrams give a little word-order signal; sublinear term weighting keeps repeated
    words from dominating. Recall is weaker than a real model, which is why callers
    combine it with metadata boosts.
    """
    tokens = _TOKEN.findall((text or "").lower())
    counts: dict[str, int] = {}
    for token in tokens:
        counts[token] = counts.get(token, 0) + 1
    for first, second in zip(tokens, tokens[1:]):
        bigram = f"{first}_{second}"
        counts[bigram] = counts.get(bigram, 0) + 1
    vector = [0.0] * FALLBACK_DIM
    for term, count in counts.items():
        digest = hashlib.blake2b(term.encode("utf-8"), digest_size=8).digest()
        index = int.from_bytes(digest[:4], "big") % FALLBACK_DIM
        sign = 1.0 if digest[4] % 2 == 0 else -1.0
        vector[index] += sign * (1.0 + math.log(count))
    return _normalize(vector)


def _normalize(vector: list[float]) -> list[float]:
    norm = math.sqrt(sum(value * value for value in vector))
    if norm <= 0:
        return [0.0] * len(vector)
    return [value / norm for value in vector]
