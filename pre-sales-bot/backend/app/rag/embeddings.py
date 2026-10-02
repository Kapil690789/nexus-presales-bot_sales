from __future__ import annotations

import hashlib
import logging
import math
import os
import re
import threading
from functools import lru_cache
from typing import Any, NamedTuple

log = logging.getLogger(__name__)

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


class EmbeddingError(RuntimeError):
    def __init__(self, message: str, status_code: int | None = None) -> None:
        super().__init__(message)
        self.status_code = status_code


def _l2_normalize(vec: list[float]) -> list[float]:
    norm = math.sqrt(sum(v * v for v in vec))
    if norm == 0.0:
        return vec
    return [v / norm for v in vec]


def active_embedding_version(model: str | None = None, dim: int | None = None) -> str:
    backend = embedding_backend()
    if backend == "hash":
        return f"{HASH_MODEL}@384:v1"
    m = model or get_settings().embedding_model.strip() or "gemini-embedding-001"
    d = dim or get_settings().embedding_dim or get_platform().embedding_dim or 768
    return f"{m}@{d}:v1"


class EmbeddingBatch(NamedTuple):
    model: str
    dim: int
    vectors: list[list[float]]


class EmbeddingTracker:
    def __init__(self) -> None:
        self._lock = threading.Lock()
        self.failures = 0
        self.last_error = ""

    def record_failure(self, exc: Exception) -> None:
        with self._lock:
            self.failures += 1
            status = getattr(exc, "status_code", None)
            cls_name = type(exc).__name__
            if status:
                self.last_error = f"{cls_name}({status})"
            else:
                self.last_error = cls_name

    def get_health(self) -> dict[str, Any]:
        with self._lock:
            backend = embedding_backend()
            model = get_settings().embedding_model.strip() if backend == "gemini" else (HASH_MODEL if backend == "hash" else BASE_MODEL)
            degraded = self.failures > 0
            return {
                "backend": backend,
                "model": model,
                "degraded": degraded,
                "failures": self.failures,
                "last_error": self.last_error,
            }

    def reset(self) -> None:
        with self._lock:
            self.failures = 0
            self.last_error = ""


_embedding_tracker = EmbeddingTracker()


def record_query_failure(exc: Exception) -> None:
    _embedding_tracker.record_failure(exc)


def get_embedding_health() -> dict[str, Any]:
    return _embedding_tracker.get_health()


def reset_embedding_health() -> None:
    _embedding_tracker.reset()


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


def embed_query(query: str, model_id: str | None = None) -> EmbeddingBatch:
    return embed_texts([query], model_id=model_id, mode="query")


def embed_texts(texts: list[str], model_id: str | None = None, mode: str = "ingest") -> EmbeddingBatch:
    backend = embedding_backend()
    model = model_id or (HASH_MODEL if backend == "hash" else model_id_for(None))
    if backend == "gemini" or (model and "gemini" in model):
        try:
            vectors = _gemini_embed(texts, model, mode=mode)
        except TypeError:
            vectors = _gemini_embed(texts, model)
        dim = len(vectors[0]) if vectors else (get_platform().embedding_dim if "gemini" in model else 0)
        return EmbeddingBatch(model, dim, vectors)
    if backend == "hash" or model == HASH_MODEL:
        vectors = [_hash_embed(text) for text in texts]
        dim = len(vectors[0]) if vectors else 384
        return EmbeddingBatch(HASH_MODEL, dim, vectors)
    encoder = _sentence_model(model_source(model))
    raw = encoder.encode(list(texts), normalize_embeddings=True)
    vectors = [list(map(float, row)) for row in raw]
    dim = len(vectors[0]) if vectors else 0
    return EmbeddingBatch(model, dim, vectors)


def _gemini_embed(
    texts: list[str],
    model_id: str = "gemini-embedding-001",
    mode: str = "ingest",
) -> list[list[float]]:
    import time

    import httpx

    key = get_settings().llm_api_key.strip()
    if not key:
        raise EmbeddingError("LLM_API_KEY is not set")
    if not texts:
        return []

    target_model = model_id or "gemini-embedding-001"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:batchEmbedContents"
    headers = {"x-goog-api-key": key, "Content-Type": "application/json"}

    if mode == "query":
        request_timeout = 5.0
        max_retries = 1
        wall_budget = 8.0
        max_sleep = 2.0
    else:
        request_timeout = 45.0
        max_retries = 4
        wall_budget = 120.0
        max_sleep = 30.0

    task_type = "RETRIEVAL_QUERY" if mode == "query" else "RETRIEVAL_DOCUMENT"
    settings = get_settings()
    target_dim = settings.embedding_dim or get_platform().embedding_dim or 768

    start_time = time.monotonic()
    batch_size = 40
    all_vectors: list[list[float]] = []

    try:
        with httpx.Client(timeout=request_timeout) as client:
            for i in range(0, len(texts), batch_size):
                if i > 0 and mode == "ingest":
                    time.sleep(1.2)
                chunk = texts[i : i + batch_size]
                requests = [
                    {
                        "model": f"models/{target_model}",
                        "content": {"parts": [{"text": t or " "}]},
                        "taskType": task_type,
                        "outputDimensionality": target_dim,
                    }
                    for t in chunk
                ]
                success = False
                last_status: int | None = None

                for attempt in range(max_retries + 1):
                    elapsed = time.monotonic() - start_time
                    if elapsed >= wall_budget:
                        raise EmbeddingError(
                            f"Gemini embedding exceeded time budget ({elapsed:.1f}s >= {wall_budget}s)",
                            status_code=408,
                        )

                    try:
                        resp = client.post(url, headers=headers, json={"requests": requests})
                        if resp.status_code == 200:
                            data = resp.json()
                            raw_embeddings = data.get("embeddings", [])
                            for item in raw_embeddings:
                                values = [float(v) for v in item.get("values", [])]
                                all_vectors.append(_l2_normalize(values))
                            success = True
                            try:
                                from backend.app.core.usage import record_usage

                                est_tokens = sum(max(1, len(t) // 4) for t in chunk)
                                record_usage(
                                    provider="gemini",
                                    model=target_model,
                                    call_type="embedding",
                                    prompt_tokens=est_tokens,
                                    completion_tokens=0,
                                )
                            except Exception:
                                pass
                            break

                        last_status = resp.status_code
                        if resp.status_code in (429, 500, 502, 503, 504) and attempt < max_retries:
                            if mode == "query":
                                sleep_time = min(max_sleep, 1.5)
                            else:
                                backoffs = [3.0, 6.0, 12.0, 20.0, 30.0]
                                sleep_time = backoffs[min(attempt, len(backoffs) - 1)]

                            if (time.monotonic() - start_time) + sleep_time >= wall_budget:
                                raise EmbeddingError(
                                    f"Gemini embedding budget exceeded before retry ({last_status})",
                                    status_code=last_status,
                                )

                            log.warning(
                                "Gemini embedding rate limit/error (%d), backing off %.1fs (attempt %d/%d)",
                                resp.status_code,
                                sleep_time,
                                attempt + 1,
                                max_retries + 1,
                            )
                            time.sleep(sleep_time)
                            continue
                        else:
                            log.warning("Gemini embedding failed with status %d", resp.status_code)
                            raise EmbeddingError(
                                f"Gemini embedding API error {resp.status_code}",
                                status_code=resp.status_code,
                            )
                    except httpx.RequestError as exc:
                        if attempt < max_retries:
                            sleep_time = 1.0 if mode == "query" else 2.0
                            if (time.monotonic() - start_time) + sleep_time >= wall_budget:
                                raise EmbeddingError(
                                    f"Gemini embedding connection error timed out: {type(exc).__name__}",
                                    status_code=504,
                                ) from exc
                            time.sleep(sleep_time)
                            continue
                        raise EmbeddingError(
                            f"Gemini embedding connection error: {type(exc).__name__}",
                            status_code=504,
                        ) from exc

                if not success:
                    raise EmbeddingError(
                        f"Failed to fetch Gemini embeddings for batch of {len(chunk)} items (status {last_status})",
                        status_code=last_status,
                    )

        if len(all_vectors) != len(texts):
            raise EmbeddingError(
                f"Gemini embedding vector count mismatch: expected {len(texts)}, got {len(all_vectors)}"
            )
        return all_vectors
    except EmbeddingError:
        raise
    except Exception as exc:
        log.exception("Exception in _gemini_embed: %s", type(exc).__name__)
        raise EmbeddingError(f"Gemini embedding unexpected failure: {type(exc).__name__}") from exc


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
