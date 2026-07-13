from django.test import Client, SimpleTestCase, override_settings

from home.pub_slot_defaults import pub_cover_static_path, pub_harta_url, pub_slot_live_creative


class PubSlotDefaultsTests(SimpleTestCase):
    def test_cover_path_is_deterministic(self):
        a = pub_cover_static_path("S1.14")
        b = pub_cover_static_path("S1.14")
        c = pub_cover_static_path("S1.15")
        self.assertEqual(a, b)
        self.assertNotEqual(a, c)
        self.assertTrue(a.startswith("images/pub/covers/cover_"))

    def test_default_creative_links_to_facebook(self):
        creative = pub_slot_live_creative("servicii", "S2.2", note=None)
        self.assertTrue(creative["is_default_cover"])
        self.assertIn("facebook.com", creative["link"])
        self.assertIn("61588044314372", creative["link"])
        self.assertTrue(creative["link_external"])
        self.assertTrue(creative["img"])
        self.assertIn("/pub/go/", creative["href"])
        self.assertIn("sect=servicii", creative["href"])
        self.assertIn("slot=S2.2", creative["href"])

    @override_settings(PRELAUNCH_MODE=False)
    def test_pub_slot_go_redirects_external(self):
        creative = pub_slot_live_creative("mypet", "MP.L1", note=None)
        client = Client()
        response = client.get(creative["href"])
        self.assertEqual(response.status_code, 302)
        self.assertIn("facebook.com", response["Location"])

    def test_harta_url_helper(self):
        url = pub_harta_url("shop", "SH4.1")
        self.assertIn("sect=shop", url)
        self.assertIn("slot=SH4.1", url)
