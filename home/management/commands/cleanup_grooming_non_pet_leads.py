"""
Șterge prospecte grooming care nu sunt pentru animale (frizerii oameni, pet shop generic, DDG gunoi).

  python manage.py cleanup_grooming_non_pet_leads
  python manage.py cleanup_grooming_non_pet_leads --apply
"""

from __future__ import annotations

import unicodedata
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX

_PET_MARKERS = (
    " pet",
    "pet ",
    "pets",
    "puppy",
    "puppies",
    "dog",
    "cat",
    "pisic",
    "canin",
    "canina",
    "caini",
    "câini",
    "câine",
    "groom",
    "toalet",
    "tuns cain",
    "tunsare cain",
    "patrupez",
    "animale de companie",
    "animale companie",
    "dog salon",
    "pet salon",
    "salon cain",
    "salon canin",
    "frizerie canin",
    "frizer canin",
    "spa canin",
    "beauty pet",
    "cosmetica anim",
    "cosmetica pentru anim",
    "ingrijire cain",
    "îngrijire câin",
    "hotel ham",
    "pet joy",
    "pet hotel",
    "dog spa",
)

# Doar în nume afișat — nu în notes (DDG pune text oameni în notes la toți).
_HUMAN_MARKERS = (
    "frizerie in apropiere",
    "programari frizerie",
    "programări frizerie",
    "frizerie si barber",
    "frizerie și barber",
    "barbershop",
    "frizerie/coafor",
    "salon prego",
    "crisstylle",
    "saloane de coafura",
    "saloane de coafură",
    "top saloane",
    "frizerii slobozia",
    "frizerii în slobozia",
    "program de func",
    "tuns barba",
    "tuns barb",
    "salon de infrumusetare",
    "salon infrumusetare",
    "unghii",
    "manichiura",
    "cosmetica capilar",
)

_GENERIC_PETSHOP = (
    "pet max",
    "petmart",
    "pet shop",
    "petshop",
    "pet-shop",
)

_AMBIGUOUS_TRIGGERS = ("frizer", "frizerie", "salon", "coafor", "coafur", "barber")


def _strip_d(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _norm(s: str) -> str:
    return _strip_d(s).lower().strip()


def should_remove_grooming_lead(lead: StaffOnboardingLead) -> tuple[bool, str]:
    name = _norm(lead.display_name or lead.org_display_name or "")

    if not name:
        return True, "nume gol"

    if any(p in name for p in _PET_MARKERS):
        return False, ""

    for h in _HUMAN_MARKERS:
        if h in name:
            return True, f"omeni:{h}"

    if " barber" in f" {name} " or name.endswith(" barber"):
        return True, "omeni:barber"

    if "coafor" in name and "canin" not in name and "cain" not in name:
        return True, "omeni:coafor_uman"

    if ("in slobozia" in name or "în slobozia" in name) and "canin" not in name:
        return True, "omeni:slobozia_frizerie"

    for g in _GENERIC_PETSHOP:
        if name == g or name.startswith(g + " ") or f" {g} " in f" {name} ":
            return True, "pet_shop_generic"

    if any(t in name for t in _AMBIGUOUS_TRIGGERS):
        if not any(p in name for p in _PET_MARKERS):
            return True, "frizerie/salon_fara_pet"

    # Titluri prea generice DDG
    if name in ("grooming", "pet", "salon", "toaletare", "frizerie", "pet grooming"):
        return True, "titlu_generic"

    return False, ""


class Command(BaseCommand):
    help = "Curăță lead-uri grooming non-pet (frizerii oameni, pet shop generic)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true", help="Șterge efectiv din DB.")

    def handle(self, *args: Any, **options: Any) -> None:
        apply = bool(options["apply"])
        qs = StaffOnboardingLead.objects.filter(
            collaborator_subtype=StaffOnboardingLead.COLLAB_GROOMING
        )
        total = qs.count()
        to_remove: list[tuple[StaffOnboardingLead, str]] = []

        for lead in qs.iterator():
            rm, reason = should_remove_grooming_lead(lead)
            if rm:
                to_remove.append((lead, reason))

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        log_path = Path("database/exports/grooming_cleanup_deleted.log")
        log_path.parent.mkdir(parents=True, exist_ok=True)

        lines = [
            f"# grooming cleanup {stamp} apply={apply}",
            f"# total={total} remove={len(to_remove)} keep={total - len(to_remove)}",
            "",
        ]
        by_reason: dict[str, int] = {}
        for lead, reason in to_remove:
            by_reason[reason] = by_reason.get(reason, 0) + 1
            lines.append(
                f"id={lead.pk}\t{reason}\t{lead.judet or '?'}\t{(lead.display_name or '')[:80]}"
            )

        log_path.write_text("\n".join(lines), encoding="utf-8")

        self.stdout.write(f"Grooming total: {total}")
        self.stdout.write(f"De șters: {len(to_remove)} | Păstrate: {total - len(to_remove)}")
        for reason, n in sorted(by_reason.items(), key=lambda x: -x[1]):
            self.stdout.write(f"  {reason}: {n}")
        self.stdout.write(f"Log: {log_path}")

        if not apply:
            self.stdout.write(self.style.WARNING("Dry-run. Rulează cu --apply pentru ștergere."))
            return

        ids = [lead.pk for lead, _ in to_remove]
        deleted, _ = StaffOnboardingLead.objects.filter(pk__in=ids).delete()
        self.stdout.write(self.style.SUCCESS(f"Șters: {deleted} lead-uri grooming."))
