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


class StaffInviteUatWaveTests(TestCase):
    def test_uat_order_cj_before_comuna_skips_plain_shelter(self):
        shelter = StaffOnboardingLead.objects.create(
            email="shelter@example.com",
            display_name="Adapost vechi",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            judet="Alba",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        comuna = StaffOnboardingLead.objects.create(
            email="comuna@example.com",
            display_name="Primaria X",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            is_public_shelter=True,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Alba",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        cj = StaffOnboardingLead.objects.create(
            email="cj@example.com",
            display_name="CJ Alba",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            is_public_shelter=True,
            uat_category=StaffOnboardingLead.UAT_CJ,
            judet="Alba",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        with self.settings(STAFF_INVITE_CRON_UAT_ONLY=True):
            from home.staff_invite_daily_wave import pick_leads_for_daily_wave

            picked = pick_leads_for_daily_wave(
                region_group="a",
                account_kind=StaffOnboardingLead.KIND_ADAPOST,
                wave_limit=10,
            )
        self.assertEqual([p.pk for p in picked], [cj.pk, comuna.pk])
        self.assertNotIn(shelter.pk, [p.pk for p in picked])

    def test_uat_template_key(self):
        from home.staff_onboarding_invite import staff_invite_template_key

        lead = StaffOnboardingLead(
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            uat_category=StaffOnboardingLead.UAT_CJ,
            is_public_shelter=True,
        )
        self.assertEqual(staff_invite_template_key(lead), "uat_public")

    def test_cjcs_marker_pauses_other_uat_and_adds_opening(self):
        from home.staff_invite_daily_wave import pick_uat_leads_for_daily_wave
        from home.staff_onboarding_invite import (
            CJCS_INVITE_OPENING,
            CJCS_LISTA_NOTE_MARKER,
            staff_invite_subject_body,
        )

        other = StaffOnboardingLead.objects.create(
            email="primaria.alba@example.com",
            display_name="Primăria Alba",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Alba",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        cs = StaffOnboardingLead.objects.create(
            email="primaria.testcs@example.com",
            display_name="Primăria Test CS",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Caraș-Severin",
            notes=f"{CJCS_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        picked = pick_uat_leads_for_daily_wave(wave_limit=10)
        self.assertEqual([p.pk for p in picked], [cs.pk])
        self.assertNotIn(other.pk, [p.pk for p in picked])

        from django.test import RequestFactory

        req = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        _subj, body, _key = staff_invite_subject_body(req, cs)
        self.assertIn(CJCS_INVITE_OPENING.strip(), body)
        self.assertIn("signup", body.lower())
        _subj2, body2, _ = staff_invite_subject_body(req, other)
        self.assertNotIn("Caraș-Severin", body2.split("\n\n")[1] if "\n\n" in body2 else "")
        self.assertNotIn(CJCS_INVITE_OPENING.strip(), body2)

    def test_cjvn_marker_pauses_other_uat_opening_and_attachment(self):
        from home.staff_invite_daily_wave import pick_uat_leads_for_daily_wave
        from home.staff_onboarding_invite import (
            CJVN_DORESC_CONT_BLOCK,
            CJVN_INVITE_OPENING,
            CJVN_LISTA_NOTE_MARKER,
            staff_invite_attachments_for_lead,
            staff_invite_subject_body,
        )

        other = StaffOnboardingLead.objects.create(
            email="primaria.alba2@example.com",
            display_name="Primăria Alba 2",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Alba",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        vn = StaffOnboardingLead.objects.create(
            email="primaria.testvn@example.com",
            display_name="Primăria Test VN",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Vrancea",
            notes=f"{CJVN_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        picked = pick_uat_leads_for_daily_wave(wave_limit=10)
        self.assertEqual([p.pk for p in picked], [vn.pk])
        self.assertNotIn(other.pk, [p.pk for p in picked])

        from django.test import RequestFactory

        req = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        _subj, body, _key = staff_invite_subject_body(req, vn)
        self.assertIn(CJVN_INVITE_OPENING.strip(), body)
        self.assertIn(CJVN_DORESC_CONT_BLOCK.strip(), body)
        self.assertIn("DORESC CONT", body)
        atts = staff_invite_attachments_for_lead(vn)
        self.assertEqual(len(atts), 1)
        self.assertEqual(atts[0][2], "application/pdf")
        self.assertGreater(len(atts[0][1]), 1000)
        atts_other = staff_invite_attachments_for_lead(other)
        self.assertEqual(atts_other, [])

    def test_cjolt_and_cjag_markers_in_priority_after_vn(self):
        from home.staff_invite_daily_wave import pick_uat_leads_for_daily_wave
        from home.staff_onboarding_invite import (
            CJAG_LISTA_NOTE_MARKER,
            CJOLT_LISTA_NOTE_MARKER,
            CJVN_LISTA_NOTE_MARKER,
            staff_invite_attachments_for_lead,
            staff_invite_subject_body,
        )

        olt = StaffOnboardingLead.objects.create(
            email="primaria.testolt@example.com",
            display_name="Primăria Test Olt",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Olt",
            notes=f"{CJOLT_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        ag = StaffOnboardingLead.objects.create(
            email="primaria.testag@example.com",
            display_name="Primăria Test AG",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Argeș",
            notes=f"{CJAG_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        # Fără VN: Olt are prioritate față de Argeș
        picked = pick_uat_leads_for_daily_wave(wave_limit=5)
        self.assertEqual(picked[0].pk, olt.pk)
        self.assertNotIn(ag.pk, [p.pk for p in picked])

        from django.test import RequestFactory

        req = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        _s, body, _ = staff_invite_subject_body(req, olt)
        self.assertIn("Consiliului Județean Olt", body)
        self.assertIn("DORESC CONT", body)
        self.assertEqual(len(staff_invite_attachments_for_lead(olt)), 1)

        vn = StaffOnboardingLead.objects.create(
            email="primaria.testvn2@example.com",
            display_name="Primăria Test VN2",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Vrancea",
            notes=f"{CJVN_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        picked2 = pick_uat_leads_for_daily_wave(wave_limit=5)
        self.assertEqual(picked2[0].pk, vn.pk)

    def test_cjsj_salaj_marker_after_cjag(self):
        from home.staff_invite_daily_wave import pick_uat_leads_for_daily_wave
        from home.staff_onboarding_invite import (
            CJAG_LISTA_NOTE_MARKER,
            CJSJ_LISTA_NOTE_MARKER,
            staff_invite_attachments_for_lead,
            staff_invite_subject_body,
        )
        from django.test import RequestFactory

        sj = StaffOnboardingLead.objects.create(
            email="primaria.testsj@example.com",
            display_name="Primăria Test SJ",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Sălaj",
            notes=f"{CJSJ_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        ag = StaffOnboardingLead.objects.create(
            email="primaria.testag2@example.com",
            display_name="Primăria Test AG2",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Argeș",
            notes=f"{CJAG_LISTA_NOTE_MARKER} test",
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
        )
        # Fără loturi anterioare: Argeș înainte de Sălaj
        picked = pick_uat_leads_for_daily_wave(wave_limit=5)
        self.assertEqual(picked[0].pk, ag.pk)
        self.assertNotIn(sj.pk, [p.pk for p in picked])

        ag.invite_mail_status = StaffOnboardingLead.INVITE_SENT
        ag.save(update_fields=["invite_mail_status", "updated_at"])
        picked2 = pick_uat_leads_for_daily_wave(wave_limit=5)
        self.assertEqual(picked2[0].pk, sj.pk)

        req = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        _s, body, _ = staff_invite_subject_body(req, sj)
        self.assertIn("Consiliului Județean Sălaj", body)
        self.assertIn("DORESC CONT", body)
        self.assertEqual(len(staff_invite_attachments_for_lead(sj)), 1)

    def test_cj_reinvite_uses_revenim_opening(self):
        from home.staff_onboarding_invite import (
            CJOLT_LISTA_NOTE_MARKER,
            CJ_REINVITE_NOTE_MARKER,
            staff_invite_subject_body,
        )
        from django.test import RequestFactory

        lead = StaffOnboardingLead.objects.create(
            email="primaria.revenim@example.com",
            display_name="Primăria Revenim",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            collaborator_subtype=StaffOnboardingLead.COLLAB_ADPUB,
            uat_category=StaffOnboardingLead.UAT_COMUNA,
            judet="Olt",
            notes=f"{CJOLT_LISTA_NOTE_MARKER}\n{CJ_REINVITE_NOTE_MARKER} 2026-09-23] test",
            invite_mail_status=StaffOnboardingLead.INVITE_SENT,
        )
        req = RequestFactory().get("/", HTTP_HOST="eu-adopt.ro")
        _s, body, _ = staff_invite_subject_body(req, lead)
        self.assertIn("Revenim către dumneavoastră", body)
        self.assertIn("Consiliului Județean Olt", body)
        self.assertIn("baza de date", body)
        self.assertNotIn("vă transmitem invitația de a folosi\ngratuit", body)
