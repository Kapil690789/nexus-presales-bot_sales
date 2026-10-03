from __future__ import annotations

from backend.app.core.llm import complete_json, llm_available
from backend.app.core.settings import get_settings
from backend.app.rag.embeddings import embed_texts, embedding_backend


def test_gemini_settings_configuration():
    settings = get_settings()
    assert settings.llm_provider == "gemini"
    assert "gemini" in settings.llm_model


def test_embedding_backend_selection():
    backend = embedding_backend()
    assert backend in {"gemini", "hash", "sentence-transformers"}


def test_gemini_embedding_batch(monkeypatch):
    fake_vectors = [[0.1, 0.2, 0.3], [0.4, 0.5, 0.6]]
    monkeypatch.setattr("backend.app.rag.embeddings._gemini_embed", lambda texts, _model: fake_vectors)
    monkeypatch.setattr("backend.app.rag.embeddings.embedding_backend", lambda: "gemini")

    batch = embed_texts(["Test question 1", "Test question 2"], model_id="gemini-embedding-001")
    assert batch.model == "gemini-embedding-001"
    assert len(batch.vectors) == 2
    assert batch.dim == 3


def test_gemini_llm_complete_json(monkeypatch):
    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"result": "success", "confidence": 0.95}'}]
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None):
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    monkeypatch.setattr(get_settings(), "llm_api_key", "test-key")

    data = complete_json("System prompt", "User prompt")
    assert data.get("result") == "success"
    assert data.get("confidence") == 0.95


def test_thinking_level_settings_validation():
    import pytest
    from backend.app.core.settings import Settings

    # Valid levels
    for level in ("low", "medium", "high", "LOW", "High"):
        s = Settings(llm_thinking_level=level)
        assert s.llm_thinking_level == level.lower()

    # Minimal must fail with clear error
    with pytest.raises(ValueError, match="rejected by gemini-3.8-flash"):
        Settings(llm_thinking_level="minimal")

    # Other invalid values must fail
    with pytest.raises(ValueError, match="Invalid llm_thinking_level"):
        Settings(llm_thinking_level="ultra")


def test_gemini_3_sends_thinking_level_in_request_body(monkeypatch):
    captured_payloads = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"result": "ok"}'}]
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None):
            captured_payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-3.8-flash")
    monkeypatch.setattr(settings, "llm_thinking_level", "low")

    data = complete_json("System", "User")
    assert data.get("result") == "ok"
    assert len(captured_payloads) == 1
    gen_config = captured_payloads[0].get("generationConfig", {})
    assert "thinkingConfig" in gen_config
    assert gen_config["thinkingConfig"]["thinkingLevel"] == "low"


def test_non_gemini_3_model_omits_thinking_config(monkeypatch):
    captured_payloads = []

    class FakeResponse:
        status_code = 200

        def json(self):
            return {
                "candidates": [
                    {
                        "content": {
                            "parts": [{"text": '{"result": "ok"}'}]
                        }
                    }
                ]
            }

    class FakeClient:
        def __init__(self, *args, **kwargs):
            pass

        def __enter__(self):
            return self

        def __exit__(self, *args):
            pass

        def post(self, url, json=None):
            captured_payloads.append(json)
            return FakeResponse()

    monkeypatch.setattr("httpx.Client", FakeClient)
    settings = get_settings()
    monkeypatch.setattr(settings, "llm_api_key", "test-key")
    monkeypatch.setattr(settings, "llm_model", "gemini-2.5-flash")
    monkeypatch.setattr(settings, "llm_thinking_level", "low")

    data = complete_json("System", "User")
    assert data.get("result") == "ok"
    assert len(captured_payloads) == 1
    gen_config = captured_payloads[0].get("generationConfig", {})
    assert "thinkingConfig" not in gen_config

