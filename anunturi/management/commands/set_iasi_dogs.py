# -*- coding: utf-8 -*-
"""
Pune 30 de câini la Iași, repartizați egal pe vârstă, sex, mărime (câte 3-4 per combinație)
pentru testarea filtrelor.
"""
import itertools
from django.core.management.base import BaseCommand
from anunturi.models import Pet


# Vârste aproximative (ani): 1, 3, 5
VARSTA_APROX = [1, 3, 5]
SEX = ["male", "female"]
MARIME = ["small", "medium", "large", "xlarge"]

# Toate combinațiile (3 x 2 x 4 = 24), apoi ciclăm pentru 30
COMBOS = list(itertools.product(VARSTA_APROX, SEX, MARIME))


class Command(BaseCommand):
    help = "Setează 30 câini la Județ Iași, repartizați pe vârstă/sex/mărime pentru proba filtrelor."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar afișează ce s-ar modifica, fără a salva.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        dogs = list(Pet.objects.filter(tip="dog").order_by("id")[:30])
        if len(dogs) < 30:
            self.stdout.write(
                self.style.WARNING(
                    "Există doar %d câini. Se vor seta toți la Iași." % len(dogs)
                )
            )
        for i, pet in enumerate(dogs):
            v, s, m = COMBOS[i % len(COMBOS)]
            if dry_run:
                self.stdout.write(
                    "  [dry-run] %s (pk=%s) -> judet=iasi varsta_aproximativa=%s sex=%s marime=%s"
                    % (pet.nume, pet.pk, v, s, m)
                )
                continue
            pet.judet = "iasi"
            pet.varsta_aproximativa = v
            pet.sex = s
            pet.marime = m
            pet.status = "adoptable"
            pet.save(update_fields=["judet", "varsta_aproximativa", "sex", "marime", "status"])
        if not dry_run:
            self.stdout.write(
                self.style.SUCCESS(
                    "Actualizat %d caini la Judet Iasi (repartizati varsta_aproximativa/sex/marime)." % len(dogs)
                )
            )
            qs = Pet.objects.filter(tip="dog", judet="iasi")
            self.stdout.write("  Total caini Iasi: %d" % qs.count())
            for v in VARSTA_APROX:
                self.stdout.write("    Varsta aprox %s ani: %d" % (v, qs.filter(varsta_aproximativa=v).count()))
            for s in SEX:
                self.stdout.write("    Sex %s: %d" % (s, qs.filter(sex=s).count()))
            for m in MARIME:
                self.stdout.write("    Talie %s: %d" % (m, qs.filter(marime=m).count()))
