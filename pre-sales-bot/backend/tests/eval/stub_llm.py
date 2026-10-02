"""
Eval harness stub LLM — Nexus Pre-Sales Bot
============================================
A fully deterministic LLM stub used by all eval scenarios.

Rules:
  - NEVER imports LLM_API_KEY or prints any env value.
  - Returns deterministic JSON for any complete_json call.
  - Uses a real (hash-embedding) backend so no network calls are made.
"""
from __future__ import annotations

import json
from typing import Any


# ---------------------------------------------------------------------------
# Stub responses keyed by keyword fragments in the system prompt
# ---------------------------------------------------------------------------

_STUB_TABLE: list[tuple[str, dict]] = [
    # Extractor responses
    ("extracts project scope", {"service": None, "goal": None, "platforms": [], "features": [],
                                 "feature_detail": None, "users": None, "integrations": [],
                                 "timeline": None, "budget_band": None, "decision_role": None,
                                 "company_size": None, "is_question": False, "is_off_topic": False,
                                 "uncertain": False}),
    # Estimate message
    ("indicative engineering estimate", {"message": "STUB_ESTIMATE_MESSAGE: indicative range as calculated."}),
    # Fallback / general consultant
    ("pre-sales software consultant", {"message": "STUB_FALLBACK: How can I help you scope your project?"}),
    # Discovery synth
    ("discovery", {"message": "STUB_DISCOVERY: Tell me more about your project goals."}),
    # Chips / suggestions
    ("suggest", {"chips": ["STUB_CHIP_A", "STUB_CHIP_B"]}),
]


def stub_complete_json(system_prompt: str, user_prompt: str, **_kwargs) -> dict[str, Any]:
    """
    Deterministic stub for complete_json().  Matches on system_prompt keywords
    and returns a canned dict.  Falls back to an empty dict if nothing matches.
    Never touches any real API key.
    """
    lowered = (system_prompt or "").lower()
    for fragment, response in _STUB_TABLE:
        if fragment in lowered:
            return dict(response)  # return a copy so callers can't mutate the table
    return {}


def stub_llm_available() -> bool:
    return True
