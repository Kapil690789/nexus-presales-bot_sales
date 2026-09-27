from functools import lru_cache
from pathlib import Path
from typing import Any
from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit
import os

from pydantic import model_validator
from pydantic_settings import (
    BaseSettings,
    DotEnvSettingsSource,
    PydanticBaseSettingsSource,
    SettingsConfigDict,
)

ROOT = Path(__file__).resolve().parents[3]
REPO_ROOT = ROOT.parent
KNOWN_ENVIRONMENTS = ("development", "production")

DEFAULT_CORS_ORIGINS = (
    "http://localhost:8000,http://127.0.0.1:8000,http://localhost:3000"
)
VERCEL_ORIGIN_REGEX = r"https://.*\.vercel\.app"


def resolve_app_path(value: Path | str) -> Path:
    """Resolve relative data dirs against the chat-bot root, not process cwd."""
    path = Path(value)
    if not path.is_absolute():
        path = ROOT / path
    return path.resolve()


def parse_dotenv(path: Path) -> dict[str, str]:
    values: dict[str, str] = {}
    if not path.is_file():
        return values
    for raw in path.read_text(encoding="utf-8").splitlines():
        line = raw.strip()
        if not line or line.startswith("#") or "=" not in line:
            continue
        key, value = line.split("=", 1)
        key = key.strip()
        if not key:
            continue
        values[key] = value.strip().strip("'").strip('"')
    return values


def _dotenv_value(path: Path, key: str) -> str:
    return parse_dotenv(path).get(key, "").strip()


def resolve_environment_name() -> str:
    raw = os.environ.get("ENVIRONMENT")
    if raw is None or not str(raw).strip():
        raw = _dotenv_value(ROOT / ".env", "ENVIRONMENT") or _dotenv_value(
            REPO_ROOT / ".env", "ENVIRONMENT"
        )
    name = (raw or "development").strip().lower()
    if name not in KNOWN_ENVIRONMENTS:
        return "development"
    return name


def settings_env_files() -> tuple[str, ...]:
    """Named env first, then `.env` so local secrets overlay the checklist."""
    environment = resolve_environment_name()
    files: list[str] = []
    for base in (REPO_ROOT, ROOT):
        files.append(str(base / f".env.{environment}"))
        files.append(str(base / ".env"))
    return tuple(files)


def dotenv_search_paths() -> tuple[Path, ...]:
    environment = resolve_environment_name()
    paths: list[Path] = []
    for base in (ROOT, REPO_ROOT):
        paths.append(base / ".env")
        paths.append(base / f".env.{environment}")
        for name in KNOWN_ENVIRONMENTS:
            path = base / f".env.{name}"
            if path not in paths:
                paths.append(path)
    return tuple(paths)


def missing_env_keys(path: Path) -> list[str]:
    return [key for key, value in parse_dotenv(path).items() if not value.strip()]


def print_missing_env_keys() -> None:
    """Print which checklist fields are blank. Never prints secret values."""
    files = (
        ("development", ROOT / ".env.development"),
        ("production", ROOT / ".env.production"),
        ("local overlay", ROOT / ".env"),
        ("website development", REPO_ROOT / "website" / ".env.development"),
        ("website production", REPO_ROOT / "website" / ".env.production"),
    )
    for label, path in files:
        if not path.is_file():
            print(f"{label}: file missing ({path})")
            continue
        parsed = parse_dotenv(path)
        filled = [key for key, value in parsed.items() if value.strip()]
        blank = [key for key, value in parsed.items() if not value.strip()]
        print(f"{label} ({path.name})")
        print(f"  filled: {', '.join(filled) or '(none)'}")
        print(f"  missing: {', '.join(blank) or '(none)'}")


def normalize_database_url(url: str) -> str:
    """Rewrite Neon/libpq URLs so SQLAlchemy uses pg8000.

    Strip ``ssl`` / ``sslmode`` query params. pg8000 1.31+ takes
    ``ssl_context``, and ``ssl=true`` on the URL becomes ``connect(ssl=True)``,
    which raises TypeError and 500s every session.
    """
    url = (url or "").strip()
    if url.startswith("postgresql://"):
        url = "postgresql+pg8000://" + url[len("postgresql://") :]
    elif url.startswith("postgres://"):
        url = "postgresql+pg8000://" + url[len("postgres://") :]
    if not url.startswith("postgresql+pg8000://"):
        return url
    parts = urlsplit(url)
    query = dict(parse_qsl(parts.query, keep_blank_values=True))
    query.pop("channel_binding", None)
    query.pop("sslmode", None)
    query.pop("ssl", None)
    return urlunsplit((parts.scheme, parts.netloc, parts.path, urlencode(query), parts.fragment))


class SkipEmptyDotEnvSettingsSource(DotEnvSettingsSource):
    """Blank checklist fields mean 'missing', not 'set to empty'."""

    def __call__(self) -> dict[str, Any]:
        return {
            key: value
            for key, value in super().__call__().items()
            if value is not None and str(value).strip() != ""
        }


class Settings(BaseSettings):
    model_config = SettingsConfigDict(
        env_file=settings_env_files(),
        env_file_encoding="utf-8",
        extra="ignore",
        case_sensitive=False,
    )

    @classmethod
    def settings_customise_sources(
        cls,
        settings_cls: type[BaseSettings],
        init_settings: PydanticBaseSettingsSource,
        env_settings: PydanticBaseSettingsSource,
        dotenv_settings: PydanticBaseSettingsSource,
        file_secret_settings: PydanticBaseSettingsSource,
    ) -> tuple[PydanticBaseSettingsSource, ...]:
        return (
            init_settings,
            env_settings,
            SkipEmptyDotEnvSettingsSource(settings_cls),
            file_secret_settings,
        )

    environment: str = "development"
    port: int = 8000
    config_dir: Path = ROOT / "config"
    content_dir: Path = ROOT / "content"
    database_url: str = "sqlite:///./backend/presales.db"
    admin_username: str = "admin"
    admin_password: str = ""
    admin_password_hash: str = ""
    cors_origins: str = DEFAULT_CORS_ORIGINS
    cors_origin_regex: str = ""
    upload_dir: Path = ROOT / "backend" / "uploads"
    gcs_bucket: str = ""
    gcs_prefix: str = "rfp/"
    llm_provider: str = "openai"
    llm_api_key: str = ""
    llm_model: str = "gemini-3.8-flash"
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
    def normalize_runtime_urls(self):
        object.__setattr__(self, "database_url", normalize_database_url(self.database_url))
        object.__setattr__(self, "config_dir", resolve_app_path(self.config_dir))
        object.__setattr__(self, "content_dir", resolve_app_path(self.content_dir))
        object.__setattr__(self, "upload_dir", resolve_app_path(self.upload_dir))
        redirect = self.google_redirect_uri.strip()
        public = self.public_base_url.strip().rstrip("/")
        if not redirect and public:
            object.__setattr__(self, "google_redirect_uri", f"{public}/admin/google/callback")
        else:
            object.__setattr__(self, "google_redirect_uri", redirect)
        return self

    @model_validator(mode="after")
    def blank_llm_key_does_not_mask(self):
        env = os.environ.get("LLM_API_KEY")
        if env is not None:
            object.__setattr__(self, "llm_api_key", env.strip())
            return self
        if self.llm_api_key.strip():
            return self
        for path in dotenv_search_paths():
            value = _dotenv_value(path, "LLM_API_KEY")
            if value:
                object.__setattr__(self, "llm_api_key", value)
                return self
        return self

    @property
    def explicit_cors_origins(self) -> list[str]:
        return [part.strip() for part in self.cors_origins.split(",") if part.strip()]

    @property
    def cors_origin_list(self) -> list[str]:
        parts = self.explicit_cors_origins
        if not parts and not self.cors_origin_regex.strip():
            parts = [part.strip() for part in DEFAULT_CORS_ORIGINS.split(",") if part.strip()]
        public = self.public_base_url.strip().rstrip("/")
        if public and public not in parts:
            parts = [*parts, public]
        return parts

    @property
    def effective_cors_origin_regex(self) -> str:
        pattern = self.cors_origin_regex.strip()
        if pattern:
            return pattern
        if self.environment.strip().lower() == "production":
            return VERCEL_ORIGIN_REGEX
        if self.explicit_cors_origins:
            return ""
        return VERCEL_ORIGIN_REGEX


@lru_cache
def get_settings() -> Settings:
    return Settings()
