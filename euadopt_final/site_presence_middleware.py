"""Middleware: înregistrare prezență vizitatori (Analiză / Prezență)."""
from home.site_presence import record_site_presence


class SitePresenceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        record_site_presence(request)
        return self.get_response(request)
