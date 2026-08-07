"""
Domenii EU-Adopt: redirect 301; skin EU; limba după LocaleMiddleware.
"""
from __future__ import annotations

from urllib.parse import parse_qsl, urlencode, urlsplit, urlunsplit

from django.conf import settings
from django.http import HttpResponsePermanentRedirect, HttpResponseRedirect
from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from django.utils import translation
from django.views.i18n import set_language as django_set_language

from home.euadopt_domains import inject_query_param, redirect_lang_for_host
from home.eu_site import (
    EU_HUB_UI_LANGUAGE_CODES,
    EU_SITE_BLOCKED_URL_NAMES,
    EU_SITE_LANGUAGE_CODES,
    eu_product_skin_enabled,
    hyphen_redirect_target_host,
    is_eu_hub_host,
    is_eu_site_host,
    path_blocked_on_eu_hub,
    pick_language_for_hub,
)


def _strip_query_param(full_path: str, key: str) -> str:
    parts = urlsplit(full_path or "/")
    q = [(k, v) for k, v in parse_qsl(parts.query, keep_blank_values=True) if k != key]
    new_q = urlencode(q)
    path = parts.path or "/"
    return f"{path}?{new_q}" if new_q else path


class EuSiteMiddleware:
    """Redirect 301 (alias/țară → .com) + flag-uri eu_site_* (înainte de Locale)."""

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        canon = hyphen_redirect_target_host(host)
        if canon:
            scheme = "https" if request.is_secure() else "http"
            path = request.get_full_path()
            lang = redirect_lang_for_host(host)
            if lang and "eu_lang=" not in path:
                path = inject_query_param(path, "eu_lang", lang)
            return HttpResponsePermanentRedirect(f"{scheme}://{canon}{path}")

        # Hub .com: ?eu_lang=de din redirect țară → setează sesiune/cookie + URL curat
        if is_eu_hub_host(host):
            raw = (request.GET.get("eu_lang") or "").strip().lower()
            if raw and raw in EU_HUB_UI_LANGUAGE_CODES:
                if hasattr(request, "session") and request.session is not None:
                    request.session["django_language"] = raw
                    request.session.modified = True
                clean = _strip_query_param(request.get_full_path(), "eu_lang")
                resp = HttpResponseRedirect(clean)
                cookie_name = getattr(settings, "LANGUAGE_COOKIE_NAME", "django_language")
                resp.set_cookie(
                    cookie_name,
                    raw,
                    max_age=getattr(settings, "LANGUAGE_COOKIE_AGE", 60 * 60 * 24 * 365),
                    path=getattr(settings, "LANGUAGE_COOKIE_PATH", "/"),
                    samesite=getattr(settings, "LANGUAGE_COOKIE_SAMESITE", "Lax"),
                )
                return resp

        request.eu_site_hub = False
        request.eu_site_active = False
        if eu_product_skin_enabled():
            request.eu_site_hub = is_eu_hub_host(host)
            request.eu_site_active = is_eu_site_host(host)
            if request.eu_site_active and self._should_block(request):
                return redirect("home")

        from home.eu_procedures import procedures_for_request

        request.site_proc = procedures_for_request(request)

        response = self.get_response(request)
        if getattr(request, "eu_site_active", False) and hasattr(request, "LANGUAGE_CODE"):
            response.setdefault("Content-Language", request.LANGUAGE_CODE)
        return response

    def _should_block(self, request) -> bool:
        if not getattr(request, "eu_site_active", False):
            return False
        path = request.path or "/"
        if path.startswith("/admin/"):
            return False
        user = getattr(request, "user", None)
        if user and user.is_authenticated and (user.is_staff or user.is_superuser):
            rm = getattr(request, "resolver_match", None)
            url_name = getattr(rm, "url_name", None) if rm else None
            if url_name and url_name.startswith("admin_analysis"):
                return False
        if path_blocked_on_eu_hub(path):
            return True
        try:
            match = resolve(path)
        except Resolver404:
            return False
        url_name = match.url_name
        if url_name in EU_SITE_BLOCKED_URL_NAMES:
            return True
        if url_name and url_name.startswith("publicitate_"):
            return True
        if url_name and url_name.startswith("reclama_"):
            return True
        return False


class EuSiteLocaleFixMiddleware:
    """
    După LocaleMiddleware: aplică limba hub/țară (altfel LANGUAGE_CODE=ro câștigă).
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if eu_product_skin_enabled() and is_eu_site_host(request.get_host()):
            lang = pick_language_for_hub(request)
            if lang in EU_SITE_LANGUAGE_CODES:
                translation.activate(lang)
                request.LANGUAGE_CODE = lang
                request.eu_site_lang = lang
                if hasattr(request, "session") and request.session is not None:
                    request.session["django_language"] = lang
        return self.get_response(request)


def eu_set_language(request):
    """set_language + marchează alegerea manuală (pentru .com / .de/.fr/.es)."""
    if request.method == "POST" and hasattr(request, "session"):
        request.session["eu_lang_manual"] = "1"
        lang = (request.POST.get("language") or "").strip().lower()
        if lang in EU_SITE_LANGUAGE_CODES:
            # Sync session immediately so LocaleFix on the next request sees it
            request.session["django_language"] = lang
    return django_set_language(request)
