"""
Gate: pe domeniile non-.ro, vizitatorii văd „Coming soon”;
doar staff/superuser (după login) pot lucra pe extensii.
Activ implicit: EUADOPT_NON_RO_STAFF_ONLY=1 (dezactivare = 0).
"""
from __future__ import annotations

from django.conf import settings
from django.shortcuts import render


def non_ro_staff_only_enabled() -> bool:
    raw = (getattr(settings, "EUADOPT_NON_RO_STAFF_ONLY", True))
    if isinstance(raw, bool):
        return raw
    return str(raw).strip().lower() in ("1", "true", "yes", "on")


_ALLOW_PREFIXES = (
    "/login",
    "/logout",
    "/signup",
    "/admin",
    "/static",
    "/media",
    "/i18n/",
    "/password",
    "/reset",
    "/favicon",
    "/site-guide",
    "/manifest",
    "/sw",
)


def _path_allowed(path: str) -> bool:
    p = (path or "/").lower()
    for pref in _ALLOW_PREFIXES:
        if p == pref or p.startswith(pref + "/") or p.startswith(pref + "?"):
            return True
        # /login/ etc.
        if p.rstrip("/") == pref.rstrip("/"):
            return True
    return False


class EuNonRoStaffGateMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not non_ro_staff_only_enabled():
            return self.get_response(request)

        from home.euadopt_domains import is_romania_primary_host
        from home.eu_site import hyphen_redirect_target_host, is_eu_country_host, is_eu_hub_host

        host = request.get_host()
        # Redirect hosts sunt tratate înainte în EuSiteMiddleware; aici doar active EU.
        if is_romania_primary_host(host):
            return self.get_response(request)
        if hyphen_redirect_target_host(host):
            return self.get_response(request)

        # Gate pe hub .com și pe .de/.fr/.es
        if not (is_eu_hub_host(host) or is_eu_country_host(host)):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated and (user.is_staff or user.is_superuser):
            return self.get_response(request)

        if _path_allowed(request.path or "/"):
            return self.get_response(request)

        from home.eu_coming_soon import coming_soon_copy

        return render(
            request,
            "anunturi/eu_coming_soon.html",
            {
                "ro_home_url": "https://eu-adopt.ro/",
                "login_url": "/login/",
                "cs": coming_soon_copy(request),
            },
            status=403,
        )
