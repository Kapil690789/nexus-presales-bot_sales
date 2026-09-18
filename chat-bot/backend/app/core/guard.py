from __future__ import annotations

import re
import unicodedata

MONEY_RE = re.compile(
    r"(?<!\w)(?:USD\s*)?\$\s*\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?|(?<!\w)(?:USD\s*)?\$\s*\d+(?:\.\d{1,2})?|\bUSD\s+\d{1,3}(?:,\d{3})*(?:\.\d{1,2})?",
    re.IGNORECASE,
)
ZERO_WIDTH = re.compile(r"[\u200b\u200c\u200d\ufeff]")
JAILBREAK_RE = re.compile(
    r"ignore\s+previous|ignore\s+all\s+instructions|system\s+prompt|you\s+are\s+now|disregard\s+your\s+rules",
    re.IGNORECASE,
)
LEET = str.maketrans({"0": "o", "1": "i", "3": "e", "4": "a", "5": "s", "@": "a"})
SAFE_FALLBACK = "Let's keep this to scope, estimate, and next steps."


def normalize_text(text: str) -> str:
    folded = unicodedata.normalize("NFKC", text or "")
    folded = ZERO_WIDTH.sub("", folded)
    return re.sub(r"[ \t]+", " ", folded)


def _fold_for_match(text: str) -> str:
    return normalize_text(text).lower().translate(LEET)


def looks_like_jailbreak(text: str) -> bool:
    return bool(JAILBREAK_RE.search(_fold_for_match(text)))


def strip_never_say(message: str, never: list[str]) -> str:
    text = message or ""
    needles = [_fold_for_match(phrase) for phrase in never if phrase]
    if not needles:
        return text.strip() or SAFE_FALLBACK
    parts = re.split(r"(?<=[.!?])\s+", text)
    cleaned: list[str] = []
    for part in parts:
        folded = _fold_for_match(part)
        if any(needle and needle in folded for needle in needles):
            cleaned.append(SAFE_FALLBACK)
        else:
            cleaned.append(part)
    return " ".join(cleaned).strip() or SAFE_FALLBACK


def _amount_digits(value: object) -> str:
    return re.sub(r"\D", "", str(value or ""))


def allowed_price_digits(estimate: dict | None) -> set[str]:
    if not estimate:
        return set()
    allowed = set()
    for key in ("low", "high", "raw"):
        digits = _amount_digits(estimate.get(key))
        if digits:
            allowed.add(digits)
            allowed.add(digits.lstrip("0") or "0")
    label = str(estimate.get("range_label") or "")
    for match in MONEY_RE.finditer(label):
        digits = _amount_digits(match.group(0))
        if digits:
            allowed.add(digits)
            allowed.add(digits.lstrip("0") or "0")
    return allowed


def sanitize_reply(message: str, estimate: dict | None, never: list[str]) -> str:
    text = strip_never_say(message, never)
    allowed = allowed_price_digits(estimate)
    replacement = (estimate or {}).get("range_label") or "an indicative range"

    def _swap(match: re.Match[str]) -> str:
        digits = _amount_digits(match.group(0))
        compact = digits.lstrip("0") or "0"
        if digits in allowed or compact in allowed:
            return match.group(0)
        return str(replacement)

    return MONEY_RE.sub(_swap, text).strip() or SAFE_FALLBACK
