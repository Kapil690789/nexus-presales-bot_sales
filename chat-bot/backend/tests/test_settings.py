from backend.app.core.settings import ROOT, Settings, VERCEL_ORIGIN_REGEX, normalize_database_url


def test_normalize_neon_libpq_url() -> None:
    raw = (
        "postgresql://neondb_owner:secret@ep-host.neon.tech/neondb"
        "?sslmode=require&channel_binding=require"
    )
    assert (
        normalize_database_url(raw)
        == "postgresql+pg8000://neondb_owner:secret@ep-host.neon.tech/neondb?ssl=true"
    )


def test_normalize_postgres_scheme() -> None:
    assert (
        normalize_database_url("postgres://u:p@host/db")
        == "postgresql+pg8000://u:p@host/db"
    )


def test_normalize_already_pg8000_strips_channel_binding() -> None:
    raw = "postgresql+pg8000://u:p@host/db?ssl=true&channel_binding=require"
    assert normalize_database_url(raw) == "postgresql+pg8000://u:p@host/db?ssl=true"


def test_normalize_sqlite_unchanged() -> None:
    url = "sqlite:///./backend/presales.db"
    assert normalize_database_url(url) == url


def test_settings_rewrites_database_url() -> None:
    settings = Settings(
        database_url="postgresql://u:p@host/db?sslmode=require&channel_binding=require"
    )
    assert settings.database_url == "postgresql+pg8000://u:p@host/db?ssl=true"


def test_google_redirect_falls_back_to_public_base_url() -> None:
    settings = Settings(
        google_redirect_uri="",
        public_base_url="https://bot.example.com/",
    )
    assert settings.google_redirect_uri == "https://bot.example.com/admin/google/callback"


def test_google_redirect_keeps_explicit_value() -> None:
    settings = Settings(
        google_redirect_uri="http://localhost:8000/admin/google/callback",
        public_base_url="https://bot.example.com",
    )
    assert settings.google_redirect_uri == "http://localhost:8000/admin/google/callback"


def test_relative_data_dirs_resolve_against_root() -> None:
    settings = Settings(config_dir="./config", content_dir="./content", upload_dir="backend/uploads")
    assert settings.config_dir == (ROOT / "config").resolve()
    assert settings.content_dir == (ROOT / "content").resolve()
    assert settings.upload_dir == (ROOT / "backend" / "uploads").resolve()
    assert (settings.config_dir / "brand.yaml").is_file()


def test_absolute_upload_dir_is_kept() -> None:
    settings = Settings(upload_dir="/tmp/uploads")
    assert settings.upload_dir.is_absolute()
    assert settings.upload_dir.as_posix().endswith("/tmp/uploads")


def test_empty_cors_falls_back_to_localhost_and_vercel() -> None:
    settings = Settings(cors_origins="", cors_origin_regex="")
    assert "http://localhost:3000" in settings.cors_origin_list
    assert "http://localhost:8000" in settings.cors_origin_list
    assert settings.effective_cors_origin_regex == VERCEL_ORIGIN_REGEX


def test_production_applies_vercel_regex_even_with_localhost_origins() -> None:
    settings = Settings(
        environment="production",
        cors_origins="http://localhost:8000",
        cors_origin_regex="",
        public_base_url="https://dummy-chat-bot-6w6p.vercel.app",
        admin_password="a-strong-unique-password",
    )
    assert "http://localhost:8000" in settings.cors_origin_list
    assert "https://dummy-chat-bot-6w6p.vercel.app" in settings.cors_origin_list
    assert settings.effective_cors_origin_regex == VERCEL_ORIGIN_REGEX
