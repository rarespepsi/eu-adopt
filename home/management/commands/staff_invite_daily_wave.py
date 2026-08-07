"""
Val zilnic invitații Add USER.

- morning (cron 10:00 RO): adăposturi, Grupa A/B
- afternoon (cron 16:00 RO): colaboratori cabinet/magazin/grooming, Grupa A/B separat

Activare: EUADOPT_STAFF_INVITE_CRON_ENABLED=1 în .env
"""

from django.core.management.base import BaseCommand

from home.staff_invite_daily_wave import (
    WAVE_SLOT_AFTERNOON,
    WAVE_SLOT_MORNING,
    mark_region_group_used,
    next_region_group_for_cron,
    run_staff_invite_daily_wave,
    staff_invite_cron_enabled,
    staff_invite_cron_pm_collab_subtypes,
    staff_invite_cron_pm_account_kind,
    staff_invite_cron_account_kind,
    staff_invite_cron_wave_size,
    staff_invite_cron_pm_wave_size,
)


class Command(BaseCommand):
    help = "Trimite val zilnic invitații prospecte (AM adăpost / PM colaboratori)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--slot",
            choices=(WAVE_SLOT_MORNING, WAVE_SLOT_AFTERNOON),
            default=WAVE_SLOT_MORNING,
            help="morning=adăposturi (10:00), afternoon=colaboratori (16:00).",
        )
        parser.add_argument(
            "--region-group",
            choices=("a", "b"),
            help="Forțează Grupa A sau B (altfel alternare automată pe slot).",
        )
        parser.add_argument(
            "--account-kind",
            default="",
            help="adapost / collaborator / org / pf (implicit după slot).",
        )
        parser.add_argument("--wave-size", type=int, default=0, help="Implicit 25 (AM/PM după setări).")
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
            help="Setează ultima grupă trimisă pentru slotul ales.",
        )

    def handle(self, *args, **options):
        slot = options.get("slot") or WAVE_SLOT_MORNING

        if options.get("init_last_group"):
            mark_region_group_used(options["init_last_group"], slot)
            self.stdout.write(
                self.style.SUCCESS(f"Cache grupă setat [{slot}]: {options['init_last_group']}")
            )
            return

        if options.get("dry_run"):
            grp = options.get("region_group") or next_region_group_for_cron(slot)
            if slot == WAVE_SLOT_AFTERNOON:
                kind = (options.get("account_kind") or "").strip() or staff_invite_cron_pm_account_kind()
                size = options.get("wave_size") or staff_invite_cron_pm_wave_size()
                subs = staff_invite_cron_pm_collab_subtypes()
            else:
                kind = (options.get("account_kind") or "").strip() or staff_invite_cron_account_kind()
                size = options.get("wave_size") or staff_invite_cron_wave_size()
                subs = []
            self.stdout.write(
                f"Dry-run: cron_enabled={staff_invite_cron_enabled()} slot={slot} "
                f"next_group={grp} kind={kind} wave_size={size} "
                f"subtypes={','.join(subs) or '-'} (fără trimitere)"
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
            wave_slot=slot,
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
