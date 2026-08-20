"""
Gate opțional: pe domeniile non-.ro, „Coming soon” pentru anonimi / non-PF.

Implicit OFF (EUADOPT_NON_RO_STAFF_ONLY=0): navigare liberă pe EU.
Activare (1): doar staff + useri PF (+ login/signup) trec de poartă.
"""
from __future__ import annotations

from django.conf import settings
from django.shortcuts import render


def non_ro_staff_only_enabled() -> bool:
    raw = (getattr(settings, "EUADOPT_NON_RO_STAFF_ONLY", False))
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


def _user_may_access_eu(user) -> bool:
    """Staff/superuser sau cont PF autentificat."""
    if user is None or not getattr(user, "is_authenticated", False):
        return False
    if user.is_staff or user.is_superuser:
        return True
    try:
        from home.models import AccountProfile

        role = (
            AccountProfile.objects.filter(user_id=user.pk)
            .values_list("role", flat=True)
            .first()
        )
    except Exception:
        return False
    if role is None:
        # Cont fără profil = tratat ca PF (default la creare).
        return True
    return role == AccountProfile.ROLE_PF


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

        if _user_may_access_eu(getattr(request, "user", None)):
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
