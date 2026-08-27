"""Formular adopție simplu (EUADOPT_SIMPLE_ADOPTION / soft lock legacy)."""

import json
import uuid
from unittest.mock import patch

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AccountProfile, AnimalListing, UserProfile
from home.population_simple_adoption import (
    _parse_phone_for_form,
    adoption_form_prefill_for_user,
    parse_population_adoption_form,
    population_simple_adoption_active_for_user,
)

User = get_user_model()

_SIMPLE_ON = dict(
    SIMPLE_ADOPTION_ENABLED=True,
    PRELAUNCH_MODE=False,
    PRELAUNCH_MONETIZATION_SOFT_LOCK=False,
    POPULATION_ONBOARDING_ENABLED=False,
)


@override_settings(**_SIMPLE_ON)
class PopulationSimpleAdoptionTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.owner = User.objects.create_user(
            username=f"own_{uuid.uuid4().hex[:8]}",
            password="x",
            email="owner@test.example",
        )
        self.adopter = User.objects.create_user(
            username=f"adp_{uuid.uuid4().hex[:8]}",
            password="x",
            email="adopter@test.example",
            first_name="Ana",
            last_name="Pop",
        )
        UserProfile.objects.create(
            user=self.adopter,
            phone="+40 712345678",
            judet="Iași",
            oras="Iași",
            accept_termeni=True,
            accept_gdpr=True,
        )
        self.pet = AnimalListing.objects.create(
            owner=self.owner,
            name="Rex",
            species="dog",
            is_published=True,
            county="Iași",
            city="Iași",
        )
        self.staff = User.objects.create_user(
            username=f"staff_{uuid.uuid4().hex[:8]}",
            password="x",
            is_staff=True,
            email="staff@test.example",
        )

    def test_simple_mode_active_for_regular_user(self):
        self.assertTrue(population_simple_adoption_active_for_user(self.adopter))

    def test_simple_mode_off_for_staff(self):
        self.assertFalse(population_simple_adoption_active_for_user(self.staff))

    def test_prefill_from_profile(self):
        pre = adoption_form_prefill_for_user(self.adopter)
        self.assertEqual(pre["last_name"], "Pop")
        self.assertEqual(pre["first_name"], "Ana")
        self.assertEqual(pre["judet"], "Iași")
        self.assertEqual(pre["phone_country"], "+40")
        self.assertEqual(pre["phone"], "712345678")

    def test_parse_phone_strips_ro_leading_zero(self):
        self.assertEqual(_parse_phone_for_form("0740841234"), ("+40", "740841234"))
        self.assertEqual(_parse_phone_for_form("+40 0740841234"), ("+40", "740841234"))
        self.assertEqual(_parse_phone_for_form("+40740841234"), ("+40", "740841234"))

    def test_submit_strips_ro_leading_zero_in_phone(self):
        data, errors = parse_population_adoption_form(
            {
                "last_name": "Pop",
                "first_name": "Ana",
                "email": "a@test.example",
                "phone_country": "+40",
                "phone": "0740841234",
                "judet": "Iași",
                "oras": "Iași",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            }
        )
        self.assertEqual(errors, [])
        self.assertIsNotNone(data)
        self.assertEqual(data.phone, "740841234")
        self.assertEqual(data.phone_display, "+40 740841234")

    def test_ficha_shows_active_button_not_inactive(self):
        self.client.force_login(self.adopter)
        resp = self.client.get(reverse("pets_single", args=[self.pet.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "VREAU SĂ ADOPT")
        self.assertNotContains(resp, "Inactiv în perioada de populare")
        self.assertContains(resp, 'id="petPopAdoptFormModal"')
        self.assertContains(resp, 'data-simple-populare="1"')

    def test_old_adoption_request_still_blocked(self):
        self.client.force_login(self.adopter)
        resp = self.client.post(reverse("pet_adoption_request", args=[self.pet.pk]))
        self.assertEqual(resp.status_code, 403)

    @patch("home.population_simple_adoption.send_mail_text_and_html")
    def test_population_form_submit_sends_emails(self, mock_mail):
        self.client.force_login(self.adopter)
        resp = self.client.post(
            reverse("pet_population_adoption_submit", args=[self.pet.pk]),
            {
                "last_name": "Pop",
                "first_name": "Ana",
                "email": "adopter@test.example",
                "phone_country": "+40",
                "phone": "712345678",
                "judet": "Iași",
                "oras": "Iași",
                "mesaj": "Doresc să adopt.",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(mock_mail.call_count, 2)

    def test_population_form_requires_login(self):
        resp = self.client.post(reverse("pet_population_adoption_submit", args=[self.pet.pk]))
        self.assertEqual(resp.status_code, 302)

    def test_parse_form_validation(self):
        data, errors = parse_population_adoption_form({})
        self.assertIsNone(data)
        self.assertTrue(errors)

    @patch("home.population_simple_adoption.send_mail_text_and_html")
    def test_org_public_shelter_may_submit_population_form(self, mock_mail):
        org_user = User.objects.create_user(
            username=f"org_{uuid.uuid4().hex[:8]}",
            password="x",
            email="org@test.example",
            first_name="Nicol",
            last_name="Test",
        )
        ap, _ = AccountProfile.objects.get_or_create(
            user=org_user,
            defaults={"role": AccountProfile.ROLE_ORG},
        )
        ap.role = AccountProfile.ROLE_ORG
        ap.is_public_shelter = True
        ap.save(update_fields=["role", "is_public_shelter"])
        self.assertTrue(ap.can_adopt_animals)

        self.client.force_login(org_user)
        resp = self.client.post(
            reverse("pet_population_adoption_submit", args=[self.pet.pk]),
            {
                "last_name": "Test",
                "first_name": "Nicol",
                "email": "org@test.example",
                "phone_country": "+40",
                "phone": "712345678",
                "judet": "Iași",
                "oras": "Iași",
                "accept_termeni": "on",
                "accept_gdpr": "on",
            },
        )
        self.assertEqual(resp.status_code, 200)
        data = json.loads(resp.content)
        self.assertTrue(data.get("ok"))
        self.assertGreaterEqual(mock_mail.call_count, 2)

    def test_collaborator_blocked_and_no_adopt_button_on_ficha(self):
        collab = User.objects.create_user(
            username=f"col_{uuid.uuid4().hex[:8]}",
            password="x",
            email="col@test.example",
        )
        ap, _ = AccountProfile.objects.get_or_create(
            user=collab,
            defaults={"role": AccountProfile.ROLE_COLLAB},
        )
        ap.role = AccountProfile.ROLE_COLLAB
        ap.save(update_fields=["role"])
        self.assertFalse(ap.can_adopt_animals)

        self.client.force_login(collab)
        resp = self.client.get(reverse("pets_single", args=[self.pet.pk]), follow=True)
        self.assertEqual(resp.status_code, 200)
        self.assertNotContains(resp, "VREAU SĂ ADOPT")

        resp = self.client.post(reverse("pet_population_adoption_submit", args=[self.pet.pk]))
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content)
        self.assertIn("Tipul de cont", data.get("error", ""))
