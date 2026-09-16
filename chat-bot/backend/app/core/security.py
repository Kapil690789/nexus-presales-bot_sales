import secrets
from collections import defaultdict
from time import time

from fastapi import Depends, HTTPException, Request, status
from fastapi.security import HTTPBasic, HTTPBasicCredentials

from backend.app.core.settings import get_settings

basic = HTTPBasic()
_hits: dict[str, list[float]] = defaultdict(list)


def require_admin(credentials: HTTPBasicCredentials = Depends(basic)) -> str:
    expected = get_settings().admin_password
    if not secrets.compare_digest(credentials.password, expected) or credentials.username not in {"admin", "northline"}:
        raise HTTPException(status_code=status.HTTP_401_UNAUTHORIZED, headers={"WWW-Authenticate": "Basic"})
    return credentials.username


def rate_limit(request: Request, limit: int = 40, window: int = 60) -> None:
    ip = request.client.host if request.client else "unknown"
    now = time()
    bucket = [stamp for stamp in _hits[ip] if now - stamp < window]
    if len(bucket) >= limit:
        raise HTTPException(status_code=429, detail="Too many requests")
    bucket.append(now)
    _hits[ip] = bucket


def origin_allowed(request: Request) -> None:
    settings = get_settings()
    origins = settings.cors_origin_list
    if "*" in origins or settings.environment == "development":
        return
    origin = request.headers.get("origin") or ""
    if origin and origin not in origins:
        raise HTTPException(status_code=403, detail="Origin is not allowed")
