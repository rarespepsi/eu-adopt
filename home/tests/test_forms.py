"""
Validări formular înregistrare PF (prin view signup_pf).
Rulează: python manage.py test home.tests.test_forms
"""

import uuid

from django.test import Client, TestCase
from django.urls import reverse


def _pf_payload(unique: str):
    n = abs(hash(unique)) % 900000000 + 100000000
    return {
        "first_name": "Ion",
        "last_name": "Test",
        "email": f"pf_{unique}@euadopt-test.local",
        "phone_country": "+40",
        "phone": str(n),
        "judet": "Neamț",
        "oras": "Piatra Neamț",
        "password1": "ParolaSigura12",
        "password2": "ParolaSigura12",
        "accept_termeni": "on",
        "accept_gdpr": "on",
    }


class SignupPFViewTests(TestCase):
    """1–3: PF valid, câmpuri lipsă, fără T&C."""

    def test_signup_pf_valid_redirects_to_sms(self):
        u = uuid.uuid4().hex[:12]
        c = Client()
        r = c.post(reverse("signup_pf"), _pf_payload(u))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("signup_verificare_sms"), r.url or "")

    def test_signup_pf_missing_fields_returns_errors(self):
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
        text = r.content.decode("utf-8").lower()
        self.assertTrue(
            "obligatoriu" in text
            or "email obligatoriu" in text
            or "parola trebuie" in text
            or "parolele nu coincid" in text,
        )

    def test_signup_pf_without_terms_checkbox_fails(self):
        u = uuid.uuid4().hex[:12]
        data = _pf_payload(u)
        del data["accept_termeni"]
        c = Client()
        r = c.post(reverse("signup_pf"), data)
        self.assertEqual(r.status_code, 200)
        self.assertIn("termenii", r.content.decode("utf-8").lower())
