from __future__ import annotations

import json
import re
from typing import Any

from sqlalchemy import func, select
from sqlalchemy.orm import Session

from backend.app.models.entities import LeadRow, SessionRow

PACE = ("terse", "balanced", "detailed")
CLARITY = ("following", "confused")
REGISTER = ("plain", "technical")
MOOD = ("neutral", "impatient", "skeptical")

TERSE_INTENT = re.compile(
    r"\b(just tell me(?: the price)?|just the price|price\?|get to the point|skip(?: it)?)\b",
    re.I,
)
CONFUSED = re.compile(
    r"\b(what do you mean|i don'?t understand|dont understand|confused|huh\??|"
    r"can you explain|say that again|didn'?t get that|not following)\b",
    re.I,
)
IMPATIENT = re.compile(r"\b(skip|get to the point|just tell me|hurry|don'?t care)\b", re.I)
SKEPTICAL = re.compile(r"\b(expensive|too much|cheaper|offshore|fixed price|too long|too slow)\b", re.I)
TECHNICAL = re.compile(
    r"\b(api|sdk|pgvector|postgres(?:ql)?|flutter|react native|next\.?js|fastapi|"
    r"kubernetes|oauth|rag|embedding|graphql|redis|docker|webhooks?|jwt)\b",
    re.I,
)
EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
WORDS = re.compile(r"[A-Za-z0-9']+")

TERSE_WORD_LIMIT = 36


def default_style() -> dict:
    return {
        "pace": "balanced",
        "clarity": "following",
        "register": "plain",
        "mood": "neutral",
        "notes": "",
        "returning": False,
    }


def detect_style(
    user_text: str,
    transcript: str = "",
    previous: dict | None = None,
    overlay: dict | None = None,
) -> dict:
    """Update the live style profile from this turn. Offline-safe."""
    previous = _coerce(previous)
    if _contact_only(user_text):
        return overlay_llm(previous, overlay)
    if not (user_text or "").strip():
        return overlay_llm(previous, overlay)

    detected = _heuristic(user_text or "", transcript or "")
    merged = merge_style(previous, detected, strong_terse=bool(TERSE_INTENT.search(user_text or "")))
    return overlay_llm(merged, overlay)


def merge_style(previous: dict | None, detected: dict | None, *, strong_terse: bool = False) -> dict:
    """Keep a technical register and a detailed pace through a one-word ack."""
    prev = _coerce(previous)
    new = _coerce(detected)
    pace = new["pace"]
    if pace == "terse" and prev["pace"] in {"detailed", "balanced"} and not strong_terse:
        pace = prev["pace"]
    register = new["register"]
    if register == "plain" and prev["register"] == "technical":
        register = "technical"
    mood = new["mood"]
    if mood == "neutral" and prev["mood"] in {"impatient", "skeptical"}:
        mood = prev["mood"]
    notes = new["notes"] or prev["notes"]
    return {
        "pace": pace,
        "clarity": new["clarity"],
        "register": register,
        "mood": mood,
        "notes": notes,
        "returning": bool(prev["returning"] or new["returning"]),
    }


def overlay_llm(style: dict | None, visitor_style: Any) -> dict:
    """Fold optional visitor_style from the existing LLM JSON. No extra call."""
    current = _coerce(style)
    if not isinstance(visitor_style, dict):
        return current
    allowed = {"pace": PACE, "clarity": CLARITY, "register": REGISTER, "mood": MOOD}
    for key, values in allowed.items():
        value = str(visitor_style.get(key) or "").strip().lower()
        if value in values:
            current[key] = value
    notes = _scrub_notes(str(visitor_style.get("notes") or "").strip())
    if notes:
        current["notes"] = notes
    return current


def prior_style_for_email(db: Session | None, email: str, exclude_session_id: str = "") -> dict | None:
    """Latest other session for this work email, or None. No transcripts."""
    needle = (email or "").strip().lower()
    if db is None or not needle:
        return None
    lead = db.scalar(
        select(LeadRow)
        .where(func.lower(LeadRow.email) == needle, LeadRow.session_id != (exclude_session_id or ""))
        .order_by(LeadRow.created_at.desc())
    )
    if lead is None:
        return None
    row = db.get(SessionRow, lead.session_id)
    if row is None:
        return None
    style = _coerce(_loads(getattr(row, "style_json", "") or ""))
    learning = _loads(getattr(row, "learning_json", "") or "") or {}
    bits = [str(learning.get(key) or "").strip() for key in ("tone_that_worked", "tone_to_avoid") if learning.get(key)]
    if bits and not style["notes"]:
        style["notes"] = _scrub_notes("; ".join(bits))
    style["returning"] = True
    return style


def apply_live_style(
    message: str,
    style: dict | None,
    *,
    estimate: dict | None = None,
    last_assistant: str = "",
) -> str:
    """Shape an offline fallback reply to the live profile."""
    style = _coerce(style)
    text = (message or "").strip()
    if style["clarity"] == "confused":
        if estimate and "indicative range" not in text.lower() and "not a contractual quote" not in text.lower():
            text = "The number is an indicative range for the MVP, not a contractual quote. " + text
        elif last_assistant and "in short:" not in text.lower():
            text = f"In short: {_first_sentence(last_assistant, 18)} {text}"
    if style["pace"] == "terse" or style["mood"] == "impatient":
        if estimate:
            label = str(estimate.get("range_label") or "")
            weeks = estimate.get("timeline_weeks")
            if label:
                text = (
                    f"Indicative MVP **{label}**"
                    + (f" over about **{weeks} weeks**" if weeks is not None else "")
                    + ". Not a contractual quote."
                )
        else:
            text = _first_sentence(text, TERSE_WORD_LIMIT)
    return text.strip()


def _heuristic(user_text: str, transcript: str) -> dict:
    words = _word_count(user_text)
    pace = "balanced"
    if words >= 40:
        pace = "detailed"
    elif words <= 6 or TERSE_INTENT.search(user_text):
        pace = "terse"
    clarity = "confused" if CONFUSED.search(user_text) or _repeated_ask(transcript, user_text) else "following"
    register = "technical" if TECHNICAL.search(user_text) else "plain"
    mood = "neutral"
    if IMPATIENT.search(user_text) or TERSE_INTENT.search(user_text):
        mood = "impatient"
    elif SKEPTICAL.search(user_text):
        mood = "skeptical"
    notes = ""
    if clarity == "confused":
        notes = "They asked for a simpler restatement."
    elif pace == "terse":
        notes = "Keep replies to one short sentence plus chips."
    elif register == "technical":
        notes = "They are using stack language; answer with approved names."
    return {
        "pace": pace,
        "clarity": clarity,
        "register": register,
        "mood": mood,
        "notes": notes,
        "returning": False,
    }


def _repeated_ask(transcript: str, user_text: str) -> bool:
    current = _normalize(user_text)
    if len(current) < 12:
        return False
    previous = [
        _normalize(line.split(":", 1)[-1])
        for line in (transcript or "").splitlines()
        if line.lower().startswith("user:")
    ]
    if not previous:
        return False
    return current in previous[:-1] or any(current == item or item in current or current in item for item in previous[:-1])


def _contact_only(text: str) -> bool:
    stripped = (text or "").strip()
    if not stripped:
        return False
    if EMAIL.fullmatch(stripped):
        return True
    remainder = EMAIL.sub("", stripped).strip(" .,;")
    return bool(EMAIL.search(stripped) and _word_count(remainder) <= 2)


def _coerce(style: dict | None) -> dict:
    base = default_style()
    if not isinstance(style, dict):
        return base
    for key in base:
        if key == "returning":
            base[key] = bool(style.get(key))
            continue
        value = style.get(key)
        if key == "notes":
            base[key] = _scrub_notes(str(value or ""))
            continue
        allowed = {"pace": PACE, "clarity": CLARITY, "register": REGISTER, "mood": MOOD}[key]
        text = str(value or "").strip().lower()
        if text in allowed:
            base[key] = text
    return base


def _scrub_notes(text: str) -> str:
    cleaned = EMAIL.sub("[email]", text or "")
    return cleaned.replace("@", " ").strip()[:240]


def _word_count(text: str) -> int:
    return len(WORDS.findall(text or ""))


def _normalize(text: str) -> str:
    return " ".join(WORDS.findall((text or "").lower()))


def _first_sentence(text: str, max_words: int) -> str:
    stripped = re.sub(r"\s+", " ", (text or "").strip())
    parts = re.split(r"(?<=[.!?])\s+", stripped)
    candidate = parts[0] if parts else stripped
    tokens = candidate.split()
    if len(tokens) <= max_words:
        return candidate if candidate.endswith((".", "!", "?")) or not candidate else candidate
    clipped = " ".join(tokens[:max_words]).rstrip(",;:")
    return clipped + ("." if not clipped.endswith((".", "!", "?")) else "")


def _loads(raw: str) -> dict:
    if not raw:
        return {}
    try:
        value = json.loads(raw)
    except json.JSONDecodeError:
        return {}
    return value if isinstance(value, dict) else {}
