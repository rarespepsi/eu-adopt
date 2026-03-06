"""
Middleware: site în pregătire.
Când SITE_PUBLIC = False, vizitatorii văd „În pregătire”.
Acces complet dacă:
  a) user logat și (is_staff sau is_superuser), SAU
  b) query param ?k=MAINTENANCE_SECRET (setează cookie, redirect fără ?k=), SAU
  c) cookie valid setat anterior (link /acces-pregatire/TOKEN/ sau ?k=).
MAINTENANCE_SECRET din .env.
"""

from django.conf import settings
from django.core.signing import Signer, BadSignature
from django.http import HttpResponse, HttpResponseRedirect
from django.template import loader
from urllib.parse import parse_qs, urlencode

COOKIE_NAME = "maintenance_view"
COOKIE_MAX_AGE = 30 * 24 * 60 * 60  # 30 zile

MAINTENANCE_SKIP_PREFIXES = (
    "/admin/",
    "/health/",
    "/static/",
    "/media/",
    "/login/",
    "/logout/",
    "/register/",
    "/cont/login/",
    "/cont/logout/",
    "/cont/inregistrare/",
    "/acces-pregatire/",
)


def _has_valid_maintenance_cookie(request):
    val = request.COOKIES.get(COOKIE_NAME)
    if not val:
        return False
    try:
        Signer().unsign(val)
        return True
    except BadSignature:
        return False


def _allow_access(request):
    """Permite acces dacă user e staff/superuser sau are cookie valid."""
    if request.user.is_authenticated and (request.user.is_staff or request.user.is_superuser):
        return True
    if _has_valid_maintenance_cookie(request):
        return True
    return False


def _build_url_without_param(path, query, param_to_remove="k"):
    """Returnează path + query fără parametrul param_to_remove."""
    qs = parse_qs(query, keep_blank_values=True)
    qs.pop(param_to_remove, None)
    new_query = urlencode(qs, doseq=True)
    return path + ("?" + new_query if new_query else "")


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if getattr(settings, "SITE_PUBLIC", True):
            return self.get_response(request)

        path = request.path
        for prefix in MAINTENANCE_SKIP_PREFIXES:
            if path.startswith(prefix):
                return self.get_response(request)

        # (b) Query ?k=MAINTENANCE_SECRET: setăm cookie și redirect fără ?k= în URL
        secret = getattr(settings, "MAINTENANCE_SECRET", "") or ""
        if secret and request.GET.get("k") == secret:
            signer = Signer()
            value = signer.sign("ok")
            target = _build_url_without_param(path, request.META.get("QUERY_STRING", ""))
            if not target.startswith("/"):
                target = "/" + target
            response = HttpResponseRedirect(target)
            response.set_cookie(COOKIE_NAME, value, max_age=COOKIE_MAX_AGE, httponly=True, samesite="Lax")
            return response

        if _allow_access(request):
            return self.get_response(request)

        template = loader.get_template("maintenance.html")
        html = template.render({})
        return HttpResponse(html, status=503)
