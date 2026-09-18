import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./backend/test-presales.db")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("ENVIRONMENT", "development")
os.environ["GOOGLE_REFRESH_TOKEN"] = ""
os.environ["SLACK_WEBHOOK_URL"] = ""
os.environ["PUBLIC_BASE_URL"] = ""

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.config_loader.loader import get_config
from backend.app.core.settings import get_settings
from backend.app.models.db import Base, engine, init_db


@pytest.fixture(scope="session", autouse=True)
def _db() -> Generator[None, None, None]:
    get_settings.cache_clear()
    get_config.cache_clear()
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> Generator[None, None, None]:
    from backend.app.core.security import _failed_admin, _hits
    from backend.app.core.settings import get_settings

    _hits.clear()
    _failed_admin.clear()
    get_settings.cache_clear()
    yield
    get_settings.cache_clear()


@pytest.fixture(autouse=True)
def _reset_calendar() -> Generator[None, None, None]:
    from backend.app.engines.google_client import set_google_client
    from backend.app.models.db import SessionLocal
    from backend.app.models.entities import CalendarCredentialRow

    set_google_client(None)
    yield
    set_google_client(None)
    with SessionLocal() as db:
        row = db.get(CalendarCredentialRow, "default")
        if row:
            db.delete(row)
            db.commit()


@pytest.fixture
def client() -> TestClient:
    from backend.app.main import app

    return TestClient(app)
