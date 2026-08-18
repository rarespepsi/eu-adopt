"""Oprire buclă ?next= login ↔ signup (crawleri → 504)."""

from urllib.parse import parse_qs, urlparse

from django.test import Client, SimpleTestCase, TestCase, override_settings
from django.urls import reverse

from home.auth_next import sanitize_post_login_next


class SanitizeAuthNextHelperTests(SimpleTestCase):
    def test_keeps_pet_and_account_paths(self):
        self.assertEqual(sanitize_post_login_next("/pets/"), "/pets/")
        self.assertEqual(sanitize_post_login_next("/cont/"), "/cont/")
        self.assertEqual(
            sanitize_post_login_next("/caini/toby-hateg/?from=home&back=/pets/"),
            "/caini/toby-hateg/?from=home&back=/pets/",
        )
        self.assertEqual(
            sanitize_post_login_next("/admin-analysis/prezenta/"),
            "/admin-analysis/prezenta/",
        )

    def test_unwraps_login_and_signup_next(self):
        self.assertEqual(
            sanitize_post_login_next("/login/?next=/pets/"),
            "/pets/",
        )
        self.assertEqual(
            sanitize_post_login_next("/signup/alege-tip/?next=/i-love/"),
            "/i-love/",
        )
        self.assertEqual(
            sanitize_post_login_next("/login/?next=/login/?next=/cont/"),
            "/cont/",
        )

    def test_drops_auth_only_and_external(self):
        self.assertEqual(sanitize_post_login_next("/login/"), "")
        self.assertEqual(sanitize_post_login_next("/signup/persoana-fizica/"), "")
        self.assertEqual(sanitize_post_login_next("https://evil.example/x"), "")
        self.assertEqual(sanitize_post_login_next("//evil.example"), "")

    def test_drops_oversized_nested_crawler_url(self):
        nested = "/login/?next=/signup/alege-tip/?next=" * 40 + "/pets/"
        self.assertEqual(sanitize_post_login_next(nested), "")


@override_settings(PRELAUNCH_MODE=False)
class SanitizeAuthNextHttpTests(TestCase):
    def test_login_get_nested_next_redirects_to_real_page(self):
        c = Client()
        r = c.get(reverse("login"), {"next": "/login/?next=/pets/"})
        self.assertEqual(r.status_code, 302)
        parsed = urlparse(r.url)
        self.assertEqual(parsed.path, reverse("login"))
        self.assertEqual(parse_qs(parsed.query).get("next", [""])[0], "/pets/")

    def test_login_get_huge_next_drops_query(self):
        c = Client()
        huge = "/login/?next=/signup/alege-tip/?next=" * 50 + "/pets/"
        r = c.get(reverse("login"), {"next": huge})
        self.assertEqual(r.status_code, 302)
        self.assertEqual(r.url, reverse("login"))

    def test_choose_type_keeps_real_next(self):
        c = Client(HTTP_HOST="eu-adopt.ro")
        r = c.get(reverse("signup_choose_type") + "?next=/donatii/")
        self.assertEqual(r.status_code, 200)

    @override_settings(
        EUADOPT_EU_PRODUCT_SKIN=True,
        EUADOPT_NON_RO_STAFF_ONLY=False,
    )
    def test_eu_choose_type_does_not_copy_login_loop_into_location(self):
        c = Client(HTTP_HOST="euadopt.com")
        r = c.get(
            reverse("signup_choose_type"),
            {"next": "/login/?next=/signup/alege-tip/?next=/pets/"},
        )
        self.assertEqual(r.status_code, 302)
        # 1) middleware unwraps next → 2) EU choose-type → PF
        r2 = c.get(r.url, HTTP_HOST="euadopt.com")
        self.assertEqual(r2.status_code, 302)
        loc = r2.url or ""
        self.assertLess(len(loc), 200)
        self.assertNotIn("/login/", loc)
        self.assertIn(reverse("signup_pf"), loc)
        self.assertIn("/pets/", loc.replace("%2F", "/"))
