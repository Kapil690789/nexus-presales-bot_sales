from functools import lru_cache
from pathlib import Path

from pydantic_settings import BaseSettings, SettingsConfigDict

ROOT = Path(__file__).resolve().parents[3]


class Settings(BaseSettings):
    model_config = SettingsConfigDict(env_file=str(ROOT / ".env"), env_file_encoding="utf-8", extra="ignore")

    environment: str = "development"
    port: int = 8000
    config_dir: Path = ROOT / "config"
    database_url: str = "sqlite:///./backend/presales.db"
    admin_password: str = "northline-admin"
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

    @property
    def cors_origin_list(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]


@lru_cache
def get_settings() -> Settings:
    return Settings()
