from unittest.mock import patch

from django.test import Client, SimpleTestCase, override_settings

from home.pub_slot_defaults import pub_cover_static_path, pub_harta_url, pub_slot_live_creative


class _NoteStub:
    def __init__(self, text: str):
        self.text = text


class PubSlotDefaultsTests(SimpleTestCase):
    databases = {"default"}
    def test_cover_path_is_deterministic(self):
        a = pub_cover_static_path("S1.14")
        b = pub_cover_static_path("S1.14")
        c = pub_cover_static_path("S1.15")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(a.startswith("images/pub/animals/pub_animale_"))

    def test_default_creative_has_no_click_link(self):
        creative = pub_slot_live_creative("servicii", "S2.2", note=None)
        self.assertTrue(creative["is_default_cover"])
        self.assertFalse(creative["has_link"])
        self.assertEqual(creative["link"], "")
        self.assertFalse(creative["link_external"])
        self.assertTrue(creative["img"])

    @override_settings(PRELAUNCH_MODE=False)
    @patch("home.views.pub_slot_fetch_notes")
    def test_pub_slot_go_redirects_client_link(self, mock_fetch_notes):
        note = _NoteStub(
            '{"img": "images/logo-final-cu-stele.png", "link": "https://eu-adopt.ro", "alt": "EU-Adopt"}'
        )
        mock_fetch_notes.return_value = {"A6.1": note}
        creative = pub_slot_live_creative("home", "A6.1", note=note)
        self.assertTrue(creative["has_link"])
        self.assertIn("/pub/go/", creative["href"])
        client = Client()
        response = client.get(creative["href"])
        self.assertEqual(response.status_code, 302)
        self.assertIn("eu-adopt.ro", response["Location"])

    def test_harta_url_helper(self):
        url = pub_harta_url("shop", "SH4.1")
        self.assertIn("sect=shop", url)
        self.assertIn("slot=SH4.1", url)
