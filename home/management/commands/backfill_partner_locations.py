"""
Creează puncte de lucru (sediu + principal) din UserProfile pentru colaboratori/ONG fără rânduri.
"""
from django.contrib.auth.models import User
from django.core.management.base import BaseCommand

from home.models import AccountProfile
from home.partner_locations import backfill_locations_from_profile


class Command(BaseCommand):
    help = "Backfill PartnerLocation din profil pentru conturi colaborator/ONG."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Scrie în DB (implicit doar numără).",
        )

    def handle(self, *args, **options):
        apply = bool(options.get("apply"))
        qs = User.objects.filter(
            account_profile__role__in=(
                AccountProfile.ROLE_COLLAB,
                AccountProfile.ROLE_ORG,
            )
        ).select_related("profile", "account_profile")
        would = 0
        created_rows = 0
        for user in qs.iterator():
            from home.models import PartnerLocation

            if PartnerLocation.objects.filter(user=user).exists():
                continue
            prof = getattr(user, "profile", None)
            if not prof:
                continue
            jud = (prof.company_judet or prof.judet or "").strip()
            oras = (prof.company_oras or prof.oras or "").strip()
            if not jud or not oras:
                continue
            would += 1
            if apply:
                created_rows += backfill_locations_from_profile(user)
        if apply:
            self.stdout.write(
                self.style.SUCCESS(
                    f"Conturi actualizate: {would}, rânduri create (aprox. {created_rows})."
                )
            )
        else:
            self.stdout.write(
                f"Ar crea puncte pentru {would} conturi. Rulează cu --apply."
            )
