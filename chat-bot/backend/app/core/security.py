import secrets
from collections import defaultdict
from time import time

import bcrypt
from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.app.core.settings import Settings, get_settings

basic = HTTPBasic()
_hits: dict[str, list[float]] = defaultdict(list)
_failed_admin: dict[str, list[float]] = defaultdict(list)

DEFAULT_ADMIN_PASSWORDS = frozenset({"northline-admin", "admin123", "admin", "password"})
ADMIN_LOCKOUT_LIMIT = 5
ADMIN_LOCKOUT_WINDOW = 15 * 60


def _digest_equal(left: str, right: str) -> bool:
    a = left.encode("utf-8")
    b = right.encode("utf-8")
    if len(a) != len(b):
        secrets.compare_digest(a, a)
        return False
    return secrets.compare_digest(a, b)


def _client_ip(request: Request) -> str:
    return request.client.host if request.client else "unknown"


def client_ip(request: Request) -> str:
    return _client_ip(request)


def client_user_agent(request: Request) -> str:
    return (request.headers.get("user-agent") or "")[:300]


def password_matches(password: str, settings: Settings | None = None) -> bool:
    settings = settings or get_settings()
    hashed = settings.admin_password_hash.strip()
    if hashed:
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
    ip = _client_ip(request)
    now = time()
    failures = [stamp for stamp in _failed_admin[ip] if now - stamp < ADMIN_LOCKOUT_WINDOW]
    if len(failures) >= ADMIN_LOCKOUT_LIMIT:
        _failed_admin[ip] = failures
        raise HTTPException(status_code=status.HTTP_429_TOO_MANY_REQUESTS, detail="Too many failed admin logins.")
    username_ok = _digest_equal(credentials.username, settings.admin_username)
    if not username_ok or not password_matches(credentials.password, settings):
        failures.append(now)
        _failed_admin[ip] = failures
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    _failed_admin[ip] = []
    return credentials.username


def rate_limit(request: Request, limit: int = 40, window: int = 60) -> None:
    ip = _client_ip(request)
    now = time()
    bucket = [stamp for stamp in _hits[ip] if now - stamp < window]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    bucket.append(now)
    _hits[ip] = bucket


def origin_allowed(request: Request) -> None:
    settings = get_settings()
    origins = settings.cors_origin_list
    if "*" in origins:
        return
    origin = request.headers.get("origin") or ""
    if origin and origin not in origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")
