from django.test import SimpleTestCase

from home.pub_slot_defaults import pub_cover_static_path, pub_harta_url, pub_slot_live_creative


class PubSlotDefaultsTests(SimpleTestCase):
    def test_cover_path_is_deterministic(self):
        a = pub_cover_static_path("S1.14")
        b = pub_cover_static_path("S1.14")
        c = pub_cover_static_path("S1.15")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(a.startswith("images/pub/covers/cover_"))

    def test_default_creative_links_to_publicitate(self):
        creative = pub_slot_live_creative("servicii", "S2.2", note=None)
        self.assertTrue(creative["is_default_cover"])
        self.assertIn("/publicitate/", creative["link"])
        self.assertIn("sect=servicii", creative["link"])
        self.assertIn("slot=S2.2", creative["link"])
        self.assertFalse(creative["link_external"])
        self.assertTrue(creative["img"])

    def test_harta_url_helper(self):
        url = pub_harta_url("shop", "SH4.1")
        self.assertIn("sect=shop", url)
        self.assertIn("slot=SH4.1", url)
