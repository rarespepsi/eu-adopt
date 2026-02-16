from django.contrib import admin
from django.urls import path, include
from django.conf import settings
from django.conf.urls.static import static
from django.http import HttpResponse

def health(request):
    """Endpoint ușor pentru ping (UptimeRobot) - ține serviciul treaz pe Render Free."""
    return HttpResponse("OK", content_type="text/plain")

urlpatterns = [
    path("health/", health),
    path("admin/", admin.site.urls),
    path("", include("anunturi.urls")),
]
urlpatterns += static(settings.MEDIA_URL, document_root=settings.MEDIA_ROOT)