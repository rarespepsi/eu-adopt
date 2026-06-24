"""
Restricționează /admin/ la IP-uri din EUADOPT_ADMIN_ALLOW_IP (virgulă-separate).
Dacă variabila lipsește sau e goală, middleware-ul nu face nimic.
"""
from __future__ import annotations

from django.conf import settings
from django.http import HttpResponseForbidden


def _client_ip(request) -> str:
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"


class AdminIPAllowlistMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        allowed = getattr(settings, "EUADOPT_ADMIN_ALLOW_IPS", None) or []
        if allowed:
            path = request.path or "/"
            if path == "/admin" or path.startswith("/admin/"):
                if _client_ip(request) not in allowed:
                    return HttpResponseForbidden(
                        "Acces /admin/ restricționat. Contactează administratorul."
                    )
        return self.get_response(request)
