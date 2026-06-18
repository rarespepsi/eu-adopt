import csv
import os
import pathlib
import sys

import django

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from home.models import StaffOnboardingLead as Lead  # noqa: E402


HEADER = [
    "email",
    "telefon",
    "tip_cont",
    "tip_colaborator",
    "cod_prospect_vet",
    "prenume",
    "nume",
    "denumire_afisata_contact",
    "username_propus",
    "judet",
    "localitate",
    "denumire_organizatie",
    "denumire_legala",
    "cui",
    "cui_cu_ro",
    "reg_com",
    "adresa_firma",
    "reprezentant_legal",
    "judet_firma",
    "localitate_firma",
    "adapost_public_ong",
    "segmente",
    "marketing_email_viitor",
    "nota_interna",
    "stare",
]


def split_name(full: str) -> tuple[str, str]:
    parts = (full or "").strip().split()
    if not parts:
        return "", ""
    if len(parts) == 1:
        return parts[0], ""
    return parts[0], " ".join(parts[1:])


def build_import_csv(tsv_path: pathlib.Path, csv_path: pathlib.Path) -> int:
    rows_out: list[dict[str, str]] = []
    with tsv_path.open(encoding="utf-8", newline="") as f:
        rd = csv.DictReader(f, delimiter="\t")
        for r in rd:
            email = (r.get("Mail") or "").strip().lower()
            tel = (r.get("Telefon") or "").strip()
            contact = (r.get("Persoană de contact") or "").strip()
            addr = (r.get("Adresă") or "").strip()
            city = (r.get("Localitate") or "").strip()
            county = (r.get("Județ") or "").strip()
            tip = (r.get("Tip") or "").strip()
            fn, ln = split_name(contact)
            rows_out.append(
                {
                    "email": email,
                    "telefon": tel,
                    "tip_cont": "org",
                    "tip_colaborator": "",
                    "cod_prospect_vet": "",
                    "prenume": fn,
                    "nume": ln,
                    "denumire_afisata_contact": contact,
                    "username_propus": "",
                    "judet": county,
                    "localitate": city,
                    "denumire_organizatie": contact,
                    "denumire_legala": "",
                    "cui": "",
                    "cui_cu_ro": "",
                    "reg_com": "",
                    "adresa_firma": addr,
                    "reprezentant_legal": contact,
                    "judet_firma": county,
                    "localitate_firma": city,
                    "adapost_public_ong": "",
                    "segmente": "noutati_ong",
                    "marketing_email_viitor": "1",
                    "nota_interna": f"[AUTORITATE_TSV_ONG_20260602] tip={tip}",
                    "stare": "ready",
                }
            )
    with csv_path.open("w", encoding="utf-8-sig", newline="") as f:
        wr = csv.DictWriter(f, fieldnames=HEADER)
        wr.writeheader()
        wr.writerows(rows_out)
    return len(rows_out)


def main() -> None:
    tsv = BASE_DIR / "database" / "exports" / "ong_prospecte_20260602_raw.tsv"
    out_csv = BASE_DIR / "database" / "exports" / "ong_prospecte_20260602_import.csv"
    n = build_import_csv(tsv, out_csv)
    print(f"prepared_csv={out_csv}")
    print(f"rows={n}")
    before = Lead.objects.filter(account_kind=Lead.KIND_ORG, imported_user__isnull=True).count()
    print(f"org_before={before}")


if __name__ == "__main__":
    main()
