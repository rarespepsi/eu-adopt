"""Teste modul email EU-Adopt (backend locmem, fără SMTP real)."""

from django.core import mail
from django.test import TestCase, override_settings

from home.euadopt_email import (
    MAIL_ACCOUNT_ACTIVATION,
    send_account_activation_email,
    send_euadopt_email,
)


@override_settings(
    EMAIL_BACKEND="django.core.mail.backends.locmem.EmailBackend",
    DEFAULT_FROM_EMAIL="contact@eu-adopt.ro",
    SITE_BASE_URL="https://eu-adopt.ro",
)
class EuadoptEmailTests(TestCase):
    def test_send_euadopt_email_html_and_plain(self):
        ok = send_euadopt_email(
            MAIL_ACCOUNT_ACTIVATION,
            "test@example.com",
            {"verify_url": "https://eu-adopt.ro/verify/", "username": "testuser"},
            username="testuser",
        )
        self.assertTrue(ok)
        self.assertEqual(len(mail.outbox), 1)
        msg = mail.outbox[0]
        self.assertIn("[testuser]", msg.subject)
        self.assertIn("Activează contul", msg.body)
        self.assertEqual(len(msg.alternatives), 1)
        html, mime = msg.alternatives[0]
        self.assertEqual(mime, "text/html")
        self.assertIn("EU-Adopt", html)
        self.assertIn("verify/", html)

    def test_account_activation_helper(self):
        from django.contrib.auth import get_user_model

        User = get_user_model()
        user = User.objects.create_user(
            username="activuser",
            email="activ@example.com",
            password="x",
            is_active=False,
        )
        ok = send_account_activation_email(
            user,
            "https://eu-adopt.ro/activate/",
            resend=False,
        )
        self.assertTrue(ok)
        self.assertEqual(mail.outbox[0].to, ["activ@example.com"])
