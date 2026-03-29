"""
Teste auth de bază: login reușit/eșuat, logout.
Rulează: python manage.py test home.tests.test_auth
"""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

User = get_user_model()


class LoginLogoutTests(TestCase):
    """4–6: login valid, parolă greșită, logout."""

    def setUp(self):
        u = uuid.uuid4().hex[:10]
        self.user = User.objects.create_user(
            username=f"auth_u_{u}",
            email=f"auth_{u}@test.local",
            password="AuthTest_Pass12",
        )
        self.user.is_active = True
        self.user.save()

    def test_login_valid_redirects(self):
        c = Client()
        r = c.post(
            reverse("login"),
            {"login": self.user.email, "password": "AuthTest_Pass12"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(c.session.get("_auth_user_id"))

    def test_login_invalid_password_shows_error(self):
        c = Client()
        r = c.post(
            reverse("login"),
            {"login": self.user.email, "password": "WrongPassword99"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertIn("incorect", r.content.decode("utf-8").lower())

    def test_logout_clears_session(self):
        c = Client()
        c.login(username=self.user.username, password="AuthTest_Pass12")
        self.assertTrue(c.session.get("_auth_user_id"))
        r = c.get(reverse("logout"))
        self.assertEqual(r.status_code, 302)
        self.assertFalse(c.session.get("_auth_user_id"))
