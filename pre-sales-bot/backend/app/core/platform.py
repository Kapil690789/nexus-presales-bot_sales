from __future__ import annotations

from functools import lru_cache
from typing import Any

import yaml
from pydantic import BaseModel, Field

from backend.app.core.settings import ROOT


class CalendarDefaults(BaseModel):
    timezone: str = "America/New_York"
    duration_minutes: int = 30


class PlatformConfig(BaseModel):
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    embedding_dim: int = 384
    chunk_tokens: int = 500
    chunk_overlap_tokens: int = 80
    semantic_break_similarity: float = 0.5
    max_chunks_per_doc: int = 2
    top_k: int = 4
    faq_min_score: float = 0.82
    show_min_score: float = 0.55
    weak_min_score: float = 0.35
    memory_turns: int = 8
    summary_every: int = 4
    finetune_min_positives: int = 64
    calendar: CalendarDefaults = Field(default_factory=CalendarDefaults)


@lru_cache
def get_platform() -> PlatformConfig:
    path = ROOT / "config" / "platform.yaml"
    raw: dict[str, Any] = {}
    if path.is_file():
        loaded = yaml.safe_load(path.read_text(encoding="utf-8")) or {}
        if isinstance(loaded, dict):
            raw = loaded
    return PlatformConfig.model_validate(raw)
