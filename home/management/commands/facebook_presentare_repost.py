"""
Redistribuie pe FB RO un video de prezentare (luni / miercuri).

Exemple:
  python manage.py facebook_presentare_repost --which auto
  python manage.py facebook_presentare_repost --which lun
  python manage.py facebook_presentare_repost --which mie --dry-run
"""
from __future__ import annotations

from datetime import datetime
from zoneinfo import ZoneInfo

from django.core.management.base import BaseCommand

from home.facebook_markets import facebook_auto_post_enabled, market_creds
from home.facebook_presentare_reels import (
    post_presentare_reel,
    presentare_repost_message,
    reel_by_key,
    reel_for_weekday,
)

RO_TZ = ZoneInfo("Europe/Bucharest")


class Command(BaseCommand):
    help = "Repostează video prezentare EU-Adopt pe Facebook RO (luni/miercuri)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--which",
            default="auto",
            help="auto | lun | mie (sau mon/wed). auto = după ziua RO.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează mesajul fără a posta.",
        )
        parser.add_argument(
            "--market",
            default="ro",
            help="Piață FB (implicit ro).",
        )

    def handle(self, *args, **options):
        which = (options["which"] or "auto").strip().lower()
        market = (options["market"] or "ro").strip().lower()
        dry = bool(options["dry_run"])

        if which in ("auto", "today", ""):
            wd = datetime.now(RO_TZ).weekday()
            reel = reel_for_weekday(wd)
            if reel is None:
                self.stdout.write(
                    self.style.WARNING(
                        f"Azi (weekday={wd} RO) nu e zi de redistribuire prezentare — skip."
                    )
                )
                return
        else:
            reel = reel_by_key(which)
            if reel is None:
                self.stderr.write(self.style.ERROR(f"which invalid: {which!r} (folosește lun|mie|auto)"))
                return

        self.stdout.write(f"reel={reel.key} url={reel.reel_url} market={market} dry_run={dry}")
        if dry:
            self.stdout.write(presentare_repost_message(reel))
            return

        if market == "ro" and not facebook_auto_post_enabled():
            self.stderr.write(self.style.ERROR("EUADOPT_FACEBOOK_AUTO_POST dezactivat."))
            return
        if not market_creds(market).configured:
            self.stderr.write(self.style.ERROR(f"Piața {market} fără credențiale FB."))
            return

        result = post_presentare_reel(reel, market=market)
        if result.ok:
            self.stdout.write(self.style.SUCCESS(f"posted id={result.facebook_post_id}"))
        else:
            self.stderr.write(self.style.ERROR(f"fail: {result.error}"))
