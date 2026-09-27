from __future__ import annotations

import re

from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available

PRONOUN = re.compile(r"\b(it|that|this|they|those|them|one|there)\b", re.IGNORECASE)


def rewrite_query(text: str, summary: str, previous_user_texts: list[str]) -> str:
    cleaned = (text or "").strip()
    if not cleaned or not PRONOUN.search(cleaned):
        return cleaned
    prior = previous_user_texts[-1].strip() if previous_user_texts else ""
    context = " ".join(part for part in [summary.strip(), prior] if part).strip()
    if not context:
        return cleaned
    if llm_available():
        try:
            data = complete_json(
                f"Rewrite the visitor question so it stands alone. {UNTRUSTED_RULE} Return JSON {{\"query\": \"...\"}}.",
                f"Context:\n{wrap_visitor(context)}\n\nQuestion:\n{wrap_visitor(cleaned)}",
            )
            rewritten = str(data.get("query") or "").strip()
            if rewritten:
                return rewritten
        except LLMError:
            pass
    return f"Context: {context}\nQuestion: {cleaned}"


def lookup_queries(text: str, summary: str, previous_user_texts: list[str]) -> list[str]:
    rewritten = rewrite_query(text, summary, previous_user_texts)
    queries = [rewritten]
    if PRONOUN.search(text or "") and previous_user_texts:
        prior = previous_user_texts[-1].strip()
        if prior and prior not in queries:
            queries.append(prior)
    return [item for item in queries if item.strip()]


def rolling_summary(previous: str, user_texts: list[str], every: int) -> str:
    if not user_texts or every <= 0 or len(user_texts) % every != 0:
        return previous or ""
    joined = "\n".join(user_texts[-8:])
    if llm_available():
        try:
            data = complete_json(
                "Summarize the visitor's project in under 80 words. "
                f"{UNTRUSTED_RULE} Return JSON {{\"summary\": \"...\"}}. Omit emails and phone numbers.",
                wrap_visitor(joined),
            )
            text = str(data.get("summary") or "").strip()
            if text:
                return text[:800]
        except LLMError:
            pass
    return " | ".join(user_texts[-6:])[:800]
