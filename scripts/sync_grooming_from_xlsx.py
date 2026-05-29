"""
Sync autoritar prospecte grooming din Excel (fișier final utilizator).

- Actualizează / creează lead-uri colaborator + grooming neînregistrate.
- Șterge definitiv lead-urile grooming vechi care nu apar în fișier.

Utilizare:
  python scripts/sync_grooming_from_xlsx.py "C:\\path\\saloane cu AI.xlsx"
"""

from __future__ import annotations

import os
import pathlib
import re
import sys

import django
import pandas as pd
from django.db import transaction

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from home.models import StaffOnboardingLead as Lead  # noqa: E402

AUTHORITY_MARKER = "[AUTORITATE_XLSX_GROOMING_FINAL]"
SEGMENTS = ["noutati_magazin_grooming"]


def norm(s: str) -> str:
    s = (s or "").strip().lower()
    s = "".join(ch for ch in s if ch.isalnum() or ch in " _-")
    return re.sub(r"\s+", " ", s)


def first_email(raw: str) -> str:
    txt = (raw or "").replace(";", " ").replace(",", " ").replace("/", " ")
    m = re.findall(r"[A-Za-z0-9._%+-]+@[A-Za-z0-9.-]+\.[A-Za-z]{2,}", txt)
    return m[0].lower() if m else ""


def first_phone(raw: str) -> str:
    txt = raw or ""
    parts = re.split(r"[/,;]|\s{2,}", txt)
    for part in parts:
        d = re.sub(r"[^0-9+]", "", part)
        if len(re.sub(r"[^0-9]", "", d)) >= 8:
            return d[:40]
    d = re.sub(r"[^0-9+]", "", txt)
    return d[:40] if len(re.sub(r"[^0-9]", "", d)) >= 8 else ""


def split_contact_name(raw: str) -> tuple[str, str]:
    """Încearcă prenume + nume din persoană contact; altfel tot în display."""
    t = (raw or "").strip()
    if not t or len(t.split()) < 2:
        return "", ""
    parts = t.split()
    if len(parts) == 2:
        return parts[0][:150], parts[1][:150]
    return parts[0][:150], " ".join(parts[1:])[:150]


def load_rows(xlsx_path: pathlib.Path) -> list[dict]:
    df = pd.read_excel(xlsx_path, dtype=str).fillna("")
    by_email: dict[str, dict] = {}
    for _, row in df.iterrows():
        if not any(str(v).strip() for v in row.values):
            continue
        email = first_email(str(row.get("Mail") or row.get("email") or ""))
        if not email:
            continue
        phone = first_phone(str(row.get("Telefon") or row.get("telefon") or ""))
        contact = str(row.get("Persoană de contact") or row.get("Persoana de contact") or "").strip()
        address = str(row.get("Adresă / Sediu") or row.get("Adresa / Sediu") or "").strip()[:255]
        oras = str(row.get("Localitate") or row.get("localitate") or "").strip()[:120]
        judet = str(row.get("Județ") or row.get("Judet") or row.get("judet") or "").strip()[:120]
        first_name, last_name = split_contact_name(contact)
        display = contact[:200] if contact else email[:200]
        org = display[:255]
        by_email[email] = {
            "email": email,
            "phone": phone,
            "display_name": display,
            "first_name": first_name,
            "last_name": last_name,
            "judet": judet,
            "oras": oras,
            "company_address": address,
            "org_display_name": org,
        }
    return list(by_email.values())


def sync(xlsx_path: pathlib.Path) -> None:
    """
    Înlocuire totală: șterge toate prospectele grooming neînregistrate, apoi creează din Excel.
    (Evită coliziuni la potrivire după telefon din baza veche DDG/Top100.)
    """
    rows = load_rows(xlsx_path)
    qs = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_GROOMING,
        imported_user__isnull=True,
    )
    note_tail = f"{AUTHORITY_MARKER} sursă: {xlsx_path.name}"

    with transaction.atomic():
        deleted_count, _ = qs.delete()
        created = 0
        for r in rows:
            Lead.objects.create(
                email=r["email"],
                phone=r["phone"],
                account_kind=Lead.KIND_COLLAB,
                collaborator_subtype=Lead.COLLAB_GROOMING,
                display_name=r["display_name"],
                org_display_name=r["org_display_name"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                judet=r["judet"],
                oras=r["oras"],
                company_address=r["company_address"],
                status=Lead.ST_READY,
                segments=SEGMENTS,
                notes=note_tail,
            )
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_GROOMING,
        imported_user__isnull=True,
    ).count()

    print("rows_xlsx_unique_email", len(rows))
    print("deleted_before_recreate", deleted_count)
    print("created", created)
    print("grooming_active_after", after)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python scripts/sync_grooming_from_xlsx.py "C:\\path\\file.xlsx"')
    sync(pathlib.Path(sys.argv[1]))
