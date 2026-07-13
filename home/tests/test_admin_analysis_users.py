"""Panou Utilizatori Analiza — identitate rol + listă filtre."""
import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.admin_analysis_data import (
    ADMIN_USER_ACTION_LABEL,
    FILTER_USERS_ORG,
    _user_filter_item,
)
from home.models import AccountProfile, UserProfile

User = get_user_model()


class AdminAnalysisUsersIdentityTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username=f"st_{uuid.uuid4().hex[:6]}",
            email="staff@t.local",
            password="Staff61!",
            is_staff=True,
        )

    def test_org_user_shows_identity_not_admin_label(self):
        user = User.objects.create_user(
            username="andreitudor",
            email="andreitudor@t.local",
            password="Xx61!",
            first_name="Andrei Tudor",
            last_name="SCA Protect Animale",
            is_active=True,
        )
        AccountProfile.objects.filter(user=user).update(
            role=AccountProfile.ROLE_ORG,
            is_public_shelter=False,
        )
        user.refresh_from_db()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={
                "company_display_name": "SCA Protect Animale",
                "company_legal_name": "SCA Protect Animale SRL",
                "judet": "Neamț",
                "oras": "Piatra Neamț",
            },
        )
        user = User.objects.select_related("account_profile", "profile").get(pk=user.pk)
        row = _user_filter_item(user)
        self.assertIn("[ONG]", row["primary"])
        self.assertIn("Andrei Tudor", row["primary"])
        self.assertIn("SCA Protect Animale", row["primary"])
        self.assertIn("andreitudor@t.local", row["primary"])
        self.assertIn("ONG / Adăpost / Firmă", row["secondary"])
        self.assertEqual(row["action_label"], ADMIN_USER_ACTION_LABEL)
        self.assertNotIn("Admin — cont utilizator", row["action_label"])

    def test_users_org_filter_page(self):
        user = User.objects.create_user(
            username=f"org_{uuid.uuid4().hex[:6]}",
            email="ong@t.local",
            password="Org61!",
            first_name="Contact ONG",
            last_name="Adăpost Test",
            is_active=True,
        )
        AccountProfile.objects.filter(user=user).update(role=AccountProfile.ROLE_ORG)
        user.refresh_from_db()
        UserProfile.objects.update_or_create(
            user=user,
            defaults={"company_display_name": "Adăpost Test"},
        )

        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(reverse("admin_analysis_users"), {"filter": FILTER_USERS_ORG})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "[ONG]")
        self.assertContains(r, "Adăpost Test")
        self.assertContains(r, ADMIN_USER_ACTION_LABEL)
        self.assertNotContains(r, "Admin — cont utilizator")
