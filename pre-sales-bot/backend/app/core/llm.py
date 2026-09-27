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
        log.warning("Model call failed (%s). The answer continues from project notes.", type(exc).__name__)
        raise LLMError("The model is unavailable") from exc


def _openai(system: str, user: str, api_key: str, model: str, base_url: str) -> dict[str, Any]:
    from openai import OpenAI

    kwargs: dict[str, Any] = {"api_key": api_key}
    if base_url.strip():
        kwargs["base_url"] = base_url.strip()
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
    import google.generativeai as genai

    genai.configure(api_key=api_key)
    llm = genai.GenerativeModel(model or "gemini-3.8-flash", system_instruction=system)
    return _parse_json(llm.generate_content(user).text or "{}")
