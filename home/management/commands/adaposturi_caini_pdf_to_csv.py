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


def _record_chunk_ending_at(full: str, line_start: int, line_end: int, max_back: int = 2600) -> tuple[int, str]:
    """Început index + textul unei singure înregistrări (până la ultimul \\n\\n înainte de linie sau max_back)."""
    low = max(0, line_start - max_back)
    dbl = full.rfind("\n\n", low, line_start)
    start = (dbl + 2) if dbl >= low else low
    return start, full[start:line_end]


def _iter_phone_anchor_positions(full: str) -> list[tuple[int, int, str]]:
    """
    Returnează [(start_linie, end_linie, telefon_principal)] pentru poziții utile în text.
    Include linii „doar telefon” și linii care se termină cu telefon după tab/spații.
    """
    out: list[tuple[int, int, str]] = []
    pos = 0
    while True:
        nl = full.find("\n", pos)
        line = full[pos:] if nl < 0 else full[pos:nl]
        raw = line.strip()
        if raw and "@" not in raw:
            m_end = re.search(
                r"(?<!\d)(?P<ph>0\d{9,10}|02\d{8,10}|03\d{8,10}|07\d{8,10})(?:\s*/\s*0?\d{6,12})?\s*$",
                raw,
            )
            if m_end and len(raw) <= 220:
                ph = m_end.group("ph")
                line_start = pos
                line_end = len(full) if nl < 0 else nl + 1
                out.append((line_start, line_end, ph))
        if nl < 0:
            break
        pos = nl + 1
    return out
_HEADER_NOISE = re.compile(
    r"(?i)^(tipul|adapsotului|proprietarului|adapostului|public|privat|responsabil|"
    r"adoptii|adresa|adopta|contact|tel\.|e-mail|mail|date de)\s*$"
)

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

_COUNTY_LINES = frozenset(_COUNTY_NAMES)


def _split_sections_by_county_line(full: str) -> list[tuple[str, str]]:
    """Împarte PDF-ul: fiecare linie care e exact nume județ → secțiune nouă."""
    lines = full.splitlines()
    out: list[tuple[str, str]] = []
    cur_jud = ""
    cur_buf: list[str] = []
    for line in lines:
        s = line.strip()
        if s in _COUNTY_LINES and len(s) <= 36:
            if cur_jud or cur_buf:
                out.append((cur_jud, "\n".join(cur_buf)))
            cur_jud = s
            cur_buf = []
        else:
            cur_buf.append(line)
    if cur_jud or cur_buf:
        out.append((cur_jud, "\n".join(cur_buf)))
    return out


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


def _norm_phone_key(raw: str) -> str:
    return re.sub(r"\D+", "", raw or "")[:15]


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


def _guess_org_and_address_from_block(chunk: str, phone_line_start: int) -> tuple[str, str]:
    """Înainte de linia cu telefon: denumire + adresă (euristică PDF)."""
    before = chunk[:phone_line_start].strip()
    lines = [ln.rstrip() for ln in before.splitlines() if ln.strip()]
    org_parts: list[str] = []
    addr_parts: list[str] = []
    for ln in lines:
        if ln.startswith("--"):
            continue
        if _HEADER_NOISE.match(ln.strip()):
            continue
        if _EMAIL_RE.search(ln):
            continue
        s = ln.strip()
        if re.fullmatch(r"[\d\s/\\.-]+", s):
            continue
        if re.search(r"(?i)\b(str\.|strada|calea|șos\.|sos\.|bd\.|b-dul|nr\.|fn|mun\.|com\.|sat|loc\.|jud\.|tarla|parcela|extravilan)\b", s):
            addr_parts.append(s)
        elif len(s) >= 3 and not addr_parts:
            org_parts.append(s)
        elif len(s) >= 8:
            org_parts.append(s)
    org = " ".join(org_parts).strip()[:400]
    addr = " ".join(addr_parts).strip()[:500]
    if not addr and org_parts:
        # uneori adresa e în aceeași linie cu localitatea după tab
        org = org[:400]
    return org, addr


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


def _row_adapost(
    *,
    email: str,
    telefon: str,
    jud: str,
    sub: str,
    org: str,
    addr: str,
    note: str,
) -> dict[str, str]:
    pub_ong = "1" if sub == StaffOnboardingLead.COLLAB_ADPUB else ""
    disp = (org or telefon or "Prospect fără email").strip()[:200]
    return {
        "email": email,
        "telefon": telefon[:40],
        "tip_cont": StaffOnboardingLead.KIND_ADAPOST,
        "tip_colaborator": sub,
        "prenume": "",
        "nume": "",
        "denumire_afisata_contact": disp,
        "username_propus": "",
        "judet": jud[:120],
        "localitate": "",
        "denumire_organizatie": (org or "")[:255],
        "denumire_legala": (org or "")[:255],
        "cui": "",
        "cui_cu_ro": "",
        "reg_com": "",
        "adresa_firma": (addr or "")[:255],
        "reprezentant_legal": "",
        "judet_firma": "",
        "localitate_firma": "",
        "adapost_public_ong": pub_ong,
        "segmente": "noutati_ong_adapost",
        "marketing_email_viitor": "",
        "nota_interna": note[:2000],
        "stare": StaffOnboardingLead.ST_READY,
    }


def _rows_from_pdf_text(full: str) -> list[dict[str, str]]:
    rows: list[dict[str, str]] = []
    seen_email: set[str] = set()
    seen_phone: set[str] = set()
    seen_sig: set[str] = set()

    def _sig(jud: str, org: str, tel: str, em: str) -> str:
        return f"{(jud or '').lower()}|{(org or '').lower()[:120]}|{_norm_phone_key(tel)}|{(em or '').lower()}"

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
        for pm in _PHONE_RE.finditer(tel):
            pkx = _norm_phone_key(pm.group(0))
            if pkx:
                seen_phone.add(pkx)
        note = f"Sursă: PDF Adăposturi câini fără stăpân | județ antet: {jud} | email poz {m.start()}"
        row = _row_adapost(
            email=m.group(0).strip(),
            telefon=tel,
            jud=jud,
            sub=sub,
            org=org,
            addr="",
            note=note,
        )
        rows.append(row)
        seen_sig.add(_sig(jud, org, tel, email))

    # Fără email: aceeași logică, dar DOAR în interiorul fiecărui județ (evită @ din județul anterior)
    for jud, body in _split_sections_by_county_line(full):
        if not jud or not (body or "").strip():
            continue
        for line_start, line_end, ph_raw in _iter_phone_anchor_positions(body):
            pk = _norm_phone_key(ph_raw)
            if not pk or pk in seen_phone:
                continue
            tail = body[line_end : min(len(body), line_end + 360)]
            if _EMAIL_RE.search(tail):
                continue
            chunk_start, chunk = _record_chunk_ending_at(body, line_start, line_end)
            if _EMAIL_RE.search(chunk):
                continue
            sub = _classify_pub_priv(chunk)
            rel_phone = line_start - chunk_start
            org, addr = _guess_org_and_address_from_block(chunk, rel_phone)
            if len((org + addr).strip()) < 10:
                continue
            tel = _phones_in(chunk) or ph_raw[:40]
            note = (
                f"Sursă: PDF Adăposturi câini fără stăpân | fără email în PDF | județ: {jud} | "
                "import cu email provizoriu"
            )
            sig = _sig(jud, org, tel, "")
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            seen_phone.add(pk)
            rows.append(
                _row_adapost(
                    email="",
                    telefon=tel,
                    jud=jud,
                    sub=sub,
                    org=org,
                    addr=addr,
                    note=note,
                )
            )

    # Fără email și fără telefon în bloc: doar nume + adresă (ex. liniuțe la contact)
    for jud, body in _split_sections_by_county_line(full):
        if not jud or not (body or "").strip():
            continue
        for para in re.split(r"\n\n+", body):
            p = (para or "").strip()
            if len(p) < 45 or _EMAIL_RE.search(p):
                continue
            if not re.search(r"(?i)(str\.|strada|mun\.|com\.|sat|loc\.|calea|șos\.|sos\.|nr\.)", p):
                continue
            if not re.search(r"(?i)\b(public|privat)\b", p) and " x " not in p and "\tx" not in p:
                continue
            noise = sum(1 for ln in p.splitlines() if _HEADER_NOISE.match((ln or "").strip()))
            if noise > 4 or len(p.splitlines()) > 18:
                continue
            sub = _classify_pub_priv(p)
            lines = [ln.rstrip() for ln in p.splitlines() if (ln or "").strip()]
            org_parts: list[str] = []
            addr_parts: list[str] = []
            for ln in lines:
                s = ln.strip()
                if _HEADER_NOISE.match(s) or s.startswith("--"):
                    continue
                if re.search(
                    r"(?i)\b(str\.|strada|mun\.|com\.|sat|loc\.|calea|șos\.|sos\.|nr\.|fn|jud\.)\b",
                    s,
                ):
                    addr_parts.append(s)
                elif len(s) > 5 and not re.fullmatch(r"[\d\s\-/x]+", s, flags=re.I):
                    org_parts.append(s)
            org = " ".join(org_parts).strip()[:400]
            addr = " ".join(addr_parts).strip()[:500]
            if len((org + addr).strip()) < 18:
                continue
            sig = _sig(jud, org, "", "")
            if sig in seen_sig:
                continue
            seen_sig.add(sig)
            rows.append(
                _row_adapost(
                    email="",
                    telefon="",
                    jud=jud,
                    sub=sub,
                    org=org,
                    addr=addr,
                    note=(
                        f"Sursă: PDF Adăposturi câini fără stăpân | fără email/telefon în bloc | județ: {jud} | "
                        "import cu email provizoriu"
                    )[:2000],
                )
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
        n_em = sum(1 for r in prospect_rows if (r.get("email") or "").strip())
        n_no = len(prospect_rows) - n_em
        self.stdout.write(
            self.style.SUCCESS(
                f"Scrie {out_path} — {len(prospect_rows)} rânduri "
                f"({n_em} cu email, {n_no} fără email → la import primesc email provizoriu dacă au date).\n"
            )
        )
