"""Signup EU simplu (PF) — fără telefon, fără SMS, fără județ RO."""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import UserProfile


def _eu_pf_payload(unique: str):
    return {
        "first_name": "Maria",
        "last_name": "Mueller",
        "email": f"eu_{unique}@euadopt-test.local",
        "country": "DE",
        "password1": "SecurePass12",
        "password2": "SecurePass12",
        "accept_termeni": "on",
        "accept_gdpr": "on",
    }


@override_settings(
    EUADOPT_EU_PRODUCT_SKIN=True,
    EUADOPT_NON_RO_STAFF_ONLY=True,
    EUADOPT_STAFF_INVITE_EMAIL_ENABLED=False,
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
)
class EuSimpleSignupTests(TestCase):
    def test_gate_allows_signup_on_com(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get(reverse("signup_pf"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'name="country"')
        self.assertNotContains(r, 'name="judet"')
        self.assertNotContains(r, 'name="phone"')
        self.assertNotContains(r, 'name="phone_country"')

    def test_choose_type_redirects_to_pf(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_pf"), r.url or "")

    def test_eu_pf_post_skips_sms_creates_inactive_user(self):
        u = uuid.uuid4().hex[:12]
        c = Client(HTTP_HOST="euadopt.com")
        r = c.post(reverse("signup_pf"), _eu_pf_payload(u))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_pf_check_email"), r.url or "")
        self.assertNotIn(reverse("signup_verificare_sms"), r.url or "")
        User = get_user_model()
        user = User.objects.get(email=f"eu_{u}@euadopt-test.local")
        self.assertFalse(user.is_active)
        self.assertEqual(user.first_name, "Maria")
        self.assertEqual(user.last_name, "Mueller")
        prof = UserProfile.objects.get(user=user)
        self.assertEqual(prof.country, "DE")
        self.assertEqual((prof.phone or "").strip(), "")
        self.assertEqual((prof.judet or "").strip(), "")

    def test_ro_signup_still_goes_to_sms(self):
        from home.tests.test_forms import _pf_payload

        u = uuid.uuid4().hex[:12]
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.post(reverse("signup_pf"), _pf_payload(u))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")
