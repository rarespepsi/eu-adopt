"""Pre-lansare: blocare soft Shop, donații, coș comercial (staff poate testa)."""

import json
import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse

from home.models import AnimalListing, SiteCartItem

User = get_user_model()

_SOFT_LOCK_SETTINGS = dict(
    PRELAUNCH_MODE=True,
    PRELAUNCH_MONETIZATION_SOFT_LOCK=True,
    PUBLICITATE_PRELAUNCH_FREE=True,
    POPULATION_ONBOARDING_ENABLED=False,
)


@override_settings(**_SOFT_LOCK_SETTINGS)
class PrelaunchSoftLockTests(TestCase):
    def setUp(self):
        self.client = Client()
        self.user = User.objects.create_user(
            username=f"soft_{uuid.uuid4().hex[:8]}",
            password="x",
        )
        self.staff = User.objects.create_user(
            username=f"staff_{uuid.uuid4().hex[:8]}",
            password="x",
            is_staff=True,
        )

    def test_shop_redirects_for_regular_user(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("shop"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("mypet"))

    def test_donatii_formular_redirects(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("donatii_formular_230"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("mypet"))

    def test_donatii_contract_redirects(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("donatii_contract_sponsorizare"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("mypet"))

    def test_staff_bypass_shop(self):
        self.client.force_login(self.staff)
        resp = self.client.get(reverse("shop"))
        self.assertEqual(resp.status_code, 200)

    def test_cart_toggle_blocks_shop_kind(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("site_cart_toggle"),
            {
                "kind": SiteCartItem.KIND_SHOP,
                "ref_key": "shop:demo:1",
                "title": "Produs test",
            },
        )
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content)
        self.assertFalse(data.get("ok"))

    def test_cart_toggle_allows_publicitate_kind(self):
        self.client.force_login(self.user)
        resp = self.client.post(
            reverse("site_cart_toggle"),
            {
                "kind": SiteCartItem.KIND_PUBLICITATE,
                "ref_key": "pub:0123456789abcdef",
                "title": "Slot test",
            },
        )
        self.assertIn(resp.status_code, (200, 302))

    def test_checkout_blocked_with_shop_in_cart(self):
        SiteCartItem.objects.create(
            user=self.user,
            kind=SiteCartItem.KIND_SHOP,
            ref_key="shop:demo:1",
            title="Produs test",
        )
        self.client.force_login(self.user)
        resp = self.client.get(reverse("site_cart_checkout"))
        self.assertEqual(resp.status_code, 302)
        self.assertEqual(resp.url, reverse("i_love_cos"))

    @override_settings(PRELAUNCH_MONETIZATION_SOFT_LOCK=False)
    def test_soft_lock_off_allows_shop(self):
        self.client.force_login(self.user)
        resp = self.client.get(reverse("shop"))
        self.assertEqual(resp.status_code, 200)

    def test_adoption_request_blocked(self):
        owner = User.objects.create_user(username=f"own_{uuid.uuid4().hex[:8]}", password="x")
        pet = AnimalListing.objects.create(
            owner=owner,
            name="Rex",
            species="dog",
            is_published=True,
        )
        self.client.force_login(self.user)
        resp = self.client.post(reverse("pet_adoption_request", args=[pet.pk]))
        self.assertEqual(resp.status_code, 403)
        data = json.loads(resp.content)
        self.assertFalse(data.get("ok"))
        self.assertIn("populare", (data.get("error") or "").lower())

    def test_pet_ficha_shows_adopt_button_without_inactive_label(self):
        owner = User.objects.create_user(username=f"own2_{uuid.uuid4().hex[:8]}", password="x")
        pet = AnimalListing.objects.create(
            owner=owner,
            name="Mira",
            species="dog",
            is_published=True,
        )
        resp = self.client.get(reverse("pets_single", args=[pet.pk]))
        self.assertEqual(resp.status_code, 200)
        self.assertContains(resp, "VREAU SĂ ADOPT")
        self.assertNotContains(resp, "Inactiv în perioada de populare")
