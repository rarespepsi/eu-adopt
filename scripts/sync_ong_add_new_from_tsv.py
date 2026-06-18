"""
Adaugă doar ONG-urile NOI din TSV user (fără duplicate după email).
Nu șterge și nu modifică lead-urile ONG existente.
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


def main() -> None:
    tsv_path = BASE_DIR / "database" / "exports" / "ong_social_media_20260602_raw.tsv"
    if not tsv_path.exists():
        raise SystemExit(f"Lipsește fișierul: {tsv_path}")

    existing = {
        (e or "").strip().lower()
        for e in Lead.objects.filter(
            account_kind=Lead.KIND_ORG,
            imported_user__isnull=True,
        ).values_list("email", flat=True)
    }
    before = len(existing)

    created = 0
    skipped_existing = 0
    skipped_invalid = 0
    seen_in_file: set[str] = set()

    with tsv_path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            email = clean_email(r.get("Mail") or "")
            if not email:
                skipped_invalid += 1
                continue
            if email in seen_in_file:
                continue
            seen_in_file.add(email)
            if email in existing:
                skipped_existing += 1
                continue

            contact = (r.get("Persoană de contact") or "").strip()
            city = (r.get("Localitate") or "").strip()
            county = (r.get("Județ") or "").strip()
            addr = (r.get("Adresă") or "").strip()
            tip = (r.get("Tip") or "").strip()

            Lead.objects.create(
                email=email,
                phone=(r.get("Telefon") or "").strip()[:40],
                display_name=contact or email.split("@")[0],
                org_display_name=contact,
                account_kind=Lead.KIND_ORG,
                collaborator_subtype="",
                vet_prospect_kind=Lead.VET_PROSPECT_NONE,
                judet=county,
                oras=city,
                company_address=addr,
                company_judet=county,
                company_oras=city,
                is_public_shelter=False,
                segments=["noutati_ong"],
                marketing_emails_requested=True,
                notes=f"[AUTORITATE_TSV_ONG_SOCIAL_20260602] tip={tip}",
                status=Lead.ST_READY,
            )
            existing.add(email)
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_ORG,
        imported_user__isnull=True,
    ).count()

    print(f"org_before={before}")
    print(f"created_new={created}")
    print(f"skipped_existing={skipped_existing}")
    print(f"skipped_invalid={skipped_invalid}")
    print(f"org_after={after}")


if __name__ == "__main__":
    main()

