from django.contrib.auth import get_user_model
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

    def test_blocked_paths(self):
        self.assertTrue(path_blocked_on_eu_hub("/shop/"))
        self.assertTrue(path_blocked_on_eu_hub("/servicii/"))
        self.assertFalse(path_blocked_on_eu_hub("/pets/"))

    def test_nav_labels_all_languages(self):
        for code in EU_SITE_LANGUAGE_CODES:
            self.assertTrue(eu_nav_label(code, "home"))

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
    def test_language_switcher_present(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/contact/")
        self.assertEqual(r.status_code, 200)
        self.assertContains(r, "a0-eu-lang-select")
        self.assertNotContains(r, ">Shop</a>")

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


@override_settings(EUADOPT_NON_RO_STAFF_ONLY=True, PRELAUNCH_MODE=False)
class EuNonRoStaffGateTests(TestCase):
    def test_anon_gets_coming_soon_on_com(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/")
        self.assertEqual(r.status_code, 403)
        self.assertContains(r, "coming soon", status_code=403)

    def test_login_allowed(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get("/login/")
        self.assertIn(r.status_code, (200, 302))

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
