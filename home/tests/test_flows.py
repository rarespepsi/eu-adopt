"""
Fluxuri: cerere transport, trimitere email (reset parolă).
Rulează: python manage.py test home.tests.test_flows
"""

import uuid

from django.contrib.auth import get_user_model
from django.core import mail
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import TransportVeterinaryRequest

User = get_user_model()


class TransportSubmitFlowTests(TestCase):
    """9: POST transport cu date minime valide."""

    @override_settings(PRELAUNCH_MODE=False)
    def test_transport_submit_valid_creates_request(self):
        c = Client()
        r = c.post(
            reverse("transport_submit"),
            {
                "judet": "Cluj",
                "oras": "Cluj-Napoca",
                "plecare": "Veterinar A",
                "sosire": "Veterinar B",
                "nr_caini": "2",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            TransportVeterinaryRequest.objects.filter(
                judet="Cluj",
                oras="Cluj-Napoca",
            ).exists(),
        )

    @override_settings(EUADOPT_EU_PRODUCT_SKIN=True, EUADOPT_NON_RO_STAFF_ONLY=False, PRELAUNCH_MODE=False)
    def test_eu_transport_submit_without_county_city(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.post(
            reverse("transport_submit"),
            {
                "country": "FR",
                "plecare": "Shelter Romania",
                "sosire": "Paris",
                "nr_caini": "1",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertTrue(
            TransportVeterinaryRequest.objects.filter(
                country="FR",
                plecare="Shelter Romania",
                sosire="Paris",
            ).exists(),
        )


@override_settings(EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend")
class ForgotPasswordEmailTests(TestCase):
    """10: forgot password trimite email când utilizatorul există."""

    def test_forgot_password_sends_email_for_known_user(self):
        u = uuid.uuid4().hex[:10]
        User.objects.create_user(
            username=f"mail_{u}",
            email=f"mail_{u}@test.local",
            password="MailTest_Pass12",
        )
        mail.outbox.clear()
        c = Client()
        r = c.post(
            reverse("forgot_password"),
            {"email": f"mail_{u}@test.local"},
        )
        self.assertEqual(r.status_code, 200)
        self.assertEqual(len(mail.outbox), 1)
        self.assertIn("reset", mail.outbox[0].subject.lower())
