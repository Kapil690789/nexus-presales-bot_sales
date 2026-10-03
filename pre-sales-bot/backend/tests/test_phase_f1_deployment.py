from __future__ import annotations

import logging
from unittest.mock import patch, MagicMock

import pytest
from fastapi.testclient import TestClient

from backend.app.core.security import is_admin_misconfigured
from backend.app.core.settings import Settings, get_settings
from backend.app.main import create_app
from backend.app.models.db import SessionLocal, init_db
from backend.app.rag.ingest import ingest_all


def test_f1_vercel_default_password_and_dev_env_fails_closed_404(monkeypatch):
    """
    VERCEL=1 + default password + ENVIRONMENT=development -> /admin is 404.
    Production guards apply whenever VERCEL is set, regardless of ENVIRONMENT string.
    """
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ADMIN_PASSWORD", "admin123")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    monkeypatch.setenv("ALLOW_EPHEMERAL_DB", "true")
    get_settings.cache_clear()

    settings = get_settings()
    assert settings.is_production_like is True
    assert is_admin_misconfigured(settings) is True

    app = create_app()
    client = TestClient(app)

    # In production-like environments, misconfigured admin router is omitted -> 404 Not Found
    resp = client.get("/admin")
    assert resp.status_code == 404

    resp_auth = client.get("/admin", auth=("admin", "admin123"))
    assert resp_auth.status_code == 404

    # Public health is minimal status ok or degraded
    health_resp = client.get("/health")
    assert health_resp.status_code == 200
    assert health_resp.json()["status"] in {"ok", "degraded"}
    assert set(health_resp.json().keys()) == {"status"}


def test_f1_production_sqlite_raises_value_error(monkeypatch):
    """
    production + sqlite -> ValueError.
    """
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.delenv("ALLOW_EPHEMERAL_DB", raising=False)
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="SQLite database_url is not allowed in production"):
        Settings(
            environment="production",
            database_url="sqlite:///./test.db",
            allow_ephemeral_db=False,
        )


def test_f1_production_sqlite_with_allow_ephemeral_starts_and_logs_error(monkeypatch, caplog):
    """
    production + sqlite + ALLOW_EPHEMERAL_DB=true -> starts and logs the ERROR once.
    """
    from backend.app.core import settings as settings_module

    # Reset single-log latch for the test
    settings_module._ephemeral_db_logged = False

    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ALLOW_EPHEMERAL_DB", "true")
    monkeypatch.delenv("VERCEL", raising=False)
    get_settings.cache_clear()

    with caplog.at_level(logging.ERROR, logger="backend.app.core.settings"):
        s = Settings(
            environment="production",
            database_url="sqlite:///./test.db",
            allow_ephemeral_db=True,
        )
        assert s.allow_ephemeral_db is True
        assert s.is_production_like is True

    assert "EPHEMERAL DATABASE: sessions, bookings and handoffs will be lost" in caplog.text


def test_f1_visitor_request_on_empty_corpus_returns_200_without_running_ingest(monkeypatch):
    """
    A visitor request on an empty corpus returns 200 without running ingest.
    The bot answers through the transparent 'no verified knowledge' path.
    """
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    # Create a new session
    session_res = client.post("/api/v1/sessions", json={"tenant": "demo"})
    assert session_res.status_code == 200
    sid = session_res.json()["session_id"]

    # Verify sending a message against empty/un-indexed corpus does not fail or hang
    msg_res = client.post(
        f"/api/v1/sessions/{sid}/messages",
        json={"content": "What is your refund policy?"},
    )
    assert msg_res.status_code == 200
    data = msg_res.json()
    assert "message" in data
    assert data["message"] != ""


def test_f1_one_failing_tenant_ingest_does_not_stop_others(monkeypatch, caplog):
    """
    Wrap per-tenant ingest in try/except so one tenant's error cannot abort the others.
    """
    with SessionLocal() as db:
        with patch("backend.app.rag.ingest.list_tenant_slugs", return_value=["broken_tenant", "demo"]), \
             patch("backend.app.tenants.loader.ensure_tenant_row") as mock_ensure, \
             patch("backend.app.rag.ingest.ingest_tenant") as mock_ingest:


            mock_ensure.side_effect = lambda _db, slug: MagicMock(slug=slug)

            def fake_ingest(_db, tenant):
                if tenant.slug == "broken_tenant":
                    raise RuntimeError("Corrupted tenant metadata")
                return {"documents": 12, "tenant": "demo"}

            mock_ingest.side_effect = fake_ingest

            with caplog.at_level(logging.ERROR):
                results = ingest_all(db)

            # broken_tenant failed and logged exception, but demo succeeded and was returned
            assert len(results) == 1
            assert results[0]["tenant"] == "demo"
            assert "Ingest failed for tenant 'broken_tenant'" in caplog.text


def test_f1_admin_reindex_needs_auth(monkeypatch):
    """
    POST /admin/reindex requires admin authentication (401 without auth, 200 with auth).
    """
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_pass_123")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    # 1. Unauthenticated request -> 401
    resp_unauth = client.post("/admin/reindex")
    assert resp_unauth.status_code == 401

    # 2. Wrong password -> 401
    resp_wrong = client.post("/admin/reindex", auth=("admin", "wrong_password"))
    assert resp_wrong.status_code == 401

    # 3. Valid credentials -> 200
    with patch("backend.app.rag.ingest.ingest_all", return_value=[{"tenant": "demo", "documents": 5}]):
        resp_valid = client.post("/admin/reindex", auth=("admin", "secret_pass_123"))
        assert resp_valid.status_code == 200
        data = resp_valid.json()
        assert data["status"] == "ok"
        assert data["tenants_indexed"] == 1


def test_f1_admin_api_health_reports_persistence_and_public_health_does_not(monkeypatch):
    """
    admin health reports persistence: 'ephemeral' or 'persistent'; public health does not.
    """
    monkeypatch.delenv("VERCEL", raising=False)
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("ADMIN_PASSWORD", "secret_pass_123")
    monkeypatch.setenv("DATABASE_URL", "sqlite:///./test.db")
    get_settings.cache_clear()

    app = create_app()
    client = TestClient(app)

    # Public health does NOT contain 'persistence'
    public_resp = client.get("/health")
    assert public_resp.status_code == 200
    assert "persistence" not in public_resp.json()

    # Admin health contains 'persistence': 'ephemeral' for SQLite
    admin_resp = client.get("/admin/api/health", auth=("admin", "secret_pass_123"))
    assert admin_resp.status_code == 200
    assert admin_resp.json()["persistence"] == "ephemeral"


def test_f1_cors_wildcard_rejected_when_vercel_is_set_even_in_dev_environment(monkeypatch):
    """
    VERCEL=1 + ENVIRONMENT=development + CORS wildcard -> raises ValueError.
    """
    monkeypatch.setenv("VERCEL", "1")
    monkeypatch.setenv("ENVIRONMENT", "development")
    monkeypatch.setenv("CORS_ORIGINS", "*")
    monkeypatch.setenv("ALLOW_EPHEMERAL_DB", "true")
    get_settings.cache_clear()

    with pytest.raises(ValueError, match="Wildcard CORS origin"):
        create_app()
