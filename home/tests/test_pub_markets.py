from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
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

    def test_superuser_pub_applies_to_ro_market(self):
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
        self.assertEqual(_publicitate_order_target_market(order_su), PUB_MARKET_RO)
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
            buyer_note='{"img":"/media/x.jpg","link":"https://eu-adopt.ro/pets/1/","alt":"RO dog"}',
        )
        _apply_publicitate_line_to_site(line, order_su)
        self.assertTrue(
            ReclamaSlotNote.objects.filter(
                section="home", slot_code="A5.1", market=PUB_MARKET_RO
            ).exists()
        )
        self.assertFalse(
            ReclamaSlotNote.objects.filter(
                section="home", slot_code="A5.1", market=PUB_MARKET_EU
            ).exists()
        )

    def test_eu_direct_publish_superuser_only(self):
        User = get_user_model()
        su = User.objects.create_superuser("eu_direct_su", "d@b.c", "x")
        normal = User.objects.create_user("eu_direct_u", "n@b.c", "x")
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(normal)
        r = c.get(reverse("publicitate_eu_direct"))
        self.assertEqual(r.status_code, 302)
        c.force_login(su)
        r = c.get(reverse("publicitate_eu_direct"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "PUB EU")
        self.assertContains(r, "pub-eu-quad")
        self.assertContains(r, "pub-home-wire-clip")
        self.assertContains(r, "Postează")
        r2 = c.get(reverse("publicitate_eu_direct") + "?sect=home&slot=A5.1")
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "pub-eu-cal-day")
        self.assertContains(r2, "pub-eu-cal-month")
        tiny = SimpleUploadedFile(
            "eu.png", b"\x89PNG\r\n\x1a\n" + b"0" * 40, content_type="image/png"
        )
        r = c.post(
            reverse("publicitate_eu_direct"),
            {
                "sect": "home",
                "slot": "A5.1",
                "action": "publish",
                "start_date": "2026-07-23",
                "end_date": "2027-07-23",
                "link": "https://euadopt.com/pets/",
                "alt": "Adopt",
                "keep_media": "0",
                "image": tiny,
            },
        )
        self.assertEqual(r.status_code, 302)
        note = ReclamaSlotNote.objects.get(section="home", slot_code="A5.1", market=PUB_MARKET_EU)
        self.assertIn("Adopt", note.text)
        r3 = c.get(reverse("publicitate_eu_direct") + "?sect=home")
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, "eu-wire-previews-json")
        self.assertIn("A5.1", r3.context["eu_wire_previews"])
        self.assertTrue(r3.context["eu_wire_previews"]["A5.1"].get("occupied"))
        self.assertTrue((r3.context["eu_wire_previews"]["A5.1"].get("image_url") or "").startswith("/media/"))

    def test_normalize_pub_link_http_and_www(self):
        from home.pub_slot_defaults import normalize_pub_outbound_link, pub_slot_live_creative
        from home.models import ReclamaSlotNote

        self.assertEqual(
            normalize_pub_outbound_link("www.facebook.com/page"),
            "https://www.facebook.com/page",
        )
        self.assertEqual(
            normalize_pub_outbound_link("http://example.com/a"),
            "http://example.com/a",
        )
        self.assertEqual(
            normalize_pub_outbound_link("https://example.com/a"),
            "https://example.com/a",
        )
        self.assertEqual(normalize_pub_outbound_link("/pets/12/"), "/pets/12/")
        note = ReclamaSlotNote.objects.create(
            section="home",
            slot_code="A5.2",
            market=PUB_MARKET_EU,
            text='{"img":"/media/x.jpg","video":"","link":"www.example.com/ad","alt":"t","caption":"t"}',
        )
        creative = pub_slot_live_creative("home", "A5.2", note, market=PUB_MARKET_EU)
        self.assertTrue(creative.get("has_link"))
        self.assertEqual(creative.get("link"), "https://www.example.com/ad")

    def test_harta_allows_superuser_on_ro(self):
        User = get_user_model()
        su = User.objects.create_superuser("eu_redir_su", "r@b.c", "x")
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(su)
        r = c.get(reverse("publicitate_harta"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "PUB EU")
        self.assertContains(r, "Campanii.ro")
        self.assertNotContains(r, "fără limită de casete pe .ro")
        self.assertContains(r, reverse("publicitate_eu_direct"))
        self.assertContains(r, reverse("publicitate_campanii_ro"))
        slot_map = r.context["pub_slot_map"]
        home_codes = {row["code"] for row in slot_map.get("home") or []}
        self.assertNotIn("A5.3", home_codes)
        self.assertIn("A5.1", home_codes)
        pt_codes = {row["code"] for row in slot_map.get("pt") or []}
        self.assertNotIn("P4.3", pt_codes)
        tr_codes = {row["code"] for row in slot_map.get("transport") or []}
        self.assertNotIn("TDR.3", tr_codes)
        il_codes = {row["code"] for row in slot_map.get("i_love") or []}
        self.assertNotIn("IL.L1", il_codes)

    def test_campanii_map_and_judet_pages(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get(reverse("publicitate_campanii_ro"))
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Campanii.ro")
        self.assertContains(r, "Neamț")
        r2 = c.get(reverse("publicitate_campanii_judet", kwargs={"judet_slug": "neamt"}))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Neamț")
        self.assertContains(r2, "nu sunt campanii active")
        self.assertContains(r2, "Piatra Neamț")

    def test_eu_host_uses_eu_market(self):
        from home.eu_site import eu_product_skin_enabled

        self.assertTrue(eu_product_skin_enabled())
        req = RequestFactory().get("/", HTTP_HOST="euadopt.com")
        self.assertEqual(pub_market_for_request(req), PUB_MARKET_EU)
        req2 = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        self.assertEqual(pub_market_for_request(req2), PUB_MARKET_RO)
