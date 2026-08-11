"""
Poll postări Facebook RO + mirror pe DE/FR/ES/COM (dacă mirror e activ).

Implicit OFF: EUADOPT_FACEBOOK_RO_MIRROR_ENABLED=0
Test fetch: --test-fetch (nu mirror, doar verifică GET /posts)
"""

from django.core.management.base import BaseCommand

from home.facebook_markets import (
    configured_markets,
    facebook_ro_mirror_enabled,
)
from home.facebook_ro_mirror import fetch_ro_page_posts, run_ro_mirror_poll


class Command(BaseCommand):
    help = "Poll RO Facebook posts; mirror către piețe (dacă enabled)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=0)
        parser.add_argument(
            "--test-fetch",
            action="store_true",
            help="Doar GET /{PAGE_ID_RO}/posts cu permisiunile existente (fără mirror).",
        )

    def handle(self, *args, **options):
        self.stdout.write(f"ro_mirror_enabled={facebook_ro_mirror_enabled()}")
        self.stdout.write(
            f"mirror_targets_configured={','.join(configured_markets(for_mirror_targets=True)) or '(none)'}"
        )
        if options["test_fetch"]:
            posts, err = fetch_ro_page_posts(limit=options["limit"] or 5)
            if err:
                self.stdout.write(self.style.ERROR(f"fetch_error={err}"))
                return
            self.stdout.write(self.style.SUCCESS(f"fetch_ok count={len(posts)}"))
            for p in posts[:5]:
                pid = p.get("id")
                msg = (p.get("message") or "")[:80].replace("\n", " ")
                self.stdout.write(f"  - {pid}: {msg}")
            return
        limit = options["limit"] or None
        result = run_ro_mirror_poll(limit=limit)
        if result.get("fetch_error"):
            self.stdout.write(self.style.ERROR(f"fetch_error={result['fetch_error']}"))
        self.stdout.write(self.style.SUCCESS(f"result={result}"))
