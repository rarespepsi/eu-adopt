from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.models import AccountProfile, ReclamaSlotNote, UserProfile
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
        r2 = c.get(reverse("publicitate_eu_direct") + "?sect=home&slot=A6.1")
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
                "slot": "A6.1",
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
        note = ReclamaSlotNote.objects.get(section="home", slot_code="A6.1", market=PUB_MARKET_EU)
        self.assertIn("Adopt", note.text)
        r3 = c.get(reverse("publicitate_eu_direct") + "?sect=home")
        self.assertEqual(r3.status_code, 200)
        self.assertContains(r3, "eu-wire-previews-json")
        self.assertIn("A6.1", r3.context["eu_wire_previews"])
        self.assertTrue(r3.context["eu_wire_previews"]["A6.1"].get("occupied"))
        self.assertTrue((r3.context["eu_wire_previews"]["A6.1"].get("image_url") or "").startswith("/media/"))

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
        self.assertContains(r, ">Campanii</a>")
        self.assertNotContains(r, ">Campanii.ro</a>")
        self.assertNotContains(r, "fără limită de casete pe .ro")
        self.assertContains(r, reverse("publicitate_eu_direct"))
        self.assertContains(r, reverse("publicitate_campanii_ro"))
        slot_map = r.context["pub_slot_map"]
        home_codes = {row["code"] for row in slot_map.get("home") or []}
        self.assertNotIn("A5.3", home_codes)
        self.assertNotIn("A5.1", home_codes)
        self.assertNotIn("A5.2", home_codes)
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
        self.assertContains(r, "Campanii gratuite de sterilizare")
        self.assertNotContains(r, "Intrare din casetele")
        self.assertContains(r, "campaniiMapStage")
        self.assertIn("NT", r.context["campanii_url_by_code"])
        self.assertTrue(r.context["campanii_url_by_code"]["NT"].endswith("/neamt/"))
        self.assertEqual(r.context["campanii_count_by_code"], {})
        r2 = c.get(reverse("publicitate_campanii_judet", kwargs={"judet_slug": "neamt"}))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Neamț")
        self.assertContains(r2, "nu sunt campanii active")
        self.assertContains(r2, "Piatra Neamț")

    def test_campanie_create_shows_on_map_and_expires_after_grace(self):
        from datetime import date, timedelta
        from django.core.files.uploadedfile import SimpleUploadedFile
        from home.models import CampanieSterilizare

        User = get_user_model()
        u = User.objects.create_user("camp_poster", "c@b.c", "x")
        ap, _ = AccountProfile.objects.get_or_create(user=u)
        ap.role = AccountProfile.ROLE_PF
        ap.save(update_fields=["role"])
        UserProfile.objects.get_or_create(user=u)
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(u)
        start = date.today()
        end = date.today() + timedelta(days=2)
        photo = SimpleUploadedFile("afiș.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
        r = c.post(
            reverse("account_edit"),
            {
                "form_type": "campanie_sterilizare",
                "campanie_judet": "Neamț",
                "campanie_localitate": "Roman",
                "campanie_dogs": "1",
                "campanie_date_start": start.isoformat(),
                "campanie_date_end": end.isoformat(),
                "campanie_link": "https://example.com/camp",
                "campanie_photo": photo,
            },
        )
        self.assertEqual(r.status_code, 302)
        self.assertEqual(CampanieSterilizare.objects.count(), 1)
        camp = CampanieSterilizare.objects.get()
        self.assertEqual(camp.judet_slug, "neamt")
        self.assertEqual(camp.localitate, "Roman")
        self.assertNotIn(u.username, camp.localitate)

        r_map = c.get(reverse("publicitate_campanii_ro"))
        self.assertEqual(r_map.context["campanii_count_by_code"].get("NT"), 1)
        r_judet = c.get(reverse("publicitate_campanii_judet", kwargs={"judet_slug": "neamt"}))
        self.assertContains(r_judet, "Roman")
        self.assertContains(r_judet, "Câini")
        self.assertContains(r_judet, 'class="campanii-list-loc"')
        self.assertNotContains(r_judet, 'class="campanii-list-user"')

        camp.date_end = date.today() - timedelta(days=4)
        camp.save(update_fields=["date_end"])
        r_map2 = c.get(reverse("publicitate_campanii_ro"))
        self.assertEqual(r_map2.context["campanii_count_by_code"].get("NT"), None)
        r_judet2 = c.get(reverse("publicitate_campanii_judet", kwargs={"judet_slug": "neamt"}))
        self.assertContains(r_judet2, "nu sunt campanii active")

    def test_internal_placeholder_pages(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r1 = c.get(reverse("animale_pierdute"))
        self.assertEqual(r1.status_code, 200)
        self.assertContains(r1, "Animale pierdute sau găsite")
        self.assertContains(r1, "Pagină în lucru")
        r2 = c.get(reverse("semnaleaza_abuz"))
        self.assertEqual(r2.status_code, 200)
        self.assertContains(r2, "Semnalează un abuz")
        self.assertContains(r2, "Pagină în lucru")

    def test_campanie_list_edit_delete_from_account(self):
        from datetime import date, timedelta
        from django.core.files.uploadedfile import SimpleUploadedFile
        from home.models import CampanieSterilizare

        User = get_user_model()
        u = User.objects.create_user("camp_owner", "o@b.c", "x")
        ap, _ = AccountProfile.objects.get_or_create(user=u)
        ap.role = AccountProfile.ROLE_PF
        ap.save(update_fields=["role"])
        UserProfile.objects.get_or_create(user=u)
        photo = SimpleUploadedFile("a.jpg", b"\xff\xd8\xff\xd9", content_type="image/jpeg")
        camp = CampanieSterilizare.objects.create(
            user=u,
            judet="Neamț",
            judet_slug="neamt",
            localitate="Roman",
            species_dogs=True,
            species_cats=False,
            date_start=date.today(),
            date_end=date.today() + timedelta(days=5),
            photo=photo,
            link="",
        )
        c = Client(HTTP_HOST="eu-adopt.ro")
        c.force_login(u)
        r = c.get(reverse("account") + "?campanii_mele=1")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Campaniile mele")
        self.assertContains(r, "Roman")
        self.assertContains(r, "Modifică")
        self.assertContains(r, "Șterge")
        r_edit = c.get(reverse("account") + f"?campanie_edit={camp.pk}")
        self.assertContains(r_edit, "Modifică campania")
        self.assertContains(r_edit, 'value="Roman"')
        r_del = c.post(
            reverse("account_edit"),
            {"form_type": "campanie_sterilizare_delete", "campanie_id": str(camp.pk)},
        )
        self.assertEqual(r_del.status_code, 302)
        self.assertFalse(CampanieSterilizare.objects.filter(pk=camp.pk).exists())

    def test_internal_home_pub_slots_use_dedicated_image_and_link(self):
        from home.pub_slot_defaults import pub_slot_live_creative

        cases = (
            ("A5.1", "animale-pierdute", "a5-pierdute-gasite"),
            ("A5.2", "semnaleaza-abuz", "a5-semnaleaza-abuz"),
        )
        for code, path_part, img_part in cases:
            creative = pub_slot_live_creative("home", code, None, market=PUB_MARKET_RO)
            self.assertTrue(creative.get("has_link"), code)
            dest = (creative.get("href") or creative.get("link") or "")
            self.assertIn(f"/{path_part}/", dest, code)
            self.assertIn(img_part, creative.get("img") or "", code)
            self.assertTrue(creative.get("is_internal_home_pub"), code)

    def test_campanie_pub_slots_use_campaign_image_and_map_link(self):
        from home.pub_slot_defaults import pub_slot_live_creative

        cases = (
            ("home", "A5.3"),
            ("pt", "P4.3"),
            ("transport", "TDR.3"),
            ("i_love", "IL.L1"),
        )
        for section, code in cases:
            creative = pub_slot_live_creative(section, code, None, market=PUB_MARKET_RO)
            self.assertTrue(creative.get("has_link"), code)
            dest = (creative.get("href") or creative.get("link") or "")
            self.assertIn("/publicitate/campanii/", dest, code)
            self.assertIn("campanii-gratuite-pub", creative.get("img") or "", code)

    def test_eu_host_uses_eu_market(self):
        from home.eu_site import eu_product_skin_enabled

        self.assertTrue(eu_product_skin_enabled())
        req = RequestFactory().get("/", HTTP_HOST="euadopt.com")
        self.assertEqual(pub_market_for_request(req), PUB_MARKET_EU)
        req2 = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        self.assertEqual(pub_market_for_request(req2), PUB_MARKET_RO)
