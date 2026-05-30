"""
Arhivează prospectele dinainte de curățarea/listele finale user.
Copii în proiect (database/backups/) și pe Desktop — separate de exportul curent curat.
"""

from __future__ import annotations

import csv
import json
import os
import shutil
import sys
from collections import Counter
from datetime import datetime, timezone
from pathlib import Path

BASE_DIR = Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")

import django  # noqa: E402

django.setup()

from home.models import StaffOnboardingLead  # noqa: E402
from home.staff_onboarding_csv import export_csv_bytes  # noqa: E402

STAMP = datetime.now().strftime("%Y%m%d")
ARCHIVE_NAME = f"PROSPECTE_ARHIVA_EUADOPT_{STAMP}"
DESKTOP = Path.home() / "Desktop"


def analyze_csv(path: Path) -> tuple[int, dict[str, int], int]:
    with path.open(encoding="utf-8-sig", newline="") as f:
        rows = list(csv.DictReader(f))
    by_kind = Counter((r.get("tip_cont", ""), r.get("tip_colaborator", "")) for r in rows)
    placeholder = sum(
        1
        for r in rows
        if "placeholder" in (r.get("email") or "").lower()
        or "@lead-placeholder" in (r.get("email") or "").lower()
    )
    breakdown = {f"{a}|{b}": c for (a, b), c in by_kind.most_common()}
    return len(rows), breakdown, placeholder


def main() -> None:
    proj_base = BASE_DIR / "database" / "backups" / f"archive_pre_curatare_{STAMP}"
    desk_base = DESKTOP / ARCHIVE_NAME

    for base in (proj_base, desk_base):
        (base / "ARHIVA_PRE_CURATARE").mkdir(parents=True, exist_ok=True)
        (base / "LISTE_CURATE_ACTUALE").mkdir(parents=True, exist_ok=True)

    exports = BASE_DIR / "database" / "exports"
    snapshots = [
        ("prospecte_2026-05-20_enriched.csv", "snapshot_2026-05-20.csv"),
        ("prospecte_2026-05-21_enriched.csv", "snapshot_2026-05-21.csv"),
        ("prospecte_2026-05-22_enriched.csv", "PROSPECTE_ARHIVA_COMPLETA_PRE_CURATARE.csv"),
    ]

    primary_src = exports / "prospecte_2026-05-22_enriched.csv"
    if not primary_src.exists():
        raise SystemExit(f"Lipseste exportul principal: {primary_src}")

    primary_count, primary_breakdown, primary_ph = analyze_csv(primary_src)

    manifest: dict = {
        "created_at_utc": datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC"),
        "purpose": "Arhiva prospecte INAINTE de curatarea/listele finale user.",
        "primary_archive": {
            "file": "ARHIVA_PRE_CURATARE/PROSPECTE_ARHIVA_COMPLETA_PRE_CURATARE.csv",
            "source": "database/exports/prospecte_2026-05-22_enriched.csv",
            "export_date": "2026-05-22",
            "rows": primary_count,
            "placeholder_emails_approx": primary_ph,
            "breakdown": primary_breakdown,
        },
        "snapshots_older": [],
        "current_clean_export": None,
        "warning": "NU importati ARHIVA_PRE_CURATARE in DB live — doar recuperare urgente.",
    }

    for src_name, dst_name in snapshots:
        src = exports / src_name
        if not src.exists():
            continue
        cnt, _, ph = analyze_csv(src)
        for base in (proj_base, desk_base):
            shutil.copy2(src, base / "ARHIVA_PRE_CURATARE" / dst_name)
        if dst_name != "PROSPECTE_ARHIVA_COMPLETA_PRE_CURATARE.csv":
            manifest["snapshots_older"].append(
                {"file": dst_name, "rows": cnt, "placeholder_approx": ph}
            )

    qs = StaffOnboardingLead.objects.all().order_by("pk")
    clean_bytes = export_csv_bytes(qs)
    clean_name = f"prospecte_ACTIVE_CURATE_{STAMP}.csv"
    for base in (proj_base, desk_base):
        (base / "LISTE_CURATE_ACTUALE" / clean_name).write_bytes(clean_bytes)

    with (proj_base / "LISTE_CURATE_ACTUALE" / clean_name).open(
        encoding="utf-8-sig", newline=""
    ) as f:
        clean_rows = list(csv.DictReader(f))
    clean_breakdown = Counter(
        (r.get("tip_cont", ""), r.get("tip_colaborator", "")) for r in clean_rows
    )
    manifest["current_clean_export"] = {
        "file": f"LISTE_CURATE_ACTUALE/{clean_name}",
        "rows": len(clean_rows),
        "breakdown": {
            f"{a}|{b}": c for (a, b), c in clean_breakdown.most_common()
        },
    }

    readme_lines = [
        f"# Arhiva prospecte EU-Adopt ({STAMP})",
        "",
        "## IMPORTANT",
        f"- **ARHIVA_PRE_CURATARE/** = baza veche ({primary_count:,} prospecte) INAINTE de listele finale.",
        f"- **LISTE_CURATE_ACTUALE/** = DB live acum ({len(clean_rows):,} prospecte) — listele bune.",
        "- **NU** importati arhiva veche in site decat pentru recuperare explicita.",
        "",
        "## Fisier principal (urgente)",
        "`ARHIVA_PRE_CURATARE/PROSPECTE_ARHIVA_COMPLETA_PRE_CURATARE.csv`",
        "- Sursa: export Django 2026-05-22 (ultimul inainte de sync adapost/grooming/cabinete)",
        f"- Randuri: {primary_count:,}",
        f"- Email placeholder approx: {primary_ph:,}",
        "",
        "## Breakdown arhiva veche (2026-05-22)",
    ]
    for k, v in sorted(primary_breakdown.items(), key=lambda x: -x[1]):
        readme_lines.append(f"- {k.replace('|', ' / ')}: {v}")

    readme_lines.extend(
        [
            "",
            f"## Liste curate actuale ({len(clean_rows):,} randuri)",
        ]
    )
    for (a, b), v in clean_breakdown.most_common():
        readme_lines.append(f"- {a} / {b or '—'}: {v}")

    readme_lines.extend(
        [
            "",
            "## Snapshots mai vechi (optional)",
            "- snapshot_2026-05-20.csv",
            "- snapshot_2026-05-21.csv",
            "",
            "## Copii",
            f"- Proiect: `database/backups/archive_pre_curatare_{STAMP}/`",
            f"- Desktop: `{desk_base}`",
        ]
    )
    readme = "\n".join(readme_lines) + "\n"

    for base in (proj_base, desk_base):
        (base / "README.md").write_text(readme, encoding="utf-8")
        (base / "manifest.json").write_text(
            json.dumps(manifest, indent=2, ensure_ascii=False), encoding="utf-8"
        )

    print(f"project: {proj_base}")
    print(f"desktop: {desk_base}")
    print(f"archive rows: {primary_count}")
    print(f"clean rows: {len(clean_rows)}")


if __name__ == "__main__":
    main()
