"""Pre-lansare: publicitate și promovare gratuite + limite per user."""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import (
    AccountProfile,
    AnimalListing,
    CollaboratorServiceOffer,
    PromoA2Order,
    PublicitateOrder,
    PublicitateOrderLine,
    StaffOnboardingLead,
)
from home.prelaunch_free_access import (
    promo_a2_price_lei,
    publicitate_effective_slot_map,
    publicitate_prelaunch_free_enabled,
    publicitate_user_can_reserve_slots,
)

User = get_user_model()


@override_settings(
    PUBLICITATE_PRELAUNCH_FREE=True,
    PRELAUNCH_MODE=True,
    POPULATION_ONBOARDING_ENABLED=False,
)
class PrelaunchFreeAccessTests(TestCase):
    def test_prices_zero_when_prelaunch_free(self):
        from home.views import PUBLICITATE_SLOT_MAP

        self.assertTrue(publicitate_prelaunch_free_enabled())
        self.assertEqual(promo_a2_price_lei(), 0)
        eff = publicitate_effective_slot_map(PUBLICITATE_SLOT_MAP)
        self.assertEqual(eff["home"][0]["price"], 0)

    def test_publicitate_user_slot_limit(self):
        user = User.objects.create_user(username=f"pubu_{uuid.uuid4().hex[:6]}", password="x")
        order = PublicitateOrder.objects.create(
            user=user,
            status=PublicitateOrder.STATUS_PAID,
            total_lei=0,
            payment_provider="prelaunch_free",
            paid_at=timezone.now(),
        )
        PublicitateOrderLine.objects.create(
            order=order,
            section="mypet",
            slot_code="MP.L1",
            title_snapshot="MyPet L1",
            unit_label="saptamana",
            unit_price_lei=0,
            quantity=1,
            line_total_lei=0,
            ends_at=timezone.now() + timezone.timedelta(days=7),
        )
        ok, msg = publicitate_user_can_reserve_slots(user, 1)
        self.assertFalse(ok)
        self.assertIn("caseta", msg.lower())

    def test_collab_offer_limit(self):
        user = User.objects.create_user(username=f"col_{uuid.uuid4().hex[:6]}", password="x")
        AccountProfile.objects.filter(user=user).update(role=AccountProfile.ROLE_COLLAB)
        CollaboratorServiceOffer.objects.create(
            collaborator=user,
            partner_kind=CollaboratorServiceOffer.PARTNER_KIND_SERVICII,
            title="Serviciu 1",
            description="Test",
            price_hint="100 lei",
            discount_percent=10,
            is_active=True,
        )
        c = Client()
        c.force_login(user)
        r = c.post(
            reverse("collab_offer_add"),
            {
                "title": "Serviciu 2",
                "description": "Alt serviciu",
                "price_hint": "50 lei",
                "discount_percent": "5",
                "species_dog": "on",
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CollaboratorServiceOffer.objects.filter(collaborator=user).count(), 1)

    def test_promo_a2_limit_after_paid(self):
        user = User.objects.create_user(
            username=f"pf_{uuid.uuid4().hex[:6]}",
            email=f"pf_{uuid.uuid4().hex[:6]}@t.local",
            password="x",
        )
        pet = AnimalListing.objects.create(
            owner=user,
            name="Rex",
            species="dog",
            is_published=True,
        )
        PromoA2Order.objects.create(
            pet=pet,
            payer_user=user,
            payer_email=user.email,
            package=PromoA2Order.PACKAGE_A2_24,
            quantity=1,
            unit_price=0,
            total_price=0,
            status=PromoA2Order.STATUS_PAID,
            payment_provider="prelaunch_free",
            slot_code="A2.1",
            start_date=timezone.localdate(),
        )
        pet2 = AnimalListing.objects.create(
            owner=user,
            name="Mia",
            species="cat",
            is_published=True,
        )
        c = Client()
        c.force_login(user)
        r = c.post(reverse("promo_a2_order", args=[pet2.pk]))
        self.assertEqual(r.status_code, 302)
        self.assertIn(reverse("promo_a2_order", args=[pet2.pk]), r.url)
