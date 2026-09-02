"""Generare PDF donații (fpdf2 + Helvetica / Latin-1)."""

from __future__ import annotations

_RO_ASCII = str.maketrans(
    {
        "ă": "a",
        "â": "a",
        "î": "i",
        "ș": "s",
        "ş": "s",
        "ț": "t",
        "ţ": "t",
        "Ă": "A",
        "Â": "A",
        "Î": "I",
        "Ș": "S",
        "Ş": "S",
        "Ț": "T",
        "Ţ": "T",
    }
)


def _sanitize_pdf_text(value: str | None) -> str:
    """Fpdf2 Helvetica = Latin-1: transliterăm diacritice RO + înlocuim em dash."""
    s = (value or "").replace("\u2014", "-").replace("\u2013", "-").replace("\u00a0", " ")
    s = s.translate(_RO_ASCII)
    return s.encode("latin-1", "replace").decode("latin-1")


def _fpdf_build_formular_230(org: dict, d: dict) -> bytes | None:
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError:
        return None

    _nx = XPos.LMARGIN
    _ny = YPos.NEXT

    class _P(FPDF):
        pass

    pdf = _P()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(
        0,
        8,
        _sanitize_pdf_text("Declaratie orientativa - 230 (3,5%) EU-ADOPT"),
        new_x=_nx,
        new_y=_ny,
    )
    pdf.set_font("Helvetica", size=9)
    pdf.ln(2)
    pdf.multi_cell(
        0,
        5,
        _sanitize_pdf_text(
            "Document generat automat. Nu inlocuieste formularul oficial ANAF. Verificati versiunea in vigoare."
        ),
        new_x=_nx,
        new_y=_ny,
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    rows = [
        ("Nume", d.get("nume", "")),
        ("Prenume", d.get("prenume", "")),
        ("CNP", d.get("cnp", "")),
        ("Adresa", d.get("adresa", "")),
        ("Judet", d.get("judet", "")),
        ("Localitate", d.get("localitate", "")),
        ("E-mail", d.get("email", "")),
        ("Telefon", d.get("telefon") or "-"),
    ]
    for label, val in rows:
        pdf.set_font("Helvetica", "B", 10)
        line = _sanitize_pdf_text(f"{label}: {val}")
        pdf.multi_cell(0, 7, line, new_x=_nx, new_y=_ny)
        pdf.ln(1)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, _sanitize_pdf_text("Beneficiar (date publicate pe site):"), new_x=_nx, new_y=_ny)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, _sanitize_pdf_text(org.get("name", "")), new_x=_nx, new_y=_ny)
    if org.get("address"):
        pdf.multi_cell(0, 6, _sanitize_pdf_text(f"Localitate: {org.get('address', '')}"), new_x=_nx, new_y=_ny)
    cui = (org.get("cui") or "").strip()
    if cui:
        pdf.multi_cell(0, 6, _sanitize_pdf_text(f"CUI: {cui}"), new_x=_nx, new_y=_ny)
    iban = (org.get("iban") or "").strip()
    if iban:
        bank = (org.get("bank") or "").strip()
        pdf.multi_cell(
            0,
            6,
            _sanitize_pdf_text(f"IBAN: {iban}" + (f" - {bank}" if bank else "")),
            new_x=_nx,
            new_y=_ny,
        )
    email = (org.get("email_contact") or "").strip()
    if email:
        pdf.multi_cell(
            0,
            6,
            _sanitize_pdf_text(f"Date suplimentare (CUI, sediu, IBAN): {email}"),
            new_x=_nx,
            new_y=_ny,
        )
    return bytes(pdf.output())


def _fpdf_build_contract(org: dict, c: dict) -> bytes | None:
    try:
        from fpdf import FPDF
        from fpdf.enums import XPos, YPos
    except ImportError:
        return None

    _nx = XPos.LMARGIN
    _ny = YPos.NEXT

    class _P(FPDF):
        pass

    pdf = _P()
    pdf.set_auto_page_break(auto=True, margin=14)
    pdf.add_page()
    pdf.set_font("Helvetica", "B", 14)
    pdf.multi_cell(0, 8, _sanitize_pdf_text("Contract sponsorizare (model) EU-ADOPT"), new_x=_nx, new_y=_ny)
    pdf.set_font("Helvetica", size=9)
    pdf.ln(2)
    pdf.multi_cell(
        0, 5, _sanitize_pdf_text("Document generat automat - verificare juridica recomandata."), new_x=_nx, new_y=_ny
    )
    pdf.ln(4)
    pdf.set_font("Helvetica", size=10)
    for label, val in (
        ("Sponsor (firma)", c.get("denumire_firma", "")),
        ("CUI / CIF", c.get("cui", "")),
        ("Nr. Reg. Com.", c.get("nr_reg_com", "")),
        ("Adresa sediu", c.get("adresa_firma", "")),
        ("Reprezentant legal", c.get("reprezentant", "")),
        ("Valoare (RON)", c.get("suma", "")),
    ):
        pdf.set_font("Helvetica", "B", 10)
        pdf.multi_cell(0, 7, _sanitize_pdf_text(f"{label}: {val}"), new_x=_nx, new_y=_ny)
        pdf.ln(1)
    pdf.ln(2)
    pdf.set_font("Helvetica", "B", 10)
    pdf.multi_cell(0, 6, _sanitize_pdf_text("Beneficiar:"), new_x=_nx, new_y=_ny)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, _sanitize_pdf_text(org.get("name", "")), new_x=_nx, new_y=_ny)
    if org.get("address"):
        pdf.multi_cell(0, 6, _sanitize_pdf_text(f"Localitate: {org.get('address', '')}"), new_x=_nx, new_y=_ny)
    cui = (org.get("cui") or "").strip()
    if cui:
        pdf.multi_cell(0, 6, _sanitize_pdf_text(f"CUI: {cui}"), new_x=_nx, new_y=_ny)
    iban = (org.get("iban") or "").strip()
    if iban:
        bank = (org.get("bank") or "").strip()
        pdf.multi_cell(
            0,
            6,
            _sanitize_pdf_text(f"IBAN: {iban}" + (f" ({bank})" if bank else "")),
            new_x=_nx,
            new_y=_ny,
        )
    email = (org.get("email_contact") or "").strip()
    if email:
        pdf.multi_cell(
            0,
            6,
            _sanitize_pdf_text(f"Date suplimentare (CUI, sediu, IBAN): {email}"),
            new_x=_nx,
            new_y=_ny,
        )
    pdf.ln(2)
    pdf.set_font("Helvetica", size=10)
    pdf.multi_cell(0, 6, _sanitize_pdf_text("Obiect (rezumat): " + str(c.get("descriere") or "")), new_x=_nx, new_y=_ny)
    pdf.ln(1)
    pdf.set_font("Helvetica", size=8)
    pdf.multi_cell(
        0,
        4,
        _sanitize_pdf_text(
            "Nota: fara semnatura electronica. Clauze complete intre parti conform legii."
        ),
        new_x=_nx,
        new_y=_ny,
    )
    return bytes(pdf.output())


def render_formular_230_pdf_bytes(org: dict, d: dict) -> bytes | None:
    return _fpdf_build_formular_230(org, d)


def render_contract_sponsorizare_pdf_bytes(org: dict, c: dict) -> bytes | None:
    return _fpdf_build_contract(org, c)
