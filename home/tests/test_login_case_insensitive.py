"""Login: username case-insensitive (ca email)."""

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AccountProfile

User = get_user_model()


@override_settings(PRELAUNCH_MODE=False, POPULATION_ONBOARDING_ENABLED=False)
class LoginUsernameCaseInsensitiveTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username="ComunaTestUser",
            email="comuna_test@example.com",
            password="Secret12ab",
        )
        AccountProfile.objects.update_or_create(
            user=self.user,
            defaults={"role": AccountProfile.ROLE_ORG, "is_public_shelter": True},
        )

    def test_login_username_wrong_case(self):
        r = self.client.post(
            reverse("login"),
            {"login": "comunatestuser", "password": "Secret12ab"},
            HTTP_HOST="testserver",
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.pk)

    def test_login_email_wrong_case(self):
        self.client.logout()
        r = self.client.post(
            reverse("login"),
            {"login": "COMUNA_TEST@EXAMPLE.COM", "password": "Secret12ab"},
            HTTP_HOST="testserver",
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(int(self.client.session.get("_auth_user_id")), self.user.pk)
