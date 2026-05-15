"""
Descarcă https://asociatiaramses.ro/adaposturi/ și scrie CSV cu antet Add USER
(același format ca `import_prospecte_csv` / `registru_caini_to_csv`).

Exemplu:
  python manage.py ramses_adaposturi_to_csv --out database/exports/ramses_adaposturi.csv
  python manage.py ramses_adaposturi_to_csv --from-html tmp_ramses.html --out /tmp/x.csv
"""

from __future__ import annotations

import csv
from pathlib import Path

from django.core.management.base import BaseCommand

from home.ramses_adaposturi_scrape import RAMSES_ADAPOSTURI_URL, iter_ramses_rows, parse_ramses_adaposturi_html
from home.staff_onboarding_csv import CSV_HEADER_ROW


class Command(BaseCommand):
    help = "Extrage adăposturi din asociatiaramses.ro/adaposturi/ → CSV prospecte staff."

    def add_arguments(self, parser):
        parser.add_argument("--out", type=str, required=True, help="Cale fișier CSV de ieșire (UTF-8 BOM).")
        parser.add_argument(
            "--delay",
            type=float,
            default=0.0,
            help="Pauză după descărcare (secunde). Implicit 0 (o singură pagină).",
        )
        parser.add_argument(
            "--from-html",
            type=str,
            default="",
            help="Parsare offline din fișier HTML (test).",
        )

    def handle(self, *args, **opts):
        out_path = Path(opts["out"]).expanduser().resolve()
        out_path.parent.mkdir(parents=True, exist_ok=True)
        delay = float(opts["delay"] or 0.0)
        from_html = (opts.get("from_html") or "").strip()

        if from_html:
            p = Path(from_html).expanduser()
            if not p.is_file():
                self.stderr.write(f"Fișier inexistent: {p}")
                return
            html = p.read_text(encoding="utf-8", errors="replace")
            rows = parse_ramses_adaposturi_html(html, page_url=f"file:{p.name}")
            all_dicts = [r.to_csv_dict() for r in rows]
            self.stdout.write(f"Parsat din fișier: {len(all_dicts)} rânduri.")
        else:
            all_dicts = []
            for slug, label, shelter_rows in iter_ramses_rows(delay_sec=delay):
                n = len(shelter_rows)
                self.stdout.write(f"{slug} ({label}): {n} adăposturi <- {RAMSES_ADAPOSTURI_URL}")
                all_dicts.extend(r.to_csv_dict() for r in shelter_rows)

        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER_ROW, extrasaction="ignore")
            w.writeheader()
            for row in all_dicts:
                w.writerow(row)

        self.stdout.write(self.style.SUCCESS(f"Scrie {len(all_dicts)} rânduri în {out_path}"))
