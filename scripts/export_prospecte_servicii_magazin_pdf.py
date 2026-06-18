"""
Export PDF prospecte Servicii + Magazin pe Desktop (fișiere separate).
"""

from __future__ import annotations

import os
import pathlib
import sys
from datetime import datetime

import django

BASE_DIR = pathlib.Path(__file__).resolve().parents[1]
if str(BASE_DIR) not in sys.path:
    sys.path.insert(0, str(BASE_DIR))
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")
django.setup()

from fpdf import FPDF  # noqa: E402

from home.models import StaffOnboardingLead as Lead  # noqa: E402


DESKTOP = pathlib.Path.home() / "Desktop"
STAMP = datetime.now().strftime("%Y%m%d")


def _sanitize(value: str | None) -> str:
    if not value:
        return ""
    s = str(value)
  # Latin-1 safe for Helvetica
    replacements = {
        "\u2013": "-",
        "\u2014": "-",
        "\u0219": "s",
        "\u0218": "S",
        "\u021b": "t",
        "\u021a": "T",
        "\u0103": "a",
        "\u0102": "A",
        "\u00e2": "a",
        "\u00c2": "A",
        "\u00ee": "i",
        "\u00ce": "I",
        "\u00e3": "a",
        "\u00c3": "A",
    }
    for k, v in replacements.items():
        s = s.replace(k, v)
    return s.encode("latin-1", errors="replace").decode("latin-1")


def _is_placeholder(email: str) -> bool:
    e = (email or "").lower()
    return "placeholder" in e or "@lead-placeholder" in e or not e.strip()


class ProspectPDF(FPDF):
    def header(self):
        self.set_font("Helvetica", "B", 11)
        self.cell(0, 8, _sanitize(self.title_text), new_x="LMARGIN", new_y="NEXT", align="C")
        self.set_font("Helvetica", size=8)
        self.cell(0, 5, _sanitize(self.subtitle_text), new_x="LMARGIN", new_y="NEXT", align="C")
        self.ln(2)

    def footer(self):
        self.set_y(-12)
        self.set_font("Helvetica", size=8)
        self.cell(0, 8, f"Pagina {self.page_no()}/{{nb}}", align="C")


def _export_category(
    *,
    subtype: str,
    label: str,
    outfile: pathlib.Path,
) -> int:
    qs = (
        Lead.objects.filter(
            account_kind=Lead.KIND_COLLAB,
            collaborator_subtype=subtype,
            imported_user__isnull=True,
        )
        .exclude(status=Lead.ST_ARCHIVED)
        .order_by("judet", "oras", "email")
    )
    rows = list(qs)
    real = sum(1 for r in rows if not _is_placeholder(r.email))

    pdf = ProspectPDF(orientation="L", unit="mm", format="A4")
    pdf.title_text = f"EU-ADOPT Prospecte {label}"
    pdf.subtitle_text = (
        f"Export {datetime.now().strftime('%d.%m.%Y %H:%M')} | "
        f"Total: {len(rows)} | Email real: {real} | Placeholder/lipsa: {len(rows) - real}"
    )
    pdf.alias_nb_pages()
    pdf.set_auto_page_break(auto=True, margin=12)
    pdf.add_page()

    headers = ["#", "Email", "Telefon", "Contact", "Adresa", "Localitate", "Judet", "Nota"]
    widths = [8, 42, 22, 38, 52, 28, 22, 62]
    pdf.set_font("Helvetica", "B", 7)
    for h, w in zip(headers, widths):
        pdf.cell(w, 6, _sanitize(h), border=1)
    pdf.ln()

    pdf.set_font("Helvetica", size=6)
    for i, lead in enumerate(rows, 1):
        note = (lead.notes or "")[:180]
        if _is_placeholder(lead.email):
            note = ("[PLACEHOLDER] " + note).strip()
        cells = [
            str(i),
            lead.email or "",
            lead.phone or "",
            lead.display_name or "",
            lead.company_address or "",
            lead.oras or "",
            lead.judet or "",
            note,
        ]
        line_h = 5
        x0 = pdf.get_x()
        y0 = pdf.get_y()
        max_h = line_h
        # simple wrap height estimate
        for txt, w in zip(cells, widths):
            lines = pdf.multi_cell(w, line_h, _sanitize(txt), border=0, split_only=True)
            max_h = max(max_h, line_h * max(1, len(lines)))
        if pdf.get_y() + max_h > 190:
            pdf.add_page()
            pdf.set_font("Helvetica", "B", 7)
            for h, w in zip(headers, widths):
                pdf.cell(w, 6, _sanitize(h), border=1)
            pdf.ln()
            pdf.set_font("Helvetica", size=6)
            y0 = pdf.get_y()
        x = x0
        for txt, w in zip(cells, widths):
            pdf.set_xy(x, y0)
            pdf.multi_cell(w, line_h, _sanitize(txt), border=1)
            x += w
        pdf.set_xy(x0, y0 + max_h)

    outfile.parent.mkdir(parents=True, exist_ok=True)
    pdf.output(str(outfile))
    return len(rows)


def main() -> None:
    servicii_path = DESKTOP / f"prospecte_SERVICII_{STAMP}.pdf"
    magazin_path = DESKTOP / f"prospecte_MAGAZIN_{STAMP}.pdf"

    n_serv = _export_category(
        subtype=Lead.COLLAB_SERVICII,
        label="Servicii (altele)",
        outfile=servicii_path,
    )
    n_mag = _export_category(
        subtype=Lead.COLLAB_MAGAZIN,
        label="Magazin",
        outfile=magazin_path,
    )

    print(f"servicii_rows={n_serv}")
    print(f"servicii_pdf={servicii_path}")
    print(f"magazin_rows={n_mag}")
    print(f"magazin_pdf={magazin_path}")


if __name__ == "__main__":
    main()
