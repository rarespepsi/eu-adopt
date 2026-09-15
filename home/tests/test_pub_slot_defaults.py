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

    def test_pt_p1_radio_somes_on_each_set(self):
        note = _NoteStub(
            '{"img": "images/other.png", "link": "https://example.com", "alt": "X"}'
        )
        somes = (
            "P1.1",
            "P1.16",
            "P1.31",
            "P3.1",
            "P3.16",
            "P3.31",
            "S1.1",
            "S1.16",
            "S1.31",
            "S7.1",
            "S7.16",
            "S7.31",
        )
        metronom = (
            "P1.6",
            "P1.21",
            "P1.36",
            "P3.6",
            "P3.21",
            "P3.36",
            "S1.6",
            "S1.21",
            "S1.36",
            "S7.6",
            "S7.21",
            "S7.36",
        )
        star = (
            "P1.11",
            "P1.26",
            "P3.11",
            "P3.26",
            "S1.11",
            "S1.26",
            "S7.11",
            "S7.26",
        )
        for code in somes:
            section = "pt" if code.startswith("P") else "servicii"
            creative = pub_slot_live_creative(section, code, note=note, market="ro")
            self.assertTrue(creative.get("is_strip_partner"), code)
            self.assertFalse(creative["is_default_cover"], code)
            self.assertTrue(creative["has_link"], code)
            self.assertIn("radio_somes_logo", creative.get("img") or "", code)
            self.assertEqual(creative.get("link"), "https://www.radiosomes.ro", code)
            self.assertIn("/pub/go/", creative.get("href") or "", code)
        for code in metronom:
            section = "pt" if code.startswith("P") else "servicii"
            creative = pub_slot_live_creative(section, code, note=note, market="ro")
            self.assertTrue(creative.get("is_strip_partner"), code)
            self.assertIn("radio_metronom_logo", creative.get("img") or "", code)
            self.assertEqual(creative.get("link"), "http://metronom-fm.ro:8000/stream.ogg", code)
            self.assertIn("/pub/go/", creative.get("href") or "", code)
        for code in star:
            section = "pt" if code.startswith("P") else "servicii"
            creative = pub_slot_live_creative(section, code, note=note, market="ro")
            self.assertTrue(creative.get("is_strip_partner"), code)
            self.assertIn("radio_star_sebes_logo", creative.get("img") or "", code)
            self.assertEqual(creative.get("link"), "https://radiostarsebes.ro/", code)
            self.assertIn("/pub/go/", creative.get("href") or "", code)
        for section, neighbor in (("pt", "P1.2"), ("pt", "P3.3"), ("servicii", "S1.2"), ("servicii", "S7.7")):
            other = pub_slot_live_creative(section, neighbor, note=None, market="ro")
            self.assertFalse(other.get("is_strip_partner"), neighbor)
            self.assertTrue(other["is_default_cover"], neighbor)
        eu = pub_slot_live_creative("pt", "P3.1", note=None, market="eu")
        self.assertFalse(eu.get("is_strip_partner"))
        self.assertTrue(eu["is_default_cover"])

    @override_settings(PRELAUNCH_MODE=False)
    def test_pub_slot_go_radio_somes_p1_sets(self):
        client = Client()
        for section, code, host in (
            ("pt", "P1.1", "radiosomes.ro"),
            ("pt", "P3.6", "metronom-fm.ro"),
            ("pt", "P1.11", "radiostarsebes.ro"),
            ("servicii", "S1.16", "radiosomes.ro"),
            ("servicii", "S7.21", "metronom-fm.ro"),
            ("servicii", "S7.26", "radiostarsebes.ro"),
        ):
            creative = pub_slot_live_creative(section, code, note=None, market="ro")
            response = client.get(creative["href"])
            self.assertEqual(response.status_code, 302, code)
            self.assertIn(host, response["Location"], code)
