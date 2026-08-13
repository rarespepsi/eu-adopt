from django.test import SimpleTestCase

from home.ro_landline_prefixes import (
    combine_landline,
    default_landline_prefix_for_county,
    is_ro_mobile_number,
    landline_prefix_choices,
)


class RoLandlinePrefixesTests(SimpleTestCase):
    def test_mobile_detection(self):
        self.assertTrue(is_ro_mobile_number("0722123456"))
        self.assertTrue(is_ro_mobile_number("+40 722 123 456"))
        self.assertFalse(is_ro_mobile_number("0256123456"))
        self.assertFalse(is_ro_mobile_number(""))

    def test_combine_landline(self):
        self.assertEqual(combine_landline("0256", "212345"), "0256 212345")
        self.assertEqual(combine_landline("0256", ""), "")
        self.assertEqual(combine_landline("", "212345"), "")

    def test_default_prefix_iasi(self):
        self.assertEqual(default_landline_prefix_for_county("Iași"), "0232")
        self.assertEqual(default_landline_prefix_for_county("Iasi"), "0232")

    def test_choices_include_timis(self):
        values = {p for p, _ in landline_prefix_choices()}
        self.assertIn("0256", values)
        self.assertIn("021", values)
