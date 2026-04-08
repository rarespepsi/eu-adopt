"""Sitemap-uri SEO + robots.txt."""
from urllib.parse import urlparse

from django.conf import settings
from django.contrib.sitemaps import Sitemap
from django.http import HttpResponse
from django.urls import reverse

from home.models import AnimalListing


def _site_proto_and_host():
    base = (getattr(settings, "SITE_BASE_URL", None) or "").strip().rstrip("/")
    if not base:
        return None, None
    parsed = urlparse(base if "://" in base else f"https://{base}")
    proto = (parsed.scheme or "https").lower()
    host = parsed.netloc
    return proto, host


class EuadoptSitemap(Sitemap):
    """URL-uri absolute: folosește SITE_BASE_URL dacă e setat, altfel django.contrib.sites."""

    def get_domain(self, site=None):
        _, host = _site_proto_and_host()
        if host:
            return host
        return super().get_domain(site=site)

    @property
    def protocol(self):
        proto, _ = _site_proto_and_host()
        if proto:
            return proto
        return "http" if settings.DEBUG else "https"


class StaticViewSitemap(EuadoptSitemap):
    """Pagini publice (fără login obligatoriu)."""

    priority = 0.7
    changefreq = "weekly"

    def items(self):
        return [
            "home",
            "pets_all",
            "servicii",
            "transport",
            "shop",
            "shop_comanda_personalizate",
            "shop_magazin_foto",
            "contact",
            "termeni",
            "termeni_read",
            "politica_confidentialitate",
            "politici_altele",
            "politica_cookie",
            "politica_servicii_platite",
            "politica_moderare",
            "public_offers_list",
            "custi",
        ]

    def location(self, item):
        return reverse(item)


class AnimalListingSitemap(EuadoptSitemap):
    changefreq = "daily"
    priority = 0.85

    def items(self):
        return AnimalListing.objects.filter(is_published=True).order_by("-updated_at")

    def lastmod(self, obj):
        return obj.updated_at

    def location(self, obj):
        return reverse("pets_single", args=[obj.pk])


def robots_txt(request):
    sitemap_url = request.build_absolute_uri("/sitemap.xml")
    body = "\n".join(
        [
            "User-agent: *",
            "Allow: /",
            "",
            f"Sitemap: {sitemap_url}",
        ]
    )
    return HttpResponse(body, content_type="text/plain; charset=utf-8")
