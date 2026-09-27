import os
import shutil
from pathlib import Path

ROOT = Path(__file__).resolve().parents[2]
DB_PATH = ROOT / "backend" / "test-presales.db"
os.environ["DATABASE_URL"] = f"sqlite:///{DB_PATH}"
os.environ["EMBEDDING_BACKEND"] = "hash"
os.environ["LLM_API_KEY"] = ""
os.environ["ADMIN_PASSWORD"] = "test-admin"
os.environ["ADMIN_USERNAME"] = "admin"
os.environ["ENVIRONMENT"] = "test"
os.environ["GOOGLE_CLIENT_ID"] = ""
os.environ["GOOGLE_CLIENT_SECRET"] = ""
os.environ["GOOGLE_REFRESH_TOKEN"] = ""
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ.pop("CORS_ORIGINS", None)

if DB_PATH.exists():
    DB_PATH.unlink()

import pytest
from fastapi.testclient import TestClient

from backend.app.core.settings import get_settings
from backend.app.models.db import Base, engine, init_db


@pytest.fixture(scope="session", autouse=True)
def _db():
    get_settings.cache_clear()
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)
    engine.dispose()
    if DB_PATH.exists():
        DB_PATH.unlink()


@pytest.fixture(autouse=True)
def _clear_settings():
    from backend.app.core.security import _failed_admin, _llm_ip_hits, _llm_session_counts, _message_hits

    _failed_admin.clear()
    _message_hits.clear()
    _llm_session_counts.clear()
    _llm_ip_hits.clear()
    from backend.app.models import db as dbmod

    dbmod._ready = False
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture
def client():
    from backend.app.main import app

    with TestClient(app) as test_client:
        yield test_client


@pytest.fixture
def auth():
    return ("admin", "test-admin")


def cleanup_tenant(slug: str) -> None:
    folder = ROOT / "tenants" / slug
    if folder.exists() and slug != "demo":
        shutil.rmtree(folder)
