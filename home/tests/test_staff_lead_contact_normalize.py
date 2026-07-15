from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings

from home.models import StaffOnboardingInviteLog, StaffOnboardingLead
from home.staff_invite_daily_report import (
    _classify_invite_day_errors,
    build_staff_invite_day_report,
    format_staff_invite_day_report_text,
)
from home.staff_lead_contact_normalize import normalize_lead_phone, split_phone_field

RO = ZoneInfo("Europe/Bucharest")


class StaffLeadContactNormalizeTests(TestCase):
    def test_split_phone_field(self):
        raw = "0257270352/0257214211"
        self.assertEqual(split_phone_field(raw), ["0257270352", "0257214211"])

    def test_normalize_lead_phone(self):
        lead = StaffOnboardingLead.objects.create(
            email="x@test.ro",
            display_name="Test",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
            phone="0723.211.448 / 0758.100.511",
        )
        self.assertTrue(normalize_lead_phone(lead, save=True))
        lead.refresh_from_db()
        self.assertEqual(lead.phone, "0723.211.448")
        self.assertIn("Telefoane suplimentare", lead.notes)


class StaffInviteReportErrorClassifyTests(TestCase):
    def _lead(self, email: str) -> StaffOnboardingLead:
        return StaffOnboardingLead.objects.create(
            email=email,
            display_name="Test",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
        )

    def test_classify_resolved_via_split(self):
        day = datetime(2026, 7, 14, 13, 58, 0, tzinfo=RO)
        lead = self._lead("a@test.ro")
        err = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="a@test.ro b@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_ERROR,
            error_message="Invalid address",
        )
        ok = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="a@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
        )
        StaffOnboardingInviteLog.objects.filter(pk=err.pk).update(sent_at=day)
        StaffOnboardingInviteLog.objects.filter(pk=ok.pk).update(
            sent_at=day + timedelta(minutes=10)
        )
        err_logs = StaffOnboardingInviteLog.objects.filter(pk=err.pk)
        sent_logs = StaffOnboardingInviteLog.objects.filter(pk=ok.pk)
        resolved, unresolved = _classify_invite_day_errors(err_logs, sent_logs)
        self.assertEqual(len(resolved), 1)
        self.assertEqual(len(unresolved), 0)

    def test_report_shows_resolved_section(self):
        day = datetime(2026, 7, 14, 13, 58, 0, tzinfo=RO)
        lead = self._lead("a@test.ro")
        err = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="a@test.ro b@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_ERROR,
        )
        ok = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="a@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
        )
        StaffOnboardingInviteLog.objects.filter(pk=err.pk).update(sent_at=day)
        StaffOnboardingInviteLog.objects.filter(pk=ok.pk).update(
            sent_at=day + timedelta(minutes=10)
        )
        report = build_staff_invite_day_report(datetime(2026, 7, 14).date())
        text = format_staff_invite_day_report_text(report)
        self.assertEqual(report.errors_resolved, 1)
        self.assertIn("corectate", text)
