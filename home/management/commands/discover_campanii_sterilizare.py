"""
Descoperă campanii sterilizare GRATUIT (DuckDuckGo / Bing) pe județe goale.

Nu publică automat (lipsește afișul confirmat). Scrie CSV candidați:
  judet, title, url, snippet, image_url (dacă --fetch-images), …

Exemple:
  python manage.py discover_campanii_sterilizare --empty-only --limit-judete 3
  python manage.py discover_campanii_sterilizare --judet ilfov --fetch-images
  python manage.py discover_campanii_sterilizare --empty-only --out database/exports/campanii_discover.csv
"""
from __future__ import annotations

from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from home.campanii_discover import (
    discover_empty_judete,
    empty_campanii_judete,
    write_candidates_csv,
)
from home.campanii_ro import campanii_count_by_code, campanii_judete


class Command(BaseCommand):
    help = (
        "Căutare gratuită campanii sterilizare (DDG/Bing) pe județe fără campanii vizibile. "
        "Output CSV — fără creare automată în DB."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empty-only",
            action="store_true",
            help="Doar județe fără campanii vizibile (implicit dacă nu dai --judet).",
        )
        parser.add_argument(
            "--judet",
            action="append",
            default=[],
            help="Slug sau nume județ (poate fi repetat). Ignoră empty-only.",
        )
        parser.add_argument("--limit-judete", type=int, default=0, help="Max județe de scanat.")
        parser.add_argument("--max-per-query", type=int, default=8)
        parser.add_argument("--sleep", type=float, default=1.2, help="Pauză între query-uri (sec).")
        parser.add_argument(
            "--no-smeura",
            action="store_true",
            help="Fără query site:smeura.com.",
        )
        parser.add_argument(
            "--fetch-images",
            action="store_true",
            help="Încearcă og:image pe URL-urile găsite (mai lent; skip facebook).",
        )
        parser.add_argument(
            "--out",
            type=str,
            default="",
            help="Cale CSV (implicit database/exports/campanii_discover_YYYYMMDD_HHMM.csv).",
        )
        parser.add_argument(
            "--list-empty",
            action="store_true",
            help="Doar listează județele goale, fără căutare.",
        )

    def handle(self, *args, **options):
        if options["list_empty"]:
            empty = empty_campanii_judete()
            counts = campanii_count_by_code()
            self.stdout.write(f"Judete goale (vizibile=0): {len(empty)} / {len(campanii_judete())}")
            for j in empty:
                self.stdout.write(f"  {j.code:3} {j.slug:22} {j.name}")
            covered = [j for j in campanii_judete() if int(counts.get(j.code, 0) or 0) > 0]
            self.stdout.write(f"Cu campanii: {len(covered)}")
            return

        judete = options.get("judet") or []
        empty_only = bool(options.get("empty_only")) or not judete
        if judete:
            empty_only = False

        self.stdout.write(
            self.style.NOTICE(
                f"discover campanii · empty_only={empty_only} · judet={judete or '-'} · "
                f"fetch_images={options['fetch_images']}"
            )
        )
        try:
            rows = discover_empty_judete(
                judet_slugs=judete or None,
                limit_judete=int(options["limit_judete"] or 0),
                max_per_query=int(options["max_per_query"] or 8),
                sleep_s=float(options["sleep"] or 1.2),
                include_smeura=not bool(options["no_smeura"]),
                fetch_images=bool(options["fetch_images"]),
            )
        except Exception as exc:
            raise CommandError(f"Cautare esuata: {exc}") from exc

        out = (options.get("out") or "").strip()
        if not out:
            stamp = timezone.now().strftime("%Y%m%d_%H%M")
            out = f"database/exports/campanii_discover_{stamp}.csv"
        path = write_candidates_csv(Path(out), rows)
        self.stdout.write(self.style.SUCCESS(f"Candidati: {len(rows)} -> {path}"))
        for row in rows[:25]:
            img = " +img" if row.image_url else ""
            self.stdout.write(f"  [{row.judet_code}] {row.title[:70]}{img}")
            self.stdout.write(f"       {row.url}")
        if len(rows) > 25:
            self.stdout.write(f"  ... +{len(rows) - 25} in CSV")
        self.stdout.write(
            "Urmatorul pas: alegi link+afis -> publicare Cont / script (fara auto-create)."
        )
