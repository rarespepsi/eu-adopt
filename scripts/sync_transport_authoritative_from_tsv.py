"""
Sync autoritar transport din TSV user:
- șterge toate prospectele transport neimportate existente
- creează din TSV doar rândurile cu email valid
"""

from __future__ import annotations

import csv
import os
import pathlib
import re
import sys

import django
from django.db import transaction

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from home.models import StaffOnboardingLead as Lead  # noqa: E402


EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def clean_email(v: str) -> str:
    txt = (v or "").strip().lower()
    m = EMAIL_RE.search(txt)
    return m.group(0).lower() if m else ""


def main() -> None:
    tsv_path = BASE_DIR / "database" / "exports" / "_user_paste_transportatori.tsv"
    if not tsv_path.exists():
        raise SystemExit(f"Lipsește fișierul: {tsv_path}")

    existing_qs = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_TRANSPORT,
        imported_user__isnull=True,
    )
    before = existing_qs.count()

    rows: list[dict[str, str]] = []
    with tsv_path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            email = clean_email(r.get("Mail") or "")
            if not email:
                continue
            rows.append(
                {
                    "email": email,
                    "phone": (r.get("Telefon") or "").strip()[:40],
                    "display_name": (r.get("Persoană de contact") or "").strip() or email.split("@")[0],
                    "judet": (r.get("Județ") or "").strip(),
                    "oras": (r.get("Localitate") or "").strip(),
                    "company_address": (r.get("Adresă") or "").strip(),
                    "tip": (r.get("Tip") or "").strip(),
                }
            )

    # păstrăm duplicatele doar pe primul email (listă finală curată)
    unique: dict[str, dict[str, str]] = {}
    for r in rows:
        unique.setdefault(r["email"], r)
    rows_final = list(unique.values())

    with transaction.atomic():
        deleted, _ = existing_qs.delete()
        created = 0
        for r in rows_final:
            Lead.objects.create(
                email=r["email"],
                phone=r["phone"],
                display_name=r["display_name"],
                account_kind=Lead.KIND_COLLAB,
                collaborator_subtype=Lead.COLLAB_TRANSPORT,
                vet_prospect_kind=Lead.VET_PROSPECT_NONE,
                judet=r["judet"],
                oras=r["oras"],
                company_address=r["company_address"],
                notes=f"[AUTORITATE_TSV_TRANSPORT_20260602] tip={r['tip']}",
                segments=["noutati_colaboratori_transport"],
                marketing_emails_requested=True,
                status=Lead.ST_READY,
            )
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_TRANSPORT,
        imported_user__isnull=True,
    ).count()

    print(f"transport_before={before}")
    print(f"deleted_rows={deleted}")
    print(f"created_rows={created}")
    print(f"transport_after={after}")


if __name__ == "__main__":
    main()

