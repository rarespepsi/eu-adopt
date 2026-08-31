"""Pagină CSRF 403 prietenoasă pe POST fără token."""

from django.contrib.auth import get_user_model
from django.test import Client, RequestFactory, TestCase
from django.urls import reverse

from home.csrf_views import _safe_retry_path
from home.models import AccountProfile

User = get_user_model()


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
        self.assertIn("Alege tipul de cont", body)
        self.assertNotIn("Contul meu", body)

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

    def test_retry_path_account_edit_opens_campanie_form(self):
        rf = RequestFactory()
        req = rf.post(reverse("account_edit"), {"form_type": "campanie_sterilizare"})
        self.assertEqual(_safe_retry_path(req), reverse("account") + "?campanie=1")

    def test_retry_path_account_edit_opens_campanie_edit(self):
        rf = RequestFactory()
        req = rf.post(
            reverse("account_edit"),
            {"form_type": "campanie_sterilizare", "campanie_id": "42"},
        )
        self.assertEqual(_safe_retry_path(req), reverse("account") + "?campanie_edit=42")

    def test_retry_path_account_edit_delete_opens_list(self):
        rf = RequestFactory()
        req = rf.post(
            reverse("account_edit"),
            {"form_type": "campanie_sterilizare_delete", "campanie_id": "7"},
        )
        self.assertEqual(_safe_retry_path(req), reverse("account") + "?campanii_mele=1")

    def test_retry_path_account_edit_other_form_goes_to_account(self):
        rf = RequestFactory()
        req = rf.post(reverse("account_edit"), {"form_type": "firma"})
        self.assertEqual(_safe_retry_path(req), reverse("account"))

    def test_campanie_post_without_token_retries_campaign_form(self):
        u = User.objects.create_user("csrf_camp", "csrf_camp@test.local", "x")
        ap, _ = AccountProfile.objects.get_or_create(user=u)
        ap.role = AccountProfile.ROLE_PF
        ap.save(update_fields=["role"])
        c = Client(enforce_csrf_checks=True)
        c.force_login(u)
        r = c.post(
            reverse("account_edit"),
            {"form_type": "campanie_sterilizare", "campanie_judet": "Neamț"},
        )
        self.assertEqual(r.status_code, 403)
        body = r.content.decode("utf-8")
        self.assertIn("Nu am putut trimite formularul", body)
        self.assertIn(reverse("account") + "?campanie=1", body)
        self.assertNotIn(reverse("account_edit"), body)
        self.assertIn("Contul meu", body)
        self.assertNotIn("Alege tipul de cont", body)
        self.assertNotIn(f'href="{reverse("login")}"', body)

    def test_account_get_sets_csrf_cookie(self):
        u = User.objects.create_user("csrf_acct", "csrf_acct@test.local", "x")
        ap, _ = AccountProfile.objects.get_or_create(user=u)
        ap.role = AccountProfile.ROLE_PF
        ap.save(update_fields=["role"])
        c = Client(enforce_csrf_checks=True)
        c.force_login(u)
        r = c.get(reverse("account"))
        self.assertEqual(r.status_code, 200)
        self.assertIn("csrftoken", r.cookies)

    def test_account_csrf_refresh_returns_token(self):
        u = User.objects.create_user("csrf_ref", "csrf_ref@test.local", "x")
        ap, _ = AccountProfile.objects.get_or_create(user=u)
        ap.role = AccountProfile.ROLE_PF
        ap.save(update_fields=["role"])
        c = Client(enforce_csrf_checks=True)
        c.force_login(u)
        r = c.get(reverse("account_csrf_refresh"))
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data.get("ok"))
        self.assertTrue(data.get("csrfToken"))
        self.assertIn("csrftoken", r.cookies)
