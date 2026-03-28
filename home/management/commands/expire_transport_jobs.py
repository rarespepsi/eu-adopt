"""
Cron: expiră cereri de transport deschise cu expires_at în trecut (trimite email utilizatorului).
Rulează periodic (ex. la 5 minute): python manage.py expire_transport_jobs
"""

from django.core.management.base import BaseCommand

from home.models import TransportDispatchJob
from home.transport_dispatch import maybe_expire_job


class Command(BaseCommand):
    help = "Marchează ca expirate joburile dispatch deschise cu termen depășit."

    def handle(self, *args, **options):
        qs = (
            TransportDispatchJob.objects.filter(status=TransportDispatchJob.STATUS_OPEN)
            .exclude(expires_at__isnull=True)
            .only("id", "status", "expires_at")
        )
        n = 0
        for job in qs:
            if maybe_expire_job(job):
                n += 1
        self.stdout.write(self.style.SUCCESS(f"Expirate acum: {n} job(uri)."))
