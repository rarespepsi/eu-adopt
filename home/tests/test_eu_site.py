from django.contrib.auth import get_user_model
from django.conf import settings
from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.eu_nav_labels import eu_nav_label
from home.eu_site import (
    EU_SITE_LANGUAGE_CODES,
    is_eu_hub_host,
    path_blocked_on_eu_hub,
    pick_language_for_hub,
    seo_canonical_url,
    seo_hreflang_alternates,
)
from home.euadopt_domains import hyphen_redirect_map


class EuSiteHostTests(SimpleTestCase):
    def test_hub_hosts(self):
        self.assertTrue(is_eu_hub_host("euadopt.com"))
        self.assertTrue(is_eu_hub_host("www.euadopt.com"))
        self.assertFalse(is_eu_hub_host("euadopt.eu"))
        self.assertFalse(is_eu_hub_host("eu-adopt.ro"))

    def test_alias_redirects_to_com(self):
        m = hyphen_redirect_map()
        self.assertEqual(m.get("euadopt.eu"), "euadopt.com")
        self.assertEqual(m.get("euadopt.org"), "euadopt.com")
        self.assertEqual(m.get("eu-adopt.eu"), "euadopt.com")
        self.assertEqual(m.get("eu-adopt.com"), "euadopt.com")
        self.assertIsNone(m.get("euadopt.de"))
        self.assertIsNone(m.get("euadopt.fr"))
        self.assertIsNone(m.get("euadopt.es"))

    def test_country_hosts_active_no_redirect_lang(self):
        from home.euadopt_domains import redirect_lang_for_host
        from home.eu_site import is_eu_country_host, is_eu_site_host

        self.assertTrue(is_eu_country_host("euadopt.de"))
        self.assertIsNone(redirect_lang_for_host("euadopt.de"))
        with self.settings(EUADOPT_EU_PRODUCT_SKIN=True):
            self.assertTrue(is_eu_site_host("euadopt.fr"))
            self.assertTrue(is_eu_site_host("euadopt.com"))

    def test_blocked_paths(self):
        self.assertTrue(path_blocked_on_eu_hub("/shop/"))
        self.assertTrue(path_blocked_on_eu_hub("/servicii/"))
        self.assertTrue(path_blocked_on_eu_hub("/adaposturi/"))
        self.assertTrue(path_blocked_on_eu_hub("/signup/organizatie"))
        self.assertTrue(path_blocked_on_eu_hub("/signup/colaborator"))
        self.assertFalse(path_blocked_on_eu_hub("/pets/"))
        self.assertFalse(path_blocked_on_eu_hub("/signup/persoana-fizica/"))
        self.assertFalse(path_blocked_on_eu_hub("/transport/"))
        self.assertFalse(path_blocked_on_eu_hub("/transport"))
        self.assertFalse(path_blocked_on_eu_hub("/custi/"))
        self.assertFalse(path_blocked_on_eu_hub("/donatii/"))
        self.assertTrue(path_blocked_on_eu_hub("/shop/"))

    def test_nav_labels_all_languages(self):
        from home.eu_nav_labels import assert_all_languages_complete, eu_nav_label

        assert_all_languages_complete()
        for code in EU_SITE_LANGUAGE_CODES:
            self.assertTrue(eu_nav_label(code, "home"))
            self.assertTrue(eu_nav_label(code, "open_menu"))
            self.assertTrue(eu_nav_label(code, "eu_blocked"))

    def test_language_choices_count_24(self):
        from home.eu_site import EU_SITE_LANGUAGE_CHOICES

        self.assertEqual(len(EU_SITE_LANGUAGE_CHOICES), 24)

    def test_seo_canonical_points_to_ro(self):
        rf = RequestFactory()
        req = rf.get("/pets/12/", HTTP_HOST="euadopt.de")
        self.assertEqual(seo_canonical_url(req), "https://eu-adopt.ro/pets/12/")
        alts = seo_hreflang_alternates(req)
        langs = {a["hreflang"] for a in alts}
        self.assertIn("ro", langs)
        self.assertIn("en", langs)
        self.assertIn("de", langs)
        self.assertIn("x-default", langs)


@override_settings(EUADOPT_NON_RO_STAFF_ONLY=False)
class EuSiteMiddlewareTests(TestCase):
    def test_shop_redirects_on_hub_host(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/shop/")
        self.assertIn(r.status_code, (200, 302))

    @override_settings(EUADOPT_EU_PRODUCT_SKIN=True)
    def test_shop_redirects_when_eu_skin_on(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/shop/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("home"))

    def test_home_ok_on_hub_host(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/")
        self.assertIn(r.status_code, (200, 302))

    def test_ro_shop_not_blocked_by_middleware(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get("/shop/")
        self.assertIn(r.status_code, (200, 302))

    def test_hyphen_redirect_preserves_query(self):
        c = Client(HTTP_HOST="eu-adopt.eu")
        r = c.get("/contact/?foo=bar")
        self.assertEqual(r.status_code, 301)
        self.assertIn("euadopt.com", r["Location"])
        self.assertIn("foo=bar", r["Location"])

    def test_eu_alias_redirects_to_com(self):
        c = Client(HTTP_HOST="euadopt.org")
        r = c.get("/pets/")
        self.assertEqual(r.status_code, 301)
        self.assertIn("euadopt.com", r["Location"])

    def test_ro_hyphen_not_redirected(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get("/")
        self.assertNotEqual(r.status_code, 301)

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_language_switcher_on_com_hub(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/contact/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "a0-eu-lang-select")
        self.assertContains(r, "a0-eu-lang-bar")
        self.assertContains(r, 'id="a0_eu_lang_select_bar"')
        self.assertContains(r, 'value="en" selected')
        self.assertNotContains(r, "a0-eu-lang-item--forced")
        self.assertNotContains(r, "a0-eu-lang-forced-label")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_language_switcher_on_com_de_manual(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.post(
            "/i18n/setlang/",
            {"language": "de", "next": "/contact/"},
            follow=True,
            HTTP_HOST="euadopt.com",
        )
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="de" selected')
        self.assertContains(r, "Kontakt")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_language_forced_en_on_com_hub_removed(self):
        """Legacy test replaced: .com now has language selector (variant B)."""
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/contact/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "a0-eu-lang-select")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_login_english_on_com(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/login/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Sign in")
        self.assertContains(r, "Forgot your password?")
        self.assertNotContains(r, "Intră în cont")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_home_english_chrome_on_com(self):
        User = get_user_model()
        staff = User.objects.create_user(username="eu_en_staff", password="x", is_staff=True)
        c = Client(HTTP_HOST="euadopt.com")
        c.force_login(staff)
        r = c.get("/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "Support EU-Adopt")
        self.assertContains(r, "Come meet us!")
        self.assertContains(r, "Quick guide")
        self.assertNotContains(r, "Susține EU-Adopt")
        self.assertNotContains(r, "Hai la noi!")
        self.assertContains(r, "#DontBuy")
        self.assertNotContains(r, "#NuCumpar")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_burtiera_default_en_for_eu_market(self):
        from home.views import HOME_BURTIERA_DEFAULT_TEXT_EN, _get_home_burtiera_text
        from home.pub_markets import PUB_MARKET_EU, PUB_MARKET_RO

        self.assertIn("DontBuy", _get_home_burtiera_text(market=PUB_MARKET_EU))
        self.assertEqual(_get_home_burtiera_text(market=PUB_MARKET_EU), HOME_BURTIERA_DEFAULT_TEXT_EN)
        self.assertIn("NuCumpar", _get_home_burtiera_text(market=PUB_MARKET_RO))

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_adaposturi_redirects_on_eu(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/adaposturi/")
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r["Location"], reverse("home"))

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_transport_allowed_on_eu(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/transport/")
        self.assertIn(r.status_code, (200, 302))
        if r.status_code == 302:
            self.assertNotEqual(r["Location"], reverse("home"))

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_de_host_stays_on_de_german_ui(self):
        c = Client(HTTP_HOST="euadopt.de")
        r = c.get("/contact/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="de" selected')
        self.assertContains(r, "Kontakt")
        self.assertNotContains(r, "Contact EU-ADOPT")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_com_eu_lang_sets_german_ui(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/contact/?eu_lang=de", follow=True)
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, 'value="de" selected')
        self.assertContains(r, "Kontakt")
        self.assertNotContains(r, "Contact EU-ADOPT")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_es_host_stays_on_es(self):
        c = Client(HTTP_HOST="euadopt.es")
        r = c.get("/contact/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "a0-eu-lang-select")
        self.assertContains(r, 'value="es" selected')

    def test_pick_language_default_en(self):
        rf = RequestFactory()
        req = rf.get("/", HTTP_HOST="euadopt.com")
        req.session = {}
        req.COOKIES = {}
        self.assertEqual(pick_language_for_hub(req), "en")

    def test_pick_language_de_host(self):
        rf = RequestFactory()
        req = rf.get("/", HTTP_HOST="euadopt.de")
        req.session = {}
        req.COOKIES = {}
        self.assertEqual(pick_language_for_hub(req), "de")

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_eu_ui_pack_on_com(self):
        from home.eu_site import eu_site_context_for_request

        rf = RequestFactory()
        req = rf.get("/", HTTP_HOST="euadopt.com")
        ctx = eu_site_context_for_request(req)
        self.assertFalse(ctx["eu_force_english"])
        self.assertTrue(ctx["eu_ui"].get("login_heading"))
        self.assertEqual(ctx["eu_site_lang"], "en")
        self.assertEqual(len(ctx["eu_site_languages"]), 9)
        self.assertTrue(ctx["site_proc"].is_eu)
        self.assertTrue(ctx["site_proc"].adoption_skip_pickup_choice)
        self.assertFalse(ctx["site_proc"].nav_servicii)
        self.assertTrue(ctx["site_proc_adoption_simple_intermediation"])

    def test_hub_ui_labels_complete(self):
        from home.eu_ui_labels import assert_hub_ui_languages_complete

        assert_hub_ui_languages_complete()


class EuProceduresTests(SimpleTestCase):
    def test_ro_vs_eu_flags(self):
        from home.eu_procedures import EU_PROCEDURES, RO_PROCEDURES, procedures_for_eu_flag

        self.assertFalse(RO_PROCEDURES.is_eu)
        self.assertTrue(RO_PROCEDURES.adoption_transport_in_flow)
        self.assertTrue(RO_PROCEDURES.nav_shop)
        self.assertTrue(EU_PROCEDURES.is_eu)
        self.assertTrue(EU_PROCEDURES.adoption_simple_intermediation)
        self.assertFalse(EU_PROCEDURES.adoption_transport_in_flow)
        self.assertFalse(EU_PROCEDURES.adoption_bonus_enabled)
        self.assertTrue(EU_PROCEDURES.transport_destination_country_field)
        self.assertTrue(EU_PROCEDURES.transport_email_inbox)
        self.assertFalse(RO_PROCEDURES.transport_email_inbox)
        self.assertTrue(EU_PROCEDURES.pt_hide_marquee_strips)
        self.assertFalse(RO_PROCEDURES.pt_hide_marquee_strips)
        self.assertFalse(EU_PROCEDURES.pt_country_filter)
        self.assertFalse(RO_PROCEDURES.pt_country_filter)
        self.assertIs(procedures_for_eu_flag(True), EU_PROCEDURES)
        self.assertIs(procedures_for_eu_flag(False), RO_PROCEDURES)

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_context_ro_host(self):
        from home.eu_site import eu_site_context_for_request

        rf = RequestFactory()
        req = rf.get("/", HTTP_HOST="eu-adopt.ro")
        ctx = eu_site_context_for_request(req)
        self.assertFalse(ctx["eu_site_active"])
        self.assertFalse(ctx["site_proc"].is_eu)
        self.assertTrue(ctx["site_proc"].nav_servicii)
        self.assertFalse(ctx["site_proc"].adoption_skip_pickup_choice)


@override_settings(EUADOPT_NON_RO_STAFF_ONLY=True, PRELAUNCH_MODE=False)
class EuNonRoStaffGateTests(TestCase):
    def test_anon_gets_coming_soon_on_com(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "coming soon", status_code=403)

    def test_coming_soon_french_from_cookie(self):
        c = Client(HTTP_HOST="euadopt.com")
        c.cookies[settings.LANGUAGE_COOKIE_NAME] = "fr"
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "bientôt disponible", status_code=403)
        self.assertContains(r, "Connexion staff", status_code=403)
        self.assertNotContains(r, "This international site", status_code=403)

    def test_coming_soon_german_from_cookie(self):
        c = Client(HTTP_HOST="euadopt.com")
        c.cookies[settings.LANGUAGE_COOKIE_NAME] = "de"
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "demnächst", status_code=403)

    def test_coming_soon_spanish_from_cookie(self):
        c = Client(HTTP_HOST="euadopt.com")
        c.cookies[settings.LANGUAGE_COOKIE_NAME] = "es"
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "próximamente", status_code=403)

    def test_coming_soon_french_on_fr_host(self):
        c = Client(HTTP_HOST="euadopt.fr")
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "bientôt disponible", status_code=403)
        self.assertContains(r, "Connexion staff", status_code=403)

    def test_login_allowed(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/login/")
        self.assertIn(r.status_code, (200, 302))

    def test_signup_allowed_under_gate(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/signup/persoana-fizica/")
        self.assertEqual(r.status_code, 200)

    def test_staff_can_access(self):
        User = get_user_model()
        u = User.objects.create_user(username="eu_staff", password="x", is_staff=True)
        c = Client(HTTP_HOST="euadopt.com")
        c.force_login(u)
        r = c.get("/")
        self.assertIn(r.status_code, (200, 302))
        self.assertNotContains(r, "coming soon", status_code=r.status_code)

    def test_ro_unaffected(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get("/")
        self.assertNotEqual(r.status_code, 403)


class PetFieldValueEnTests(SimpleTestCase):
    def test_size_yes_no_age(self):
        from home.pet_ui_display import pet_field_value, pet_field_value_en

        self.assertEqual(pet_field_value_en("mica"), "Small")
        self.assertEqual(pet_field_value_en("mică"), "Small")
        self.assertEqual(pet_field_value_en("medie"), "Medium")
        self.assertEqual(pet_field_value_en("mare"), "Large")
        self.assertEqual(pet_field_value_en("da"), "Yes")
        self.assertEqual(pet_field_value_en("Nu"), "No")
        self.assertEqual(pet_field_value_en("Nu știu"), "Don't know")
        self.assertEqual(pet_field_value_en("2 ani"), "2 years")
        self.assertEqual(pet_field_value_en("1 an"), "1 year")
        self.assertEqual(pet_field_value_en("10+ ani"), "10+ years")
        self.assertEqual(pet_field_value_en("<1 an"), "<1 year")
        self.assertEqual(pet_field_value_en("Cluj-Napoca"), "Cluj-Napoca")

    def test_de_fr_es_yes_no_size(self):
        from home.pet_ui_display import pet_field_value

        self.assertEqual(pet_field_value("da", "de"), "Ja")
        self.assertEqual(pet_field_value("nu", "de"), "Nein")
        self.assertEqual(pet_field_value("mica", "de"), "Klein")
        self.assertEqual(pet_field_value("2 ani", "de"), "2 Jahre")
        self.assertEqual(pet_field_value("da", "fr"), "Oui")
        self.assertEqual(pet_field_value("nu", "fr"), "Non")
        self.assertEqual(pet_field_value("mare", "fr"), "Grand")
        self.assertEqual(pet_field_value("da", "es"), "Sí")
        self.assertEqual(pet_field_value("medie", "es"), "Mediano")
        self.assertEqual(pet_field_value("3 ani", "es"), "3 años")

    def test_a2_quote_pools_aligned(self):
        from home.data import (
            A2_QUOTE_POOL_DE,
            A2_QUOTE_POOL_EN,
            A2_QUOTE_POOL_ES,
            A2_QUOTE_POOL_FR,
            A2_QUOTE_POOLS_BY_LANG,
        )

        n = len(A2_QUOTE_POOL_EN)
        self.assertEqual(len(A2_QUOTE_POOL_DE), n)
        self.assertEqual(len(A2_QUOTE_POOL_FR), n)
        self.assertEqual(len(A2_QUOTE_POOL_ES), n)
        self.assertEqual(A2_QUOTE_POOLS_BY_LANG["de"][0], A2_QUOTE_POOL_DE[0])


class EuCountriesTests(SimpleTestCase):
    def test_normalize_and_labels(self):
        from home.eu_countries import country_label, normalize_country_code

        self.assertEqual(normalize_country_code("de"), "DE")
        self.assertEqual(normalize_country_code("xx"), "")
        self.assertEqual(country_label("RO", english=True), "Romania")
        self.assertEqual(country_label("RO", english=False), "România")


@override_settings(EUADOPT_EU_PRODUCT_SKIN=True, PRELAUNCH_MODE=False, EUADOPT_NON_RO_STAFF_ONLY=False)
class EuPtNoGeoFilterTests(TestCase):
    def test_de_shows_ro_listing_without_geo_filters(self):
        from django.contrib.auth.models import AnonymousUser

        from home.models import AnimalListing
        from home.pt_p2_list import pt_pets_page_context

        User = get_user_model()
        owner = User.objects.create_user("ptgeo_ro", "ptgeo@t.local", "x")
        AnimalListing.objects.create(
            owner=owner,
            name="BrunoRO",
            species="dog",
            is_published=True,
            country="RO",
        )
        AnimalListing.objects.create(
            owner=owner,
            name="HansDE",
            species="dog",
            is_published=True,
            country="DE",
        )
        rf = RequestFactory()
        req = rf.get("/pets/?country=DE&judet=Cluj", HTTP_HOST="euadopt.de")
        req.eu_site_active = True
        req.user = AnonymousUser()
        ctx = pt_pets_page_context(req)
        self.assertFalse(ctx["show_pt_country_filter"])
        self.assertFalse(ctx["show_county_filter"])
        self.assertEqual(ctx["selected_country"], "")
        self.assertEqual(ctx["selected_judet"], "")
        names = [p["nume"] for p in ctx["p2_list"]]
        self.assertIn("BrunoRO", names)
        self.assertNotIn("HansDE", names)
