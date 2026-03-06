# -*- coding: utf-8 -*-
"""
Corectează adresa/oras unde a fost lipit mesajul „AICI BAGA SI CURSOR...” –
pune doar „Piatra Neamț” și județul Neamț.
"""
from django.core.management.base import BaseCommand
from django.db.models import Q
from anunturi.models import UserProfile, OngProfile, AdoptionRequest


# Cuvinte care indică mesajul lipit (nu o adresă reală)
ADRESA_SPURCA = ("AICI", "BAGA", "CURSOR", "VARIANTA", "LOCALITATIL", "litera", "apara", "dupa prima", "a doua litera")


def _contine_mesaj_lipit(text):
    if not text or not text.strip():
        return False
    t = (text or "").strip().upper()
    return any(kw.upper() in t for kw in ADRESA_SPURCA)


class Command(BaseCommand):
    help = "Înlocuiește adresa/oras cu mesaj lipit cu doar 'Piatra Neamț' (și județ Neamț)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar afișează ce s-ar modifica, fără a salva.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        oras_ok = "Piatra Neamț"
        judet_ok = "neamt"

        # UserProfile: oras + judet
        q_oras = Q()
        for kw in ADRESA_SPURCA:
            q_oras |= Q(oras__icontains=kw)
        profiles = list(UserProfile.objects.filter(q_oras))
        for up in profiles:
            self.stdout.write(
                "  UserProfile user=%s (pk=%s) oras -> Piatra Neamt, judet=neamt"
                % (up.user.username, up.pk)
            )
            if not dry_run:
                up.oras = oras_ok
                up.judet = judet_ok
                up.save(update_fields=["oras", "judet"])
        count_up = len(profiles)
        if not dry_run and count_up:
            self.stdout.write(self.style.SUCCESS("Actualizat %d UserProfile." % count_up))

        # OngProfile: oras + judet
        q_ong = Q()
        for kw in ADRESA_SPURCA:
            q_ong |= Q(oras__icontains=kw)
        ongs = list(OngProfile.objects.filter(q_ong))
        for op in ongs:
            self.stdout.write(
                "  OngProfile user=%s (pk=%s) oras -> Piatra Neamt, judet=neamt"
                % (op.user.username, op.pk)
            )
            if not dry_run:
                op.oras = oras_ok
                op.judet = judet_ok
                op.save(update_fields=["oras", "judet"])
        count_ong = len(ongs)
        if not dry_run and count_ong:
            self.stdout.write(self.style.SUCCESS("Actualizat %d OngProfile." % count_ong))

        # AdoptionRequest: adresa
        q_adr = Q()
        for kw in ADRESA_SPURCA:
            q_adr |= Q(adresa__icontains=kw)
        requests = list(AdoptionRequest.objects.filter(q_adr))
        for ar in requests:
            self.stdout.write(
                "  AdoptionRequest pk=%s adresa -> Piatra Neamt"
                % (ar.pk,)
            )
            if not dry_run:
                ar.adresa = oras_ok
                ar.save(update_fields=["adresa"])
        count_ar = len(requests)
        if not dry_run and count_ar:
            self.stdout.write(self.style.SUCCESS("Actualizat %d AdoptionRequest." % count_ar))

        total = count_up + count_ong + count_ar
        if total == 0:
            self.stdout.write("Nicio inregistrare cu mesaj lipit la adresa/oras.")
        elif dry_run:
            self.stdout.write(self.style.WARNING("Dry-run: %d inregistrari s-ar modifica. Rulati fara --dry-run pentru a salva." % total))
