"""
Alias: folosește staff_lead_free_email_enrich --website-only (pipeline gratuit extins).
"""

from django.core.management import call_command
from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = "Redirect către staff_lead_free_email_enrich --website-only."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--force", action="store_true")

    def handle(self, *args, **options):
        call_command(
            "staff_lead_free_email_enrich",
            limit=options["limit"],
            apply=options["apply"],
            force=options["force"],
            website_only=True,
        )
