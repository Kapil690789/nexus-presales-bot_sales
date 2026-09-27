import sys
import types

import pytest

from backend.app.core import llm as llm_mod
from backend.app.core.llm import LLMError, MAX_OUTPUT_TOKENS, complete_json, request_timeout
from backend.app.rag import embeddings as embeddings_mod


def test_request_timeout_uses_settings(monkeypatch) -> None:
    monkeypatch.setattr(llm_mod, "get_settings", lambda: types.SimpleNamespace(llm_timeout_seconds=20))
    assert request_timeout() == 20
    monkeypatch.setattr(llm_mod, "get_settings", lambda: types.SimpleNamespace(llm_timeout_seconds=0))
    assert request_timeout() == 1.0


def test_complete_json_maps_timeout_to_llm_error(monkeypatch) -> None:
    monkeypatch.setattr(
        llm_mod,
        "get_settings",
        lambda: types.SimpleNamespace(llm_api_key="sk-test", llm_provider="gemini", llm_model="gemini-3.8-flash"),
    )

    def boom(*args, **kwargs):
        raise TimeoutError("Timeout of 20.0s exceeded")

    monkeypatch.setattr(llm_mod, "_gemini", boom)
    with pytest.raises(LLMError, match="Timeout"):
        complete_json("sys", "user")


def test_gemini_passes_timeout_and_output_cap(monkeypatch) -> None:
    captured: dict = {}

    class FakeResponse:
        text = '{"ok": true}'

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, user, generation_config=None, request_options=None):
            captured["generation_config"] = generation_config
            captured["request_options"] = request_options
            return FakeResponse()

    fake = types.SimpleNamespace(configure=lambda **kwargs: None, GenerativeModel=FakeModel)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake)
    monkeypatch.setattr(llm_mod, "get_settings", lambda: types.SimpleNamespace(llm_timeout_seconds=20))
    data = llm_mod._gemini("sys", "user", "key", "gemini-3.8-flash")
    assert data == {"ok": True}
    assert captured["request_options"]["timeout"] == 20
    assert captured["generation_config"]["max_output_tokens"] == MAX_OUTPUT_TOKENS


def test_gemini_empty_text_is_llm_error(monkeypatch) -> None:
    class FakeResponse:
        text = "  "

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, user, generation_config=None, request_options=None):
            return FakeResponse()

    fake = types.SimpleNamespace(configure=lambda **kwargs: None, GenerativeModel=FakeModel)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake)
    monkeypatch.setattr(llm_mod, "get_settings", lambda: types.SimpleNamespace(llm_timeout_seconds=20))
    with pytest.raises(LLMError, match="empty"):
        llm_mod._gemini("sys", "user", "key", "gemini-3.8-flash")


def test_gemini_blocked_text_is_llm_error(monkeypatch) -> None:
    class FakeResponse:
        @property
        def text(self):
            raise ValueError("blocked: SAFETY")

    class FakeModel:
        def __init__(self, *args, **kwargs):
            pass

        def generate_content(self, user, generation_config=None, request_options=None):
            return FakeResponse()

    fake = types.SimpleNamespace(configure=lambda **kwargs: None, GenerativeModel=FakeModel)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake)
    monkeypatch.setattr(llm_mod, "get_settings", lambda: types.SimpleNamespace(llm_timeout_seconds=20))
    with pytest.raises(LLMError, match="blocked"):
        llm_mod._gemini("sys", "user", "key", "gemini-3.8-flash")


def test_gemini_embed_passes_timeout(monkeypatch) -> None:
    captured: dict = {}

    def fake_embed_content(*, model, content, request_options=None):
        captured["request_options"] = request_options
        return {"embedding": [0.1, 0.2]}

    fake = types.SimpleNamespace(configure=lambda **kwargs: None, embed_content=fake_embed_content)
    monkeypatch.setitem(sys.modules, "google.generativeai", fake)
    monkeypatch.setattr(embeddings_mod, "get_settings", lambda: types.SimpleNamespace(llm_api_key="k", llm_timeout_seconds=20))
    monkeypatch.setattr(embeddings_mod, "request_timeout", lambda: 20)
    vectors = embeddings_mod._gemini("text-embedding-004", ["hello"])
    assert vectors == [[0.1, 0.2]]
    assert captured["request_options"]["timeout"] == 20
