"""Teste middleware restricție IP /admin/."""
from django.test import Client, TestCase, override_settings


@override_settings(EUADOPT_ADMIN_ALLOW_IPS=["203.0.113.50"])
class AdminIPAllowlistTests(TestCase):
    def test_admin_forbidden_for_other_ip(self):
        c = Client()
        r = c.get("/admin/", REMOTE_ADDR="198.51.100.1")
        self.assertEqual(r.status_code, 403)

    def test_admin_allowed_for_listed_ip(self):
        c = Client()
        r = c.get("/admin/", REMOTE_ADDR="203.0.113.50")
        self.assertIn(r.status_code, (200, 302))
