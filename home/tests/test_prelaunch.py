"""
Mod PRE-LAUNCH (EUADOPT_PRELAUNCH_MODE): acces anonim restricționat.
Rulează: python manage.py test home.tests.test_prelaunch
"""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AnimalListing

User = get_user_model()


@override_settings(PRELAUNCH_MODE=False)
class PrelaunchDisabledTests(TestCase):
    def test_anonymous_can_view_home(self):
        c = Client()
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_anonymous_can_view_signup(self):
        c = Client()
        r = c.get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 200)


@override_settings(PRELAUNCH_MODE=True, POPULATION_ONBOARDING_ENABLED=False)
class PrelaunchEnabledTests(TestCase):
    def setUp(self):
        u = uuid.uuid4().hex[:10]
        self.user = User.objects.create_user(
            username=f"prelaunch_{u}",
            email=f"prelaunch_{u}@test.local",
            password="Prelaunch_Pass12",
        )
        self.user.is_active = True
        self.user.save()

    def test_anonymous_home_redirects_login(self):
        c = Client()
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_anonymous_pets_redirects_login(self):
        c = Client()
        r = c.get(reverse("pets_all"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_anonymous_pet_ficha_accessible(self):
        listing = AnimalListing.objects.create(
            owner=self.user,
            name="Rex",
            species="dog",
            is_published=True,
        )
        c = Client()
        r = c.get(reverse("pets_single", args=[listing.pk]))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Rex", r.content)

    def test_anonymous_pets_p2_more_still_blocked(self):
        c = Client()
        r = c.get("/pets/p2-more/")
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_anonymous_signup_blocked(self):
        c = Client()
        r = c.get(reverse("signup_choose_type"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_anonymous_signup_pf_blocked(self):
        c = Client()
        r = c.get(reverse("signup_pf"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)

    def test_login_page_accessible(self):
        c = Client()
        r = c.get(reverse("login"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"PRE-LAUNCH", r.content)

    def test_login_hides_signup_link(self):
        c = Client()
        r = c.get(reverse("login"))
        self.assertNotIn(b'class="login-links"', r.content)

    def test_forgot_password_accessible(self):
        c = Client()
        r = c.get(reverse("forgot_password"))
        self.assertEqual(r.status_code, 200)

    def test_activation_status_accessible(self):
        c = Client()
        r = c.get(reverse("signup_check_activation_status"))
        self.assertEqual(r.status_code, 200)

    def test_authenticated_user_can_view_home(self):
        c = Client()
        c.login(username=self.user.username, password="Prelaunch_Pass12")
        r = c.get(reverse("home"))
        self.assertEqual(r.status_code, 200)

    def test_logout_redirects_to_login(self):
        c = Client()
        c.login(username=self.user.username, password="Prelaunch_Pass12")
        r = c.get(reverse("logout"))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/login/", r.url)
        r2 = c.get(reverse("home"))
        self.assertEqual(r2.status_code, 302)
        self.assertIn("/login/", r2.url)
