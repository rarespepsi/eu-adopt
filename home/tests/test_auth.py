"""
Teste auth de bază: login reușit/eșuat, logout.
Rulează: python manage.py test home.tests.test_auth
"""

import uuid

from django.contrib.auth import get_user_model
from django.core.management import call_command
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from home.models import AccountProfile

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
        self.assertEqual(r.url, "/")
        self.assertTrue(c.session.get("_auth_user_id"))

    def test_login_campanii_landing_user_opens_campaign_form(self):
        self.user.email = "serbacov.ioana@gmail.com"
        self.user.save(update_fields=["email"])
        AccountProfile.objects.get_or_create(
            user=self.user,
            defaults={"role": AccountProfile.ROLE_PF},
        )
        c = Client()
        r = c.post(
            reverse("login"),
            {"login": self.user.email, "password": "AuthTest_Pass12"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("account") + "?campanie=1")

    def test_login_campanii_landing_respects_explicit_next(self):
        self.user.email = "serbacov.ioana@gmail.com"
        self.user.save(update_fields=["email"])
        c = Client()
        r = c.post(
            reverse("login") + "?next=/pets/",
            {"login": self.user.email, "password": "AuthTest_Pass12"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, "/pets/")

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

    def test_account_delete_schedule_then_cancel(self):
        AccountProfile.objects.get_or_create(
            user=self.user,
            defaults={"role": AccountProfile.ROLE_PF},
        )
        c = Client()
        c.login(username=self.user.username, password="AuthTest_Pass12")
        r = c.get(reverse("account_delete"))
        self.assertEqual(r.status_code, 200)
        r2 = c.post(
            reverse("account_delete"),
            {"password": "AuthTest_Pass12", "confirm_deletion": "1"},
        )
        self.assertEqual(r2.status_code, 302)
        self.user.refresh_from_db()
        self.assertTrue(self.user.is_active)
        ap = self.user.account_profile
        self.assertIsNotNone(ap.pending_deletion_grace_until)
        r3 = c.post(reverse("account_delete_cancel"), {})
        self.assertEqual(r3.status_code, 302)
        ap.refresh_from_db()
        self.assertIsNone(ap.pending_deletion_grace_until)

    def test_finalize_pending_account_deletions_command(self):
        AccountProfile.objects.get_or_create(
            user=self.user,
            defaults={"role": AccountProfile.ROLE_PF},
        )
        ap = self.user.account_profile
        ap.pending_deletion_requested_at = timezone.now() - timezone.timedelta(days=20)
        ap.pending_deletion_grace_until = timezone.now() - timezone.timedelta(days=1)
        ap.save()
        call_command("finalize_pending_account_deletions")
        self.user.refresh_from_db()
        self.assertFalse(self.user.is_active)
        ap.refresh_from_db()
        self.assertIsNotNone(ap.pending_deletion_finalized_at)
