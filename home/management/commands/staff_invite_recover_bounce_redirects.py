"""
Recuperare one-shot: bounce/reply vechi cu adresă nouă — update + retransmitere.

  python manage.py staff_invite_recover_bounce_redirects
  python manage.py staff_invite_recover_bounce_redirects --dry-run
  python manage.py staff_invite_recover_bounce_redirects --imap-only --max-imap 300
"""
from django.core.management.base import BaseCommand

from home.staff_onboarding_invite_inbound import (
    poll_imap_inbox,
    recover_missed_bounce_redirects,
    staff_invite_imap_configured,
)


class Command(BaseCommand):
    help = (
        "Recuperare bounce/reply cu adresă alternativă — prospecte fără [BOUNCE-REDIRECT] "
        "(din DB inbound + re-scan IMAP complet)."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar numără candidații DB, fără update/retransmitere.",
        )
        parser.add_argument(
            "--db-only",
            action="store_true",
            help="Doar din snippet-uri inbound salvate în DB.",
        )
        parser.add_argument(
            "--imap-only",
            action="store_true",
            help="Doar re-scan IMAP (body complet, ignoră duplicate inbound).",
        )
        parser.add_argument("--max-leads", type=int, default=500, help="Max. lead-uri din DB.")
        parser.add_argument("--max-imap", type=int, default=250, help="Max. mesaje IMAP.")
        parser.add_argument(
            "--since-days",
            type=int,
            default=90,
            help="Câte zile înapoi (DB + IMAP).",
        )

    def handle(self, *args, **options):
        dry_run = bool(options.get("dry_run"))
        db_only = bool(options.get("db_only"))
        imap_only = bool(options.get("imap_only"))
        since_days = int(options.get("since_days") or 90)
        run_db = not imap_only
        run_imap = not db_only

        if dry_run:
            self.stdout.write(self.style.WARNING("DRY-RUN — fără modificări DB"))

        if run_db:
            stats_db = recover_missed_bounce_redirects(
                dry_run=dry_run,
                max_leads=max(1, int(options.get("max_leads") or 500)),
                since_days=since_days,
            )
            self.stdout.write(self.style.SUCCESS(f"DB recover: {stats_db}"))

        if run_imap:
            if not staff_invite_imap_configured():
                self.stderr.write("IMAP neconfigurat — skip recover IMAP.")
            elif dry_run:
                self.stdout.write("IMAP recover: skip în dry-run (ar citi inbox).")
            else:
                stats_imap = poll_imap_inbox(
                    max_messages=max(1, int(options.get("max_imap") or 250)),
                    mark_seen=False,
                    mode="bounce_recover",
                    since_days=since_days,
                )
                self.stdout.write(self.style.SUCCESS(f"IMAP recover: {stats_imap}"))
