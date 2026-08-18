"""Strip nested/oversized ?next= on login and signup before the view runs."""

from __future__ import annotations

from django.http import HttpResponseRedirect

from home.auth_next import apply_sanitized_next_to_querydict, sanitize_post_login_next


class SanitizeAuthNextMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.method not in ("GET", "HEAD"):
            return self.get_response(request)
        path = request.path or "/"
        if not (path.startswith("/login") or path.startswith("/signup")):
            return self.get_response(request)
        raw = request.GET.get("next")
        if raw is None:
            return self.get_response(request)
        clean = sanitize_post_login_next(raw)
        if clean == (raw or "").strip():
            return self.get_response(request)
        q = request.GET.copy()
        apply_sanitized_next_to_querydict(q)
        qs = q.urlencode()
        url = path + (("?" + qs) if qs else "")
        return HttpResponseRedirect(url)
