from __future__ import annotations

import secrets
from collections import defaultdict
from contextvars import ContextVar, Token
from time import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.app.core.settings import Settings, get_settings

basic = HTTPBasic()
_failed_admin: dict[str, list[float]] = defaultdict(list)
_message_hits: dict[str, list[float]] = defaultdict(list)
_llm_session_counts: dict[str, int] = defaultdict(int)
_llm_ip_hits: dict[str, list[float]] = defaultdict(list)
_llm_actor: ContextVar[tuple[str, str] | None] = ContextVar("llm_actor", default=None)
DEFAULT_ADMIN_PASSWORDS = frozenset({"admin", "password", "admin123", "northline-admin"})
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


def assert_admin_configured(settings: Settings | None = None) -> None:
    settings = settings or get_settings()
    if settings.environment.strip().lower() != "production":
        return
    if settings.admin_password_hash.strip():
        return
    password = settings.admin_password.strip()
    if not password or password.lower() in DEFAULT_ADMIN_PASSWORDS:
        raise RuntimeError("Set a non-default ADMIN_PASSWORD or ADMIN_PASSWORD_HASH in production.")


def require_admin(
    request: Request,
    credentials: HTTPBasicCredentials = Depends(basic),
) -> str:
    settings = get_settings()
    ip = request.client.host if request.client else "unknown"
    now = time()
    failures = [stamp for stamp in _failed_admin[ip] if now - stamp < ADMIN_LOCKOUT_WINDOW]
    if len(failures) >= ADMIN_LOCKOUT_LIMIT:
        _failed_admin[ip] = failures
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed admin logins.")
    username_ok = _digest_equal(credentials.username, settings.admin_username)
    if not username_ok or not password_matches(credentials.password, settings):
        failures.append(now)
        _failed_admin[ip] = failures
        raise HTTPException(
            status_code=status.HTTP_401_UNAUTHORIZED,
            detail="Invalid admin credentials.",
            headers={"WWW-Authenticate": "Basic"},
        )
    _failed_admin[ip] = []
    return credentials.username


def client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def rate_limit_messages(request: Request) -> None:
    settings = get_settings()
    ip = client_ip(request)
    now = time()
    window = settings.message_rate_window_seconds
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
    recent = [stamp for stamp in _llm_ip_hits[ip] if now - stamp < LLM_IP_WINDOW]
    over_session = _llm_session_counts[session_id] >= settings.llm_calls_per_session
    over_ip = len(recent) >= settings.llm_calls_per_ip_per_hour
    if over_session or over_ip:
        _llm_ip_hits[ip] = recent
        return False
    _llm_session_counts[session_id] += 1
    recent.append(now)
    _llm_ip_hits[ip] = recent
    return True
