from django.test import SimpleTestCase

from home.euadopt_domains import (
    DomainRole,
    EUADOPT_DOMAIN_REGISTRY,
    hyphen_redirect_map,
    is_romania_primary_host,
)


class EuadoptDomainsRegistryTests(SimpleTestCase):
    def test_ro_not_in_hyphen_redirect(self):
        m = hyphen_redirect_map()
        self.assertNotIn("eu-adopt.ro", m)
        self.assertNotIn("www.eu-adopt.ro", m)

    def test_hyphen_pairs(self):
        m = hyphen_redirect_map()
        self.assertEqual(m["eu-adopt.com"], "euadopt.com")
        self.assertEqual(m["www.eu-adopt.eu"], "www.euadopt.eu")

    def test_no_italy_without_purchase(self):
        hosts = {e.host for e in EUADOPT_DOMAIN_REGISTRY}
        self.assertNotIn("euadopt.it", hosts)

    def test_romania_primary(self):
        self.assertTrue(is_romania_primary_host("eu-adopt.ro"))
        self.assertFalse(is_romania_primary_host("euadopt.com"))

    def test_roles_count(self):
        roles = {e.role for e in EUADOPT_DOMAIN_REGISTRY}
        self.assertIn(DomainRole.RO_PRIMARY, roles)
        self.assertIn(DomainRole.ACTIVE, roles)
        self.assertIn(DomainRole.REDIRECT_301, roles)
