from __future__ import annotations

import re

from backend.app.config_loader.models import RagRedaction

EMAIL = re.compile(r"[\w.+-]+@[\w-]+\.[\w.-]+")
PHONE = re.compile(r"(?<!\w)(?:\+?\d[\d\s().-]{7,}\d)(?!\w)")
URL = re.compile(r"\b(?:https?://|www\.)\S+", re.IGNORECASE)
# Two or more consecutive capitalised words: company and person names in practice.
PROPER_NOUN = re.compile(r"\b(?:[A-Z][a-z]{1,}\.?)(?:\s+(?:[A-Z][a-z]{1,}\.?|&|of|and|the))*\s+(?:[A-Z][a-z]{1,}\.?)\b")

# Capitalised phrases that carry no identifying information and are worth keeping.
KEEP = {
    "App Store",
    "Google Play",
    "Play Store",
    "React Native",
    "Next Js",
    "Node Js",
    "Product Designer",
    "Backend Engineer",
    "Frontend Engineer",
    "Mobile Engineer",
    "Solutions Architect",
    "Delivery Lead",
    "Full Stack Engineer",
    "Product Discovery",
}


def redact(text: str, rules: RagRedaction) -> str:
    """Strip identifying details before anything visitor-authored is persisted for reuse."""
    cleaned = text or ""
    if rules.emails:
        cleaned = EMAIL.sub("[email]", cleaned)
    if rules.urls:
        cleaned = URL.sub("[link]", cleaned)
    if rules.phones:
        cleaned = PHONE.sub("[phone]", cleaned)
    if rules.proper_nouns:
        cleaned = PROPER_NOUN.sub(_replace_proper_noun, cleaned)
    return cleaned.strip()


def _replace_proper_noun(match: re.Match[str]) -> str:
    phrase = match.group(0)
    return phrase if phrase in KEEP else "[name]"
