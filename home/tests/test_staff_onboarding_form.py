"""Validare formular manual Add USER — câmpuri vs. template, salvare adapost."""

from django.test import SimpleTestCase, TestCase

from home.models import StaffOnboardingLead
from home.staff_onboarding_form import StaffOnboardingLeadForm

_FORM_EXCLUDED_MODEL_FIELDS = frozenset(
    {
        "invite_max_sends",
        "invite_cooldown_days",
        "invite_staff_notes",
    }
)


class StaffOnboardingLeadFormFieldsTests(SimpleTestCase):
    def test_manual_form_excludes_invite_control_fields(self):
        form_fields = set(StaffOnboardingLeadForm.Meta.fields)
        for name in _FORM_EXCLUDED_MODEL_FIELDS:
            self.assertNotIn(
                name,
                form_fields,
                msg=f"{name} nu trebuie în StaffOnboardingLeadForm fără input în template",
            )


class StaffOnboardingLeadFormSaveTests(TestCase):
    def test_adapost_edit_preserves_subtype_when_missing_from_post(self):
        lead = StaffOnboardingLead.objects.create(
            email="old@example.com",
            display_name="Nicol",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            judet="Neamț",
            oras="Piatra-Neamț",
        )
        data = {
            "email": "new@example.com",
            "phone": "",
            "display_name": "Nicol",
            "username_suggested": "",
            "account_kind": StaffOnboardingLead.KIND_ADAPOST,
            "first_name": "",
            "last_name": "",
            "judet": "Neamț",
            "oras": "Piatra-Neamț",
            "org_display_name": "Adăpost test",
            "notes": "",
        }
        form = StaffOnboardingLeadForm(data, instance=lead)
        self.assertTrue(form.is_valid(), form.errors)
        saved = form.save()
        self.assertEqual(saved.email, "new@example.com")
        self.assertEqual(saved.collaborator_subtype, StaffOnboardingLead.COLLAB_ADPUB)
