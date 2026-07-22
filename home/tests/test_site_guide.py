"""Ghid EU-Adopt — FAQ, refuzuri, API."""

from unittest.mock import patch

from django.test import Client, TestCase, override_settings
from django.urls import reverse


@override_settings(SITE_GUIDE_ENABLED=True, SITE_GUIDE_GEMINI_ENABLED=False)
class SiteGuideLogicTests(TestCase):
    def test_faq_match_adopt(self):
        from home.site_guide import answer_question

        r = answer_question("cum adopt un caine")
        self.assertEqual(r["source"], "faq")
        self.assertEqual(r["faq_id"], "adopt_cum")

    def test_faq_match_pt_filtre(self):
        from home.site_guide import answer_question

        r = answer_question("cum filtrez dupa judet si talie")
        self.assertEqual(r["source"], "faq")
        self.assertEqual(r["faq_id"], "pt_cautare")
        self.assertIn("Talie", r["answer"])
        self.assertIn("Județ", r["answer"])

    def test_faq_match_servicii_filtre(self):
        from home.site_guide import answer_question

        r = answer_question("ce filtre sunt la servicii")
        self.assertEqual(r["source"], "faq")
        self.assertEqual(r["faq_id"], "servicii_ce")
        self.assertIn("Oraș", r["answer"])

    def test_refuse_medical(self):
        from home.site_guide import answer_question

        r = answer_question("ce vaccinuri are nevoie")
        self.assertEqual(r["source"], "refuse")
        self.assertIn("medical", r["answer"].lower())

    def test_faq_id_chip(self):
        from home.site_guide import answer_question

        r = answer_question("", faq_id="ilove_ce")
        self.assertEqual(r["source"], "faq")
        self.assertIn("I Love", r["answer"])

    def test_fallback_no_gemini(self):
        from home.site_guide import answer_question

        r = answer_question("xyzabc nonsense query 12345")
        self.assertEqual(r["source"], "fallback")

    def test_path_whitelist(self):
        from home.site_guide import is_site_guide_path

        self.assertTrue(is_site_guide_path("/"))
        self.assertTrue(is_site_guide_path("/pets/"))
        self.assertTrue(is_site_guide_path("/pets/12/"))
        self.assertTrue(is_site_guide_path("/mypet/"))
        self.assertTrue(is_site_guide_path("/login/"))
        self.assertTrue(is_site_guide_path("/shop/comanda-personalizate/"))
        self.assertFalse(is_site_guide_path("/admin/"))


@override_settings(SITE_GUIDE_ENABLED=True, SITE_GUIDE_GEMINI_ENABLED=False, PRELAUNCH_MODE=False)
class SiteGuideApiTests(TestCase):
    def test_ask_faq_post(self):
        c = Client()
        r = c.post(
            reverse("site_guide_ask"),
            {"faq_id": "pt_unde", "page_path": "/pets/"},
        )
        self.assertEqual(r.status_code, 200)
        data = r.json()
        self.assertTrue(data["ok"])
        self.assertEqual(data["source"], "faq")
        self.assertIn("Prietenul", data["answer"])

    def test_disabled_returns_404(self):
        with self.settings(SITE_GUIDE_ENABLED=False):
            c = Client()
            r = c.post(reverse("site_guide_ask"), {"question": "test", "page_path": "/"})
            self.assertEqual(r.status_code, 404)

    def test_wrong_page_403(self):
        c = Client()
        r = c.post(
            reverse("site_guide_ask"),
            {"question": "cum adopt", "page_path": "/admin/"},
        )
        self.assertEqual(r.status_code, 403)

    @patch("home.site_guide.ask_gemini", return_value="Răspuns AI test.")
    @override_settings(SITE_GUIDE_GEMINI_ENABLED=True, EUADOPT_GEMINI_API_KEY="test-key")
    def test_gemini_fallback(self, _mock):
        from home.site_guide import answer_question

        r = answer_question("descriere detaliata flux necunoscut xyz123")
        self.assertEqual(r["source"], "gemini")
