"""Panou Alerte Analiza — numere live și filtre ?filter=."""
import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse
from django.utils import timezone

from home.admin_analysis_data import (
    FILTER_ACCOUNTS_INACTIVE,
    FILTER_ADOPTION_PENDING_48H,
    staff_analysis_home_alert_rows,
)
from home.models import AdoptionRequest, AnimalListing

User = get_user_model()


class AdminAnalysisAlertsTests(TestCase):
    def setUp(self):
        self.staff = User.objects.create_user(
            username=f"st_{uuid.uuid4().hex[:6]}",
            email="staff@t.local",
            password="Staff61!",
            is_staff=True,
        )
        self.owner = User.objects.create_user(
            username=f"ow_{uuid.uuid4().hex[:6]}",
            email="owner@t.local",
            password="Ow61!",
            is_active=True,
        )
        self.adopter = User.objects.create_user(
            username=f"ad_{uuid.uuid4().hex[:6]}",
            email="adopter@t.local",
            password="Ad61!",
            is_active=True,
        )
        self.animal = AnimalListing.objects.create(
            owner=self.owner,
            name="Rex",
            species="dog",
            is_published=True,
        )

    def test_home_alert_rows_linked(self):
        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(reverse("admin_analysis_home"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "analysis-alert-link")
        self.assertContains(r, "Cereri adopție fără răspuns")
        self.assertContains(r, f'filter={FILTER_ADOPTION_PENDING_48H}')

    def test_adoption_pending_48h_filter_list(self):
        ar = AdoptionRequest.objects.create(
            animal=self.animal,
            adopter=self.adopter,
            status=AdoptionRequest.STATUS_PENDING,
        )
        past = timezone.now() - timezone.timedelta(hours=50)
        AdoptionRequest.objects.filter(pk=ar.pk).update(created_at=past)

        rows = staff_analysis_home_alert_rows()
        adoption_row = next(x for x in rows if "48h" in x["text"])
        self.assertGreaterEqual(adoption_row["count"], 1)

        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(
            reverse("admin_analysis_requests"),
            {"filter": FILTER_ADOPTION_PENDING_48H},
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "analysis-filter-list")
        self.assertContains(r, "Rex")
        self.assertContains(r, "Admin — cerere adopție")
        self.assertContains(r, "/admin/home/adoptionrequest/")

    def test_cats_page_and_romanian_nav(self):
        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(reverse("admin_analysis_cats"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Analiza / Pisici")
        self.assertContains(r, "Pisici</a>")
        self.assertContains(r, "Câini</a>")
        r2 = c.get(reverse("admin_analysis_cats"), {"filter": "cats_no_photo"})
        self.assertContains(r2, "Pisici publice fără poze complete")

    def test_requests_page_kpis_and_panel_links(self):
        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(reverse("admin_analysis_requests"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "requests-kpi-num")
        self.assertContains(r, "Total cereri")
        self.assertContains(r, "Cereri</a>")
        self.assertContains(r, "Pisici</a>")
        self.assertContains(r, "requests-panel-link")
        self.assertContains(r, "filter=adoption_pending_48h")

    def test_inactive_accounts_filter(self):
        User.objects.create_user(
            username=f"in_{uuid.uuid4().hex[:6]}",
            email="inactive@t.local",
            password="In61!",
            is_active=False,
        )
        c = Client()
        c.login(username=self.staff.username, password="Staff61!")
        r = c.get(reverse("admin_analysis_users"), {"filter": FILTER_ACCOUNTS_INACTIVE})
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "inactive@t.local")
