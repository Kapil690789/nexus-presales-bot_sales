from __future__ import annotations

import re

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)


def redact(text: str) -> str:
    cleaned = EMAIL.sub("[email]", text or "")
    cleaned = URL.sub("[link]", cleaned)
    cleaned = PHONE.sub("[phone]", cleaned)
    return cleaned
