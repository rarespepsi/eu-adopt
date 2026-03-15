# -*- coding: utf-8 -*-
"""Dacă MAINTENANCE_MODE este True, toate cererile (în afară de static/media) primesc pagina „Site în lucru”."""
from django.conf import settings
from django.http import HttpResponse
from django.template import loader


class MaintenanceMiddleware:
    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if not getattr(settings, 'MAINTENANCE_MODE', False):
            return self.get_response(request)
        path = request.path
        if path.startswith('/static/') or path.startswith('/media/') or path.startswith('/admin/'):
            return self.get_response(request)
        template = loader.get_template('maintenance.html')
        return HttpResponse(template.render({}, request), status=503)
