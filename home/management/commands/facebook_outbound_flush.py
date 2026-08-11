"""
Golește coada de postări Facebook (pending / retry failed).

Activare: EUADOPT_FACEBOOK_AUTO_POST=1 + token pagină în .env
Cron recomandat: la fiecare 15–30 min (plafon zilnic + retry).
"""

from django.core.management.base import BaseCommand

from home.facebook_page_post import (
    facebook_auto_post_enabled,
    flush_pending,
    posts_today_count,
    remaining_posts_today,
)


class Command(BaseCommand):
    help = "Procesează coada FacebookOutboundPost (animale + campanii)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--limit",
            type=int,
            default=0,
            help="Max rânduri de procesat acum (implicit = locuri rămase azi).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează starea fără a posta.",
        )

    def handle(self, *args, **options):
        enabled = facebook_auto_post_enabled()
        self.stdout.write(f"facebook_auto_post_enabled={enabled}")
        self.stdout.write(f"posts_today={posts_today_count()} remaining={remaining_posts_today()}")
        if options["dry_run"]:
            from home.models import FacebookOutboundPost

            pending = FacebookOutboundPost.objects.filter(status="pending").count()
            failed = FacebookOutboundPost.objects.filter(status="failed").count()
            self.stdout.write(f"pending={pending} failed={failed}")
            return
        if not enabled:
            self.stdout.write(self.style.WARNING("Dezactivat — setează EUADOPT_FACEBOOK_AUTO_POST=1 și token."))
            return
        limit = options["limit"] or None
        stats = flush_pending(limit=limit)
        self.stdout.write(self.style.SUCCESS(f"flush: {stats}"))
