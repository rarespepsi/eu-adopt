"""Pagină prietenoasă când verificarea CSRF eșuează (ex. browser in-app WhatsApp)."""

from __future__ import annotations

import logging

from django.shortcuts import render

logger = logging.getLogger("euadopt.csrf")

_IN_APP_MARKERS = (
    "whatsapp",
    "fban",
    "fbav",
    "fb_iab",
    "instagram",
    "line/",
    "tiktok",
)


def csrf_failure(request, reason="", template_name=None):
    """CSRF_FAILURE_VIEW: 403 fără pagina Django „Interzis (403)”."""
    path = request.get_full_path() or "/"
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:400]
    logger.warning("CSRF failure path=%s reason=%s ua=%s", path, reason or "", ua)
    ua_l = ua.lower()
    in_app = any(m in ua_l for m in _IN_APP_MARKERS)
    return render(
        request,
        "403_csrf.html",
        {
            "retry_path": _safe_retry_path(request),
            "in_app_browser": in_app,
        },
        status=403,
    )


def _safe_retry_path(request) -> str:
    path = request.path or "/"
    if (
        not path.startswith("/")
        or path.startswith("//")
        or "\\" in path
        or ".." in path
        or "\n" in path
        or "\r" in path
    ):
        return "/"
    if path.startswith("/admin"):
        return "/"
    qs = request.META.get("QUERY_STRING") or ""
    if any(c in qs for c in ("\n", "\r", "<")) or len(qs) > 200:
        return path
    full = f"{path}?{qs}" if qs else path
    if len(full) > 400:
        return path
    return full
