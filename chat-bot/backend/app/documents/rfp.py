from __future__ import annotations

import re

from backend.app.agents.brief import ProjectBrief
from backend.app.agents.extract import extract_from_text

CONSTRAINT_MARKERS = (
    "must not",
    "must-have",
    "constraint",
    "no custom",
    "keep the stack",
    "hipaa",
    "on-prem",
)


def extract_rfp(brief: ProjectBrief, text: str) -> ProjectBrief:
    brief = extract_from_text(brief, text)
    lowered = (text or "").lower()
    if "salesforce" in lowered and "salesforce" not in brief.integrations:
        brief.integrations.append("salesforce")
    if "stripe" in lowered and "stripe" not in brief.integrations:
        brief.integrations.append("stripe")
    for marker in CONSTRAINT_MARKERS:
        if marker in lowered:
            snippet = _sentence_containing(text, marker)
            if snippet and snippet not in brief.constraints:
                brief.constraints.append(snippet[:180])
    if not brief.goal:
        match = re.search(r"goal:\s*(.+)", text or "", flags=re.I)
        if match:
            brief.goal = match.group(1).strip()[:240]
    return brief


def _sentence_containing(text: str, marker: str) -> str:
    for line in (text or "").splitlines():
        if marker in line.lower():
            return line.strip()
    return marker
