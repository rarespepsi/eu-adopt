from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.admin_analysis_data import (
    FILTER_USERS_ALL_ACTIVE,
    FILTER_USERS_STAFF,
    staff_analysis_users_kpis,
    staff_analysis_users_page_context,
)


class AdminAnalysisUsersTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.staff = User.objects.create_user(
            username="rares",
            password="TestUsers1!",
            is_staff=True,
            is_superuser=True,
            is_active=True,
        )
        self.pf = User.objects.create_user(
            username="rarespepsi",
            password="TestUsers1!",
            is_active=True,
        )
        self.client = Client()
        self.client.login(username="rares", password="TestUsers1!")

    def test_kpis_include_staff_in_total(self):
        kpis = staff_analysis_users_kpis()
        self.assertGreaterEqual(kpis["total"], 2)
        self.assertGreaterEqual(kpis["staff"], 1)

    def test_kpi_links_show_user_list(self):
        ctx = staff_analysis_users_page_context(FILTER_USERS_ALL_ACTIVE)
        self.assertEqual(ctx["analysis_filter"], FILTER_USERS_ALL_ACTIVE)
        self.assertGreaterEqual(ctx["analysis_filter_total"], 2)
        self.assertGreaterEqual(len(ctx["analysis_filter_items"]), 2)

    def test_staff_filter_lists_superuser(self):
        ctx = staff_analysis_users_page_context(FILTER_USERS_STAFF)
        self.assertGreaterEqual(ctx["analysis_filter_total"], 1)
        labels = " ".join(i["primary"] for i in ctx["analysis_filter_items"])
        self.assertIn("rares", labels)

    def test_users_page_renders_kpi_links(self):
        r = self.client.get(reverse("admin_analysis_users"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Total activi")
        self.assertContains(r, f"filter={FILTER_USERS_ALL_ACTIVE}")
