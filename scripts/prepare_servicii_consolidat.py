"""Pregătește CSV import din TSV consolidat servicii."""

from __future__ import annotations

import csv
import os
import pathlib
import re
import sys
from collections import Counter

import django

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from home.models import StaffOnboardingLead as Lead  # noqa: E402

EMAIL_RE = re.compile(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}")
HEADER = [
    "email", "telefon", "tip_cont", "tip_colaborator", "cod_prospect_vet",
    "prenume", "nume", "denumire_afisata_contact", "username_propus",
    "judet", "localitate", "denumire_organizatie", "denumire_legala",
    "cui", "cui_cu_ro", "reg_com", "adresa_firma", "reprezentant_legal",
    "judet_firma", "localitate_firma", "adapost_public_ong", "segmente",
    "marketing_email_viitor", "nota_interna", "stare",
]


def split_name(full: str) -> tuple[str, str]:
    p = (full or "").strip().split()
    if not p:
        return "", ""
    if len(p) == 1:
        return p[0], ""
    return p[0], " ".join(p[1:])


def clean_email(v: str) -> str:
    m = EMAIL_RE.search((v or "").strip().lower())
    return m.group(0).lower() if m else ""


def main() -> None:
    tsv = BASE_DIR / "database" / "exports" / "servicii_prospecte_20260602_consolidat.tsv"
    out = BASE_DIR / "database" / "exports" / "servicii_prospecte_20260602_import.csv"

    rows_out = []
    with tsv.open(encoding="utf-8", newline="") as f:
        for r in csv.DictReader(f, delimiter="\t"):
            email = clean_email(r.get("Mail") or "")
            if not email:
                continue
            contact = (r.get("Persoană de contact") or "").strip()
            fn, ln = split_name(contact)
            tip = (r.get("Tip") or "").strip()
            rows_out.append({
                "email": email,
                "telefon": (r.get("Telefon") or "").strip()[:40],
                "tip_cont": "collaborator",
                "tip_colaborator": "servicii",
                "cod_prospect_vet": "",
                "prenume": fn,
                "nume": ln,
                "denumire_afisata_contact": contact,
                "username_propus": "",
                "judet": (r.get("Județ") or "").strip(),
                "localitate": (r.get("Localitate") or "").strip(),
                "denumire_organizatie": "",
                "denumire_legala": "",
                "cui": "",
                "cui_cu_ro": "",
                "reg_com": "",
                "adresa_firma": (r.get("Adresă") or "").strip(),
                "reprezentant_legal": contact,
                "judet_firma": (r.get("Județ") or "").strip(),
                "localitate_firma": (r.get("Localitate") or "").strip(),
                "adapost_public_ong": "",
                "segmente": "noutati_colaboratori_servicii",
                "marketing_email_viitor": "1",
                "nota_interna": f"[AUTORITATE_TSV_SERVICII_20260602] tip={tip}",
                "stare": "ready",
            })

    with out.open("w", encoding="utf-8-sig", newline="") as f:
        w = csv.DictWriter(f, fieldnames=HEADER)
        w.writeheader()
        w.writerows(rows_out)

    emails = [r["email"] for r in rows_out]
    dup = [e for e, c in Counter(emails).items() if c > 1]
    db_serv = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_SERVICII,
        imported_user__isnull=True,
    ).count()

    print(f"rows_total={len(rows_out)}")
    print(f"unique_emails={len(set(emails))}")
    print(f"duplicate_emails={len(dup)}")
    if dup:
        print("dup_list:", ", ".join(dup))
    print(f"db_servicii_now={db_serv}")
    print(f"csv={out}")


if __name__ == "__main__":
    main()
