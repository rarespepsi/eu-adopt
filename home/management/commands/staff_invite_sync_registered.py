"""Leagă lead-uri de conturi User existente (același email) și marchează signed_up."""

from __future__ import annotations

from django.core.management.base import BaseCommand

from home.staff_onboarding_invite import staff_invite_sync_all_registered_leads


class Command(BaseCommand):
    help = "Sincronizează prospectele cu utilizatori deja înregistrați (blocare invitații duplicate)."

    def handle(self, *args, **options):
        n = staff_invite_sync_all_registered_leads()
        self.stdout.write(self.style.SUCCESS(f"Actualizate {n} lead-uri (cont existent pe email)."))
