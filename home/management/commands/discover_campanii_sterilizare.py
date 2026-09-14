"""
Descoperă campanii sterilizare GRATUIT (DuckDuckGo / Bing).

Implicit: județe goale → CSV.
Cu --all-judete: toate județele RO.
Cu --refresh-db: salvează/împrospătează CampanieDiscoverHit.
Cu --auto-publish: publică hit-uri noi eligibile pe hartă + Facebook (afiș obligatoriu).

Exemple:
  python manage.py discover_campanii_sterilizare --empty-only --limit-judete 3
  python manage.py discover_campanii_sterilizare --all-judete --refresh-db --auto-publish
  python manage.py discover_campanii_sterilizare --list-empty
"""
from __future__ import annotations

from datetime import date
from pathlib import Path

from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from home.campanii_discover import (
    discover_all_judete,
    discover_empty_judete,
    empty_campanii_judete,
    write_candidates_csv,
)
from home.campanii_ro import campanii_count_by_code, campanii_judete


class Command(BaseCommand):
    help = (
        "Căutare gratuită campanii sterilizare (DDG/Bing). "
        "Opțional: refresh DB + auto-publicare hartă/Facebook."
    )

    def add_arguments(self, parser):
        parser.add_argument(
            "--empty-only",
            action="store_true",
            help="Doar județe fără campanii vizibile.",
        )
        parser.add_argument(
            "--all-judete",
            action="store_true",
            help="Scan pe toate județele RO.",
        )
        parser.add_argument(
            "--judet",
            action="append",
            default=[],
            help="Slug sau nume județ (poate fi repetat).",
        )
        parser.add_argument("--limit-judete", type=int, default=0, help="Max județe de scanat.")
        parser.add_argument("--max-per-query", type=int, default=6)
        parser.add_argument("--sleep", type=float, default=1.0, help="Pauză între query-uri (sec).")
        parser.add_argument(
            "--no-smeura",
            action="store_true",
            help="Fără query site:smeura.com.",
        )
        parser.add_argument(
            "--fetch-images",
            action="store_true",
            help="og:image la CSV (implicit și la --refresh-db).",
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
        parser.add_argument(
            "--refresh-db",
            action="store_true",
            help="Upsert rezultate în CampanieDiscoverHit.",
        )
        parser.add_argument(
            "--auto-publish",
            action="store_true",
            help="Publică hit-uri noi eligibile (hartă + enqueue FB). Impune --refresh-db.",
        )
        parser.add_argument(
            "--publish-limit",
            type=int,
            default=8,
            help="Max campanii noi publicate per rulare (implicit 8).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Cu --auto-publish: clasifică fără a crea CampanieSterilizare.",
        )
        parser.add_argument(
            "--min-date",
            type=str,
            default="2026-08-01",
            help="Ignorează campanii cu date înainte de YYYY-MM-DD.",
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
        all_judete = bool(options.get("all_judete"))
        empty_only = bool(options.get("empty_only"))
        if judete:
            empty_only = False
            all_judete = False
        elif all_judete:
            empty_only = False
        elif not empty_only:
            # compat: fără flag → empty-only ca înainte
            empty_only = True

        auto_publish = bool(options.get("auto_publish"))
        refresh_db = bool(options.get("refresh_db")) or auto_publish
        dry_run = bool(options.get("dry_run"))

        min_raw = (options.get("min_date") or "2026-08-01").strip()
        try:
            y, m, d = [int(x) for x in min_raw.split("-")]
            min_date = date(y, m, d)
        except Exception as exc:
            raise CommandError(f"--min-date invalid: {min_raw}") from exc

        self.stdout.write(
            self.style.NOTICE(
                f"discover campanii · all={all_judete} empty_only={empty_only} "
                f"judet={judete or '-'} refresh_db={refresh_db} auto_publish={auto_publish} "
                f"min_date={min_date}"
            )
        )

        try:
            if judete:
                rows = discover_empty_judete(
                    judet_slugs=judete,
                    limit_judete=int(options["limit_judete"] or 0),
                    max_per_query=int(options["max_per_query"] or 6),
                    sleep_s=float(options["sleep"] or 1.0),
                    include_smeura=not bool(options["no_smeura"]),
                    fetch_images=bool(options["fetch_images"]) and not refresh_db,
                )
            elif all_judete:
                rows = discover_all_judete(
                    limit_judete=int(options["limit_judete"] or 0),
                    max_per_query=int(options["max_per_query"] or 6),
                    sleep_s=float(options["sleep"] or 1.0),
                    include_smeura=not bool(options["no_smeura"]),
                    fetch_images=bool(options["fetch_images"]) and not refresh_db,
                )
            else:
                rows = discover_empty_judete(
                    limit_judete=int(options["limit_judete"] or 0),
                    max_per_query=int(options["max_per_query"] or 6),
                    sleep_s=float(options["sleep"] or 1.0),
                    include_smeura=not bool(options["no_smeura"]),
                    fetch_images=bool(options["fetch_images"]) and not refresh_db,
                )
        except Exception as exc:
            raise CommandError(f"Cautare esuata: {exc}") from exc

        out = (options.get("out") or "").strip()
        if not out:
            stamp = timezone.now().strftime("%Y%m%d_%H%M")
            out = f"database/exports/campanii_discover_{stamp}.csv"
        path = write_candidates_csv(Path(out), rows)
        self.stdout.write(self.style.SUCCESS(f"Candidati: {len(rows)} -> {path}"))

        if refresh_db:
            from home.campanii_discover_publish import publish_new_hits, upsert_candidates

            ups = upsert_candidates(rows, min_date=min_date, fetch_images=True)
            self.stdout.write(
                f"DB upsert: created={ups['created']} updated={ups['updated']} "
                f"skipped={ups['skipped']}"
            )
            if auto_publish:
                pub = publish_new_hits(
                    limit=int(options.get("publish_limit") or 8),
                    dry_run=dry_run,
                )
                self.stdout.write(
                    self.style.SUCCESS(
                        f"Publish: published={pub['published']} skipped={pub['skipped']} "
                        f"errors={pub['errors']} dry={pub['dry']}"
                    )
                )
            else:
                self.stdout.write("Fara --auto-publish: doar refresh DB / CSV.")
        else:
            self.stdout.write(
                "Urmatorul pas: --refresh-db [--auto-publish] sau alegi manual link+afis."
            )

        for row in rows[:15]:
            self.stdout.write(f"  [{row.judet_code}] {row.title[:70]}")
            self.stdout.write(f"       {row.url}")
        if len(rows) > 15:
            self.stdout.write(f"  ... +{len(rows) - 15} in CSV")
