"""Bounce NDR cu adresă alternativă → update prospect + retransmitere."""

from django.contrib.auth import get_user_model
from django.test import TestCase, override_settings

from home.models import StaffOnboardingInviteLog, StaffOnboardingLead
from home.staff_onboarding_invite_inbound import (
    _sanitize_imap_text,
    extract_suggested_redirect_email,
    process_inbound_email,
)

User = get_user_model()


class BounceRedirectEmailTests(TestCase):
    def test_extract_suggested_try_sending_to(self):
        body = (
            "Final-Recipient: rfc822; vechi@primarie.ro\n"
            "The recipient address has changed. Please try sending to: nou@primarie.ro\n"
        )
        got = extract_suggested_redirect_email(
            body,
            failed_emails=["vechi@primarie.ro"],
            lead_email="vechi@primarie.ro",
        )
        self.assertEqual(got, "nou@primarie.ro")

    def test_extract_ignores_try_again_later(self):
        body = (
            "primaria@yahoo.com, ERROR CODE :552 - mailbox is full. "
            "Please try again later or contact the recipient directly.\n"
            "Final-Recipient: rfc822; primaria@yahoo.com\n"
        )
        got = extract_suggested_redirect_email(
            body,
            failed_emails=["primaria@yahoo.com"],
            lead_email="primaria@yahoo.com",
        )
        self.assertIsNone(got)

    def test_extract_romanian_adresa_noua(self):
        body = "Adresa nouă este: contact@primaria-exemplu.ro\nFinal-Recipient: rfc822; old@primaria-exemplu.ro"
        got = extract_suggested_redirect_email(
            body,
            failed_emails=["old@primaria-exemplu.ro"],
            lead_email="old@primaria-exemplu.ro",
        )
        self.assertEqual(got, "contact@primaria-exemplu.ro")

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False)
    def test_process_bounce_redirect_updates_lead_and_resends(self):
        staff = User.objects.create_user(
            username="staff_bounce_rd",
            email="staff_bounce_rd@test.local",
            password="x",
            is_staff=True,
        )
        lead = StaffOnboardingLead.objects.create(
            email="vechi@exemplu-uat.ro",
            display_name="Primaria Test",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Iași",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        body = (
            "This is a permanent error.\n"
            "Final-Recipient: rfc822; vechi@exemplu-uat.ro\n"
            "The mailbox has moved. Please use: nou@exemplu-uat.ro\n"
        )
        result = process_inbound_email(
            from_email="mailer-daemon@zoho.com",
            to_addrs=[f"invite+{lead.pk}@eu-adopt.ro"],
            subject="Undelivered Mail Returned to Sender",
            body=body,
            external_id="test-bounce-redirect-1",
        )
        self.assertEqual(result.get("kind"), "bounce")
        self.assertTrue(result.get("redirected"))
        self.assertEqual(result.get("redirect_email"), "nou@exemplu-uat.ro")
        self.assertIn(result.get("resend_outcome"), ("simulated", "sent", "daily_cap", "blocked"))
        lead.refresh_from_db()
        self.assertEqual(lead.email.lower(), "nou@exemplu-uat.ro")
        self.assertNotEqual(lead.invite_mail_status, StaffOnboardingLead.INVITE_BOUNCED)
        self.assertIn("[BOUNCE-REDIRECT]", lead.invite_staff_notes or "")
        self.assertTrue(
            StaffOnboardingInviteLog.objects.filter(
                lead=lead,
                dispatch_kind=StaffOnboardingInviteLog.DISPATCH_BOUNCE_RD,
            ).exists()
            or result.get("resend_outcome") in ("daily_cap", "blocked", "error")
        )
        # staff created ensures _cron_staff_user finds someone
        self.assertTrue(User.objects.filter(pk=staff.pk, is_staff=True).exists())

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False)
    def test_process_bounce_without_suggestion_still_marks_bounced(self):
        lead = StaffOnboardingLead.objects.create(
            email="doar-bad@exemplu-uat.ro",
            display_name="Bad Only",
            account_kind=StaffOnboardingLead.KIND_PF,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        body = (
            "Final-Recipient: rfc822; doar-bad@exemplu-uat.ro\n"
            "Status: 550 - No Such User Here\n"
        )
        result = process_inbound_email(
            from_email="mailer-daemon@zoho.com",
            to_addrs=[f"invite+{lead.pk}@eu-adopt.ro"],
            subject="Undelivered Mail Returned to Sender",
            body=body,
            external_id="test-bounce-no-redirect-1",
        )
        self.assertFalse(result.get("redirected", False))
        lead.refresh_from_db()
        self.assertEqual(lead.invite_mail_status, StaffOnboardingLead.INVITE_BOUNCED)
        self.assertEqual(lead.email.lower(), "doar-bad@exemplu-uat.ro")

    def test_sanitize_imap_text_strips_nul(self):
        raw = "Undelivered\x00Mail\x00"
        self.assertEqual(_sanitize_imap_text(raw), "UndeliveredMail")

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False)
    def test_process_inbound_saves_body_with_nul_chars(self):
        lead = StaffOnboardingLead.objects.create(
            email="nul@exemplu-uat.ro",
            display_name="NUL Test",
            account_kind=StaffOnboardingLead.KIND_PF,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        body = (
            "Final-Recipient: rfc822; nul@exemplu-uat.ro\n"
            "Please use: nou-nul@exemplu-uat.ro\x00extra\n"
        )
        result = process_inbound_email(
            from_email="mailer-daemon@zoho.com",
            to_addrs=[f"invite+{lead.pk}@eu-adopt.ro"],
            subject="Undelivered\x00 Mail",
            body=body,
            external_id="test-bounce-nul-1",
        )
        self.assertEqual(result.get("kind"), "bounce")
        self.assertTrue(result.get("redirected"))
        self.assertIsNotNone(result.get("inbound_id"))

    @override_settings(STAFF_INVITE_EMAIL_ENABLED=False)
    def test_process_reply_with_new_address_redirects(self):
        User.objects.create_user(
            username="staff_reply_rd",
            email="staff_reply_rd@test.local",
            password="x",
            is_staff=True,
        )
        lead = StaffOnboardingLead.objects.create(
            email="vechi-reply@exemplu-uat.ro",
            display_name="Reply Redirect",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Iași",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        body = "Bună ziua, adresa corectă este contact@exemplu-uat.ro. Mulțumim."
        result = process_inbound_email(
            from_email="vechi-reply@exemplu-uat.ro",
            to_addrs=["contact@eu-adopt.ro"],
            subject="Re: Invitație EU-Adopt",
            body=body,
            external_id="test-reply-redirect-1",
        )
        self.assertEqual(result.get("kind"), "reply")
        self.assertTrue(result.get("redirected"))
        lead.refresh_from_db()
        self.assertEqual(lead.email.lower(), "contact@exemplu-uat.ro")
        self.assertIn("[BOUNCE-REDIRECT]", lead.invite_staff_notes or "")
