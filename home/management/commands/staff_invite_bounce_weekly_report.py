"""Trimite raport săptămânal bounce invitații Add USER."""

from django.core.management.base import BaseCommand, CommandError

from home.staff_invite_bounce_weekly_report import send_bounce_weekly_report
from home.staff_invite_daily_report import staff_invite_report_recipients


class Command(BaseCommand):
    help = "Raport email bounce / inbound invitații (ultimele N zile)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=7)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        if not options.get("dry_run") and not staff_invite_report_recipients():
            raise CommandError("Lipsește destinatar raport (STAFF_INVITE_REPORT_EMAIL / CONTACT_NOTIFY_EMAIL).")
        body = send_bounce_weekly_report(
            days=int(options.get("days") or 7),
            dry_run=bool(options.get("dry_run")),
        )
        if options.get("dry_run"):
            self.stdout.write(body)
        else:
            self.stdout.write(self.style.SUCCESS("Raport bounce trimis."))
