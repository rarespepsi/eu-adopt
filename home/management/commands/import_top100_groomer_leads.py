"""
Prospecte colaboratori grooming — saloane înfrumusețare canină/felină (Top 100 România).

Sursă publică: https://www.top100ofromania.eu/sub-category/89/groomer
- Un lead per firmă (company_id Top100).
- account_kind=collaborator, collaborator_subtype=grooming.
- Email placeholder determinist (top100-groom-{company_id}).
- NU modifică pagina publică Servicii / Grooming.

Exemplu:
  python manage.py import_top100_groomer_leads
  python manage.py import_top100_groomer_leads --apply
  python manage.py import_top100_groomer_leads --html C:\\path\\page.html --apply
  python manage.py import_top100_groomer_leads --apply --export-csv database/exports/groomer_top100.csv
"""

from __future__ import annotations

import csv
import html as html_mod
import re
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand, CommandError

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX

DEFAULT_URL = "https://www.top100ofromania.eu/sub-category/89/groomer"
BASE_SITE = "https://www.top100ofromania.eu"
LIST_URL = DEFAULT_URL

_CARD_RE = re.compile(
    r'<a href="/company/(\d+)/([^"]+)" class=" box_zwyciezcy2?  filtruj">\s*'
    r'<div class="blok">.*?'
    r'<div class="zwyciezcy_nazwa tooltip">\s*(.*?)\s*</div>\s*'
    r'<div class="zwyciezcy_miejscowosc">([^<]*)</div>',
    re.DOTALL,
)

_EDITION_RE = re.compile(
    r'<div id="top100"[^>]*data-edition-key="(\d{4})"',
    re.I,
)


def _fetch_html(url: str, timeout: int = 60) -> str:
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EU-Adopt staff import/1.0)",
            "Accept": "text/html,*/*",
            "Accept-Language": "ro,en;q=0.9",
        },
        method="GET",
    )
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        return resp.read().decode("utf-8", errors="replace")


def _clean_name(raw: str) -> str:
    t = re.sub(r"<[^>]+>", " ", raw)
    t = html_mod.unescape(t)
    t = re.sub(r"\s+", " ", t).strip()
    if "..." in t:
        t = t.split("...", 1)[0].strip()
    return t[:500]


def _parse_groomers(page_html: str) -> tuple[str, list[dict[str, str]]]:
    ed = _EDITION_RE.search(page_html)
    edition = ed.group(1) if ed else ""
    rows: list[dict[str, str]] = []
    seen_ids: set[str] = set()
    for company_id, slug, name_raw, city in _CARD_RE.findall(page_html):
        cid = (company_id or "").strip()
        if not cid or cid in seen_ids:
            continue
        seen_ids.add(cid)
        name = _clean_name(name_raw)
        slug = slug.strip()
        city = html_mod.unescape(re.sub(r"\s+", " ", city).strip())
        profile_url = f"{BASE_SITE.rstrip('/')}/company/{cid}/{slug}"
        rows.append(
            {
                "edition": edition,
                "company_id": cid,
                "slug": slug,
                "url": profile_url,
                "name": name,
                "city": city,
            }
        )
    return edition, rows


def _placeholder_email(company_id: str) -> str:
    cid = re.sub(r"\D", "", company_id) or "0"
    return f"top100-groom-{cid}{PLACEHOLDER_EMAIL_SUFFIX}"[:254]


def _build_notes(row: dict[str, str], stamp: str, edition: str) -> str:
    lines = [
        "Sursă: Top 100 Of Romania — industrie Groomer (saloane înfrumusețare / frizerie canină).",
        f"Listă: {LIST_URL}",
        f"Profil: {row.get('url') or '—'}",
        f"ID Top100: {row.get('company_id') or '—'} | ediție: {edition or row.get('edition') or '—'}",
        "",
        f"[import_top100_groomer {stamp}]",
    ]
    return "\n".join(lines)[:12000]


class Command(BaseCommand):
    help = "Import prospecte grooming (Top 100 România, sub-categorie Groomer)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Scrie în DB; fără flag, simulare.",
        )
        parser.add_argument(
            "--html",
            metavar="PATH",
            help="HTML salvat din browser (în loc de download).",
        )
        parser.add_argument(
            "--url",
            default=DEFAULT_URL,
            help=f"URL listă (implicit: {DEFAULT_URL}).",
        )
        parser.add_argument(
            "--export-csv",
            metavar="PATH",
            help="Opțional: salvează extragerea în CSV înainte/după import.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        dry = not bool(options.get("apply"))
        html_path = (options.get("html") or "").strip()
        url = (options.get("url") or DEFAULT_URL).strip()
        export_csv = (options.get("export_csv") or "").strip()

        if html_path:
            try:
                with open(html_path, "r", encoding="utf-8", errors="replace") as f:
                    page = f.read()
            except OSError as e:
                raise CommandError(f"Nu pot citi --html: {e}") from e
        else:
            self.stdout.write(self.style.NOTICE(f"Descarc {url} …"))
            try:
                page = _fetch_html(url)
            except Exception as e:
                raise CommandError(
                    f"Download eșuat ({e}). Salvează pagina și rulează cu --html cale\\fișier.html"
                ) from e

        edition, rows = _parse_groomers(page)
        if not rows:
            raise CommandError("Nu s-a putut parsa niciun salon (structură HTML schimbată?).")

        if export_csv:
            out_path = Path(export_csv)
            out_path.parent.mkdir(parents=True, exist_ok=True)
            with open(out_path, "w", encoding="utf-8-sig", newline="") as f:
                w = csv.DictWriter(
                    f,
                    fieldnames=["edition", "company_id", "slug", "url", "name", "city"],
                )
                w.writeheader()
                w.writerows(rows)
            self.stdout.write(self.style.NOTICE(f"CSV export: {out_path} ({len(rows)} rânduri)"))

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        self.stdout.write(
            f"Salonuri parsate: {len(rows)} | ediție Top100: {edition or '—'}"
        )

        created = 0
        updated = 0
        for row in rows:
            cid = row["company_id"]
            email = _placeholder_email(cid)
            name = (row.get("name") or "Salon grooming")[:200]
            city = (row.get("city") or "")[:120]
            org = name[:255]
            notes = _build_notes(row, stamp, edition)

            if dry:
                exists = StaffOnboardingLead.objects.filter(email=email).exists()
                self.stdout.write(
                    f"[dry-run] {'UPDATE' if exists else 'CREATE'} | {name[:55]} | {city} | id={cid}"
                )
                continue

            existing = StaffOnboardingLead.objects.filter(email=email).first()
            if existing:
                existing.display_name = name
                existing.org_display_name = org
                existing.company_legal_name = name[:255]
                existing.judet = city
                existing.oras = city
                existing.company_judet = city
                existing.company_oras = city
                existing.account_kind = StaffOnboardingLead.KIND_COLLAB
                existing.collaborator_subtype = StaffOnboardingLead.COLLAB_GROOMING
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
                self.stdout.write(self.style.SUCCESS(f"Actualizat | {city} | {name[:70]}"))
                continue

            StaffOnboardingLead.objects.create(
                created_by=None,
                email=email,
                phone="",
                display_name=name,
                org_display_name=org,
                username_suggested="",
                first_name="",
                last_name="",
                account_kind=StaffOnboardingLead.KIND_COLLAB,
                collaborator_subtype=StaffOnboardingLead.COLLAB_GROOMING,
                vet_prospect_kind="",
                judet=city,
                oras=city,
                company_legal_name=name[:255],
                company_cui="",
                company_cui_has_ro=False,
                company_reg_com="",
                company_address=f"Top100 Groomer — {city}"[:255] if city else "Top100 Groomer",
                company_representative="",
                company_judet=city,
                company_oras=city,
                is_public_shelter=False,
                segments=[],
                marketing_emails_requested=False,
                notes=notes,
                status=StaffOnboardingLead.ST_READY,
            )
            created += 1
            self.stdout.write(self.style.SUCCESS(f"Creat | {city} | {name[:70]}"))

        if dry:
            self.stdout.write(self.style.NOTICE("Simulare. Rulează cu --apply pentru a scrie în DB."))
        else:
            self.stdout.write(self.style.SUCCESS(f"Gata. Create: {created}, actualizate: {updated}."))
