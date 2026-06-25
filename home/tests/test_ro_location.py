from django.test import SimpleTestCase

from home.ro_location import (
    fold_key,
    lead_matches_location_filter,
    normalize_location_pair,
    resolve_county,
    resolve_locality,
)


class RoLocationTests(SimpleTestCase):
    def test_resolve_county_diacritics(self):
        self.assertEqual(resolve_county("neamt"), "Neamț")
        self.assertEqual(resolve_county("NEAMT"), "Neamț")
        self.assertEqual(resolve_county("Neamț"), "Neamț")

    def test_resolve_locality_hyphen(self):
        j, o = normalize_location_pair("Neamt", "Piatra Neamt")
        self.assertEqual(j, "Neamț")
        self.assertEqual(o, "Piatra-Neamț")

    def test_filter_match_nicol(self):
        self.assertTrue(
            lead_matches_location_filter(
                judet="Neamț",
                company_judet="",
                oras="Piatra-Neamț",
                company_oras="",
                filter_judet="Neamt",
                filter_oras="Piatra Neamt",
            )
        )

    def test_fold_key_hyphen_space(self):
        self.assertEqual(fold_key("Piatra-Neamț"), fold_key("Piatra Neamt"))
