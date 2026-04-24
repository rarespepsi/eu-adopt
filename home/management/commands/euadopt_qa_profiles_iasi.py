"""
Seteaza judet + oras + company_judet + company_oras la Iasi/Iasi pentru userii
din scripts/_align_user_roles.py + seed (daca exista in DB).

Nu modifica alti utilizatori.

Rulare:
  python manage.py euadopt_qa_profiles_iasi
"""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from home.models import UserProfile

# Aceeasi lista ca in scripts/_align_user_roles.py + seed_portfolio PF list
USERNAMES = (
    "dpf",
    "e2e_pf",
    "e2e_staff",
    "rarespepsi",
    "radu",
    "nccristescu",
    "dg1",
    "dg2",
    "dm",
    "rares",
)

COUNTY = "Iași"
CITY = "Iași"


class Command(BaseCommand):
    help = "QA: profile Iasi pentru userii din lista align/seed."

    def handle(self, *args, **options):
        User = get_user_model()
        ok = 0
        miss = []
        for raw in USERNAMES:
            u = User.objects.filter(username__iexact=raw.strip()).first()
            if not u:
                miss.append(raw)
                continue
            prof, _ = UserProfile.objects.get_or_create(user=u)
            prof.judet = COUNTY
            prof.oras = CITY
            prof.company_judet = COUNTY
            prof.company_oras = CITY
            prof.save(
                update_fields=["judet", "oras", "company_judet", "company_oras", "updated_at"]
            )
            ok += 1
        self.stdout.write(f"Updated profiles: {ok} users.")
        if miss:
            self.stdout.write(f"Skipped (not in DB): {', '.join(miss)}")
        self.stdout.write("Done.")
