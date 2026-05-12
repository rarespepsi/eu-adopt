"""
CSV import/export pentru lead-uri staff (Add USER) — format prietenos ChatGPT / Excel.
Capete de tabel aliniate la câmpuri din fișele de înregistrare (PF/ONG/colaborator).
Coloanele neaplicabile (ex. CUI pentru PF) rămân goale; nu e nevoie de toate coloanele din șablon.
Rândurile fără email dar cu alte date (județ, telefon, nume etc.) se importă cu email provizoriu pentru căutări.
"""

from __future__ import annotations

import csv
import io
import re
import uuid
from typing import Any

from home.models import StaffOnboardingLead
from home.staff_onboarding_form import SEGMENT_CHOICES

SEGMENT_KEYS = frozenset(dict(SEGMENT_CHOICES).keys())

# Prima linie CSV = aceste etichete (ordine fixă, recomandat pentru ChatGPT).
CSV_HEADER_ROW = [
    "email",
    "telefon",
    "tip_cont",
    "tip_colaborator",
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

# Mapare antet normalizat (lowercase, fără spații extra) → cheie canonică din CSV_HEADER_ROW
_HEADER_ALIASES = {
    "email": "email",
    "e-mail": "email",
    "telefon": "telefon",
    "phone": "telefon",
    "tip_cont": "tip_cont",
    "tip cont": "tip_cont",
    "rol": "tip_cont",
    "account_kind": "tip_cont",
    "tip_colaborator": "tip_colaborator",
    "tip colaborator": "tip_colaborator",
    "prenume": "prenume",
    "nume": "nume",
    "denumire_afisata_contact": "denumire_afisata_contact",
    "denumire contact": "denumire_afisata_contact",
    "display_name": "denumire_afisata_contact",
    "username_propus": "username_propus",
    "username": "username_propus",
    "judet": "judet",
    "județ": "judet",
    "localitate": "localitate",
    "oras": "localitate",
    "oraș": "localitate",
    "denumire_organizatie": "denumire_organizatie",
    "denumire organizatie": "denumire_organizatie",
    "denumire_legala": "denumire_legala",
    "cui": "cui",
    "cui_cu_ro": "cui_cu_ro",
    "cui cu ro": "cui_cu_ro",
    "reg_com": "reg_com",
    "adresa_firma": "adresa_firma",
    "reprezentant_legal": "reprezentant_legal",
    "judet_firma": "judet_firma",
    "localitate_firma": "localitate_firma",
    "adapost_public_ong": "adapost_public_ong",
    "segmente": "segmente",
    "marketing_email_viitor": "marketing_email_viitor",
    "nota_interna": "nota_interna",
    "stare": "stare",
    "status": "stare",
}


def _norm_header(s: str) -> str:
    s = (s or "").strip().lower()
    s = s.replace("\ufeff", "")
    return s


def _bool_cell(raw: str) -> bool:
    t = (raw or "").strip().lower()
    return t in ("1", "true", "yes", "da", "x", "on")


def _parse_segments(raw: str) -> list[str]:
    if not (raw or "").strip():
        return []
    parts = re.split(r"[,;|]", raw)
    out = []
    for p in parts:
        k = p.strip().lower().replace(" ", "_")
        if k in SEGMENT_KEYS:
            out.append(k)
    return out


def _normalize_tip_cont(raw: str) -> str:
    t = (raw or "").strip().lower()
    if t in ("pf", "persoana_fizica", "persoană fizică", "fizica", "fizic"):
        return StaffOnboardingLead.KIND_PF
    if t in ("org", "ong", "asociatie", "asociație", "adapost", "adăpost", "firma", "firmă", "srl"):
        return StaffOnboardingLead.KIND_ORG
    if t in ("collaborator", "colaborator", "colab", "partener"):
        return StaffOnboardingLead.KIND_COLLAB
    return StaffOnboardingLead.KIND_PF


def _normalize_collab_subtype(raw: str) -> str:
    t = (raw or "").strip().lower()
    mapping = {
        "cabinet": StaffOnboardingLead.COLLAB_CABINET,
        "cabinet veterinar": StaffOnboardingLead.COLLAB_CABINET,
        "cv": StaffOnboardingLead.COLLAB_CV,
        "vet": StaffOnboardingLead.COLLAB_CABINET,
        "veterinar": StaffOnboardingLead.COLLAB_CABINET,
        "servicii": StaffOnboardingLead.COLLAB_SERVICII,
        "magazin": StaffOnboardingLead.COLLAB_MAGAZIN,
        "grooming": StaffOnboardingLead.COLLAB_MAGAZIN,
        "transport": StaffOnboardingLead.COLLAB_TRANSPORT,
        "transportator": StaffOnboardingLead.COLLAB_TRANSPORT,
    }
    return mapping.get(t, "")


def _normalize_status(raw: str) -> str:
    t = (raw or "").strip().lower()
    allowed = {x[0] for x in StaffOnboardingLead.STATUS_CHOICES}
    if t in allowed:
        return t
    return StaffOnboardingLead.ST_READY


_CANON_KEYS = frozenset(CSV_HEADER_ROW)

# Adrese generate când lipsește coloana / valoarea email — prospect doar pentru căutare; nu se trimit invitații.
PLACEHOLDER_EMAIL_SUFFIX = "@lead-placeholder.invalid"


def is_placeholder_lead_email(email: str | None) -> bool:
    e = (email or "").strip().lower()
    return bool(e) and e.endswith(PLACEHOLDER_EMAIL_SUFFIX)


def _placeholder_email_for_csv_row(line_no: int) -> str:
    return f"prospect-l{line_no}-{uuid.uuid4().hex[:12]}{PLACEHOLDER_EMAIL_SUFFIX}"


def _csv_row_has_identity(canon: dict[str, str]) -> bool:
    """True dacă rândul are cel puțin o informație utilă în afară de email (import parțial)."""
    for key in (
        "telefon",
        "tip_cont",
        "tip_colaborator",
        "prenume",
        "nume",
        "denumire_afisata_contact",
        "username_propus",
        "judet",
        "localitate",
        "denumire_organizatie",
        "denumire_legala",
        "cui",
        "reg_com",
        "adresa_firma",
        "reprezentant_legal",
        "judet_firma",
        "localitate_firma",
        "nota_interna",
        "segmente",
    ):
        if (canon.get(key) or "").strip():
            return True
    if _bool_cell(canon.get("cui_cu_ro") or ""):
        return True
    if _bool_cell(canon.get("marketing_email_viitor") or ""):
        return True
    if _bool_cell(canon.get("adapost_public_ong") or ""):
        return True
    st = (canon.get("stare") or "").strip().lower()
    if st and st not in ("ready", "pregatit", "draft"):
        return True
    return False


def _canon_row_from_reader(row: dict[str, str | None]) -> dict[str, str]:
    out: dict[str, str] = {}
    for k, v in row.items():
        nk = _norm_header(k or "")
        if not nk:
            continue
        ck = _HEADER_ALIASES.get(nk)
        if ck is None and nk in _CANON_KEYS:
            ck = nk
        if ck:
            out[ck] = (v or "").strip()
    return out


def row_canon_to_lead_kwargs(canon: dict[str, str]) -> dict[str, Any]:
    def g(key: str) -> str:
        return (canon.get(key) or "").strip()

    email = g("email")
    tip = _normalize_tip_cont(g("tip_cont"))
    sub = _normalize_collab_subtype(g("tip_colaborator"))
    if tip != StaffOnboardingLead.KIND_COLLAB:
        sub = ""

    prenume = g("prenume")
    nume = g("nume")
    display = g("denumire_afisata_contact")
    if not display:
        display = (" ".join(x for x in (prenume, nume) if x)).strip()
    if not display:
        display = email.split("@")[0] if email else "Prospect"

    segments = _parse_segments(g("segmente"))
    notes_raw = g("nota_interna")
    notes = notes_raw[:5000]

    return {
        "email": email,
        "phone": g("telefon")[:40],
        "display_name": display[:200],
        "org_display_name": g("denumire_organizatie")[:255],
        "username_suggested": g("username_propus")[:150],
        "first_name": prenume[:150],
        "last_name": nume[:150],
        "company_legal_name": g("denumire_legala")[:255],
        "company_cui": g("cui")[:32],
        "company_cui_has_ro": _bool_cell(g("cui_cu_ro")),
        "company_address": g("adresa_firma")[:255],
        "company_reg_com": g("reg_com")[:64],
        "company_representative": g("reprezentant_legal")[:255],
        "company_judet": g("judet_firma")[:120],
        "company_oras": g("localitate_firma")[:120],
        "is_public_shelter": _bool_cell(g("adapost_public_ong")),
        "account_kind": tip,
        "collaborator_subtype": sub,
        "judet": g("judet")[:120],
        "oras": g("localitate")[:120],
        "segments": segments,
        "marketing_emails_requested": _bool_cell(g("marketing_email_viitor")),
        "notes": notes,
        "status": _normalize_status(g("stare")),
    }


def lead_to_csv_row(lead: StaffOnboardingLead) -> dict[str, str]:
    seg = ",".join(lead.segments) if isinstance(lead.segments, list) else ""
    return {
        "email": lead.email,
        "telefon": lead.phone or "",
        "tip_cont": lead.account_kind,
        "tip_colaborator": lead.collaborator_subtype or "",
        "prenume": lead.first_name or "",
        "nume": lead.last_name or "",
        "denumire_afisata_contact": lead.display_name or "",
        "username_propus": lead.username_suggested or "",
        "judet": lead.judet or "",
        "localitate": lead.oras or "",
        "denumire_organizatie": lead.org_display_name or "",
        "denumire_legala": lead.company_legal_name or "",
        "cui": lead.company_cui or "",
        "cui_cu_ro": "1" if lead.company_cui_has_ro else "",
        "reg_com": lead.company_reg_com or "",
        "adresa_firma": lead.company_address or "",
        "reprezentant_legal": lead.company_representative or "",
        "judet_firma": lead.company_judet or "",
        "localitate_firma": lead.company_oras or "",
        "adapost_public_ong": "1" if lead.is_public_shelter else "",
        "segmente": seg,
        "marketing_email_viitor": "1" if lead.marketing_emails_requested else "",
        "nota_interna": lead.notes or "",
        "stare": lead.status,
    }


def export_csv_bytes(qs) -> bytes:
    buf = io.StringIO()
    w = csv.DictWriter(buf, fieldnames=CSV_HEADER_ROW, extrasaction="ignore")
    w.writeheader()
    for lead in qs.iterator():
        w.writerow(lead_to_csv_row(lead))
    return buf.getvalue().encode("utf-8-sig")


def import_csv_bytes(data: bytes, created_by=None) -> tuple[list[str], int, int]:
    """
    Importă rânduri CSV. Returnează (erori, număr rânduri create, număr rânduri fără email cu adresă provizorie).

    Nu e obligatoriu să existe coloana `email` sau să fie completate toate câmpurile: dacă rândul are alte
    date (județ, telefon, nume, firmă etc.), se creează prospectul cu email provizoriu (completat ulterior în UI).
    """
    text = data.decode("utf-8-sig")
    f = io.StringIO(text)
    reader = csv.DictReader(f)
    if not reader.fieldnames:
        return (["Fișier CSV fără antet."], 0, 0)

    errors: list[str] = []
    created = 0
    placeholder_emails = 0
    line_no = 1
    for row in reader:
        line_no += 1
        if not row:
            continue
        if not any((v or "").strip() for v in row.values()):
            continue
        canon = _canon_row_from_reader({k: v for k, v in row.items() if k is not None})
        try:
            kwargs = row_canon_to_lead_kwargs(canon)
        except Exception as e:
            errors.append(f"Linia {line_no}: parse {e}")
            continue
        if not kwargs.get("email"):
            if _csv_row_has_identity(canon):
                kwargs["email"] = _placeholder_email_for_csv_row(line_no)
                placeholder_emails += 1
            else:
                continue
        StaffOnboardingLead.objects.create(created_by=created_by, **kwargs)
        created += 1

    return errors, created, placeholder_emails
