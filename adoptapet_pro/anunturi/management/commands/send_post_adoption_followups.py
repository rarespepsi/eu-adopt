"""
Trimite emailuri de verificare post-adopție la 3 sau 6 luni după ce adopția a fost finalizată.

Rulează manual sau prin cron (ex. zilnic):
  python manage.py send_post_adoption_followups

Setează în settings.py (opțional):
  POST_ADOPTION_FOLLOWUP_MONTHS = 6   # trimite la 6 luni (implicit)
  # sau POST_ADOPTION_FOLLOWUP_MONTHS = [3, 6]  # trimite la 3 și la 6 luni (necesită câmp suplimentar)
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from datetime import timedelta

from anunturi.models import AdoptionRequest
from anunturi.adoption_platform import send_post_adoption_followup_email


class Command(BaseCommand):
    help = "Trimite email de follow-up (soarta animalului) la adoptii finalizate de 3 sau 6 luni."

    def add_arguments(self, parser):
        parser.add_argument(
            "--months",
            type=int,
            default=None,
            help="Număr luni după data cererii (implicit: din settings POST_ADOPTION_FOLLOWUP_MONTHS sau 6).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar afișează ce cereri ar primi email, fără a trimite.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        months = options["months"]
        if months is None:
            months = getattr(settings, "POST_ADOPTION_FOLLOWUP_MONTHS", 6)
        if isinstance(months, (list, tuple)):
            months = months[0]  # prima perioadă (ex. 3)
        dry_run = options["dry_run"]
        since = timezone.now() - timedelta(days=months * 30)  # aproximativ
        # Cereri approved_ong făcute cu cel puțin `months` în urmă, care nu au primit încă follow-up
        qs = AdoptionRequest.objects.filter(
            status="approved_ong",
            data_cerere__lte=since,
            post_adoption_followup_sent_at__isnull=True,
        )
        count = qs.count()
        if count == 0:
            self.stdout.write(f"Nicio cerere de adoptie finalizată de {months}+ luni fără follow-up trimis.")
            return
        if dry_run:
            self.stdout.write(f"[DRY-RUN] S-ar trimite {count} emailuri de follow-up (cereri de {months}+ luni).")
            for req in qs[:10]:
                self.stdout.write(f"  - {req.nume_complet} – {req.pet.nume} (data_cerere: {req.data_cerere.date()})")
            if count > 10:
                self.stdout.write(f"  ... și încă {count - 10}")
            return
        sent = 0
        for req in qs:
            if send_post_adoption_followup_email(req):
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"Trimis: {req.nume_complet} – {req.pet.nume}"))
        self.stdout.write(self.style.SUCCESS(f"Total trimise: {sent} emailuri de follow-up post-adopție."))
