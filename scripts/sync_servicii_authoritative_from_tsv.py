"""
Sync autoritar servicii (pensiuni/hotel/cazare) din TSV consolidat user.
- Salvează backup CSV din DB înainte de ștergere
- Șterge prospecte servicii neimportate
- Creează din TSV (păstrează toate rândurile, inclusiv duplicate email)
"""

from __future__ import annotations

import csv
import os
import pathlib
import re
import sys
from datetime import datetime, timezone

import django
from django.db import transaction

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from home.models import StaffOnboardingLead as Lead  # noqa: E402
from home.staff_onboarding_csv import export_csv_bytes  # noqa: E402

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")


def clean_email(v: str) -> str:
    m = EMAIL_RE.search((v or "").strip().lower())
    return m.group(0).lower() if m else ""


def split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def backup_old(qs) -> pathlib.Path:
    out = BASE_DIR / "database" / "exports" / f"servicii_DB_inainte_sync_{datetime.now().strftime('%Y%m%d')}.csv"
    out.write_bytes(export_csv_bytes(qs.order_by("pk")))
    return out


def main() -> None:
    tsv = BASE_DIR / "database" / "exports" / "servicii_prospecte_20260602_consolidat.tsv"
    if not tsv.exists():
        raise SystemExit(f"Lipsește: {tsv}")

    qs = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_SERVICII,
        imported_user__isnull=True,
    )
    before = qs.count()
    backup_path = backup_old(qs)
    print(f"backup_csv={backup_path}")
    print(f"backup_rows={before}")

    rows: list[dict[str, str]] = []
    with tsv.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            email = clean_email(r.get("Mail") or "")
            if not email:
                continue
            contact = (r.get("Persoană de contact") or "").strip()
            fn, ln = split_name(contact)
            rows.append(
                {
                    "email": email,
                    "phone": (r.get("Telefon") or "").strip()[:40],
                    "display_name": contact or email.split("@")[0],
                    "first_name": fn,
                    "last_name": ln,
                    "judet": (r.get("Județ") or "").strip(),
                    "oras": (r.get("Localitate") or "").strip(),
                    "company_address": (r.get("Adresă") or "").strip(),
                    "tip": (r.get("Tip") or "").strip(),
                }
            )

    with transaction.atomic():
        deleted, _ = qs.delete()
        created = 0
        for r in rows:
            Lead.objects.create(
                email=r["email"],
                phone=r["phone"],
                display_name=r["display_name"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                account_kind=Lead.KIND_COLLAB,
                collaborator_subtype=Lead.COLLAB_SERVICII,
                vet_prospect_kind=Lead.VET_PROSPECT_NONE,
                judet=r["judet"],
                oras=r["oras"],
                company_address=r["company_address"],
                notes=f"[AUTORITATE_TSV_SERVICII_20260602] tip={r['tip']}",
                segments=["noutati_colaboratori_servicii"],
                marketing_emails_requested=True,
                status=Lead.ST_READY,
            )
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_SERVICII,
        imported_user__isnull=True,
    ).count()

    log = BASE_DIR / "database" / "exports" / "servicii_sync_20260602.log"
    log.write_text(
        f"[{datetime.now(timezone.utc).isoformat()}] servicii sync\n"
        f"before={before}\n"
        f"deleted={deleted}\n"
        f"created={created}\n"
        f"after={after}\n"
        f"backup={backup_path}\n",
        encoding="utf-8",
    )
    print(f"deleted={deleted}")
    print(f"created={created}")
    print(f"servicii_after={after}")


if __name__ == "__main__":
    main()
