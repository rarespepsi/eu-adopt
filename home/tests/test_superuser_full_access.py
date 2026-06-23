"""Superuser: acces complet UI (excepție permanentă față de rol profil)."""
from __future__ import annotations

import uuid

from django.contrib.auth import get_user_model
from django.test import RequestFactory, TestCase, override_settings

from home.models import AccountProfile, AnimalListing
from home.population_onboarding import (
    is_superuser_full_access,
    population_ui_restricted_for_user,
    user_may_adopt_animals,
)
from home.pt_p2_list import pt_pets_page_context

User = get_user_model()


@override_settings(PRELAUNCH_MODE=True, POPULATION_ONBOARDING_ENABLED=True)
class SuperuserFullAccessTests(TestCase):
    def setUp(self):
        u = uuid.uuid4().hex[:8]
        self.superuser = User.objects.create_superuser(
            username=f"su_{u}",
            email=f"su_{u}@test.local",
            password="Su_Pass_12345",
        )
        AccountProfile.objects.filter(user=self.superuser).update(role=AccountProfile.ROLE_COLLAB)
        self.owner = User.objects.create_user(
            username=f"own_{u}",
            email=f"own_{u}@test.local",
            password="Own_Pass_12345",
        )
        AccountProfile.objects.filter(user=self.owner).update(role=AccountProfile.ROLE_ORG)
        self.listing = AnimalListing.objects.create(
            owner=self.owner,
            name="TestPet",
            species="dog",
            is_published=True,
            adoption_state=AnimalListing.ADOPTION_STATE_FREE,
        )

    def test_superuser_flags(self):
        self.assertTrue(is_superuser_full_access(self.superuser))
        self.assertFalse(population_ui_restricted_for_user(self.superuser))
        self.assertTrue(user_may_adopt_animals(self.superuser))

    def test_pt_plic_visible_for_superuser_on_foreign_listing(self):
        rf = RequestFactory()
        req = rf.get("/pets/")
        req.user = self.superuser
        ctx = pt_pets_page_context(req)
        match = next((p for p in ctx["p2_list"] if p.get("pk") == self.listing.pk), None)
        self.assertIsNotNone(match)
        self.assertTrue(match.get("show_pt_ask_plic"))
