from __future__ import annotations

import hashlib
import logging
import secrets
from collections import defaultdict
from contextvars import ContextVar, Token
from time import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.app.core.settings import Settings, get_settings

log = logging.getLogger(__name__)

basic = HTTPBasic()


class _SyncDict(defaultdict):
    def clear(self):
        super().clear()
        try:
            from backend.app.models.db import get_engine
            from sqlalchemy import text
            with get_engine().begin() as conn:
                conn.execute(text("DELETE FROM rate_limits"))
        except Exception:
            pass


_failed_admin: dict[str, list[float]] = _SyncDict(list)
_message_hits: dict[str, list[float]] = _SyncDict(list)
_llm_session_counts: dict[str, int] = _SyncDict(int)
_llm_ip_hits: dict[str, list[float]] = _SyncDict(list)
_llm_actor: ContextVar[tuple[str, str] | None] = ContextVar("llm_actor", default=None)
DEFAULT_ADMIN_PASSWORDS = frozenset({"admin", "password", "admin123", "nexus-admin"})
ADMIN_LOCKOUT_LIMIT = 5
ADMIN_LOCKOUT_WINDOW = 15 * 60
LLM_IP_WINDOW = 60 * 60
MESSAGE_LIMIT_DETAIL = "Too many messages. Please wait a moment."


def _digest_equal(left: str, right: str) -> bool:
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        secrets.compare_digest(a, a)
        return False
    return secrets.compare_digest(a, b)


def password_matches(password: str, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    hashed = settings.admin_password_hash.strip()
    if hashed:
        try:
            import bcrypt
        except ImportError:
            return False
        try:
            return bcrypt.checkpw(password.encode("utf-8"), hashed.encode("utf-8"))
        except (ValueError, TypeError):
            return False
    expected = settings.admin_password
    if not expected:
        return False
    return _digest_equal(password, expected)


def is_admin_misconfigured(settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    if not settings.is_production_like:
        return False
    if settings.admin_password_hash.strip():
        return False
    password = settings.admin_password.strip()
    return not password or password.lower() in DEFAULT_ADMIN_PASSWORDS


def assert_admin_configured(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.admin_password_hash.strip():
        return
    password = settings.admin_password.strip()
    if not password or password.lower() in DEFAULT_ADMIN_PASSWORDS:
        raise RuntimeError("Set a non-default ADMIN_PASSWORD or ADMIN_PASSWORD_HASH.")


def assert_ip_salt_configured(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.is_production_like and (not settings.ip_hash_salt or settings.ip_hash_salt == "default-salt-pre-sales"):
        raise RuntimeError("IP_HASH_SALT required in production-like environments.")


def hash_ip(ip: str, settings: Settings | None = None) -> str:
    settings = settings or get_settings()
    salt = (settings.ip_hash_salt or "").strip() or "default-salt-pre-sales"
    return hashlib.sha256(f"{salt}:{ip}".encode("utf-8")).hexdigest()


_table_ensured = False


def _ensure_rate_limits_table():
    global _table_ensured
    if _table_ensured:
        return
    try:
        from backend.app.models.db import get_engine
        from backend.app.models.entities import RateLimitRow

        RateLimitRow.__table__.create(bind=get_engine(), checkfirst=True)
        _table_ensured = True
    except Exception:
        pass


def _atomic_upsert_rate_limit(key_hash: str, window_seconds: float) -> tuple[int, float]:
    """Atomically insert or update the rate limit bucket for key_hash within window_seconds.

    Works on SQLite and PostgreSQL.
    Prunes rows older than 24h.
    """
    _ensure_rate_limits_table()
    from backend.app.models.db import get_engine
    from sqlalchemy import text

    now = time()
    cutoff = now - 86400.0  # 24 hours
    engine = get_engine()

    upsert_sql = text(
        """
        INSERT INTO rate_limits (key_hash, window_start, count)
        VALUES (:key_hash, :now, 1)
        ON CONFLICT (key_hash) DO UPDATE SET
            count = CASE
                WHEN rate_limits.window_start < (:now - :window) THEN 1
                ELSE rate_limits.count + 1
            END,
            window_start = CASE
                WHEN rate_limits.window_start < (:now - :window) THEN :now
                ELSE rate_limits.window_start
            END
        """
    )
    select_sql = text("SELECT count, window_start FROM rate_limits WHERE key_hash = :key_hash")
    prune_sql = text("DELETE FROM rate_limits WHERE window_start < :cutoff")

    with engine.begin() as conn:
        conn.execute(upsert_sql, {"key_hash": key_hash, "now": now, "window": window_seconds})
        row = conn.execute(select_sql, {"key_hash": key_hash}).fetchone()
        conn.execute(prune_sql, {"cutoff": cutoff})
        if row:
            return int(row[0]), float(row[1])
        return 1, now


def _get_rate_limit(key_hash: str, window_seconds: float) -> tuple[int, float]:
    """Retrieve current count and window_start without incrementing."""
    _ensure_rate_limits_table()
    from backend.app.models.db import get_engine
    from sqlalchemy import text

    now = time()
    engine = get_engine()
    select_sql = text("SELECT count, window_start FROM rate_limits WHERE key_hash = :key_hash")
    with engine.connect() as conn:
        row = conn.execute(select_sql, {"key_hash": key_hash}).fetchone()
        if not row:
            return 0, now
        count, window_start = int(row[0]), float(row[1])
        if now - window_start >= window_seconds:
            return 0, now
        return count, window_start


def _reset_rate_limit(key_hash: str) -> None:
    _ensure_rate_limits_table()
    from backend.app.models.db import get_engine
    from sqlalchemy import text

    engine = get_engine()
    with engine.begin() as conn:
        conn.execute(text("DELETE FROM rate_limits WHERE key_hash = :key_hash"), {"key_hash": key_hash})


def client_ip(request: Request) -> str:
    xff = request.headers.get("x-forwarded-for")
    if xff:
        return xff.split(",")[0].strip()
    return request.client.host if request.client else "unknown"


def current_actor() -> tuple[str, str] | None:
    return _llm_actor.get()


def current_ip() -> str:
    actor = _llm_actor.get()
    return actor[1] if actor else "127.0.0.1"


def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(basic),
) -> str:
    settings = get_settings()
    ip = client_ip(request)
    now = time()
    key_hash = hash_ip(f"admin:{ip}", settings)

    try:
        fail_count, _ = _get_rate_limit(key_hash, ADMIN_LOCKOUT_WINDOW)
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        # Fail CLOSED for admin login
        raise HTTPException(
            status_code=status.HTTP_429_TOO_MANY_REQUESTS,
            detail="Too many failed admin logins.",
        )

    mem_failures = [stamp for stamp in _failed_admin[ip] if now - stamp < ADMIN_LOCKOUT_WINDOW]
    if fail_count >= ADMIN_LOCKOUT_LIMIT or len(mem_failures) >= ADMIN_LOCKOUT_LIMIT:
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed admin logins.")

    username_ok = _digest_equal(credentials.username, settings.admin_username)
    if not username_ok or not password_matches(credentials.password, settings):
        mem_failures.append(now)
        _failed_admin[ip] = mem_failures
        try:
            _atomic_upsert_rate_limit(key_hash, ADMIN_LOCKOUT_WINDOW)
        except Exception as exc:
            log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )

    _failed_admin[ip] = []
    try:
        _reset_rate_limit(key_hash)
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
    return credentials.username


def rate_limit_messages(request: Request) -> None:
    settings = get_settings()
    ip = client_ip(request)
    now = time()
    window = settings.message_rate_window_seconds
    key_hash = hash_ip(f"msg:{ip}", settings)

    try:
        count, _ = _atomic_upsert_rate_limit(key_hash, window)
        if count > settings.message_rate_limit:
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=MESSAGE_LIMIT_DETAIL)
    except HTTPException:
        raise
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        # Fallback to in-process memory when DB fails (fail open)
        bucket = [stamp for stamp in _message_hits[ip] if now - stamp < window]
        if len(bucket) >= settings.message_rate_limit:
            _message_hits[ip] = bucket
            raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail=MESSAGE_LIMIT_DETAIL)
        bucket.append(now)
        _message_hits[ip] = bucket


def bind_llm_actor(session_id: str, ip: str) -> Token:
    return _llm_actor.set((session_id, ip))


def reset_llm_actor(token: Token) -> None:
    _llm_actor.reset(token)


def allow_llm_call() -> bool:
    """Reserve one model call for the current request. Unscoped callers are not counted."""
    actor = _llm_actor.get()
    if actor is None:
        return True
    session_id, ip = actor
    settings = get_settings()
    now = time()

    if _llm_session_counts.get(session_id, 0) >= settings.llm_calls_per_session:
        return False
    recent_mem = [stamp for stamp in _llm_ip_hits[ip] if now - stamp < LLM_IP_WINDOW]
    if len(recent_mem) >= settings.llm_calls_per_ip_per_hour:
        _llm_ip_hits[ip] = recent_mem
        return False

    sess_key = hash_ip(f"llm_sess:{session_id}", settings)
    ip_key = hash_ip(f"llm_ip:{ip}", settings)

    try:
        sess_count, _ = _get_rate_limit(sess_key, 86400.0)
        ip_count, _ = _get_rate_limit(ip_key, LLM_IP_WINDOW)
        if sess_count >= settings.llm_calls_per_session or ip_count >= settings.llm_calls_per_ip_per_hour:
            return False
        _atomic_upsert_rate_limit(sess_key, 86400.0)
        _atomic_upsert_rate_limit(ip_key, LLM_IP_WINDOW)
        _llm_session_counts[session_id] += 1
        recent_mem.append(now)
        _llm_ip_hits[ip] = recent_mem
        return True
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        _llm_session_counts[session_id] += 1
        recent_mem.append(now)
        _llm_ip_hits[ip] = recent_mem
        return True


def check_booking_ip_limit(ip: str, settings: Settings | None = None) -> tuple[int, bool]:
    """Check if the given IP is within the daily booking cap (default 3 per 24h)."""
    settings = settings or get_settings()
    key_hash = hash_ip(f"book_ip:{ip}", settings)
    try:
        count, _ = _get_rate_limit(key_hash, 86400.0)
        return count, count < settings.max_bookings_per_ip_per_day
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        return 0, True


def record_booking_for_ip(ip: str, settings: Settings | None = None) -> int:
    """Record a new confirmed booking for the given IP in the 24h window."""
    settings = settings or get_settings()
    key_hash = hash_ip(f"book_ip:{ip}", settings)
    try:
        count, _ = _atomic_upsert_rate_limit(key_hash, 86400.0)
        return count
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        return 1


def check_email_submission_limit(session_id: str, settings: Settings | None = None) -> tuple[int, bool]:
    """Check and record email submission count for this session (max 5)."""
    settings = settings or get_settings()
    key_hash = hash_ip(f"email_sub:{session_id}", settings)
    try:
        count, _ = _atomic_upsert_rate_limit(key_hash, 86400.0)
        return count, count <= settings.max_email_submissions_per_session
    except Exception as exc:
        log.warning("Rate limit DB error: %s", exc.__class__.__name__)
        return 1, True

