"""
QA: seteaza county + city la Iasi pentru TOATE randurile AnimalListing.

Atentie: ruleaza pe tot DB-ul de animale (dev/QA). Nu folosi pe producție
fara intentie explicita.

Rulare:
  python manage.py euadopt_qa_animals_all_iasi
"""
from __future__ import annotations

from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import AnimalListing

COUNTY = "Iași"
CITY = "Iași"


class Command(BaseCommand):
    help = "QA: all AnimalListing -> county/city Iasi."

    def handle(self, *args, **options):
        now = timezone.now()
        n = AnimalListing.objects.update(county=COUNTY, city=CITY, updated_at=now)
        self.stdout.write(f"Updated AnimalListing rows: {n}")
        self.stdout.write("Done.")
