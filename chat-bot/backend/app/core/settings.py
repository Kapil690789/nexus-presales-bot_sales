from functools import lru_cache
from pathlib import Path
import os

from pydantic import model_validator
from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parent


def _dotenv_value(path: Path, key: str) -> str:
    if not path.is_file():
        return ""
    prefix = f"{key}="
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or not line.upper().startswith(prefix.upper()):
            continue
        value = line.split("=", 1)[1].strip().strip("'").strip('"')
        return value.strip()
    return ""


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=(str(REPO_ROOT / ".env"), str(ROOT / ".env")),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    environment: str = "development"
    port: int = 8000
    config_dir: Path = ROOT / "config"
    content_dir: Path = ROOT / "content"
    database_url: str = "sqlite:///./backend/presales.db"
    admin_username: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    cors_origins: str = "http://localhost:8000,http://127.0.0.1:8000"
    upload_dir: Path = ROOT / "backend" / "uploads"
    gcs_bucket: str = ""
    gcs_prefix: str = "rfp/"
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.6-flash"
    llm_base_url: str = ""
    rag_enabled: bool = True
    rag_backend: str = "auto"  # auto | pgvector | fallback
    embedding_model: str = ""
    learning_enabled: bool = True
    google_client_id: str = ""
    google_client_secret: str = ""
    google_redirect_uri: str = "http://localhost:8000/admin/google/callback"
    google_refresh_token: str = ""
    google_calendar_id: str = "primary"
    slack_webhook_url: str = ""
    public_base_url: str = ""

    @model_validator(mode="after")
    def blank_llm_key_does_not_mask(self):
        env = os.environ.get("LLM_API_KEY")
        if env is not None:
            object.__setattr__(self, "llm_api_key", env.strip())
            return self
        if self.llm_api_key.strip():
            return self
        for path in (ROOT / ".env", REPO_ROOT / ".env"):
            value = _dotenv_value(path, "LLM_API_KEY")
            if value:
                object.__setattr__(self, "llm_api_key", value)
                return self
        return self

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
