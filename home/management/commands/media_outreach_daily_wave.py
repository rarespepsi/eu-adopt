"""
Val zilnic email Radio (spot audio).

  python manage.py media_outreach_daily_wave
  python manage.py media_outreach_daily_wave --force --wave-size 5
"""

from django.core.management.base import BaseCommand

from home.media_outreach_daily_wave import (
    media_outreach_cron_enabled,
    media_outreach_cron_wave_size,
    run_media_outreach_radio_daily_wave,
)


class Command(BaseCommand):
    help = "Trimite val zilnic email outreach către posturi radio (max/zi din setări)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--wave-size",
            type=int,
            default=0,
            help="Câte emailuri în acest val (0 = din setări / plafon zilnic).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rulează chiar dacă EUADOPT_MEDIA_OUTREACH_CRON_ENABLED=0.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Arată setările, fără trimitere.",
        )

    def handle(self, *args, **options):
        if options.get("dry_run"):
            self.stdout.write(
                f"Dry-run: cron_enabled={media_outreach_cron_enabled()} "
                f"wave_size={media_outreach_cron_wave_size()} (fără trimitere)"
            )
            return

        wave_limit = options.get("wave_size") or None
        if wave_limit == 0:
            wave_limit = None

        result = run_media_outreach_radio_daily_wave(
            wave_limit=wave_limit,
            force=bool(options.get("force")),
        )
        if result.skipped:
            self.stdout.write(self.style.WARNING(result.message))
        elif result.stats.get("sent") or result.stats.get("simulated"):
            self.stdout.write(self.style.SUCCESS(result.message))
        else:
            self.stdout.write(self.style.WARNING(result.message))
        self.stdout.flush()
