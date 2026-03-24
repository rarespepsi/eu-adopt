"""
Trimite rezumatul final către plătitor pentru comenzile promo A2 a căror perioadă cumpărată a expirat.
Se recomandă rulare periodică (cron), ex. la 5 minute.
"""
import logging

from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import PromoA2Order
from home.views import _promo_a2_send_summary_email

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = "Send final summary emails for expired paid Promo A2 orders."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează ce s-ar trimite fără a actualiza DB / trimite email.",
        )

    def handle(self, *args, **options):
        dry = bool(options.get("dry_run"))
        now = timezone.now()
        qs = PromoA2Order.objects.filter(
            status=PromoA2Order.STATUS_PAID,
            ends_at__isnull=False,
            ends_at__lte=now,
            summary_sent_at__isnull=True,
        ).order_by("ends_at", "id")
        total = qs.count()
        self.stdout.write(f"Orders eligible for final summary: {total}")
        sent = 0
        for o in qs.iterator(chunk_size=100):
            if dry:
                self.stdout.write(f"[dry-run] would send summary for order #{o.pk} to {o.payer_email}")
                continue
            try:
                ok = _promo_a2_send_summary_email(o)
                if not ok:
                    logger.warning("promo_a2_summary_skip_no_email order=%s", o.pk)
                    continue
                o.summary_sent_at = timezone.now()
                o.save(update_fields=["summary_sent_at", "updated_at"])
                sent += 1
            except Exception:
                logger.exception("promo_a2_summary_send_fail order=%s", o.pk)
        if dry:
            self.stdout.write("Dry-run done.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Final summaries sent: {sent}"))
