import bcrypt
import pytest
from fastapi.testclient import TestClient

from backend.app.core.security import ADMIN_LOCKOUT_LIMIT, assert_admin_configured, password_matches
from backend.app.core.settings import Settings, get_settings
from backend.app.models.db import SessionLocal
from backend.app.models.entities import SessionRow
from backend.tests.test_api import accept_nda, nda_version


def test_production_refuses_default_password(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    monkeypatch.setenv("ADMIN_PASSWORD", "northline-admin")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        assert_admin_configured(get_settings())
    monkeypatch.setenv("ADMIN_PASSWORD", "")
    get_settings.cache_clear()
    with pytest.raises(RuntimeError):
        assert_admin_configured(get_settings())
    monkeypatch.setenv("ADMIN_PASSWORD", "a-strong-unique-password")
    get_settings.cache_clear()
    assert_admin_configured(get_settings())


def test_password_hash_is_preferred() -> None:
    hashed = bcrypt.hashpw(b"hashed-secret", bcrypt.gensalt()).decode()
    settings = Settings(admin_password="ignored-plaintext", admin_password_hash=hashed)
    assert password_matches("hashed-secret", settings)
    assert not password_matches("ignored-plaintext", settings)
    assert not password_matches("wrong", settings)


def test_admin_lockout_after_repeated_failures(client) -> None:
    for _ in range(ADMIN_LOCKOUT_LIMIT):
        assert client.get("/api/v1/admin/leads", auth=("admin", "nope")).status_code == 401
    locked = client.get("/api/v1/admin/leads", auth=("admin", "nope"))
    assert locked.status_code == 429
    still = client.get("/api/v1/admin/leads", auth=("admin", "test-admin"))
    assert still.status_code == 429


def test_nda_requires_current_version(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/"}).json()["session_id"]
    missing = client.post(f"/api/v1/sessions/{session_id}/nda")
    assert missing.status_code == 422
    wrong = accept_nda(client, session_id, version="1999-01-1")
    assert wrong.status_code == 409
    ok = accept_nda(client, session_id)
    assert ok.status_code == 200
    assert ok.json()["nda_accepted"] is True
    with SessionLocal() as db:
        row = db.get(SessionRow, session_id)
        assert row is not None
        assert row.nda_accepted is True
        assert row.nda_version == nda_version()
        assert row.nda_accepted_at is not None
        assert row.nda_ip
        assert row.nda_user_agent


def test_unknown_origin_is_forbidden(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8000")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", "")
    get_settings.cache_clear()
    try:
        from backend.app.main import app

        local = TestClient(app)
        blocked = local.post("/api/v1/sessions", json={"path": "/"}, headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        allowed = local.post("/api/v1/sessions", json={"path": "/"}, headers={"Origin": "http://localhost:8000"})
        assert allowed.status_code == 200
    finally:
        get_settings.cache_clear()


def test_cors_origin_regex_allows_vercel(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", r"https://.*\.vercel\.app")
    get_settings.cache_clear()
    try:
        from backend.app.main import app

        local = TestClient(app)
        blocked = local.post("/api/v1/sessions", json={"path": "/"}, headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        allowed = local.post(
            "/api/v1/sessions",
            json={"path": "/"},
            headers={"Origin": "https://devconsult-site.vercel.app"},
        )
        assert allowed.status_code == 200
    finally:
        get_settings.cache_clear()


def test_production_localhost_cors_still_allows_vercel_chat(monkeypatch) -> None:
    monkeypatch.setenv("ENVIRONMENT", "production")
    monkeypatch.setenv("ADMIN_PASSWORD", "a-strong-unique-password")
    monkeypatch.setenv("ADMIN_PASSWORD_HASH", "")
    monkeypatch.setenv("CORS_ORIGINS", "http://localhost:8000")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", "")
    get_settings.cache_clear()
    try:
        from backend.app.main import create_app

        local = TestClient(create_app())
        blocked = local.post("/api/v1/sessions", json={"path": "/"}, headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        site = local.post(
            "/api/v1/sessions",
            json={"path": "/"},
            headers={"Origin": "https://dummy-web-portal-ten.vercel.app"},
        )
        assert site.status_code == 200
        bot = local.post(
            "/api/v1/sessions",
            json={"path": "/"},
            headers={
                "Origin": "https://dummy-chat-bot-6w6p.vercel.app",
                "Host": "dummy-chat-bot-6w6p.vercel.app",
                "X-Forwarded-Proto": "https",
            },
        )
        assert bot.status_code == 200
    finally:
        get_settings.cache_clear()


def test_empty_cors_allows_localhost_and_vercel(monkeypatch) -> None:
    monkeypatch.setenv("CORS_ORIGINS", "")
    monkeypatch.setenv("CORS_ORIGIN_REGEX", "")
    get_settings.cache_clear()
    try:
        from backend.app.main import create_app

        local = TestClient(create_app())
        blocked = local.post("/api/v1/sessions", json={"path": "/"}, headers={"Origin": "https://evil.example"})
        assert blocked.status_code == 403
        vercel = local.post(
            "/api/v1/sessions",
            json={"path": "/"},
            headers={"Origin": "https://dummy-web-portal-ten.vercel.app"},
        )
        assert vercel.status_code == 200
        site = local.post(
            "/api/v1/sessions",
            json={"path": "/"},
            headers={"Origin": "http://localhost:3000"},
        )
        assert site.status_code == 200
    finally:
        get_settings.cache_clear()


def test_health_survives_init_db_failure(monkeypatch) -> None:
    def boom() -> None:
        raise OSError("read-only filesystem")

    monkeypatch.setattr("backend.app.main.init_db", boom)
    from backend.app.main import create_app

    with TestClient(create_app()) as local:
        body = local.get("/health").json()
        assert body["ok"] is True
        assert "brand" in local.get("/api/v1/public-config").json()


def test_message_and_upload_limits(client) -> None:
    session_id = client.post("/api/v1/sessions", json={"path": "/"}).json()["session_id"]
    too_long = client.post(f"/api/v1/sessions/{session_id}/messages", json={"content": "x" * 4001})
    assert too_long.status_code == 400
    assert accept_nda(client, session_id).status_code == 200
    empty = client.post(
        f"/api/v1/sessions/{session_id}/documents",
        files={"file": ("empty.txt", b"", "text/plain")},
        data={"nda_accepted": "true", "nda_version": nda_version()},
    )
    assert empty.status_code == 400
