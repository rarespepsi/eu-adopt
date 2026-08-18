"""
Mod PRE-LAUNCH: acces site doar după autentificare.

Activ doar când settings.PRELAUNCH_MODE este True (env EUADOPT_PRELAUNCH_MODE=1).
Când PRELAUNCH_MODE este False, middleware-ul nu face nimic — vitrina publică normală.
"""
from __future__ import annotations

from urllib.parse import quote

from django.conf import settings
from django.shortcuts import redirect

from euadopt_final.prelaunch_paths import is_prelaunch_public_request


class LoginRequiredMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, "PRELAUNCH_MODE", False):
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
