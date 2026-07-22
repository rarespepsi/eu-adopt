"""
Domenii EU-Adopt: redirect 301 cu cratimă; skin EU opțional (EUADOPT_EU_PRODUCT_SKIN).
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponsePermanentRedirect
from django.shortcuts import redirect
from django.urls import Resolver404, resolve
from django.utils import translation

from home.eu_site import (
    EU_SITE_BLOCKED_URL_NAMES,
    EU_SITE_LANGUAGE_CODES,
    eu_product_skin_enabled,
    hyphen_redirect_target_host,
    is_eu_hub_host,
    is_eu_site_host,
    path_blocked_on_eu_hub,
    pick_language_for_hub,
)


class EuSiteMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        host = request.get_host()
        canon = hyphen_redirect_target_host(host)
        if canon:
            scheme = "https" if request.is_secure() else "http"
            path = request.get_full_path()
            return HttpResponsePermanentRedirect(f"{scheme}://{canon}{path}")

        request.eu_site_hub = False
        request.eu_site_active = False
        if eu_product_skin_enabled():
            request.eu_site_hub = is_eu_hub_host(host)
            request.eu_site_active = is_eu_site_host(host)

            if request.eu_site_active:
                lang = pick_language_for_hub(request)
                if lang in EU_SITE_LANGUAGE_CODES:
                    if hasattr(request, "session") and request.session is not None:
                        request.session["django_language"] = lang
                    translation.activate(lang)
                    request.LANGUAGE_CODE = lang

                if self._should_block(request):
                    return redirect("home")

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
