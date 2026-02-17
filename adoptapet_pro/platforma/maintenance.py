"""
Middleware: site în pregătire.
Când SITE_PUBLIC = False, vizitatorii văd „În pregătire”.
Acces: (1) user staff, (2) cookie setat prin link secret /acces-pregatire/TOKEN/
"""

from django.conf import settings
from django.core.signing import Signer, BadSignature
from django.http import HttpResponse
from django.template import loader

COOKIE_NAME = "maintenance_view"

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

        if request.user.is_authenticated and request.user.is_staff:
            return self.get_response(request)

        if _has_valid_maintenance_cookie(request):
            return self.get_response(request)

        template = loader.get_template("maintenance.html")
        html = template.render({})
        return HttpResponse(html, status=503)
