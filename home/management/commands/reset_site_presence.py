"""
Resetează statisticile Prezență (șterge istoric sesiuni / zilnice / online).

  python manage.py reset_site_presence          # previzualizare
  python manage.py reset_site_presence --apply  # execută
"""

from __future__ import annotations

from django.core.management.base import BaseCommand

from home.site_presence import reset_site_presence_data


class Command(BaseCommand):
    help = "Șterge tot istoricul modulului Prezență (Analiză / Prezență)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Execută ștergerea (fără acest flag = doar afișare număr înregistrări).",
        )

    def handle(self, *args, **options):
        from home.models import (
            SitePresenceActive,
            SitePresenceDaily,
            SitePresenceDaySession,
            SitePresenceDayUser,
        )

        counts = {
            "daily": SitePresenceDaily.objects.count(),
            "day_sessions": SitePresenceDaySession.objects.count(),
            "day_users": SitePresenceDayUser.objects.count(),
            "active": SitePresenceActive.objects.count(),
        }
        self.stdout.write(
            "Prezență curentă: "
            f"{counts['daily']} zile, {counts['day_sessions']} sesiuni-zilnic, "
            f"{counts['day_users']} user-zilnic, {counts['active']} active."
        )
        if not options["apply"]:
            self.stdout.write(self.style.WARNING("Dry-run. Repetă cu --apply pentru ștergere."))
            return
        reset_site_presence_data()
        self.stdout.write(self.style.SUCCESS("Prezență resetată — contorul pornește de la zero."))
