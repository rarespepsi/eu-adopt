"""Teste rate-limit login și forgot-password."""
from django.core.cache import cache
from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(
    AUTH_LOGIN_RATE_LIMIT_PER_15MIN=2,
    AUTH_FORGOT_PASSWORD_RATE_LIMIT_PER_HOUR=2,
)
class AuthRateLimitTests(TestCase):
    def setUp(self):
        cache.clear()

    def test_login_blocks_after_limit(self):
        c = Client()
        url = reverse("login")
        for _ in range(2):
            c.post(url, {"login": "x", "password": "y"})
        r = c.post(url, {"login": "x", "password": "y"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Prea multe încercări")

    def test_forgot_password_blocks_after_limit(self):
        c = Client()
        url = reverse("forgot_password")
        for _ in range(2):
            c.post(url, {"email": "nobody@example.com"})
        r = c.post(url, {"email": "nobody@example.com"})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Prea multe solicitări")
