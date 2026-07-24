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
    SiteCartCheckoutIntent,
    SiteCartItem,
)
from home.prelaunch_free_access import (
    promo_a2_price_lei,
    publicitate_effective_slot_map,
    publicitate_max_weeks_per_order,
    publicitate_prelaunch_free_enabled,
    publicitate_temp_superuser_only,
    publicitate_user_can_reserve_slots,
    publicitate_user_has_access,
    publicitate_user_needs_pub_nudge,
    site_cart_skip_payment_form_enabled,
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
        self.assertEqual(publicitate_max_weeks_per_order(), 1)
        eff = publicitate_effective_slot_map(PUBLICITATE_SLOT_MAP)
        self.assertEqual(eff["home"][0]["price"], 0)

    @override_settings(PUBLICITATE_TEMP_SUPERUSER_ONLY=False)
    def test_pub_nudge_for_user_without_active_slot(self):
        user = User.objects.create_user(username=f"nudge_{uuid.uuid4().hex[:6]}", password="x")
        self.assertTrue(publicitate_user_needs_pub_nudge(user))

    @override_settings(PUBLICITATE_TEMP_SUPERUSER_ONLY=True)
    def test_pub_temp_superuser_only_blocks_collab(self):
        from home.prelaunch_free_access import publicitate_user_has_access

        collab = User.objects.create_user(username=f"col_{uuid.uuid4().hex[:6]}", password="x")
        AccountProfile.objects.filter(user=collab).update(role=AccountProfile.ROLE_COLLAB)
        super_u = User.objects.create_superuser(
            username=f"su_{uuid.uuid4().hex[:6]}",
            email=f"su_{uuid.uuid4().hex[:6]}@t.local",
            password="x",
        )
        self.assertFalse(publicitate_user_has_access(collab))
        self.assertTrue(publicitate_user_has_access(super_u))
        self.assertFalse(publicitate_user_needs_pub_nudge(collab))

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

    def test_superuser_unlimited_pub_slots(self):
        from home.prelaunch_free_access import (
            publicitate_user_has_unlimited_slots,
            publicitate_user_slots_remaining,
        )

        su = User.objects.create_superuser(
            username=f"su_pub_{uuid.uuid4().hex[:6]}",
            email=f"su_pub_{uuid.uuid4().hex[:6]}@t.local",
            password="x",
        )
        order = PublicitateOrder.objects.create(
            user=su,
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
        self.assertTrue(publicitate_user_has_unlimited_slots(su))
        self.assertIsNone(publicitate_user_slots_remaining(su))
        ok, msg = publicitate_user_can_reserve_slots(su, 12)
        self.assertTrue(ok)
        self.assertEqual(msg, "")

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

    def test_skip_payment_form_flag_and_period_parse(self):
        from home.views import _site_cart_publicitate_lines_from_checkout

        self.assertTrue(site_cart_skip_payment_form_enabled())
        lines, keys = _site_cart_publicitate_lines_from_checkout(
            [
                {
                    "kind": SiteCartItem.KIND_PUBLICITATE,
                    "ref_key": "pub:0123456789abcdef",
                    "title": "HOME · A5.1 · perioada 2026-07-16 → 2026-07-22 · 0 lei — Home A5.1",
                    "detail_url": "/publicitate/?sect=home&sd=2026-07-16",
                }
            ]
        )
        self.assertEqual(len(lines), 1)
        self.assertEqual(lines[0]["code"], "A5.1")
        self.assertEqual(lines[0]["qty"], 1)
        self.assertEqual(lines[0]["selected_weeks"], ["2026-07-16"])
        self.assertEqual(keys, ["pub:0123456789abcdef"])

    @override_settings(PUBLICITATE_TEMP_SUPERUSER_ONLY=False)
    def test_free_acquire_from_cart_skips_payment_form(self):
        user = User.objects.create_user(
            username=f"acq_{uuid.uuid4().hex[:6]}",
            email=f"acq_{uuid.uuid4().hex[:6]}@t.local",
            password="x",
        )
        AccountProfile.objects.filter(user=user).update(role=AccountProfile.ROLE_COLLAB)
        start = timezone.localdate().isoformat()
        SiteCartItem.objects.create(
            user=user,
            kind=SiteCartItem.KIND_PUBLICITATE,
            ref_key=f"pub:{uuid.uuid4().hex[:16]}",
            title=f"MYPET · MP.L1 · perioada {start} → {start} · 0 lei — MyPet L1",
            detail_url=f"/publicitate/?sect=mypet&sd={start}",
        )
        c = Client()
        c.force_login(user)
        cos = c.get(reverse("i_love_cos"))
        self.assertEqual(cos.status_code, 200)
        self.assertContains(cos, "ACHIZIȚIONEAZĂ")
        self.assertNotContains(cos, ">PLATESTE<")
        r = c.post(reverse("site_cart_free_acquire"))
        self.assertEqual(r.status_code, 302)
        order = PublicitateOrder.objects.filter(user=user, status=PublicitateOrder.STATUS_PAID).first()
        self.assertIsNotNone(order)
        self.assertEqual(r.url, reverse("publicitate_creative_order", args=[order.pk]))
        self.assertEqual(SiteCartItem.objects.filter(user=user).count(), 0)
        self.assertTrue(SiteCartCheckoutIntent.objects.filter(user=user).exists())
