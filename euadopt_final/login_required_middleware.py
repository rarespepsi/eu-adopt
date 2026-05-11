from django.conf import settings
from django.shortcuts import redirect


class LoginRequiredMiddleware:
    """
    Enforce authenticated access site-wide, except explicit public paths.
    """

    def __init__(self, get_response):
        self.get_response = get_response

    def __call__(self, request):
        if request.user.is_authenticated:
            return self.get_response(request)

        path = request.path or "/"
        public_prefixes = (
            "/login/",
            "/admin/",
            "/static/",
            "/media/",
            "/favicon.ico",
            "/robots.txt",
            "/sitemap.xml",
        )

        if path.startswith(public_prefixes):
            return self.get_response(request)

        login_url = getattr(settings, "LOGIN_URL", "/login/")
        return redirect(f"{login_url}?next={request.get_full_path()}")
