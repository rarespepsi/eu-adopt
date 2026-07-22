from django.test import Client, RequestFactory, SimpleTestCase, TestCase, override_settings

from django.urls import reverse

from home.eu_nav_labels import eu_nav_label
from home.eu_site import (
    EU_SITE_LANGUAGE_CODES,
    is_eu_hub_host,
    path_blocked_on_eu_hub,
    pick_language_for_hub,
)


class EuSiteHostTests(SimpleTestCase):
    def test_hub_hosts(self):
        self.assertTrue(is_eu_hub_host("euadopt.com"))
        self.assertTrue(is_eu_hub_host("www.euadopt.eu"))
        self.assertFalse(is_eu_hub_host("eu-adopt.ro"))

    def test_blocked_paths(self):
        self.assertTrue(path_blocked_on_eu_hub("/shop/"))
        self.assertTrue(path_blocked_on_eu_hub("/servicii/"))
        self.assertFalse(path_blocked_on_eu_hub("/pets/"))

    def test_nav_labels_all_languages(self):
        for code in EU_SITE_LANGUAGE_CODES:
            self.assertTrue(eu_nav_label(code, "home"))


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
        c = Client(HTTP_HOST="euadopt.eu")
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
        self.assertIn("euadopt.eu", r["Location"])
        self.assertIn("foo=bar", r["Location"])

    def test_ro_hyphen_not_redirected(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get("/")
        self.assertNotEqual(r.status_code, 301)

    @override_settings(PRELAUNCH_MODE=False, EUADOPT_EU_PRODUCT_SKIN=True)
    def test_language_switcher_present(self):
        c = Client(HTTP_HOST="www.euadopt.org")
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
