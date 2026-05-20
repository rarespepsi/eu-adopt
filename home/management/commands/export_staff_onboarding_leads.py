"""Exportă toate lead-urile staff în CSV (format Add USER / import_prospecte_csv)."""

from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import export_csv_bytes


class Command(BaseCommand):
    help = "Export CSV prospecte StaffOnboardingLead → database/exports/"

    def add_arguments(self, parser):
        parser.add_argument(
            "--output",
            default="",
            help="Cale fișier (implicit: database/exports/prospecte_YYYY-MM-DD_enriched.csv).",
        )

    def handle(self, *args, **options):
        out = (options.get("output") or "").strip()
        if not out:
            out = f"database/exports/prospecte_{date.today().isoformat()}_enriched.csv"
        path = Path(out)
        path.parent.mkdir(parents=True, exist_ok=True)
        qs = StaffOnboardingLead.objects.all().order_by("pk")
        path.write_bytes(export_csv_bytes(qs))
        self.stdout.write(self.style.SUCCESS(f"Exportat {qs.count()} lead-uri → {path}"))
