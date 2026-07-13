from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from home.models import SitePresenceDaily, SitePresenceDaySession
from home.site_presence import (
    ONLINE_WINDOW_MINUTES,
    record_site_presence,
    staff_analysis_presence_page_context,
)


class SitePresenceTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="staff_presence",
            password="TestPresence1!",
            is_staff=True,
        )
        self.client = Client()

    def test_record_increments_daily_stats(self):
        request = self.client.get("/login/").wsgi_request
        record_site_presence(request)
        today = timezone.localdate()
        daily = SitePresenceDaily.objects.get(date=today)
        self.assertGreaterEqual(daily.page_views, 1)
        self.assertGreaterEqual(daily.unique_visitors, 1)
        self.assertTrue(
            SitePresenceDaySession.objects.filter(day=today).exists()
        )

    def test_presence_page_staff_only(self):
        r = self.client.get(reverse("admin_analysis_presence"))
        self.assertEqual(r.status_code, 302)
        self.client.login(username="staff_presence", password="TestPresence1!")
        r2 = self.client.get(reverse("admin_analysis_presence"))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Prezență")
        self.assertContains(r2, "Vizitatori online")

    def test_presence_context_structure(self):
        ctx = staff_analysis_presence_page_context()
        self.assertIn("presence_online_visitors", ctx)
        self.assertIn("presence_week_visitors", ctx)
        self.assertIn("presence_year_visitors", ctx)
        self.assertGreaterEqual(len(ctx["presence_recent_days"]), 1)
        self.assertEqual(ctx["presence_online_window"], ONLINE_WINDOW_MINUTES)

    def test_skips_static_paths(self):
        before = SitePresenceDaily.objects.count()
        request = self.client.get("/static/css/style.css").wsgi_request
        record_site_presence(request)
        self.assertEqual(SitePresenceDaily.objects.count(), before)

    def test_reset_site_presence_clears_tables(self):
        request = self.client.get("/login/").wsgi_request
        record_site_presence(request)
        self.assertGreater(SitePresenceDaily.objects.count(), 0)
        from home.site_presence import reset_site_presence_data

        reset_site_presence_data()
        self.assertEqual(SitePresenceDaily.objects.count(), 0)
        self.assertEqual(SitePresenceDaySession.objects.count(), 0)
