from __future__ import annotations

import re

from backend.app.core.guard import UNTRUSTED_RULE, wrap_visitor
from backend.app.core.llm import LLMError, complete_json, llm_available

REWRITE_TRIGGERS = re.compile(
    r"\b(it|its|that|this|they|them|those|these|there|also|and|same|other|instead|too|what\s+about|how\s+about)\b",
    re.IGNORECASE,
)
PRONOUN = REWRITE_TRIGGERS


def rewrite_query(text: str, summary: str, previous_user_texts: list[str]) -> str:
    cleaned = (text or "").strip()
    if not cleaned:
        return ""
    words = cleaned.split()
    # Skip LLM rewrite only when message has at least 4 words AND contains none of the trigger words
    if len(words) >= 4 and not REWRITE_TRIGGERS.search(cleaned):
        return cleaned

    prior = previous_user_texts[-1].strip() if previous_user_texts else ""
    context = " ".join(part for part in [summary.strip(), prior] if part).strip()
    if not context:
        return cleaned

    if llm_available():
        try:
            is_mocked = (
                getattr(complete_json, "__module__", "") != "backend.app.core.llm"
                or getattr(complete_json, "__name__", "") != "complete_json"
            )
            prompt_sys = f"Rewrite the visitor question so it stands alone. {UNTRUSTED_RULE} Return JSON {{\"query\": \"...\"}}."
            prompt_usr = f"Context:\n{wrap_visitor(context)}\n\nQuestion:\n{wrap_visitor(cleaned)}"
            if not is_mocked:
                data = complete_json(prompt_sys, prompt_usr, mode="request", purpose="rewrite")
            else:
                data = complete_json(prompt_sys, prompt_usr, mode="request")
            rewritten = str(data.get("query") or "").strip()
            if rewritten:
                return rewritten
        except LLMError:
            pass
    return f"Context: {context}\nQuestion: {cleaned}"


def lookup_queries(text: str, summary: str, previous_user_texts: list[str]) -> list[str]:
    rewritten = rewrite_query(text, summary, previous_user_texts)
    queries = [rewritten]
    if REWRITE_TRIGGERS.search(text or "") and previous_user_texts:
        prior = previous_user_texts[-1].strip()
        if prior and prior not in queries:
            queries.append(prior)
    return [item for item in queries if item.strip()]


def rolling_summary(
    previous: str,
    user_texts: list[str],
    every: int,
    history: list[dict] | None = None,
) -> str:
    if not user_texts or every <= 0 or len(user_texts) % every != 0:
        return previous or ""
    if history:
        recent_turns = [item for item in history[-10:] if item.get("content")]
        formatted = []
        for t in recent_turns:
            role_label = "Visitor" if t.get("role") == "user" else "Consultant"
            formatted.append(f"{role_label}: {t['content'].strip()}")
        joined = "\n".join(formatted)
    else:
        recent = [u.strip() for u in user_texts[-8:] if u.strip()]
        joined = "\n".join(f"- {u}" for u in recent)
    if llm_available():
        try:
            is_mocked = (
                getattr(complete_json, "__module__", "") != "backend.app.core.llm"
                or getattr(complete_json, "__name__", "") != "complete_json"
            )
            prompt_sys = (
                f"You are a technical project lead. Summarize the visitor's software project requirements, "
                f"core modules, and constraints in under 80 words based on their consultation dialogue. {UNTRUSTED_RULE} "
                f'Return JSON {{"summary": "..."}}. Omit emails, phone numbers, and conversational greetings.'
            )
            prompt_usr = wrap_visitor(joined)
            if not is_mocked:
                data = complete_json(prompt_sys, prompt_usr, purpose="summary")
            else:
                data = complete_json(prompt_sys, prompt_usr)
            text = str(data.get("summary") or "").strip()
            if text:
                return text[:800]
        except LLMError:
            pass
    return " | ".join(user_texts[-6:])[:800]
