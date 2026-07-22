"""Afișează registrul domeniilor EU-Adopt (principal / activ / redirect)."""

from django.core.management.base import BaseCommand

from home.euadopt_domains import (
    EUADOPT_DOMAIN_REGISTRY,
    DomainRole,
    format_registry_table,
    hyphen_redirect_map,
)


class Command(BaseCommand):
    help = "Listează domeniile din registrul EU-Adopt și rolurile lor."

    def handle(self, *args, **options):
        self.stdout.write("=== EU-Adopt - domenii inregistrate ===\n")
        self.stdout.write(format_registry_table())
        self.stdout.write("")
        self.stdout.write("Redirect 301 (cu cratima -> fara cratima, pastreaza calea):")
        for src, dst in sorted(hyphen_redirect_map().items()):
            self.stdout.write(f"  https://{src}/* -> https://{dst}/*")
        self.stdout.write("")
        n_ro = sum(1 for e in EUADOPT_DOMAIN_REGISTRY if e.role == DomainRole.RO_PRIMARY)
        n_act = sum(1 for e in EUADOPT_DOMAIN_REGISTRY if e.role == DomainRole.ACTIVE)
        n_red = sum(1 for e in EUADOPT_DOMAIN_REGISTRY if e.role == DomainRole.REDIRECT_301)
        self.stdout.write(f"Total: RO principal={n_ro}, active={n_act}, redirect={n_red}")
        self.stdout.write(
            self.style.WARNING(
                "Nu sunt in registru: euadopt.it, eu-adopt.org (necumparate / neconfirmate)."
            )
        )
