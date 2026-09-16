import os

os.environ.setdefault("DATABASE_URL", "sqlite:///./backend/test-presales.db")
os.environ.setdefault("LLM_API_KEY", "")
os.environ.setdefault("ADMIN_PASSWORD", "test-admin")
os.environ.setdefault("CORS_ORIGINS", "*")
os.environ.setdefault("ENVIRONMENT", "development")

from collections.abc import Generator

import pytest
from fastapi.testclient import TestClient

from backend.app.core.settings import get_settings
from backend.app.models.db import Base, engine, init_db


@pytest.fixture(scope="session", autouse=True)
def _db() -> Generator[None, None, None]:
    get_settings.cache_clear()
    init_db()
    yield
    Base.metadata.drop_all(bind=engine)


@pytest.fixture(autouse=True)
def _reset_rate_limit() -> None:
    from backend.app.core.security import _hits

    _hits.clear()


@pytest.fixture
def client() -> TestClient:
    from backend.app.main import app

    return TestClient(app)
