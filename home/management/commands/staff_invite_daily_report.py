"""Raport email zilnic — invitații Add USER trimise ieri (cron 09:00 RO)."""

from datetime import datetime

from django.core.management.base import BaseCommand, CommandError

from home.staff_invite_daily_report import (
    send_staff_invite_daily_report,
    staff_invite_report_enabled,
    staff_invite_report_recipients,
    yesterday_ro,
)


class Command(BaseCommand):
    help = "Trimite raport email pentru invitațiile din ziua anterioară (Europe/Bucharest)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--date",
            help="Zi raportată YYYY-MM-DD (implicit: ieri RO).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Trimite chiar dacă EUADOPT_STAFF_INVITE_REPORT_ENABLED=0.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează raportul, fără email.",
        )

    def handle(self, *args, **options):
        for_date = None
        if options.get("date"):
            try:
                for_date = datetime.strptime(options["date"], "%Y-%m-%d").date()
            except ValueError as exc:
                raise CommandError("Format --date invalid (YYYY-MM-DD).") from exc
        else:
            for_date = yesterday_ro()

        if options.get("dry_run"):
            from home.staff_invite_daily_report import format_staff_invite_day_report_text

            report = send_staff_invite_daily_report(
                for_date=for_date, force=True, dry_run=True
            )
            self.stdout.write(format_staff_invite_day_report_text(report))
            return

        if not options.get("force") and not staff_invite_report_enabled():
            self.stdout.write(
                self.style.WARNING(
                    "Raport oprit (EUADOPT_STAFF_INVITE_REPORT_ENABLED=0). Folosește --force."
                )
            )
            return

        recipients = staff_invite_report_recipients()
        if not recipients:
            raise CommandError("Lipsește STAFF_INVITE_REPORT_EMAIL sau CONTACT_NOTIFY_EMAIL.")

        report = send_staff_invite_daily_report(for_date=for_date, force=bool(options.get("force")))
        self.stdout.write(
            self.style.SUCCESS(
                f"Raport {report.date_label} trimis către {', '.join(recipients)} "
                f"({report.sent_ok} OK, {report.errors} erori)."
            )
        )
