from django.test import SimpleTestCase

from home.models import StaffOnboardingLead
from home.staff_onboarding_invite import staff_invite_org_greeting_name


class StaffInviteOrgGreetingNameTests(SimpleTestCase):
    def _lead(self, **kwargs):
        defaults = {
            "email": "office@example.ro",
            "display_name": "X",
            "account_kind": StaffOnboardingLead.KIND_ADAPOST,
        }
        defaults.update(kwargs)
        return StaffOnboardingLead(**defaults)

    def test_prefers_real_org_name(self):
        lead = self._lead(
            org_display_name="ADAPOST ASOCIAŢIA ARCHE NOAH TRANSILVANIA",
            display_name="ADAPOST ASOCIAŢIA ARCHE NOAH TRANSILVANIA",
        )
        self.assertIn("ARCHE NOAH", staff_invite_org_greeting_name(lead))

    def test_strips_address_tail(self):
        lead = self._lead(
            org_display_name=(
                "Adăpostul de Câini fără Stăpân Unirea (S.U.P.A.G.L. Brăila) "
                "Adresă Fizică: Comuna Unirea"
            ),
            email="supagbraila@gmail.com",
        )
        name = staff_invite_org_greeting_name(lead)
        self.assertIn("Unirea", name)
        self.assertNotIn("Adresă", name)
        self.assertNotIn("Comuna", name)

    def test_skips_street_address_uses_email(self):
        lead = self._lead(
            org_display_name="Str. Drumul Dealu Bistrii, Nr. 25, Sector 4, București",
            display_name="Str. Drumul Dealu Bistrii, Nr. 25, Sector 4, București",
            email="asociatia.littlepawsenvironment@gmail.com",
        )
        name = staff_invite_org_greeting_name(lead)
        self.assertEqual(name, "Asociatia Littlepawsenvironment")
        self.assertNotIn("Str.", name)

    def test_domain_fallback_for_generic_local(self):
        lead = self._lead(
            org_display_name="Str. Barbu Văcărescu, Nr. 162",
            display_name="Str. Barbu Văcărescu, Nr. 162",
            email="office@red-panda.ro",
        )
        self.assertEqual(staff_invite_org_greeting_name(lead), "Red Panda")
