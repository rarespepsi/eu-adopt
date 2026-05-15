"""
Prospecte colaboratori transportatori — sursă publică ANSVSA Domino (MTL = rutier lungă durată).

- Parsează lista MTL, păstrează rândurile cu keyword câini/pisici/pet (euristic, ca la extragerea CSV).
- Agregă pe operator + județ (un lead / mai multe vehicule în notițe).
- account_kind=collaborator, collaborator_subtype=transport.
- Fără CUI în sursă: email placeholder determinist (aceeași cheie → același lead la rerulare).
- NU atinge pagina publică Transport.

Exemplu:
  python manage.py import_ansvsa_mtl_pet_transport_leads
  python manage.py import_ansvsa_mtl_pet_transport_leads --apply
  python manage.py import_ansvsa_mtl_pet_transport_leads --csv C:\\path\\to\\mtl.html
"""

from __future__ import annotations

import hashlib
import re
import urllib.request
from collections import defaultdict
from datetime import datetime, timezone
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX

MTL_DEFAULT_URL = "https://domino.iqm.ro/ansv/ansvsa.nsf/MTL"
MTDOC_BASE = "https://domino.iqm.ro/ansv/ansvsa.nsf/MTDoc?OpenForm&NUM="

_ROW_RE = re.compile(
    r'<div class="TR">'
    r'<div class="celtabLTbsLRT"><p class="p14">([^<]*)</p></div>'
    r'<div class="celtabLTbsLRT"><p class="p14">(\d+)</p></div>'
    r'<div class="celtabhLTbsRT"[^>]*NUM=(\d+)[^>]*>.*?<p class="p14u">([^<]*)</p></div>'
    r'<div class="celtabLTbsLRT"><p class="p14">([^<]*)</p></div>'
    r'<div class="celtabLTbsLRT"><p class="p14">([^<]*)</p></div>'
    r"</div>",
    re.DOTALL,
)

_PET_KW = re.compile(
    r"("
    r"\bdogs?\b|\bcats?\b|\bpets?\b|"
    r"pets?(?![a-zăâîșț])|"
    r"(?<![0-9])pet(s)?(?![a-zăâîșț])|"
    r"dog|pisic|pisici|"
    r"câini|câine|caini|caine|"
    r"felin|canin|"
    r"compan(?!ie)|de companie|animale de companie"
    r")",
    re.I,
)


def _fetch_mtl_html(url: str, timeout: int = 120) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EU-Adopt staff import/1.0; +https://euadopt.ro)",
            "Accept": "text/html,*/*",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def _parse_rows(html: str) -> list[tuple[str, str, str, str, str, str]]:
    """Return list of (judet, doc_num, mt_num, nr_inmatriculare, operator, autorizatie_status)."""
    out: list[tuple[str, str, str, str, str, str]] = []
    for m in _ROW_RE.findall(html):
        out.append((m[0].strip(), m[1].strip(), m[2].strip(), m[3].strip(), m[4].strip(), m[5].strip()))
    return out


def _row_is_pet_keyword(row: tuple[str, str, str, str, str, str]) -> bool:
    blob = " ".join(row).lower()
    return bool(_PET_KW.search(blob))


def _norm_key(operator: str, judet: str) -> str:
    op = re.sub(r"\s+", " ", (operator or "").strip()).lower()
    jd = re.sub(r"\s+", " ", (judet or "").strip()).lower()
    return f"{op}|{jd}"


def _placeholder_email(operator: str, judet: str) -> str:
    h = hashlib.sha256(_norm_key(operator, judet).encode("utf-8")).hexdigest()[:24]
    local = f"ansvsa-mtl-pet-{h}"
    return f"{local}{PLACEHOLDER_EMAIL_SUFFIX}"[:254]


def _build_notes(
    stamp: str,
    vehicles: list[tuple[str, str, str, str, str, str]],
) -> str:
    lines = [
        "Sursă: ANSVSA — listă publică MTL (mijloace transport rutier animale vii, călătorie lungă).",
        "Filtrare automată: keyword câini/pisici/pet în textul din listă (nu înlocuiește verificarea MTDoc / specia).",
        "",
        "Vehicule:",
    ]
    for jud, _dn, mt_num, plate, op, status in vehicles:
        doc_url = f"{MTDOC_BASE}{mt_num}"
        lines.append(f"- {jud} | {plate or '—'} | {op} | doc {mt_num} | {doc_url}")
        if status:
            lines.append(f"  ({status[:200]}{'…' if len(status) > 200 else ''})")
    lines.append("")
    lines.append(f"[import_ansvsa_mtl_pet {stamp}] vehicule={len(vehicles)}")
    return "\n".join(lines)[:12000]


class Command(BaseCommand):
    help = "Import prospecte transportatori pet din lista publică ANSVSA MTL (agregat operator+județ)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Scrie în DB; fără flag, simulare.",
        )
        parser.add_argument(
            "--csv",
            metavar="PATH",
            help="Fișier HTML salvat din MTL (în loc de download la URL).",
        )
        parser.add_argument(
            "--url",
            default=MTL_DEFAULT_URL,
            help=f"URL listă MTL (implicit: {MTL_DEFAULT_URL}).",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry = not bool(options.get("apply"))
        csv_path = (options.get("csv") or "").strip()
        url = (options.get("url") or MTL_DEFAULT_URL).strip()

        if csv_path:
            try:
                with open(csv_path, "r", encoding="utf-8", errors="replace") as f:
                    html = f.read()
            except OSError as e:
                raise CommandError(f"Nu pot citi --csv: {e}") from e
        else:
            self.stdout.write(self.style.NOTICE(f"Descarc {url} …"))
            try:
                html = _fetch_mtl_html(url)
            except Exception as e:
                raise CommandError(
                    f"Download eșuat ({e}). Salvează HTML din browser și rulează cu --csv cale\\către\\fișier.html"
                ) from e

        rows = _parse_rows(html)
        if not rows:
            raise CommandError("Nu s-a putut parsa niciun rând (structură HTML schimbată?).")

        pet_rows = [r for r in rows if _row_is_pet_keyword(r)]
        clusters: dict[str, list[tuple[str, str, str, str, str, str]]] = defaultdict(list)
        for r in pet_rows:
            jud, _dn, _mt, _plate, op, _st = r
            clusters[_norm_key(op, jud)].append(r)

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.stdout.write(f"Total rânduri MTL: {len(rows)} | după filtru pet: {len(pet_rows)} | lead-uri (operator+județ): {len(clusters)}")

        created = 0
        updated = 0
        for key, veh in clusters.items():
            op = veh[0][4].strip() or "—"
            jud = veh[0][0].strip() or ""
            email = _placeholder_email(op, jud)
            display = (op or "Transportator")[:200]
            org = (op or "")[:255]
            notes = _build_notes(stamp, sorted(veh, key=lambda x: (x[0], x[3])))

            if dry:
                self.stdout.write(
                    f"[dry-run] {'UPDATE' if StaffOnboardingLead.objects.filter(email=email).exists() else 'CREATE'} "
                    f"| {email[:48]}… | {jud} | {display[:60]} | vehicule={len(veh)}"
                )
                continue

            existing = StaffOnboardingLead.objects.filter(email=email).first()
            if existing:
                existing.display_name = display
                existing.org_display_name = org[:255]
                existing.company_legal_name = (op or "")[:255]
                existing.judet = jud[:120]
                existing.oras = ""
                existing.company_judet = jud[:120]
                existing.company_oras = ""
                existing.account_kind = StaffOnboardingLead.KIND_COLLAB
                existing.collaborator_subtype = StaffOnboardingLead.COLLAB_TRANSPORT
                existing.vet_prospect_kind = ""
                existing.notes = notes
                existing.status = StaffOnboardingLead.ST_READY
                existing.save(
                    update_fields=[
                        "display_name",
                        "org_display_name",
                        "company_legal_name",
                        "judet",
                        "oras",
                        "company_judet",
                        "company_oras",
                        "account_kind",
                        "collaborator_subtype",
                        "vet_prospect_kind",
                        "notes",
                        "status",
                    ]
                )
                updated += 1
                self.stdout.write(self.style.SUCCESS(f"Actualizat | {jud} | {display[:70]} | veh={len(veh)}"))
                continue

            StaffOnboardingLead.objects.create(
                created_by=None,
                email=email,
                phone="",
                display_name=display,
                org_display_name=org[:255],
                username_suggested="",
                first_name="",
                last_name="",
                account_kind=StaffOnboardingLead.KIND_COLLAB,
                collaborator_subtype=StaffOnboardingLead.COLLAB_TRANSPORT,
                vet_prospect_kind="",
                judet=jud[:120],
                oras="",
                company_legal_name=(op or "")[:255],
                company_cui="",
                company_cui_has_ro=False,
                company_reg_com="",
                company_address=f"Evidență ANSVSA MTL, județ: {jud}"[:255],
                company_representative="",
                company_judet=jud[:120],
                company_oras="",
                is_public_shelter=False,
                segments=[],
                marketing_emails_requested=False,
                notes=notes,
                status=StaffOnboardingLead.ST_READY,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Creat | {jud} | {display[:70]} | veh={len(veh)}"))

        if dry:
            self.stdout.write(self.style.NOTICE("Simulare. Rulează cu --apply pentru a scrie în DB."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Gata. Create: {created}, actualizate: {updated}."))
