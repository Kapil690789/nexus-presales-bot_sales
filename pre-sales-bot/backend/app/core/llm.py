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


def complete_json(system: str, user: str) -> dict[str, Any]:
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
            return _gemini(system, user, settings.llm_api_key, settings.llm_model)
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
    return _parse_json(text)


def _gemini(system: str, user: str, api_key: str, model: str) -> dict[str, Any]:
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

    backoffs = [3, 6, 12, 20]
    try:
        with httpx.Client(timeout=15.0) as client:
            for attempt, backoff in enumerate(backoffs + [None]):
                resp = client.post(url, json=payload)
                if resp.status_code == 200:
                    data = resp.json()
                    candidates = data.get("candidates", [])
                    if not candidates:
                        raise LLMError("Gemini returned no candidates")
                    parts = candidates[0].get("content", {}).get("parts", [])
                    text = parts[0].get("text", "") if parts else ""
                    return _parse_json(text or "{}")
                if resp.status_code == 429:
                    if backoff is None:
                        raise LLMError(f"Gemini quota exceeded after {len(backoffs)} retries: {resp.text[:200]}")
                    log.warning(
                        "Gemini LLM rate limit hit (429), backing off for %ds (attempt %d/%d)",
                        backoff,
                        attempt + 1,
                        len(backoffs),
                    )
                    time.sleep(backoff)
                    continue
                raise LLMError(f"Gemini API error {resp.status_code}: {resp.text[:200]}")
    except httpx.RequestError as exc:
        raise LLMError(f"Gemini connection error: {exc}") from exc
