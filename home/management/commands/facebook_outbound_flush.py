"""
Golește coada de livrări Facebook (pending / retry failed) pe toate piețele.

Activare RO: EUADOPT_FACEBOOK_AUTO_POST=1 + token RO
Piețe DE/FR/ES/COM: doar dacă au PAGE_ID + TOKEN în .env
"""

from django.core.management.base import BaseCommand

from home.facebook_markets import configured_markets, facebook_auto_post_enabled
from home.facebook_page_post import flush_pending, posts_today_count, remaining_posts_today


class Command(BaseCommand):
    help = "Procesează FacebookOutboundDelivery (animale + campanii + mirror)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max delivery-uri de procesat acum.",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează starea fără a posta.",
        )

    def handle(self, *args, **options):
        enabled = facebook_auto_post_enabled()
        markets = configured_markets()
        self.stdout.write(f"facebook_auto_post_enabled={enabled}")
        self.stdout.write(f"configured_markets={','.join(markets) or '(none)'}")
        self.stdout.write(
            f"ro posts_today={posts_today_count('ro')} remaining={remaining_posts_today('ro')}"
        )
        if options["dry_run"]:
            from home.models import FacebookOutboundDelivery

            for st in ("pending", "failed", "posted"):
                n = FacebookOutboundDelivery.objects.filter(status=st).count()
                self.stdout.write(f"deliveries_{st}={n}")
            return
        if not enabled and not configured_markets(for_mirror_targets=True):
            self.stdout.write(
                self.style.WARNING("Dezactivat — setează EUADOPT_FACEBOOK_AUTO_POST=1 și token RO.")
            )
            return
        limit = options["limit"] or None
        stats = flush_pending(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"flush: {stats}"))
