"""Pagină prietenoasă când verificarea CSRF eșuează (ex. browser in-app WhatsApp)."""

from __future__ import annotations

import logging

from django.shortcuts import render
from django.urls import reverse

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
    form_type = _post_field(request, "form_type")
    logger.warning(
        "CSRF failure path=%s form_type=%s reason=%s ua=%s",
        path,
        form_type or "",
        reason or "",
        ua,
    )
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


def _post_field(request, name: str) -> str:
    try:
        return (request.POST.get(name) or "").strip()
    except Exception:
        return ""


def _account_edit_retry_path(request) -> str:
    """POST /cont/editeaza/ nu are GET util — înapoi la Cont, cu formularul potrivit."""
    account = reverse("account")
    form_type = _post_field(request, "form_type")
    if form_type == "campanie_sterilizare":
        edit_id = _post_field(request, "campanie_id")
        if edit_id.isdigit():
            return f"{account}?campanie_edit={edit_id}"
        return f"{account}?campanie=1"
    if form_type == "campanie_sterilizare_delete":
        return f"{account}?campanii_mele=1"
    return account


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
    try:
        account_edit = reverse("account_edit")
    except Exception:
        account_edit = "/cont/editeaza/"
    path_norm = path.rstrip("/") or "/"
    edit_norm = account_edit.rstrip("/") or "/"
    if path_norm == edit_norm:
        return _account_edit_retry_path(request)
    qs = request.META.get("QUERY_STRING") or ""
    if any(c in qs for c in ("\n", "\r", "<")) or len(qs) > 200:
        return path
    full = f"{path}?{qs}" if qs else path
    if len(full) > 400:
        return path
    return full
