"""Rate limiting pentru login și reset parolă (cache, per IP)."""
from __future__ import annotations

from django.conf import settings
from django.core.cache import cache


def client_ip(request) -> str:
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"


def _count(key: str) -> int:
    value = cache.get(key, 0)
    try:
        return int(value)
    except (TypeError, ValueError):
        return 0


def _bump(key: str, ttl_seconds: int) -> None:
    try:
        cache.incr(key)
    except ValueError:
        cache.add(key, 1, ttl_seconds)


def is_login_rate_limited(request) -> bool:
    limit = int(getattr(settings, "AUTH_LOGIN_RATE_LIMIT_PER_15MIN", 15))
    key = f"auth:login:{client_ip(request)}"
    return _count(key) >= limit


def bump_login_attempt(request) -> None:
    _bump(f"auth:login:{client_ip(request)}", 900)


def is_forgot_password_rate_limited(request) -> bool:
    limit = int(getattr(settings, "AUTH_FORGOT_PASSWORD_RATE_LIMIT_PER_HOUR", 5))
    key = f"auth:forgot:{client_ip(request)}"
    return _count(key) >= limit


def bump_forgot_password_attempt(request) -> None:
    _bump(f"auth:forgot:{client_ip(request)}", 3600)
