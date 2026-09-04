"""
Trimite duminica mail de mulțumire către membrii noi (Luni–Duminică / catch-up 14 zile).
O singură dată per user.

  python manage.py weekly_new_member_thanks
  python manage.py weekly_new_member_thanks --dry-run
  python manage.py weekly_new_member_thanks --force   # ignoră „doar duminică”
"""
from django.core.management.base import BaseCommand

from home.weekly_new_member_thanks import process_weekly_thanks


class Command(BaseCommand):
    help = "Mail săptămânal mulțumire membri noi + îndemn recomandare colaboratori."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Listează candidații fără SMTP / fără flag în DB.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rulează indiferent de ziua săptămânii (test).",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        force = bool(options.get("force"))
        stats = process_weekly_thanks(dry_run=dry, force=force)
        if not stats.get("ok"):
            self.stdout.write(self.style.WARNING(f"SKIP: {stats.get('reason')}"))
            return
        self.stdout.write(
            self.style.SUCCESS(
                "weekly_thanks "
                f"candidates={stats['candidates']} sent={stats['sent']} "
                f"dry_run={stats['dry_run']} opt_out={stats['skipped_opt_out']} "
                f"already={stats['skipped_already']} err={stats['error']} "
                f"window={stats['start']} .. {stats['end']}"
            )
        )
        if dry:
            from home.weekly_new_member_thanks import candidates_queryset

            qs, _, _ = candidates_queryset()
            for u in qs[:50]:
                self.stdout.write(f"  would send -> {u.email} (id={u.pk}, joined={u.date_joined})")
            if qs.count() > 50:
                self.stdout.write(f"  … +{qs.count() - 50} more")
