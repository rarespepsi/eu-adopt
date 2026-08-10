from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.test import TestCase, override_settings

from home.models import StaffOnboardingLead, StaffOnboardingInviteLog
from home.staff_invite_daily_wave import (
    STAFF_INVITE_CRON_PM_REGION_CACHE_KEY,
    STAFF_INVITE_CRON_REGION_CACHE_KEY,
    WAVE_SLOT_AFTERNOON,
    mark_region_group_used,
    next_region_group_for_cron,
    pick_leads_for_daily_wave,
    run_staff_invite_daily_wave,
    staff_invite_cron_pm_collab_subtypes,
)
from home.staff_invite_email_expand import (
    is_plausible_invite_email,
    split_email_field,
    staff_invite_expand_lead_send_targets,
)


class StaffInviteDailyWaveTests(TestCase):
    def tearDown(self):
        cache.delete(STAFF_INVITE_CRON_REGION_CACHE_KEY)
        cache.delete(STAFF_INVITE_CRON_PM_REGION_CACHE_KEY)

    def test_region_group_alternates(self):
        self.assertEqual(next_region_group_for_cron(), "a")
        mark_region_group_used("a")
        self.assertEqual(next_region_group_for_cron(), "b")
        mark_region_group_used("b")
        self.assertEqual(next_region_group_for_cron(), "a")

    def test_pm_region_group_independent(self):
        mark_region_group_used("a", WAVE_SLOT_AFTERNOON)
        self.assertEqual(next_region_group_for_cron(), "a")
        self.assertEqual(next_region_group_for_cron(WAVE_SLOT_AFTERNOON), "b")

    def test_pm_default_subtypes(self):
        self.assertEqual(
            staff_invite_cron_pm_collab_subtypes(),
            ["cabinet", "magazin", "grooming"],
        )

    def test_split_email_field(self):
        raw = "a@x.ro / b@y.com   c@z.net"
        self.assertEqual(split_email_field(raw), ["a@x.ro", "b@y.com", "c@z.net"])

    def test_rejects_invalid_invite_emails(self):
        self.assertFalse(is_plausible_invite_email("babeni@://e-adm.com"))
        self.assertFalse(is_plausible_invite_email("not-an-email"))
        self.assertTrue(is_plausible_invite_email("contact@eu-adopt.ro"))
        self.assertEqual(split_email_field("ok@a.ro / babeni@://e-adm.com"), ["ok@a.ro"])

    def test_expand_skips_all_invalid_emails(self):
        lead = StaffOnboardingLead.objects.create(
            email="babeni@://e-adm.com",
            display_name="Bad",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Cluj",
        )
        self.assertEqual(staff_invite_expand_lead_send_targets(lead), [])
        lead.refresh_from_db()
        self.assertEqual(lead.invite_mail_status, StaffOnboardingLead.INVITE_BOUNCED)

    def test_pick_skips_invalid_and_fills_with_valid(self):
        StaffOnboardingLead.objects.create(
            email="babeni@://e-adm.com",
            display_name="Bad",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        good = StaffOnboardingLead.objects.create(
            email="adapost.ok@example.com",
            display_name="Good",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        picked = pick_leads_for_daily_wave(
            region_group="a",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            wave_limit=5,
        )
        self.assertEqual([p.pk for p in picked], [good.pk])
        bad = StaffOnboardingLead.objects.get(email="babeni@://e-adm.com")
        self.assertEqual(bad.invite_mail_status, StaffOnboardingLead.INVITE_BOUNCED)

    @override_settings(
        STAFF_INVITE_CRON_ENABLED=True,
        EUADOPT_STAFF_INVITE_EMAIL_ENABLED=False,
        STAFF_LEAD_INVITE_MAX_PER_DAY=55,
    )
    def test_wave_rotates_even_when_only_invalid_left(self):
        User = get_user_model()
        User.objects.create_user(username="rares", password="x", is_staff=True)
        StaffOnboardingLead.objects.create(
            email="bad@://broken.ro",
            display_name="OnlyBad",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        self.assertEqual(next_region_group_for_cron(), "a")
        result = run_staff_invite_daily_wave(region_group="a", force=True, wave_limit=5)
        self.assertFalse(result.skipped)
        self.assertEqual(result.picked_count, 0)
        self.assertEqual(next_region_group_for_cron(), "b")

    def test_pick_fills_with_resend_when_first_empty(self):
        from datetime import timedelta

        from django.utils import timezone

        # Lead deja invitat, cooldown trecut → eligibil val 2
        lead = StaffOnboardingLead.objects.create(
            email="resend.ok@example.com",
            display_name="Resend",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Cluj",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email=lead.email,
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
            dispatch_kind=StaffOnboardingInviteLog.DISPATCH_WAVE,
        )
        StaffOnboardingLead.objects.filter(pk=lead.pk).update(
            invite_email_last_sent_at=timezone.now() - timedelta(days=10),
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        lead.refresh_from_db()
        picked = pick_leads_for_daily_wave(
            region_group="a",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            wave_limit=5,
        )
        self.assertEqual([p.pk for p in picked], [lead.pk])

    @override_settings(STAFF_INVITE_CRON_ENABLED=False)
    def test_cron_disabled_skips(self):
        result = run_staff_invite_daily_wave()
        self.assertTrue(result.skipped)
