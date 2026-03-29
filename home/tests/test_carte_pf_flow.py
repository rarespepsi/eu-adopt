"""
Carte B2 puncte 11–20: flux PF (POST erori, SMS 111111, verificare email, polling, complete-login).
"""

import json
import uuid

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.signing import TimestampSigner
from django.test import Client, TestCase, override_settings
from django.urls import reverse

User = get_user_model()


def _pf_post_data(unique: str):
    n = abs(hash(unique)) % 900000000 + 100000000
    return {
        "first_name": "Ion",
        "last_name": "Test",
        "email": f"pf_{unique}@carte-test.local",
        "phone_country": "+40",
        "phone": str(n),
        "judet": "Neamț",
        "oras": "Piatra Neamț",
        "password1": "ParolaSigura12",
        "password2": "ParolaSigura12",
        "accept_termeni": "on",
        "accept_gdpr": "on",
    }


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class CartePF11to20Tests(TestCase):
    """Înregistrare PF: erori, redirect SMS, cod SMS, email, activare."""

    def test_11_incomplete_pf_shows_errors(self):
        c = Client()
        r = c.post(
            reverse("signup_pf"),
            {
                "first_name": "",
                "last_name": "",
                "email": "",
                "phone_country": "+40",
                "phone": "",
                "judet": "",
                "oras": "",
                "password1": "short",
                "password2": "other",
            },
        )
        self.assertEqual(r.status_code, 200)
        content = r.content.decode("utf-8")
        self.assertTrue(
            "obligatoriu" in content.lower()
            or "Email obligatoriu" in content
            or "Parola trebuie" in content
            or "Parolele nu coincid" in content,
        )

    def test_12_valid_pf_redirects_to_verificare_sms(self):
        u = uuid.uuid4().hex[:12]
        c = Client()
        r = c.post(reverse("signup_pf"), _pf_post_data(u))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")

    def _session_with_pending_pf(self, c: Client):
        u = uuid.uuid4().hex[:12]
        r = c.post(reverse("signup_pf"), _pf_post_data(u))
        self.assertEqual(r.status_code, 302)
        return u, _pf_post_data(u)["email"]

    def test_13_wrong_sms_code_shows_error(self):
        c = Client()
        self._session_with_pending_pf(c)
        r = c.post(reverse("signup_verificare_sms"), {"sms_code": "000000"})
        self.assertEqual(r.status_code, 200)
        self.assertIn("Cod invalid", r.content.decode("utf-8"))

    def test_13_correct_sms_redirects_to_check_email(self):
        c = Client()
        _, email = self._session_with_pending_pf(c)
        r = c.post(reverse("signup_verificare_sms"), {"sms_code": "111111"})
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_pf_check_email"), r.url or "")
        self.assertIn(email.replace("@", "%40"), r.url or "")

    def test_14_retrimite_sms_post_redirects(self):
        c = Client()
        self._session_with_pending_pf(c)
        r = c.post(reverse("signup_retrimite_sms"), {})
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")

    def test_15_pf_sms_alias_matches_verificare_sms(self):
        c = Client()
        self._session_with_pending_pf(c)
        r1 = c.get(reverse("signup_verificare_sms"))
        r2 = c.get(reverse("signup_pf_sms"))
        self.assertEqual(r1.status_code, 200)
        self.assertEqual(r2.status_code, 200)
        b1 = r1.content.decode("utf-8")
        b2 = r2.content.decode("utf-8")
        self.assertIn('name="sms_code"', b1)
        self.assertIn('name="sms_code"', b2)

    def test_16_check_email_screen_after_sms_success(self):
        c = Client()
        _, email = self._session_with_pending_pf(c)
        r = c.post(reverse("signup_verificare_sms"), {"sms_code": "111111"})
        self.assertEqual(r.status_code, 302)
        r2 = c.get(r.url)
        self.assertEqual(r2.status_code, 200)
        self.assertIn("Verifică email", r2.content.decode("utf-8"))
        self.assertIn(email, r2.content.decode("utf-8"))

    def test_17_retrimite_email_post_redirects(self):
        c = Client()
        _, email = self._session_with_pending_pf(c)
        c.post(reverse("signup_verificare_sms"), {"sms_code": "111111"})
        r = c.post(reverse("signup_retrimite_email"), {})
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_pf_check_email"), r.url or "")
        self.assertIn("retrimis=1", r.url or "")

    def test_18_check_activation_status_json(self):
        c = Client()
        r = c.get(reverse("signup_check_activation_status"))
        self.assertEqual(r.status_code, 200)
        data = json.loads(r.content.decode("utf-8"))
        self.assertFalse(data.get("activated"))

        r2 = c.get(reverse("signup_check_activation_status"), {"waiting_id": "test-wid"})
        data2 = json.loads(r2.content.decode("utf-8"))
        self.assertFalse(data2.get("activated"))

    def test_19_complete_login_no_token_redirects_home(self):
        r = Client().get(reverse("signup_complete_login"))
        self.assertEqual(r.status_code, 302)
        self.assertTrue((r.url or "").rstrip("/").endswith("/") or reverse("home") in (r.url or ""))

    def test_20_verify_email_token_activates_user(self):
        user = User.objects.create_user(
            username="inactive_pf_u",
            email="inactive_pf@carte-test.local",
            password="ParolaSigura12",
        )
        user.is_active = False
        user.save()
        token = TimestampSigner().sign(user.pk)
        c = Client()
        r = c.get(reverse("signup_verify_email"), {"token": token})
        self.assertEqual(r.status_code, 200)
        user.refresh_from_db()
        self.assertTrue(user.is_active)
        self.assertContains(r, "Cont activat", status_code=200)

    def test_19_complete_login_with_one_time_token(self):
        user = User.objects.create_user(
            username="onet_u",
            email="onet@carte-test.local",
            password="ParolaSigura12",
        )
        tok = "test-uuid-token-complete"
        cache.set("signup_onetime_" + tok, user.pk, timeout=60)
        c = Client()
        r = c.get(reverse("signup_complete_login"), {"token": tok})
        self.assertEqual(r.status_code, 302)
        self.assertIn("welcome=1", r.url or "")

