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
    return d[:40]


def subtype(v: str) -> str:
    v = norm(v)
    if v in ("adpub", "public"):
        return Lead.COLLAB_ADPUB
    if v in ("adprv", "privat", "private"):
        return Lead.COLLAB_ADPRV
    return Lead.COLLAB_ADPRV


def load_rows(csv_path: pathlib.Path) -> list[dict]:
    out = []
    with csv_path.open("r", encoding="utf-8-sig", newline="") as f:
        reader = csv.DictReader(f)
        for row in reader:
            if not any((x or "").strip() for x in row.values()):
                continue
            kind = norm(row.get("tip_cont") or "")
            if kind not in ("adapost", "adăpost", "adaposturi"):
                continue

            email = first_email(row.get("email") or row.get("Mail") or "")
            phone = first_phone(row.get("telefon") or "")
            display = (row.get("denumire_afisata_contact") or "").strip()[:200]
            judet = (row.get("judet") or "").strip()[:120]
            oras = (row.get("localitate") or "").strip()[:120]
            sub = subtype(row.get("tip_colaborator") or "")
            is_pub = sub == Lead.COLLAB_ADPUB
            first_name = (row.get("prenume") or "").strip()[:150]
            last_name = (row.get("nume") or "").strip()[:150]

            if not display:
                display = (
                    " ".join(x for x in (first_name, last_name) if x)
                    or email
                    or phone
                    or f"Adapost {judet} {oras}"
                ).strip()[:200]

            out.append(
                {
                    "email": email,
                    "phone": phone,
                    "display_name": display,
                    "judet": judet,
                    "oras": oras,
                    "sub": sub,
                    "is_pub": is_pub,
                    "first_name": first_name,
                    "last_name": last_name,
                    "org_display_name": display[:255],
                }
            )
    return out


def sync(csv_path: pathlib.Path) -> None:
    rows = load_rows(csv_path)
    qs = Lead.objects.filter(account_kind=Lead.KIND_ADAPOST, imported_user__isnull=True)

    by_email = {}
    by_phone = {}
    by_name_loc = {}
    for o in qs:
        em = (o.email or "").strip().lower()
        ph = (o.phone or "").strip()
        if em:
            by_email[em] = o
        if ph:
            by_phone[ph] = o
        by_name_loc[(norm(o.display_name), norm(o.judet), norm(o.oras))] = o

    created = updated = matched_email = matched_phone = matched_name = 0
    seen_ids = set()

    with transaction.atomic():
        for r in rows:
            obj = None
            if r["email"] and r["email"] in by_email:
                obj = by_email[r["email"]]
                matched_email += 1
            elif r["phone"] and r["phone"] in by_phone:
                obj = by_phone[r["phone"]]
                matched_phone += 1
            else:
                obj = by_name_loc.get((norm(r["display_name"]), norm(r["judet"]), norm(r["oras"])))
                if obj:
                    matched_name += 1

            if obj:
                changed = []
                if r["email"] and (obj.email or "").strip().lower() != r["email"]:
                    obj.email = r["email"]
                    changed.append("email")
                if r["phone"] and (obj.phone or "").strip() != r["phone"]:
                    obj.phone = r["phone"]
                    changed.append("phone")
                if (obj.display_name or "").strip() != r["display_name"]:
                    obj.display_name = r["display_name"]
                    changed.append("display_name")
                if (obj.judet or "").strip() != r["judet"]:
                    obj.judet = r["judet"]
                    changed.append("judet")
                if (obj.oras or "").strip() != r["oras"]:
                    obj.oras = r["oras"]
                    changed.append("oras")
                if (obj.collaborator_subtype or "").strip() != r["sub"]:
                    obj.collaborator_subtype = r["sub"]
                    changed.append("collaborator_subtype")
                if bool(obj.is_public_shelter) != bool(r["is_pub"]):
                    obj.is_public_shelter = r["is_pub"]
                    changed.append("is_public_shelter")
                if r["first_name"] and (obj.first_name or "").strip() != r["first_name"]:
                    obj.first_name = r["first_name"]
                    changed.append("first_name")
                if r["last_name"] and (obj.last_name or "").strip() != r["last_name"]:
                    obj.last_name = r["last_name"]
                    changed.append("last_name")
                if (obj.org_display_name or "").strip() != r["org_display_name"]:
                    obj.org_display_name = r["org_display_name"]
                    changed.append("org_display_name")
                if changed:
                    obj.save(update_fields=changed + ["updated_at"])
                    updated += 1
                seen_ids.add(obj.id)
            else:
                em = r["email"]
                if not em:
                    h = abs(hash((r["display_name"], r["judet"], r["oras"], r["phone"]))) % (10**10)
                    em = f"adapost-{h}@lead-placeholder.invalid"
                n = Lead.objects.create(
                    email=em,
                    phone=r["phone"],
                    account_kind=Lead.KIND_ADAPOST,
                    collaborator_subtype=r["sub"],
                    is_public_shelter=r["is_pub"],
                    display_name=r["display_name"],
                    org_display_name=r["org_display_name"],
                    first_name=r["first_name"],
                    last_name=r["last_name"],
                    judet=r["judet"],
                    oras=r["oras"],
                    status=Lead.ST_READY,
                    segments=["noutati_ong_adapost"],
                )
                by_email[(n.email or "").strip().lower()] = n
                if (n.phone or "").strip():
                    by_phone[(n.phone or "").strip()] = n
                by_name_loc[(norm(n.display_name), norm(n.judet), norm(n.oras))] = n
                created += 1
                seen_ids.add(n.id)

        stale_count = 0
        marker = "[AUTORITATE_CSV_ADAPOSTURI]"
        for o in qs.exclude(id__in=seen_ids):
            note = (o.notes or "").strip()
            if marker not in note:
                o.notes = ((note + "\n") if note else "") + marker + " nealiniat in fisierul final user"
                o.save(update_fields=["notes", "updated_at"])
                stale_count += 1

    print("rows_csv", len(rows))
    print("matched_email", matched_email)
    print("matched_phone", matched_phone)
    print("matched_name_loc", matched_name)
    print("updated", updated)
    print("created", created)
    print("stale_marked", stale_count)
    print("adapost_active_after", Lead.objects.filter(account_kind=Lead.KIND_ADAPOST, imported_user__isnull=True).count())


if __name__ == "__main__":
    if len(sys.argv) < 2:
        raise SystemExit("Usage: python scripts/sync_adapost_from_csv.py \"C:\\path\\file.csv\"")
    sync(pathlib.Path(sys.argv[1]))
