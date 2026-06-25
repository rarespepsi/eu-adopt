"""Normalizează județe/localități în DB (StaffOnboardingLead, UserProfile)."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead, UserProfile
from home.ro_location import normalize_location_pair


class Command(BaseCommand):
    help = "Normalizează judet/oras (și firma) la forma canonică din ro_counties_cities.json."

    def add_arguments(self, parser):
        parser.add_argument("--dry-run", action="store_true", help="Doar raportează, fără scriere.")
        parser.add_argument(
            "--only",
            choices=("leads", "profiles", "all"),
            default="all",
            help="Ce tabele să proceseze (implicit: all).",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        only = options.get("only") or "all"
        lead_n = 0
        prof_n = 0

        if only in ("leads", "all"):
            for lead in StaffOnboardingLead.objects.all().iterator():
                j, o = normalize_location_pair(lead.judet, lead.oras)
                cj, co = normalize_location_pair(lead.company_judet, lead.company_oras)
                changed = (j, o, cj, co) != (
                    lead.judet,
                    lead.oras,
                    lead.company_judet,
                    lead.company_oras,
                )
                if not changed:
                    continue
                lead_n += 1
                self.stdout.write(f"lead #{lead.pk} {lead.email}: {lead.judet!r}/{lead.oras!r} -> {j!r}/{o!r}")
                if not dry:
                    lead.judet, lead.oras, lead.company_judet, lead.company_oras = j, o, cj, co
                    lead.save(update_fields=["judet", "oras", "company_judet", "company_oras", "updated_at"])

        if only in ("profiles", "all"):
            for prof in UserProfile.objects.all().iterator():
                j, o = normalize_location_pair(prof.judet, prof.oras)
                cj, co = normalize_location_pair(prof.company_judet, prof.company_oras)
                changed = (j, o, cj, co) != (
                    prof.judet,
                    prof.oras,
                    prof.company_judet,
                    prof.company_oras,
                )
                if not changed:
                    continue
                prof_n += 1
                if not dry:
                    prof.judet, prof.oras, prof.company_judet, prof.company_oras = j, o, cj, co
                    prof.save(update_fields=["judet", "oras", "company_judet", "company_oras"])

        self.stdout.write(
            self.style.SUCCESS(
                f"{'[dry-run] ' if dry else ''}Actualizate: {lead_n} lead-uri, {prof_n} profiluri."
            )
        )
