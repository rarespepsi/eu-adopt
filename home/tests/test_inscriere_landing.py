"""Teste formular /inscriere/ (Facebook) și compatibilitate Add USER."""

import uuid

from django.contrib.auth import get_user_model
from django.test import Client, TestCase, override_settings
from django.urls import reverse
from django.utils import timezone

from home.models import StaffOnboardingInviteLog, StaffOnboardingLead
from home.staff_onboarding_invite import (
    staff_invite_can_send,
    staff_invite_mark_landing_access,
    staff_invite_token_usable,
)

User = get_user_model()


def _inscriere_post_data(**overrides):
    data = {
        "category": StaffOnboardingLead.KIND_ADAPOST,
        "email": f"fb_{uuid.uuid4().hex[:8]}@test.local",
        "phone": "+40722111222",
        "contact": "Contact Test",
        "accept_termeni": "on",
        "accept_gdpr": "on",
    }
    data.update(overrides)
    return data


@override_settings(
    PRELAUNCH_MODE=True,
    POPULATION_ONBOARDING_ENABLED=True,
    POPULATION_SUPERUSER_ONLY_LOGIN=True,
)
class InscriereLandingTests(TestCase):
    def test_inscriere_get_public_in_prelaunch(self):
        r = Client().get(reverse("inscriere"))
        self.assertEqual(r.status_code, 200)
        self.assertIn(b"Spre formular cont nou", r.content)

    def test_inscriere_post_redirects_to_signup_with_inv(self):
        email = f"fb_redir_{uuid.uuid4().hex[:8]}@test.local"
        c = Client()
        r = c.post(reverse("inscriere"), _inscriere_post_data(email=email))
        self.assertEqual(r.status_code, 302)
        self.assertIn("/signup/organizatie/", r.url)
        self.assertIn("inv=", r.url)
        lead = StaffOnboardingLead.objects.get(email__iexact=email)
        self.assertIn("/inscriere/", (lead.invite_staff_notes or "").lower())
        self.assertIsNone(lead.invite_email_last_sent_at)
        self.assertEqual(lead.invite_mail_status, StaffOnboardingLead.INVITE_NEVER)

    def test_landing_dry_run_does_not_block_add_user_smtp(self):
        from django.core import mail
        from django.test import RequestFactory

        from home.staff_onboarding_invite import staff_invite_process_one

        email = f"fb_smtp_{uuid.uuid4().hex[:8]}@test.local"
        c = Client()
        r = c.post(reverse("inscriere"), _inscriere_post_data(email=email))
        self.assertEqual(r.status_code, 302)
        lead = StaffOnboardingLead.objects.get(email__iexact=email)
        ok, reason = staff_invite_can_send(lead)
        self.assertTrue(ok, reason)
        self.assertEqual(
            StaffOnboardingInviteLog.objects.filter(
                lead=lead,
                outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
                template_key="facebook_landing",
            ).count(),
            1,
        )

        staff = User.objects.create_user(
            username=f"stfb_{uuid.uuid4().hex[:6]}",
            email="stfb@t.local",
            password="StaffFb!",
            is_staff=True,
        )
        mail.outbox.clear()
        req = RequestFactory().get("/admin-analysis/add-user/")
        with self.settings(STAFF_INVITE_EMAIL_ENABLED=True):
            result = staff_invite_process_one(req, staff, lead)
        self.assertEqual(result, "sent")
        lead.refresh_from_db()
        self.assertIsNotNone(lead.invite_email_last_sent_at)
        self.assertEqual(lead.invite_mail_status, StaffOnboardingLead.INVITE_SENT)
        self.assertEqual(len(mail.outbox), 1)

    def test_landing_gate_allows_signup_without_smtp_invite(self):
        email = f"fb_gate_{uuid.uuid4().hex[:8]}@test.local"
        c = Client()
        r = c.post(reverse("inscriere"), _inscriere_post_data(email=email))
        self.assertEqual(r.status_code, 302)
        lead = StaffOnboardingLead.objects.get(email__iexact=email)
        lead.refresh_from_db()
        self.assertTrue(staff_invite_token_usable(lead))
        tok = lead.consent_invite_token
        r2 = c.get(f"{reverse('signup_organizatie')}?inv={tok}")
        self.assertEqual(r2.status_code, 200)

    def test_landing_on_existing_imported_lead_still_allows_add_user(self):
        email = f"import_{uuid.uuid4().hex[:8]}@test.local"
        lead = StaffOnboardingLead.objects.create(
            email=email,
            display_name="Import Prospect",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Iași",
            status=StaffOnboardingLead.ST_READY,
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        c = Client()
        r = c.post(
            reverse("inscriere"),
            _inscriere_post_data(
                email=email,
                phone="+40733334444",
                contact="FB Contact",
            ),
        )
        self.assertEqual(r.status_code, 302)
        lead.refresh_from_db()
        self.assertEqual(lead.phone, "+40733334444")
        self.assertIsNone(lead.invite_email_last_sent_at)
        ok, _ = staff_invite_can_send(lead)
        self.assertTrue(ok)

    def test_mark_landing_access_unit(self):
        lead = StaffOnboardingLead.objects.create(
            email=f"unit_{uuid.uuid4().hex[:8]}@test.local",
            display_name="Unit",
            account_kind=StaffOnboardingLead.KIND_ORG,
            consent_privacy_at=timezone.now(),
            invite_staff_notes="Sursă: formular /inscriere/ (Facebook)",
        )
        staff_invite_mark_landing_access(lead)
        lead.refresh_from_db()
        self.assertIsNone(lead.invite_email_last_sent_at)
        self.assertTrue(staff_invite_token_usable(lead))
