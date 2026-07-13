"""T₀ campanie — contor logări și KPI staff."""

import uuid
from datetime import timedelta

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.metrics_t0 import metrics_t0_staff_context, record_site_login_event
from home.models import AccountProfile, SiteLoginEvent, StaffOnboardingLead

User = get_user_model()

_T0_SETTINGS = dict(
    METRICS_T0_DATE="2026-07-13",
    PRELAUNCH_MODE=True,
    POPULATION_ONBOARDING_ENABLED=False,
)


@override_settings(**_T0_SETTINGS)
class MetricsT0Tests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username=f"staff_{uuid.uuid4().hex[:6]}",
            password="x",
            is_staff=True,
        )
        self.client = Client()

    def test_login_event_recorded_for_regular_user(self):
        user = User.objects.create_user(username=f"u_{uuid.uuid4().hex[:6]}", password="x")
        record_site_login_event(user, SiteLoginEvent.SOURCE_LOGIN)
        self.assertEqual(SiteLoginEvent.objects.filter(user=user).count(), 1)

    def test_staff_login_not_recorded(self):
        record_site_login_event(self.staff, SiteLoginEvent.SOURCE_LOGIN)
        self.assertEqual(SiteLoginEvent.objects.count(), 0)

    def test_login_view_records_event(self):
        user = User.objects.create_user(username=f"login_{uuid.uuid4().hex[:6]}", password="Secret12!")
        AccountProfile.objects.filter(user=user).update(role=AccountProfile.ROLE_ORG)
        r = self.client.post(
            reverse("login"),
            {"login": user.username, "password": "Secret12!"},
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(SiteLoginEvent.objects.filter(user=user).count(), 1)

    def test_metrics_context_counts_since_t0(self):
        t0 = timezone.datetime(2026, 7, 13, 8, 0, 0)
        t0 = timezone.make_aware(t0, timezone.get_current_timezone())
        user = User.objects.create_user(username=f"nu_{uuid.uuid4().hex[:6]}", password="x")
        User.objects.filter(pk=user.pk).update(date_joined=t0 + timedelta(hours=1))
        user.refresh_from_db()
        SiteLoginEvent.objects.create(user=user, source=SiteLoginEvent.SOURCE_LOGIN)
        StaffOnboardingLead.objects.create(
            email=f"lead_{uuid.uuid4().hex[:6]}@test.local",
            display_name="Test Lead",
            account_kind=StaffOnboardingLead.KIND_ORG,
            invite_staff_notes="Sursă: formular /inscriere/ (Facebook)",
        )
        ctx = metrics_t0_staff_context()
        self.assertTrue(ctx["metrics_t0_enabled"])
        self.assertGreaterEqual(ctx["metrics_t0_new_users"], 1)
        self.assertGreaterEqual(ctx["metrics_t0_login_events"], 1)
        self.assertGreaterEqual(ctx["metrics_t0_inscriere_leads"], 1)

    def test_presence_page_shows_t0_block(self):
        self.client.force_login(self.staff)
        r = self.client.get(reverse("admin_analysis_presence"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "T₀ campanie")
        self.assertContains(r, "Lead-uri /inscriere/")
