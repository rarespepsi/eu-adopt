"""Pagină CSRF 403 prietenoasă pe POST fără token."""

from django.test import Client, TestCase
from django.urls import reverse


class CsrfFailurePageTests(TestCase):
    def test_signup_colaborator_post_without_token_shows_friendly_403(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(reverse("signup_colaborator"), {"email": "csrf@test.local"})
        self.assertEqual(r.status_code, 403)
        body = r.content.decode("utf-8")
        self.assertNotIn("Interzis (403)", body)
        self.assertNotIn("Forbidden (403)", body)
        self.assertIn("Nu am putut trimite formularul", body)
        self.assertIn("Safari", body)
        self.assertIn("Chrome", body)
        self.assertIn(reverse("signup_colaborator"), body)
        self.assertIn(reverse("login"), body)

    def test_signup_colaborator_get_sets_csrf_cookie(self):
        c = Client(enforce_csrf_checks=True)
        r = c.get(reverse("signup_colaborator"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)

    def test_whatsapp_ua_mentions_in_app_browser(self):
        c = Client(enforce_csrf_checks=True)
        r = c.post(
            reverse("signup_colaborator"),
            {"email": "wa@test.local"},
            HTTP_USER_AGENT="WhatsApp/2.0",
        )
        self.assertEqual(r.status_code, 403)
        self.assertIn("WhatsApp", r.content.decode("utf-8"))
