"""PWA manifest + service worker (instalare pe ecran principal mobil)."""
from __future__ import annotations

import json

from django.http import HttpResponse
from django.templatetags.static import static


def _static_abs(request, path: str) -> str:
    rel = static(path)
    if rel.startswith(("http://", "https://")):
        return rel
    return request.build_absolute_uri(rel)


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
    body = f"""/* EU-Adopt PWA — service worker minimal (instalare mobil) */
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
