from datetime import datetime, timedelta
from unittest.mock import patch
from zoneinfo import ZoneInfo

from django.test import TestCase, override_settings
from django.utils import timezone

from home.models import StaffOnboardingInviteLog, StaffOnboardingLead
from home.staff_invite_daily_report import (
    build_staff_invite_day_report,
    format_staff_invite_day_report_text,
    send_staff_invite_daily_report,
    yesterday_ro,
)

RO = ZoneInfo("Europe/Bucharest")


class StaffInviteDailyReportTests(TestCase):
    def _lead(self, email: str) -> StaffOnboardingLead:
        return StaffOnboardingLead.objects.create(
            email=email,
            display_name="Test",
            account_kind=StaffOnboardingLead.KIND_ADAPOST,
        )

    def test_yesterday_ro(self):
        fixed = datetime(2026, 7, 15, 8, 0, 0, tzinfo=RO)
        with patch("home.staff_invite_daily_report.timezone.now", return_value=fixed):
            self.assertEqual(yesterday_ro(), datetime(2026, 7, 14).date())

    def test_build_report_counts(self):
        day = datetime(2026, 7, 14, 13, 58, 0, tzinfo=RO)
        lead = self._lead("a@test.ro")
        ok_log = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="a@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
            dispatch_kind=StaffOnboardingInviteLog.DISPATCH_WAVE,
        )
        err_log = StaffOnboardingInviteLog.objects.create(
            lead=lead,
            to_email="bad@test.ro",
            outcome=StaffOnboardingInviteLog.OUTCOME_ERROR,
            error_message="Invalid address",
            dispatch_kind=StaffOnboardingInviteLog.DISPATCH_WAVE,
        )
        StaffOnboardingInviteLog.objects.filter(pk=ok_log.pk).update(sent_at=day)
        StaffOnboardingInviteLog.objects.filter(pk=err_log.pk).update(
            sent_at=day + timedelta(minutes=1)
        )

        report = build_staff_invite_day_report(datetime(2026, 7, 14).date())
        self.assertEqual(report.sent_ok, 1)
        self.assertEqual(report.errors, 1)
        self.assertEqual(report.dispatch_wave, 2)
        text = format_staff_invite_day_report_text(report)
        self.assertIn("14.07.2026", text)
        self.assertIn("Trimise OK", text)

    @override_settings(
        STAFF_INVITE_REPORT_ENABLED=True,
        STAFF_INVITE_REPORT_EMAIL="staff@test.ro",
        DEFAULT_FROM_EMAIL="EU-Adopt <noreply@test.ro>",
    )
    @patch("home.staff_invite_daily_report.send_mail_text_and_html")
    def test_send_report(self, mock_send):
        send_staff_invite_daily_report(datetime(2026, 7, 14).date(), force=True)
        mock_send.assert_called_once()
        args, kwargs = mock_send.call_args
        self.assertIn("14.07.2026", kwargs.get("subject", args[0] if args else ""))
