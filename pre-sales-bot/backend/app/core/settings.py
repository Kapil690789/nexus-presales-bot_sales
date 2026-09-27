from __future__ import annotations

import os
from functools import lru_cache
from pathlib import Path
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
DEFAULT_SQLITE_URL = "sqlite:///./backend/presales.db"
VERCEL_SQLITE_URL = "sqlite:////tmp/presales.db"


def uploads_root() -> Path:
    if os.environ.get("VERCEL"):
        return Path("/tmp/presales-uploads")
    return ROOT / "backend" / "uploads"


def normalize_database_url(url: str) -> str:
    """Use pg8000 for Postgres and drop libpq SSL query params.

    pg8000 1.31+ rejects ``connect(ssl=True)``. ``ssl=true`` on the URL becomes
    that call and raises TypeError. TLS is applied with ``ssl_context`` instead.
    """
    url = (url or "").strip()
    if url.startswith("postgresql://"):
        url = "postgresql+pg8000://" + url[len("postgresql://") :]
    elif url.startswith("postgres://"):
        url = "postgresql+pg8000://" + url[len("postgres://") :]
    if url.startswith("postgresql+pg8000://"):
        parts = urlsplit(url)
        query = dict(parse_qsl(parts.query, keep_blank_values=True))
        query.pop("channel_binding", None)
        query.pop("sslmode", None)
        query.pop("ssl", None)
        return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))
    if os.environ.get("VERCEL") and url == DEFAULT_SQLITE_URL:
        return VERCEL_SQLITE_URL
    return url


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=str(ROOT / ".env"),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    port: int = 8010
    database_url: str = DEFAULT_SQLITE_URL
    admin_username: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    cors_origins: str = "http://localhost:8010,http://127.0.0.1:8010"
    llm_provider: str = "gemini"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
    llm_base_url: str = ""
    embedding_backend: str = "auto"
    embedding_model: str = "BAAI/bge-small-en-v1.5"
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8010/admin/google/callback"
    google_refresh_token: str = ""
    slack_webhook_url: str = ""
    public_base_url: str = ""
    message_rate_limit: int = 20
    message_rate_window_seconds: int = 60
    llm_calls_per_session: int = 24
    llm_calls_per_ip_per_hour: int = 60

    @model_validator(mode="after")
    def apply_database_url(self):
        self.database_url = normalize_database_url(self.database_url)
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        parts = [item.strip() for item in (self.cors_origins or "").split(",") if item.strip()]
        return parts or ["http://localhost:8010"]


@lru_cache
def get_settings() -> Settings:
    return Settings()
