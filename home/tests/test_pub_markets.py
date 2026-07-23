from django.contrib.auth import get_user_model
from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.models import ReclamaSlotNote
from home.pub_markets import (
    PUB_MARKET_EU,
    PUB_MARKET_RO,
    localize_pub_link_for_market,
    pub_market_for_request,
)
from home.pub_slot_defaults import pub_slot_fetch_notes, pub_slot_live_creative


class PubMarketHelpersTests(SimpleTestCase):
    def test_localize_ro_link_on_eu(self):
        self.assertEqual(
            localize_pub_link_for_market("https://eu-adopt.ro/pets/12/", PUB_MARKET_EU),
            "/pets/12/",
        )
        self.assertEqual(
            localize_pub_link_for_market("https://eu-adopt.ro/pets/12/", PUB_MARKET_RO),
            "https://eu-adopt.ro/pets/12/",
        )


@override_settings(EUADOPT_EU_PRODUCT_SKIN=True, EUADOPT_NON_RO_STAFF_ONLY=False, PRELAUNCH_MODE=False)
class PubMarketNotesTests(TestCase):
    def test_ro_and_eu_notes_isolated(self):
        ReclamaSlotNote.objects.create(
            section="home",
            slot_code="A5.1",
            market=PUB_MARKET_RO,
            text='{"img":"/media/ro.jpg","link":"https://example.com","alt":"RO"}',
        )
        ReclamaSlotNote.objects.create(
            section="home",
            slot_code="A5.1",
            market=PUB_MARKET_EU,
            text='{"img":"/media/eu.jpg","link":"https://eu-adopt.ro/pets/1/","alt":"EU","alt_i18n":{"en":"Hello","de":"Hallo"}}',
        )
        ro = pub_slot_fetch_notes("home", ["A5.1"], market=PUB_MARKET_RO)
        eu = pub_slot_fetch_notes("home", ["A5.1"], market=PUB_MARKET_EU)
        self.assertIn("A5.1", ro)
        self.assertIn("A5.1", eu)
        self.assertNotEqual(ro["A5.1"].pk, eu["A5.1"].pk)
        cre_eu = pub_slot_live_creative("home", "A5.1", eu["A5.1"], market=PUB_MARKET_EU, lang="de")
        self.assertEqual(cre_eu["alt"], "Hallo")
        self.assertEqual(cre_eu["link"], "/pets/1/")

    def test_reclama_staff_market_toggle(self):
        User = get_user_model()
        u = User.objects.create_superuser("pub_admin", "a@b.c", "x")
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(u)
        r = c.get(reverse("reclama_staff") + "?market=eu")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Publi EU")
        self.assertContains(r, "reclama-market-toggle")

    def test_superuser_pub_applies_to_eu_market(self):
        from home.models import PublicitateOrder, PublicitateOrderLine
        from home.views import _apply_publicitate_line_to_site, _publicitate_order_target_market

        User = get_user_model()
        su = User.objects.create_superuser("eu_pub_su", "su@b.c", "x")
        other = User.objects.create_user("eu_pub_user", "u@b.c", "x")
        order_su = PublicitateOrder.objects.create(
            user=su, status=PublicitateOrder.STATUS_PAID, total_lei=0
        )
        order_ro = PublicitateOrder.objects.create(
            user=other, status=PublicitateOrder.STATUS_PAID, total_lei=10
        )
        self.assertEqual(_publicitate_order_target_market(order_su), PUB_MARKET_EU)
        self.assertEqual(_publicitate_order_target_market(order_ro), PUB_MARKET_RO)
        line = PublicitateOrderLine.objects.create(
            order=order_su,
            section="home",
            slot_code="A5.1",
            title_snapshot="A5.1",
            unit_label="luna",
            unit_price_lei=0,
            quantity=1,
            line_total_lei=0,
            buyer_note='{"img":"/media/x.jpg","link":"https://eu-adopt.ro/pets/1/","alt":"EU dog"}',
        )
        _apply_publicitate_line_to_site(line, order_su)
        self.assertTrue(
            ReclamaSlotNote.objects.filter(
                section="home", slot_code="A5.1", market=PUB_MARKET_EU
            ).exists()
        )
        self.assertFalse(
            ReclamaSlotNote.objects.filter(
                section="home", slot_code="A5.1", market=PUB_MARKET_RO
            ).exists()
        )

    def test_eu_host_uses_eu_market(self):
        rf = Client(HTTP_HOST="euadopt.com")
        # RequestFactory via client get — use middleware path
        from django.test import RequestFactory
        from home.eu_site import eu_product_skin_enabled

        self.assertTrue(eu_product_skin_enabled())
        req = RequestFactory().get("/", HTTP_HOST="euadopt.com")
        self.assertEqual(pub_market_for_request(req), PUB_MARKET_EU)
        req2 = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        self.assertEqual(pub_market_for_request(req2), PUB_MARKET_RO)
