from __future__ import annotations

import json
import logging
import re
from typing import Any

from backend.app.core.settings import get_settings

log = logging.getLogger(__name__)


class LLMError(RuntimeError):
    pass


def llm_available() -> bool:
    return bool(get_settings().llm_api_key.strip())


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", (text or "").strip(), flags=re.IGNORECASE)
    try:
        data = json.loads(cleaned)
        if isinstance(data, dict):
            return data
    except json.JSONDecodeError:
        pass
    match = re.search(r"\{.*\}", cleaned, flags=re.DOTALL)
    if not match:
        raise LLMError("Model did not return JSON")
    data = json.loads(match.group(0))
    if not isinstance(data, dict):
        raise LLMError("Model JSON was not an object")
    return data


def complete_json(system: str, user: str, mode: str = "request") -> dict[str, Any]:
    from backend.app.core.security import allow_llm_call

    settings = get_settings()
    if not settings.llm_api_key.strip():
        raise LLMError("LLM_API_KEY is not set")
    if not allow_llm_call():
        raise LLMError("LLM budget exceeded")
    provider = settings.llm_provider.lower().strip()
    try:
        if provider == "anthropic":
            return _anthropic(system, user, settings.llm_api_key, settings.llm_model)
        if provider == "gemini":
            return _gemini(system, user, settings.llm_api_key, settings.llm_model, mode=mode)
        return _openai(system, user, settings.llm_api_key, settings.llm_model, settings.llm_base_url)
    except LLMError:
        raise
    except Exception as exc:
        log.warning(
            "Model call failed (%s): %s. The answer continues from project notes.",
            type(exc).__name__,
            _public_error(exc),
        )
        raise LLMError("The model is unavailable") from exc


def _public_error(exc: Exception) -> str:
    text = " ".join(str(exc).split())
    key = get_settings().llm_api_key.strip()
    if key:
        text = text.replace(key, "[redacted]")
    return text[:300]


def _openai(system: str, user: str, api_key: str, model: str, base_url: str) -> dict[str, Any]:
    from openai import OpenAI

    kwargs: dict[str, Any] = {"api_key": api_key, "timeout": 20.0}
    if base_url.strip():
        referer = get_settings().public_base_url.strip() or "http://127.0.0.1:8010"
        kwargs["base_url"] = base_url.strip()
        # Quota errors are not transient. Retrying them burns the free daily cap.
        kwargs["max_retries"] = 0
        kwargs["default_headers"] = {
            "HTTP-Referer": referer,
            "X-Title": "pre-sales-bot",
        }
    client = OpenAI(**kwargs)
    create_kwargs: dict[str, Any] = {
        "model": model or "gpt-4.1-mini",
        "temperature": 0.2,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    if not base_url.strip():
        create_kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**create_kwargs)
    try:
        from backend.app.core.usage import record_usage

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "prompt_tokens", 0) if usage else max(1, len(system + user) // 4)
        completion_tokens = getattr(usage, "completion_tokens", 0) if usage else 0
        record_usage(
            provider="openai",
            model=model or "gpt-4.1-mini",
            call_type="llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    except Exception:
        pass
    return _parse_json(response.choices[0].message.content or "{}")


def _anthropic(system: str, user: str, api_key: str, model: str) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model or "claude-sonnet-4-20250514",
        max_tokens=800,
        temperature=0.2,
        system=system,
        messages=[{"role": "user", "content": user}],
    )
    text = "".join(block.text for block in response.content if getattr(block, "text", None))
    try:
        from backend.app.core.usage import record_usage

        usage = getattr(response, "usage", None)
        prompt_tokens = getattr(usage, "input_tokens", 0) if usage else max(1, len(system + user) // 4)
        completion_tokens = getattr(usage, "output_tokens", 0) if usage else max(1, len(text) // 4)
        record_usage(
            provider="anthropic",
            model=model or "claude-sonnet-4-20250514",
            call_type="llm",
            prompt_tokens=prompt_tokens,
            completion_tokens=completion_tokens,
        )
    except Exception:
        pass
    return _parse_json(text)


def _gemini(system: str, user: str, api_key: str, model: str, mode: str = "request") -> dict[str, Any]:
    import time

    import httpx

    target_model = (model or "").strip() or "gemini-2.5-flash"
    url = f"https://generativelanguage.googleapis.com/v1beta/models/{target_model}:generateContent?key={api_key.strip()}"
    payload: dict[str, Any] = {
        "contents": [{"parts": [{"text": user}]}],
        "generationConfig": {
            "responseMimeType": "application/json",
            "temperature": 0.2,
        },
    }
    if system.strip():
        payload["systemInstruction"] = {"parts": [{"text": system.strip()}]}

    if mode == "request":
        per_call_timeout = 15.0
        max_retries = 1
        wall_budget = 12.0
        backoffs = [3.0]
    else:
        per_call_timeout = 15.0
        max_retries = 4
        wall_budget = 60.0
        backoffs = [3.0, 6.0, 12.0, 20.0]

    start_time = time.monotonic()
    try:
        with httpx.Client(timeout=per_call_timeout) as client:
            for attempt in range(max_retries + 1):
                elapsed = time.monotonic() - start_time
                if elapsed >= wall_budget:
                    raise LLMError(f"Gemini LLM exceeded time budget ({elapsed:.1f}s >= {wall_budget}s)")

                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise LLMError("Gemini returned no candidates")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = parts[0].get("text", "") if parts else ""
                    try:
                        from backend.app.core.usage import record_usage

                        usage = data.get("usageMetadata", {})
                        prompt_tokens = usage.get("promptTokenCount", 0)
                        candidates_tokens = usage.get("candidatesTokenCount", 0)
                        thoughts_tokens = usage.get("thoughtsTokenCount", 0)
                        completion_tokens = candidates_tokens + thoughts_tokens
                        if prompt_tokens == 0 and completion_tokens == 0:
                            prompt_tokens = max(1, len(system + user) // 4)
                            completion_tokens = max(1, len(text) // 4)
                        record_usage(
                            provider="gemini",
                            model=target_model,
                            call_type="llm",
                            prompt_tokens=prompt_tokens,
                            completion_tokens=completion_tokens,
                        )
                    except Exception:
                        pass
                    return _parse_json(text or "{}")

                if resp.status_code == 429:
                    if attempt >= max_retries:
                        raise LLMError(f"Gemini quota exceeded after {max_retries} retries: {resp.text[:200]}")
                    backoff = backoffs[min(attempt, len(backoffs) - 1)]
                    if (time.monotonic() - start_time) + backoff >= wall_budget:
                        raise LLMError(f"Gemini LLM budget exceeded before retry ({resp.status_code})")
                    log.warning(
                        "Gemini LLM rate limit hit (429), backing off for %.1fs (attempt %d/%d)",
                        backoff,
                        attempt + 1,
                        max_retries,
                    )
                    time.sleep(backoff)
                    continue

                raise LLMError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
    except httpx.RequestError as exc:
        raise LLMError(f"Gemini connection error: {exc}") from exc


def record_system_event(
    kind: str,
    reason: str,
    stage: str,
    error_class: str,
) -> None:
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import delete
    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import SystemEventRow

    now = datetime.now(timezone.utc)
    cutoff = now - timedelta(days=7)
    try:
        with SessionLocal() as db:
            try:
                db.execute(delete(SystemEventRow).where(SystemEventRow.created_at < cutoff))
            except Exception:
                pass
            event = SystemEventRow(
                created_at=now,
                kind=kind[:40],
                reason=reason[:200],
                stage=stage[:50],
                error_class=error_class[:100],
            )
            db.add(event)
            db.commit()
    except Exception:
        log.warning("Failed to record system event: %s", error_class)


def get_llm_health(db: Any = None) -> dict[str, Any]:
    from datetime import datetime, timedelta, timezone
    from sqlalchemy import select
    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import SystemEventRow

    cutoff = datetime.now(timezone.utc) - timedelta(hours=1)

    def _query(session):
        events = session.scalars(
            select(SystemEventRow)
            .where(SystemEventRow.kind == "llm_failure", SystemEventRow.created_at >= cutoff)
            .order_by(SystemEventRow.created_at.desc())
        ).all()
        failures_1h = len(events)
        last_error = events[0].error_class if events else ""
        return {
            "failures_1h": failures_1h,
            "last_error_class": last_error,
            "degraded": failures_1h > 0,
        }

    if db is not None:
        try:
            return _query(db)
        except Exception:
            return {"failures_1h": 0, "last_error_class": "", "degraded": False}

    try:
        with SessionLocal() as session:
            return _query(session)
    except Exception:
        return {"failures_1h": 0, "last_error_class": "", "degraded": False}


def handle_embedding_failure(exc: Exception) -> None:
    try:
        cls_name = type(exc).__name__
        record_system_event(
            kind="embedding_failure",
            reason=f"{cls_name} during embedding",
            stage="embeddings",
            error_class=cls_name,
        )
    except Exception:
        pass


def register_embedding_failure_listener() -> None:
    try:
        from backend.app.rag.embeddings import set_failure_listener

        set_failure_listener(handle_embedding_failure)
    except Exception:
        pass


register_embedding_failure_listener()
