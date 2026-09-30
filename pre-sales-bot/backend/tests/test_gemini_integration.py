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
