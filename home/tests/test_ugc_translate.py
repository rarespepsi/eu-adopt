"""Tests for UGC translation (ficha + messages display)."""

from unittest.mock import patch

from django.test import RequestFactory, SimpleTestCase, override_settings

from home.ugc_translate import (
    body_for_viewer,
    display_lang_for_request,
    translate_pet_fields_for_display,
    translate_text,
)


class UgcTranslateTests(SimpleTestCase):
    def setUp(self):
        self.rf = RequestFactory()

    def test_display_lang_ro_vs_eu(self):
        req = self.rf.get("/")
        req.eu_site_active = False
        self.assertEqual(display_lang_for_request(req), "ro")
        req.eu_site_active = True
        req.eu_site_lang = "en"
        self.assertEqual(display_lang_for_request(req), "en")

    @override_settings(UGC_TRANSLATE_ENABLED=True, EUADOPT_GEMINI_API_KEY="test-key")
    @patch("home.ugc_translate._gemini_translate", return_value="I am a friendly dog.")
    def test_translate_ro_to_en(self, _mock):
        out = translate_text("Sunt un câine prietenos.", "en")
        self.assertEqual(out, "I am a friendly dog.")
        _mock.assert_called_once()

    @override_settings(UGC_TRANSLATE_ENABLED=True, EUADOPT_GEMINI_API_KEY="test-key")
    @patch("home.ugc_translate._gemini_translate")
    def test_skip_when_already_romanian_on_ro(self, mock_g):
        text = "Sunt un câine prietenos și blând."
        out = translate_text(text, "ro")
        self.assertEqual(out, text)
        mock_g.assert_not_called()

    @override_settings(UGC_TRANSLATE_ENABLED=True, EUADOPT_GEMINI_API_KEY="test-key")
    @patch("home.ugc_translate._gemini_translate", return_value="Translated story.")
    def test_pet_fields_only_on_eu_site(self, _mock):
        req = self.rf.get("/")
        req.eu_site_active = True
        req.eu_site_lang = "en"
        fields = {"cine_sunt": "Sunt un câine din adăpost.", "nume": "Rex"}
        out = translate_pet_fields_for_display(fields, req)
        self.assertEqual(out["cine_sunt"], "Translated story.")
        self.assertEqual(out["nume"], "Rex")

        req.eu_site_active = False
        out2 = translate_pet_fields_for_display(fields, req)
        self.assertEqual(out2["cine_sunt"], fields["cine_sunt"])

    @override_settings(UGC_TRANSLATE_ENABLED=True, EUADOPT_GEMINI_API_KEY="test-key")
    @patch("home.ugc_translate._gemini_translate", return_value="Please tell me more.")
    def test_body_for_viewer_bidirectional(self, mock_g):
        req = self.rf.get("/")
        req.eu_site_active = True
        req.eu_site_lang = "en"
        self.assertEqual(body_for_viewer("Te rog spune-mi mai multe.", req), "Please tell me more.")
        mock_g.assert_called()

        mock_g.reset_mock()
        mock_g.return_value = "Vreau să adopt."
        req.eu_site_active = False
        self.assertEqual(body_for_viewer("I want to adopt.", req), "Vreau să adopt.")

    @override_settings(UGC_TRANSLATE_ENABLED=False, EUADOPT_GEMINI_API_KEY="test-key")
    @patch("home.ugc_translate._gemini_translate")
    def test_disabled_returns_original(self, mock_g):
        text = "Sunt un câine."
        self.assertEqual(translate_text(text, "en"), text)
        mock_g.assert_not_called()
