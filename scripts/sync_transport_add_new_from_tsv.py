"""
Adaugă doar transportatorii NOI din TSV-ul userului, fără să șteargă nimic existent.

Input:
  database/exports/_user_paste_transportatori.tsv

Reguli:
  - Creează doar emailurile care NU există deja la prospecte transport neimportate.
  - Nu modifică/șterge rânduri existente.
"""

from __future__ import annotations

import csv
import os
import pathlib
import re
import sys

import django

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


def clean_phone(v: str) -> str:
    return (v or "").strip()[:40]


def main() -> None:
    tsv_path = BASE_DIR / "database" / "exports" / "_user_paste_transportatori.tsv"
    if not tsv_path.exists():
        raise SystemExit(f"Lipsește fișierul: {tsv_path}")

    before = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_TRANSPORT,
        imported_user__isnull=True,
    ).count()

    existing_emails = {
        (e or "").strip().lower()
        for e in Lead.objects.filter(
            account_kind=Lead.KIND_COLLAB,
            collaborator_subtype=Lead.COLLAB_TRANSPORT,
            imported_user__isnull=True,
        ).values_list("email", flat=True)
    }

    created = 0
    skipped_existing = 0
    skipped_invalid = 0

    with tsv_path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            email = clean_email(r.get("Mail") or "")
            if not email:
                skipped_invalid += 1
                continue
            if email in existing_emails:
                skipped_existing += 1
                continue

            contact = (r.get("Persoană de contact") or "").strip()
            city = (r.get("Localitate") or "").strip()
            county = (r.get("Județ") or "").strip()
            addr = (r.get("Adresă") or "").strip()
            tip = (r.get("Tip") or "").strip()

            Lead.objects.create(
                email=email,
                phone=clean_phone(r.get("Telefon") or ""),
                display_name=contact or email.split("@")[0],
                account_kind=Lead.KIND_COLLAB,
                collaborator_subtype=Lead.COLLAB_TRANSPORT,
                vet_prospect_kind=Lead.VET_PROSPECT_NONE,
                judet=county,
                oras=city,
                company_address=addr,
                notes=f"[AUTORITATE_TSV_TRANSPORT_20260602] tip={tip}",
                segments=["noutati_colaboratori_transport"],
                marketing_emails_requested=True,
                status=Lead.ST_READY,
            )
            existing_emails.add(email)
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_TRANSPORT,
        imported_user__isnull=True,
    ).count()

    print(f"transport_before={before}")
    print(f"created_new={created}")
    print(f"skipped_existing={skipped_existing}")
    print(f"skipped_invalid={skipped_invalid}")
    print(f"transport_after={after}")


if __name__ == "__main__":
    main()

