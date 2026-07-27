"""Anunțuri animal DEMO — fără buton adopție, fără cerere adopție."""

import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.demo_listings import DEMO_ADOPTION_INACTIVE_MESSAGE, is_demo_animal_listing
from home.models import AnimalListing

User = get_user_model()

_SOFT_LOCK = dict(
    PRELAUNCH_MODE=True,
    PRELAUNCH_MONETIZATION_SOFT_LOCK=True,
    POPULATION_ONBOARDING_ENABLED=False,
    EUADOPT_DEMO_ANIMAL_OWNER_USERNAMES=("rarespepsi",),
    EUADOPT_NON_RO_STAFF_ONLY=False,
)


@override_settings(**_SOFT_LOCK)
class DemoAnimalListingAdoptionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.demo_owner = User.objects.create_user(
            username="rarespepsi",
            password="x",
            email="demo-owner@test.example",
        )
        self.real_owner = User.objects.create_user(
            username=f"real_{uuid.uuid4().hex[:8]}",
            password="x",
            email="real-owner@test.example",
        )
        self.adopter = User.objects.create_user(
            username=f"adp_{uuid.uuid4().hex[:8]}",
            password="x",
            email="adopter@test.example",
        )
        self.demo_pet = AnimalListing.objects.create(
            owner=self.demo_owner,
            name="Charlie",
            species="dog",
            is_published=True,
            county="Neamț",
            city="Piatra Neamț",
        )
        self.real_pet = AnimalListing.objects.create(
            owner=self.real_owner,
            name="RealDog",
            species="dog",
            is_published=True,
            county="Iași",
            city="Iași",
        )

    def test_is_demo_by_owner_username(self):
        self.assertTrue(is_demo_animal_listing(self.demo_pet))

    def test_is_demo_by_seed_prefix(self):
        seed = AnimalListing.objects.create(
            owner=self.real_owner,
            name="[seed] test-dog",
            species="dog",
            is_published=True,
        )
        self.assertTrue(is_demo_animal_listing(seed))
        self.assertFalse(is_demo_animal_listing(self.real_pet))

    def test_is_demo_by_owner_keyword(self):
        demo_kw_owner = User.objects.create_user(
            username=f"demo_user_{uuid.uuid4().hex[:6]}",
            password="x",
            email="demo-kw@test.example",
        )
        kw_pet = AnimalListing.objects.create(
            owner=demo_kw_owner,
            name="Bella",
            species="dog",
            is_published=True,
        )
        self.assertTrue(is_demo_animal_listing(kw_pet))

    def test_ficha_hides_demo_adopt_button(self):
        self.client.force_login(self.adopter)
        resp = self.client.get(reverse("pets_single", args=[self.demo_pet.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'id="petAdoptCorner"')

    def test_ficha_real_pet_still_shows_adopt_for_anonymous(self):
        self.client.force_login(self.adopter)
        resp = self.client.get(reverse("pets_single", args=[self.real_pet.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "VREAU SĂ ADOPT")

    def test_ficha_demo_hides_adopt_corner_on_eu(self):
        self.client.force_login(self.adopter)
        resp = self.client.get(
            reverse("pets_single", args=[self.demo_pet.pk]),
            HTTP_HOST="euadopt.com",
            follow=True,
        )
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, 'id="petAdoptCorner"')

    @patch("home.population_simple_adoption.send_mail_text_and_html")
    def test_demo_submit_blocked(self, mock_mail):
        self.client.force_login(self.adopter)
        resp = self.client.post(
            reverse("pet_population_adoption_submit", args=[self.demo_pet.pk]),
            {
                "last_name": "Pop",
                "first_name": "Ana",
                "email": "adopter@test.example",
                "phone_country": "+40",
                "phone": "712345678",
                "judet": "Iași",
                "oras": "Iași",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            },
        )
        self.assertEqual(resp.status_code, 403)
        mock_mail.assert_not_called()
        self.assertIn("DEMO", resp.json().get("error", ""))
        self.assertIn(DEMO_ADOPTION_INACTIVE_MESSAGE, resp.json().get("error", ""))
