"""
Trimite mailul „+15 zile” adoptatorilor după adopție finalizată.
Rulează zilnic din Task Scheduler: python manage.py send_adoption_goodwill_emails
"""

from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import AdoptionRequest
from home.views import _send_adoption_goodwill_15d_email


class Command(BaseCommand):
    help = "Trimite emailuri cu 3 sugestii de oferte la 15 zile după adopție finalizată."

    def handle(self, *args, **options):
        from datetime import timedelta

        cutoff = timezone.now() - timedelta(days=15)
        qs = list(
            AdoptionRequest.objects.filter(
                status=AdoptionRequest.STATUS_FINALIZED,
                finalized_at__lte=cutoff,
                goodwill_email_sent_at__isnull=True,
            ).select_related("adopter", "animal")
        )
        n_ok = 0
        n_skip = 0
        for ar in qs:
            if _send_adoption_goodwill_15d_email(ar):
                ar.goodwill_email_sent_at = timezone.now()
                ar.save(update_fields=["goodwill_email_sent_at", "updated_at"])
                n_ok += 1
            else:
                n_skip += 1
        self.stdout.write(
            self.style.SUCCESS(
                f"Goodwill +15d: sent={n_ok}, skipped={n_skip}, candidates={len(qs)}"
            )
        )
