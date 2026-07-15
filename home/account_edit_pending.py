"""Profil în așteptare la schimbare email — cache server-side (confirmare cross-device)."""

from __future__ import annotations

from typing import Any

from django.core.cache import cache

EDIT_PENDING_CACHE_PREFIX = "euadopt:edit_pending:"
EDIT_PENDING_CACHE_TTL = 3600  # aliniat cu max_age token confirmare email


def edit_pending_cache_key(user_pk: int) -> str:
    return f"{EDIT_PENDING_CACHE_PREFIX}{int(user_pk)}"


def save_edit_pending(user_pk: int, data: dict[str, Any]) -> None:
    cache.set(edit_pending_cache_key(user_pk), dict(data), EDIT_PENDING_CACHE_TTL)


def load_edit_pending(user_pk: int) -> dict[str, Any] | None:
    data = cache.get(edit_pending_cache_key(user_pk))
    if not isinstance(data, dict):
        return None
    if str(data.get("user_pk")) != str(user_pk):
        return None
    return data


def clear_edit_pending(user_pk: int) -> None:
    cache.delete(edit_pending_cache_key(user_pk))


def resolve_edit_pending(request, user_pk: int | None = None) -> dict[str, Any] | None:
    """Sesiune (browser curent) sau cache (confirmare de pe alt dispozitiv)."""
    session_data = request.session.get("edit_pending")
    if isinstance(session_data, dict):
        pk = user_pk if user_pk is not None else session_data.get("user_pk")
        if pk is not None and str(session_data.get("user_pk")) == str(pk):
            return session_data
    if user_pk is None:
        user = getattr(request, "user", None)
        if user and getattr(user, "is_authenticated", False):
            user_pk = user.pk
    if user_pk is None:
        return None
    return load_edit_pending(user_pk)


def sync_edit_pending(request, data: dict[str, Any]) -> None:
    """Salvează pending în sesiune + cache."""
    request.session["edit_pending"] = data
    user_pk = data.get("user_pk")
    if user_pk is not None:
        save_edit_pending(int(user_pk), data)


def drop_edit_pending(request, user_pk: int) -> None:
    request.session.pop("edit_pending", None)
    clear_edit_pending(user_pk)


def email_change_confirmed(user, pending_email: str) -> bool:
    expected = (pending_email or "").strip().lower()
    if not expected:
        return False
    current = (getattr(user, "email", None) or "").strip().lower()
    return current == expected

    expected = (pending_email or "").strip().lower()
    if not expected:
        return False
    current = (getattr(user, "email", None) or "").strip().lower()
    return current == expected
