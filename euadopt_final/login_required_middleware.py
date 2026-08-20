"""
Mod PRE-LAUNCH: pe .ro, acces site doar după autentificare (cu excepții publice).

Activ doar când settings.PRELAUNCH_MODE este True (env EUADOPT_PRELAUNCH_MODE=1).
Pe site-urile EU (.com / .de / .fr / .es) navigarea rămâne liberă fără login;
adopția și acțiunile de cont cer autentificare separat (view-uri @login_required).
"""
from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect

from euadopt_final.prelaunch_paths import is_prelaunch_public_request


def _is_eu_browse_host(request) -> bool:
    """EU product hosts: vitrină publică chiar în PRELAUNCH (doar .ro rămâne blocat)."""
    try:
        from home.eu_site import is_eu_country_host, is_eu_hub_host

        host = request.get_host()
        return bool(is_eu_hub_host(host) or is_eu_country_host(host))
    except Exception:
        return False


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "PRELAUNCH_MODE", False):
            return self.get_response(request)

        # EU: navigare liberă; login doar la acțiuni (adopție, cont, etc.).
        if _is_eu_browse_host(request):
            return self.get_response(request)

        user = getattr(request, "user", None)
        if user is not None and user.is_authenticated:
            return self.get_response(request)

        path = request.path or "/"
        if is_prelaunch_public_request(request):
            return self.get_response(request)

        login_url = getattr(settings, "LOGIN_URL", "/login/")
        if path.rstrip("/") == login_url.rstrip("/"):
            return self.get_response(request)

        from home.auth_next import sanitize_post_login_next

        next_target = sanitize_post_login_next(request.get_full_path())
        if next_target:
            return redirect(f"{login_url}?next={quote(next_target, safe='/')}")
        return redirect(login_url)
