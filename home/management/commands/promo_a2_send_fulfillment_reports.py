"""
Trimite raportul email („24 apariții”) pentru comenzile promo A2/a2_24 unde toate sloturile au logged_at.

Face backfill pentru ferestre încheiate și verifică comenzi eligibile — la fel ca fluxul HOME.
Programare recomandată (cron / Task Scheduler), ex. la 15 minute:

  cd /cale/către/proiect && /cale/venv/bin/python manage.py promo_a2_send_fulfillment_reports
"""

from __future__ import annotations

import logging

from django.core.management.base import BaseCommand

from home.views import _promo_a2_try_send_fulfillment_reports

logger = logging.getLogger(__name__)


class Command(BaseCommand):
    help = (
        "Send A2 fulfillment report emails when all 24 slot plans have logged_at "
        "(backfills past windows, then mails)."
    )

    def handle(self, *args, **options):
        try:
            sent = _promo_a2_try_send_fulfillment_reports()
        except Exception:
            logger.exception("promo_a2_send_fulfillment_reports command failed")
            raise
        self.stdout.write(
            self.style.SUCCESS(
                f"promo_a2_send_fulfillment_reports: sweep completed (reports sent this run: {sent}).",
            ),
        )
