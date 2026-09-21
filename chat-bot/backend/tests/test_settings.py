from backend.app.core.settings import Settings, normalize_database_url


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
