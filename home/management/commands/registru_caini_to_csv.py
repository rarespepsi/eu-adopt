"""
Descarcă paginile județ de pe registru-caini.ro (listă URL canonică, nu meniul principal)
și scrie CSV cu antet Add USER (import cu `import_prospecte_csv`).

Exemplu:
  python manage.py registru_caini_to_csv --out database/exports/registru_caini_adaposturi.csv
  python manage.py registru_caini_to_csv --slug cluj --out /tmp/cluj.csv
  python manage.py registru_caini_to_csv --from-html tmp_reg_cluj.html --slug cluj --judet Cluj --out /tmp/x.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from home.registru_caini_scrape import COUNTY_PAGES, iter_county_rows, parse_county_html
from home.staff_onboarding_csv import CSV_HEADER_ROW


class Command(BaseCommand):
    help = "Extrage adăposturi din registru-caini.ro (pe județ) → CSV prospecte staff."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, required=True, help="Cale fișier CSV de ieșire (UTF-8 BOM).")
        parser.add_argument(
            "--delay",
            type=float,
            default=1.25,
            help="Pauză între cereri HTTP (secunde). Implicit 1.25.",
        )
        parser.add_argument(
            "--slug",
            action="append",
            dest="slugs",
            help="Doar județul/județele indicate (slug: cluj, timis, …). Repetabil.",
        )
        parser.add_argument(
            "--from-html",
            type=str,
            default="",
            help="Parsare offline din fișier HTML (test); necesită --slug și --judet.",
        )
        parser.add_argument(
            "--judet",
            type=str,
            default="",
            help="Eticheta județ pentru CSV când folosiți --from-html.",
        )

    def handle(self, *args, **opts):
        out_path = Path(opts["out"]).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        delay = float(opts["delay"] or 1.25)
        slugs_filter = None
        if opts.get("slugs"):
            slugs_filter = {s.strip().lower() for s in opts["slugs"] if s and s.strip()}

        from_html = (opts.get("from_html") or "").strip()
        if from_html:
            p = Path(from_html).expanduser()
            if not p.is_file():
                self.stderr.write(f"Fișier inexistent: {p}")
                return
            slugs_arg = opts.get("slugs") or []
            slug = (slugs_arg[0] or "").strip().lower() if slugs_arg else ""
            if not slug:
                self.stderr.write("--from-html necesită --slug cluj (ex.).")
                return
            judet = (opts.get("judet") or "").strip()
            page_url = ""
            if not judet:
                for s, lab, url in COUNTY_PAGES:
                    if s == slug:
                        judet = lab
                        page_url = url
                        break
                else:
                    self.stderr.write("Slug necunoscut; folosiți --judet \"Nume\".")
                    return
            else:
                page_url = next((u for s, _, u in COUNTY_PAGES if s == slug), "")
            html = p.read_text(encoding="utf-8", errors="replace")
            rows = parse_county_html(html, slug, judet, page_url or f"file:{p.name}")
            all_dicts = [r.to_csv_dict() for r in rows]
            self.stdout.write(f"Parsat din fișier: {len(all_dicts)} rânduri (slug={slug}).")
        else:
            all_dicts = []
            for slug, label, page_url, shelter_rows in iter_county_rows(
                delay_sec=delay,
                slugs_filter=slugs_filter,
            ):
                n = len(shelter_rows)
                self.stdout.write(f"{slug} ({label}): {n} adăposturi <- {page_url}")
                all_dicts.extend(r.to_csv_dict() for r in shelter_rows)

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER_ROW, extrasaction="ignore")
            w.writeheader()
            for row in all_dicts:
                w.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"Scrie {len(all_dicts)} rânduri în {out_path}"))
