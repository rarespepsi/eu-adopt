"""
Extrage prospecte din PDF-ul oficial „Adăposturi câini fără stăpân” (listă pe județe)
în CSV cu antetul Add USER (staff_onboarding_csv.CSV_HEADER_ROW).

- tip_cont = adapost
- tip_colaborator = adpub (public) sau adprv (privat), după euristică pe textul rândului
- adapost_public_ong = 1 dacă adpub, 0 dacă adprv
- segmente = noutati_ong_adapost

Exemplu:
  python manage.py adaposturi_caini_pdf_to_csv --pdf "C:\\Users\\USER\\Desktop\\adaposturi caini fara stapan.pdf" --out "C:\\Users\\USER\\Desktop\\adaposturi_prospecte.csv"

Necesită: pip install pdfplumber (vezi requirements.txt).
"""

from __future__ import annotations

import csv
import re
from pathlib import Path

from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import CSV_HEADER_ROW

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(r"(?:0\d{9,10}|(?:\+40)?7\d{8,9})(?:/\s*0?\d{6,10})?")

# Titluri județ / sector ca în PDF (variante comune Ș/Ş)
_COUNTY_NAMES = (
    "ALBA",
    "ARAD",
    "ARGEȘ",
    "ARGEŞ",
    "BACĂU",
    "BACAU",
    "BIHOR",
    "BISTRIŢA - NĂSĂUD",
    "BISTRIȚA - NĂSĂUD",
    "BRĂILA",
    "BRAILA",
    "BRAŞOV",
    "BRASOV",
    "BUCUREŞTI",
    "BUCURESTI",
    "BOTOŞANI",
    "BOTOSANI",
    "BUZĂU",
    "BUZAU",
    "CĂLĂRAŞI",
    "CALARASI",
    "CARAŞ - SEVERIN",
    "CARAS - SEVERIN",
    "CLUJ",
    "CONSTANŢA",
    "CONSTANTA",
    "COVASNA",
    "DÂMBOVIŢA",
    "DAMBOVITA",
    "DOLJ",
    "GALAŢI",
    "GALATI",
    "GIURGIU",
    "GORJ",
    "HARGHITA",
    "HUNEDOARA",
    "IALOMIŢA",
    "IALOMITA",
    "IAŞI",
    "IASI",
    "ILFOV",
    "MARAMUREŞ",
    "MARAMURES",
    "MEHEDINŢI",
    "MEHEDINTI",
    "MUREŞ",
    "MURES",
    "NEAMŢ",
    "NEAMT",
    "OLT",
    "PRAHOVA",
    "SATU MARE",
    "SĂLAJ",
    "SALAJ",
    "SIBIU",
    "SUCEAVA",
    "TELEORMAN",
    "TIMIŞ",
    "TIMIS",
    "TULCEA",
    "VASLUI",
    "VÂLCEA",
    "VALCEA",
    "VRANCEA",
)


def _county_before(text: str, pos: int) -> str:
    head = text[:pos]
    best = ""
    best_pos = -1
    for name in _COUNTY_NAMES:
        p = head.rfind(name)
        if p >= best_pos:
            best_pos = p
            best = name
    return best


def _classify_pub_priv(snippet: str) -> str:
    s = snippet.replace("\r", "")
    if re.search(r"(?i)privat\s*\t?\s*x\b", s):
        return StaffOnboardingLead.COLLAB_ADPRV
    if re.search(r"(?i)public\s*\t?\s*x\b", s):
        return StaffOnboardingLead.COLLAB_ADPUB
    if re.search(r"\bx\s+-\s", s):
        return StaffOnboardingLead.COLLAB_ADPRV
    return StaffOnboardingLead.COLLAB_ADPUB


def _guess_org_name(chunk: str, email_pos: int) -> str:
    before = chunk[:email_pos].strip()
    lines = [ln.strip() for ln in before.splitlines() if ln.strip()]
    if not lines:
        return ""
    tail = lines[-8:]
    parts: list[str] = []
    for ln in tail:
        if _EMAIL_RE.search(ln) or ln.startswith("--"):
            continue
        if re.fullmatch(r"[\d\s/\\.-]+", ln):
            continue
        parts.append(ln)
    name = " ".join(parts).strip()
    return (name[:400] or "").strip()


def _phones_in(chunk: str) -> str:
    found = _PHONE_RE.findall(chunk)
    if not found:
        return ""
    seen: set[str] = set()
    out: list[str] = []
    for p in found:
        q = re.sub(r"\s+", "", p)[:40]
        if q and q not in seen:
            seen.add(q)
            out.append(q)
    return " / ".join(out[:3])[:40]


def _rows_from_pdf_text(full: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen_email: set[str] = set()
    for m in _EMAIL_RE.finditer(full):
        email = m.group(0).strip().lower()
        if email in seen_email:
            continue
        seen_email.add(email)
        start = max(0, m.start() - 1200)
        end = min(len(full), m.end() + 400)
        chunk = full[start:end]
        rel = m.start() - start
        jud = _county_before(full, m.start())
        sub = _classify_pub_priv(chunk)
        org = _guess_org_name(chunk, rel)
        tel = _phones_in(chunk)
        note = f"Sursă: PDF Adăposturi câini fără stăpân | județ antet: {jud} | email poz {m.start()}"
        pub_ong = "1" if sub == StaffOnboardingLead.COLLAB_ADPUB else ""
        rows.append(
            {
                "email": m.group(0).strip(),
                "telefon": tel,
                "tip_cont": StaffOnboardingLead.KIND_ADAPOST,
                "tip_colaborator": sub,
                "prenume": "",
                "nume": "",
                "denumire_afisata_contact": org or m.group(0).strip(),
                "username_propus": "",
                "judet": jud,
                "localitate": "",
                "denumire_organizatie": org,
                "denumire_legala": org,
                "cui": "",
                "cui_cu_ro": "",
                "reg_com": "",
                "adresa_firma": "",
                "reprezentant_legal": "",
                "judet_firma": "",
                "localitate_firma": "",
                "adapost_public_ong": pub_ong,
                "segmente": "noutati_ong_adapost",
                "marketing_email_viitor": "",
                "nota_interna": note[:2000],
                "stare": StaffOnboardingLead.ST_READY,
            }
        )
    return rows


class Command(BaseCommand):
    help = "PDF listă adăposturi câini → CSV prospecte (tip adapost, colab ADPUB/ADPRV)."

    def add_arguments(self, parser):
        parser.add_argument("--pdf", required=True, help="Cale către fișierul PDF sursă.")
        parser.add_argument("--out", required=True, help="Fișier CSV destinație (un singur fișier).")

    def handle(self, *args, **options):
        pdf_path = Path((options.get("pdf") or "").strip()).expanduser()
        out_path = Path((options.get("out") or "").strip()).expanduser()
        if not pdf_path.is_file():
            self.stderr.write(self.style.ERROR(f"PDF inexistent: {pdf_path}\n"))
            return
        try:
            import pdfplumber
        except ImportError:
            self.stderr.write(
                self.style.ERROR("Lipsește pachetul pdfplumber. Rulează: pip install pdfplumber\n")
            )
            return

        parts: list[str] = []
        with pdfplumber.open(pdf_path) as pdf:
            for page in pdf.pages:
                t = page.extract_text() or ""
                if t.strip():
                    parts.append(t)
        full = "\n\n".join(parts)
        if not full.strip():
            self.stderr.write(self.style.ERROR("Nu s-a extras text din PDF (pagini goale?).\n"))
            return

        prospect_rows = _rows_from_pdf_text(full)
        out_path.parent.mkdir(parents=True, exist_ok=True)
        with out_path.open("w", encoding="utf-8-sig", newline="") as f:
            w = csv.DictWriter(f, fieldnames=CSV_HEADER_ROW, extrasaction="ignore")
            w.writeheader()
            for row in prospect_rows:
                w.writerow(row)
        self.stdout.write(self.style.SUCCESS(f"Scrie {out_path} — {len(prospect_rows)} rânduri (cu email).\n"))
        self.stdout.write(
            "Rânduri fără email în PDF nu sunt incluse; completează manual sau extinde parserul.\n"
        )
