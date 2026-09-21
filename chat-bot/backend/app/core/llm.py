import json
import re
from typing import Any

from backend.app.core.settings import get_settings


class LLMError(RuntimeError):
    pass


def llm_available() -> bool:
    return bool(get_settings().llm_api_key.strip())


def _parse_json(text: str) -> dict[str, Any]:
    cleaned = re.sub(r"^```(?:json)?\s*|\s*```$", "", text.strip(), flags=re.IGNORECASE)
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
    settings = get_settings()
    if not settings.llm_api_key:
        raise LLMError("LLM_API_KEY is not set")
    provider = settings.llm_provider.lower()
    if provider == "anthropic":
        return _anthropic(system, user, settings.llm_api_key, settings.llm_model)
    if provider == "gemini":
        return _gemini(system, user, settings.llm_api_key, settings.llm_model)
    return _openai(system, user, settings.llm_api_key, settings.llm_model)


def _openai(system: str, user: str, api_key: str, model: str) -> dict[str, Any]:
    from openai import OpenAI

    settings = get_settings()
    kwargs: dict[str, Any] = {"api_key": api_key}
    if settings.llm_base_url.strip():
        kwargs["base_url"] = settings.llm_base_url.strip()
    client = OpenAI(**kwargs)
    create_kwargs: dict[str, Any] = {
        "model": model or "gpt-4.1-mini",
        "temperature": 0.3,
        "messages": [{"role": "system", "content": system}, {"role": "user", "content": user}],
    }
    # Native OpenAI supports json_object; some OpenAI-compatible proxies do not.
    if not settings.llm_base_url.strip():
        create_kwargs["response_format"] = {"type": "json_object"}
    response = client.chat.completions.create(**create_kwargs)
    return _parse_json(response.choices[0].message.content or "{}")


def _anthropic(system: str, user: str, api_key: str, model: str) -> dict[str, Any]:
    from anthropic import Anthropic

    client = Anthropic(api_key=api_key)
    response = client.messages.create(
        model=model or "claude-sonnet-4-20250514",
        max_tokens=800,
        temperature=0.3,
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
