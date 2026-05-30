"""
Sync autoritar prospecte cabinete (CV) + farmacii (FV) veterinare din Excel final.

- Șterge TOATE prospectele colaborator + cabinet neînregistrate (CV/FV vechi).
- Creează din fișier TOATE rândurile (fără deduplicare — păstrează tot).
- Nu atinge alte tipuri (PF, ONG, adăpost, grooming, transport, magazin, useri importați).

Fișier fără antet, coloane pe poziții:
  0=email 1=telefon 2=contact 3=adresa 4=localitate 5=judet 6=tip(CV/FV)

Utilizare:
  python scripts/sync_cabinete_from_xlsx.py "C:\\path\\cabinete farmacii final AI.xlsx"
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

AUTHORITY_MARKER = "[AUTORITATE_XLSX_CABINETE_FARMACII_FINAL]"
SEGMENTS = ["noutati_colaboratori_servicii"]


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
    t = (raw or "").strip()
    parts = t.split()
    if len(parts) < 2:
        return "", ""
    if parts[0].lower().rstrip(".") in ("dr", "dr.", "drd", "prof"):
        parts = parts[1:]
    if len(parts) < 2:
        return "", ""
    return parts[0][:150], " ".join(parts[1:])[:150]


def vet_kind(raw: str) -> str:
    t = (raw or "").strip().upper()
    if t == "FV":
        return Lead.VET_PROSPECT_FV
    return Lead.VET_PROSPECT_CV


def load_rows(xlsx_path: pathlib.Path) -> list[dict]:
    df = pd.read_excel(xlsx_path, header=None, dtype=str).fillna("")
    cols = ["email", "telefon", "contact", "adresa", "localitate", "judet", "tip"]
    df = df.iloc[:, : len(cols)]
    df.columns = cols[: df.shape[1]]
    out = []
    for idx, row in df.iterrows():
        if not any(str(v).strip() for v in row.values):
            continue
        email = first_email(str(row.get("email", "")))
        phone = first_phone(str(row.get("telefon", "")))
        contact = str(row.get("contact", "")).strip()
        adresa = str(row.get("adresa", "")).strip()[:255]
        oras = str(row.get("localitate", "")).strip()[:120]
        judet = str(row.get("judet", "")).strip()[:120]
        vk = vet_kind(str(row.get("tip", "")))
        first_name, last_name = split_contact_name(contact)
        display = (contact or email or f"Cabinet {judet} {oras}").strip()[:200]
        out.append(
            {
                "email": email,
                "phone": phone,
                "display_name": display,
                "org_display_name": display[:255],
                "first_name": first_name,
                "last_name": last_name,
                "company_address": adresa,
                "judet": judet,
                "oras": oras,
                "vet_kind": vk,
                "_row": int(idx),
            }
        )
    return out


def sync(xlsx_path: pathlib.Path) -> None:
    rows = load_rows(xlsx_path)
    qs = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_CABINET,
        imported_user__isnull=True,
    )
    note_tail = f"{AUTHORITY_MARKER} sursă: {xlsx_path.name}"

    with transaction.atomic():
        deleted_count, _ = qs.delete()
        created = cv = fv = with_email = placeholder = 0
        for r in rows:
            email = r["email"]
            if not email:
                email = f"cabinet-row{r['_row']}-{first_phone(r['phone']) or 'noph'}@lead-placeholder.invalid"
                placeholder += 1
            else:
                with_email += 1
            if r["vet_kind"] == Lead.VET_PROSPECT_FV:
                fv += 1
            else:
                cv += 1
            Lead.objects.create(
                email=email,
                phone=r["phone"],
                account_kind=Lead.KIND_COLLAB,
                collaborator_subtype=Lead.COLLAB_CABINET,
                vet_prospect_kind=r["vet_kind"],
                display_name=r["display_name"],
                org_display_name=r["org_display_name"],
                first_name=r["first_name"],
                last_name=r["last_name"],
                company_address=r["company_address"],
                judet=r["judet"],
                oras=r["oras"],
                status=Lead.ST_READY,
                segments=SEGMENTS,
                notes=note_tail,
            )
            created += 1

    after = Lead.objects.filter(
        account_kind=Lead.KIND_COLLAB,
        collaborator_subtype=Lead.COLLAB_CABINET,
        imported_user__isnull=True,
    ).count()

    print("rows_xlsx", len(rows))
    print("deleted_old_cabinet", deleted_count)
    print("created", created)
    print("CV", cv, "FV", fv)
    print("with_real_email", with_email, "placeholder", placeholder)
    print("cabinet_active_after", after)


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit('Usage: python scripts/sync_cabinete_from_xlsx.py "C:\\path\\file.xlsx"')
    sync(pathlib.Path(sys.argv[1]))
