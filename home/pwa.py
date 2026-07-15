"""PWA manifest + service worker (instalare pe ecran principal mobil)."""
from __future__ import annotations

import json

from django.http import HttpResponse, HttpResponseBase
from django.templatetags.static import static

PWA_LOGIN_PULSE_COOKIE = "eu_pwa_login_pulse"
PWA_LOGIN_PULSE_MAX_AGE = 300  # 5 min — prima pagină după login


def _static_abs(request, path: str) -> str:
    rel = static(path)
    if rel.startswith(("http://", "https://")):
        return rel
    return request.build_absolute_uri(rel)


def attach_pwa_login_pulse(response: HttpResponseBase) -> HttpResponseBase:
    """Semnal JS: abia s-a făcut login — evaluează regula 5 + săptămânal pe mobil."""
    response.set_cookie(
        PWA_LOGIN_PULSE_COOKIE,
        "1",
        max_age=PWA_LOGIN_PULSE_MAX_AGE,
        samesite="Lax",
        path="/",
    )
    return response


def pwa_manifest_view(request):
    icons = [
        {
            "src": _static_abs(request, "images/pwa/pwa-icon-192.png"),
            "sizes": "192x192",
            "type": "image/png",
            "purpose": "any",
        },
        {
            "src": _static_abs(request, "images/pwa/pwa-icon-512.png"),
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "any",
        },
        {
            "src": _static_abs(request, "images/pwa/pwa-icon-512.png"),
            "sizes": "512x512",
            "type": "image/png",
            "purpose": "maskable",
        },
    ]
    payload = {
        "id": "/",
        "name": "EU-Adopt",
        "short_name": "EU-Adopt",
        "description": "Adopție câini și pisici, servicii veterinare și parteneri în România.",
        "start_url": "/",
        "scope": "/",
        "display": "standalone",
        "orientation": "portrait-primary",
        "background_color": "#141a22",
        "theme_color": "#0e7490",
        "lang": "ro",
        "dir": "ltr",
        "icons": icons,
    }
    return HttpResponse(
        json.dumps(payload, ensure_ascii=False, separators=(",", ":")),
        content_type="application/manifest+json; charset=utf-8",
    )


def pwa_service_worker_view(request):
    body = """/* EU-Adopt PWA — service worker minimal (instalare mobil) */
self.addEventListener("install", function (event) {{
  self.skipWaiting();
}});
self.addEventListener("activate", function (event) {{
  event.waitUntil(self.clients.claim());
}});
self.addEventListener("fetch", function (event) {{
  event.respondWith(fetch(event.request));
}});
"""
    resp = HttpResponse(body, content_type="application/javascript; charset=utf-8")
    resp["Service-Worker-Allowed"] = "/"
    resp["Cache-Control"] = "no-cache"
    return resp
