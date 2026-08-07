"""
Val zilnic invitații Add USER (cron 10:00 RO).

Alternare Grupa A / B · Adăpost · prima invitație · desfacere emailuri multiple.

Activare pe server: EUADOPT_STAFF_INVITE_CRON_ENABLED=1 în .env
"""

from django.core.management.base import BaseCommand

from home.staff_invite_daily_wave import (
    mark_region_group_used,
    next_region_group_for_cron,
    run_staff_invite_daily_wave,
    staff_invite_cron_enabled,
)


class Command(BaseCommand):
    help = "Trimite val zilnic invitații prospecte (alternare Grupa A/B)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--region-group",
            choices=("a", "b"),
            help="Forțează Grupa A sau B (altfel alternare automată).",
        )
        parser.add_argument(
            "--account-kind",
            default="",
            help="adapost (implicit), org, collab, pf.",
        )
        parser.add_argument("--wave-size", type=int, default=0, help="Implicit STAFF_INVITE_CRON_WAVE_SIZE (25).")
        parser.add_argument(
            "--force",
            action="store_true",
            help="Rulează chiar dacă EUADOPT_STAFF_INVITE_CRON_ENABLED=0.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Arată ce s-ar trimite, fără SMTP.",
        )
        parser.add_argument(
            "--init-last-group",
            choices=("a", "b"),
            help="Setează ultima grupă trimisă (ex. b după trimitere manuală Grupa B).",
        )

    def handle(self, *args, **options):
        if options.get("init_last_group"):
            mark_region_group_used(options["init_last_group"])
            self.stdout.write(self.style.SUCCESS(f"Cache grupă setat: {options['init_last_group']}"))
            return

        if options.get("dry_run"):
            grp = options.get("region_group") or next_region_group_for_cron()
            self.stdout.write(
                f"Dry-run: cron_enabled={staff_invite_cron_enabled()} "
                f"next_group={grp} (fără trimitere)"
            )
            return

        wave_limit = options.get("wave_size") or None
        if wave_limit == 0:
            wave_limit = None

        account_kind = (options.get("account_kind") or "").strip() or None
        result = run_staff_invite_daily_wave(
            region_group=options.get("region_group"),
            account_kind=account_kind,
            wave_limit=wave_limit,
            force=bool(options.get("force")),
        )
        if result.skipped:
            self.stdout.write(self.style.WARNING(result.message))
            self.stdout.flush()
            return
        if result.stats.get("sent") or result.stats.get("simulated"):
            self.stdout.write(self.style.SUCCESS(result.message))
        else:
            self.stdout.write(self.style.WARNING(result.message))
        self.stdout.flush()