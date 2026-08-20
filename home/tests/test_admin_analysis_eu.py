from django.contrib.auth import get_user_model
from django.test import Client, TestCase
from django.urls import reverse

from home.admin_analysis_eu import (
    build_eu_market_analysis_context,
    eu_user_ids_for_market,
    normalize_eu_market,
)
from home.models import AccountProfile, AdoptionRequest, AnimalListing, UserProfile


class AdminAnalysisEuTests(TestCase):
    def setUp(self):
        User = get_user_model()
        self.superuser = User.objects.create_superuser(
            "su_eu", "su_eu@test.local", "SuEuPass12!"
        )
        self.staff = User.objects.create_user(
            "staff_eu", "staff_eu@test.local", "StaffEu12!", is_staff=True
        )
        self.de_user = User.objects.create_user("de_u", "de@t.local", "PassEu12x!")
        UserProfile.objects.update_or_create(user=self.de_user, defaults={"country": "DE"})
        AccountProfile.objects.update_or_create(
            user=self.de_user, defaults={"role": AccountProfile.ROLE_PF}
        )
        self.es_user = User.objects.create_user("es_u", "es@t.local", "PassEu12x!")
        UserProfile.objects.update_or_create(user=self.es_user, defaults={"country": "ES"})
        self.it_user = User.objects.create_user("it_u", "it@t.local", "PassEu12x!")
        UserProfile.objects.update_or_create(user=self.it_user, defaults={"country": "IT"})
        self.ro_user = User.objects.create_user("ro_u", "ro@t.local", "PassEu12x!")
        UserProfile.objects.update_or_create(user=self.ro_user, defaults={"country": "RO"})

    def test_normalize_market(self):
        self.assertEqual(normalize_eu_market("DE"), "de")
        self.assertIsNone(normalize_eu_market("xx"))

    def test_market_user_split(self):
        self.assertIn(self.de_user.pk, eu_user_ids_for_market("de"))
        self.assertNotIn(self.es_user.pk, eu_user_ids_for_market("de"))
        self.assertIn(self.es_user.pk, eu_user_ids_for_market("es"))
        self.assertIn(self.it_user.pk, eu_user_ids_for_market("com"))
        self.assertNotIn(self.de_user.pk, eu_user_ids_for_market("com"))
        self.assertNotIn(self.ro_user.pk, eu_user_ids_for_market("eu"))
        eu_ids = eu_user_ids_for_market("eu")
        self.assertIn(self.de_user.pk, eu_ids)
        self.assertIn(self.es_user.pk, eu_ids)
        self.assertIn(self.it_user.pk, eu_ids)

    def test_eu_sums_markets(self):
        de = build_eu_market_analysis_context("de")["kpi_users_total"]
        es = build_eu_market_analysis_context("es")["kpi_users_total"]
        fr = build_eu_market_analysis_context("fr")["kpi_users_total"]
        com = build_eu_market_analysis_context("com")["kpi_users_total"]
        eu = build_eu_market_analysis_context("eu")["kpi_users_total"]
        self.assertEqual(eu, de + es + fr + com)

    def test_hub_superuser_ok_staff_blocked(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(self.staff)
        r = c.get(reverse("admin_analysis_eu_hub"))
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("home"))
        c.force_login(self.superuser)
        r2 = c.get(reverse("admin_analysis_eu_hub"))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Prezență EU")
        self.assertContains(r2, "ES")
        self.assertContains(r2, "COM")

    def test_market_page_and_button_on_home(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(self.superuser)
        r = c.get(reverse("admin_analysis_eu_market", kwargs={"market": "de"}))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "DE")
        r_home = c.get(reverse("admin_analysis_home"))
        self.assertContains(r_home, "PREZENȚĂ EU")
        c.force_login(self.staff)
        r_staff_home = c.get(reverse("admin_analysis_home"))
        self.assertNotContains(r_staff_home, "PREZENȚĂ EU")

    def test_adoption_counted_for_eu_adopter(self):
        owner = get_user_model().objects.create_user("own", "o@t.local", "PassEu12x!")
        listing = AnimalListing.objects.create(
            owner=owner, name="Rex", species="dog", is_published=True
        )
        AdoptionRequest.objects.create(animal=listing, adopter=self.de_user)
        ctx = build_eu_market_analysis_context("de")
        self.assertEqual(ctx["kpi_adopt_total"], 1)
        self.assertEqual(build_eu_market_analysis_context("eu")["kpi_adopt_total"], 1)
        self.assertEqual(build_eu_market_analysis_context("es")["kpi_adopt_total"], 0)
