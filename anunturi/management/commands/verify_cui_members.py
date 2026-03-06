"""
Verificare online a veridicității CUI/CIF pentru membri (OngProfile) cu date oficiale.

Surse (gratuit):
- SRL/PFA: termene.ro, listafirme.ro
- ONG/AF:  portal.just.ro (Registrul Național ONG)

Rulează:
  python manage.py verify_cui_members
  python manage.py verify_cui_members --user 5   # doar user_id 5
"""
from django.conf import settings
from django.core.management.base import BaseCommand

from anunturi.models import OngProfile
from anunturi.official_verification import (
    SOURCES,
    verify_member_official_data,
)


class Command(BaseCommand):
    help = "Verifică CUI/CIF ale membrilor (SRL/PFA/ONG/AF) pe baza surselor: termene.ro, listafirme.ro, portal.just.ro."

    def add_arguments(self, parser):
        parser.add_argument(
            "--user",
            type=int,
            default=None,
            metavar="ID",
            help="Verifică doar OngProfile pentru user_id dat.",
        )
        parser.add_argument(
            "--verbose",
            action="store_true",
            help="Afișează și sursele / URL-uri pentru verificare manuală.",
        )

    def handle(self, *args, **options):
        listafirme_key = getattr(settings, "LISTAFIRME_API_KEY", "") or None
        just_ro = getattr(settings, "JUST_RO_VERIFY_ENABLED", False)

        qs = OngProfile.objects.exclude(cui="").exclude(cui__isnull=True).filter(cui__gt="")
        if options["user"]:
            qs = qs.filter(user_id=options["user"])

        if not qs.exists():
            self.stdout.write("Niciun profil ONG cu CUI completat.")
            return

        self.stdout.write(f"Verificare {qs.count()} profil(e) cu CUI/CIF...")
        for profile in qs:
            tip = profile.tip_organizatie
            cui = (profile.cui or "").strip()
            nr_reg = (profile.numar_registru or "").strip()
            label = f"user_id={profile.user_id} {profile.denumire_legala or '(fără denumire)'} CUI={cui}"

            result = verify_member_official_data(
                tip_organizatie=tip,
                cui=cui,
                numar_registru=nr_reg,
                listafirme_api_key=listafirme_key,
                just_ro_api_key="x" if just_ro else None,
            )

            if result.get("verified"):
                self.stdout.write(self.style.SUCCESS(f"  [OK] {label}"))
                if result.get("denumire_found"):
                    self.stdout.write(f"       Denumire: {result['denumire_found']}")
            else:
                self.stdout.write(self.style.WARNING(f"  [--] {label}"))
                self.stdout.write(f"       {result.get('message', result.get('error', ''))}")
                if options["verbose"] and result.get("source_urls"):
                    for url in result["source_urls"]:
                        self.stdout.write(f"       → {url}")

        self.stdout.write("")
        self.stdout.write("Surse: SRL/PFA → termene.ro, listafirme.ro | ONG/AF → portal.just.ro (Registrul Național ONG)")
