import os
from django.contrib import admin
from django.urls import path, include, re_path
from django.conf import settings
from django.conf.urls.static import static
from django.views.static import serve as static_serve
from django.http import Http404

from home.seo_views import euadopt_sitemap
from home.sitemaps import AnimalListingSitemap, StaticViewSitemap, robots_txt

SEO_SITEMAPS = {
    "static": StaticViewSitemap,
    "animals": AnimalListingSitemap,
}


def _serve_media(request, path):
    """Servește fișiere din MEDIA_ROOT și când DEBUG=False (pentru development)."""
    document_root = str(settings.MEDIA_ROOT)
    if not document_root or not os.path.isdir(document_root):
        raise Http404("Media root invalid")
    return static_serve(request, path, document_root=document_root)


urlpatterns = [
    path('admin/', admin.site.urls),
    path('robots.txt', robots_txt),
    path(
        'sitemap.xml',
        euadopt_sitemap,
        {'sitemaps': SEO_SITEMAPS},
        name='sitemap',
    ),
    path('', include('home.urls')),
]
# Fișiere media (poze profil) – servite în development
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)
# Când DEBUG=False, static() nu adaugă ruta; folosim _serve_media ca fallback
urlpatterns += [
    re_path(r'^media/(?P<path>.*)$', _serve_media),
]