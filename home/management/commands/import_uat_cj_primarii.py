"""
Importă prospecte CJ + primării în StaffOnboardingLead (Add USER).

  python manage.py import_uat_cj_primarii --dry-run
  python manage.py import_uat_cj_primarii --apply
"""
from __future__ import annotations

import csv
import re
from pathlib import Path

from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand

from home.models import StaffOnboardingLead
from home.ro_location import normalize_lead_location_kwargs
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX, _placeholder_email_for_csv_row

DEFAULT_DIR = Path("database/exports/prospectare_cj_primarii_20260817")


def _first_email(raw: str) -> str:
    text = (raw or "").replace(";", "|")
    for part in text.split("|"):
        p = part.strip().lower()
        if "@" in p and " " not in p.strip():
            return p[:254]
        m = re.search(r"[A-Z0-9._%+\-]+@[A-Z0-9.\-]+\.[A-Z]{2,}", part, re.I)
        if m:
            return m.group(0).lower()[:254]
    return ""


def _first_phone(raw: str) -> str:
    digits = re.findall(r"(?:\+?4?0|0)[\d\s./\-]{8,16}\d", raw or "")
    if not digits:
        compact = re.sub(r"\D", "", raw or "")
        if len(compact) >= 10:
            return compact[-10:][:40]
        return ""
    cleaned = re.sub(r"[^\d+]", "", digits[0])
    return cleaned[:40]


def _is_bucuresti(judet: str) -> bool:
    j = (judet or "").lower()
    return "bucure" in j or j.strip() in {"b", "sector", "ilfov-bucuresti"}


def classify_cj(judet: str) -> str:
    if _is_bucuresti(judet):
        return StaffOnboardingLead.UAT_PMB
    return StaffOnboardingLead.UAT_CJ


def classify_primarie(localitate: str, judet: str) -> str:
    loc = (localitate or "").upper()
    if _is_bucuresti(judet) and (
        "MUNICIPIUL BUCURE" in loc or loc.strip() in {"BUCURESTI", "BUCUREȘTI", "BUCUREŞTI"}
    ):
        return StaffOnboardingLead.UAT_PMB
    if loc.startswith("MUNICIPIUL") or loc.startswith("MUNICIPIU") or "SECTOR" in loc:
        return StaffOnboardingLead.UAT_MUNICIPIU
    if loc.startswith("ORAS") or loc.startswith("ORAȘ") or loc.startswith("ORAŞ") or loc.startswith("ORAŞ"):
        return StaffOnboardingLead.UAT_ORAS
    return StaffOnboardingLead.UAT_COMUNA


def _clean_localitate_name(localitate: str) -> str:
    t = (localitate or "").strip()
    for prefix in ("MUNICIPIUL ", "MUNICIPIU ", "ORAS ", "ORAȘ ", "ORAŞ ", "COMUNA "):
        if t.upper().startswith(prefix):
            t = t[len(prefix) :].strip()
            break
    return t


class Command(BaseCommand):
    help = "Importă CJ + primării ca prospecte Adăpost public (categorie UAT)."

    def add_arguments(self, parser):
        parser.add_argument("--dir", default=str(DEFAULT_DIR), help="Folder CSV sursă")
        parser.add_argument("--apply", action="store_true", help="Scrie în baza de date")
        parser.add_argument("--username", default="", help="created_by (implicit: rares / superuser)")

    def handle(self, *args, **options):
        base = Path(options["dir"]).expanduser()
        cj_path = base / "01_consilii_judetene.csv"
        prim_path = base / "03_primarii_toate_uat.csv"
        if not cj_path.exists() or not prim_path.exists():
            self.stderr.write(f"Lipsesc CSV-urile în {base}")
            return

        User = get_user_model()
        user = None
        un = (options.get("username") or "").strip()
        if un:
            user = User.objects.filter(username=un).first()
        if user is None:
            user = (
                User.objects.filter(username__iexact="rares", is_staff=True).first()
                or User.objects.filter(is_superuser=True).first()
            )
        apply = bool(options.get("apply"))
        rows = []
        rows.extend(self._cj_rows(cj_path))
        rows.extend(self._prim_rows(prim_path))

        created = 0
        skipped_dup = 0
        placeholders = 0
        seen_emails: set[str] = set()
        line_no = 1
        for payload in rows:
            line_no += 1
            email = (payload.get("email") or "").strip().lower()
            if not email:
                payload["email"] = _placeholder_email_for_csv_row(line_no)
                placeholders += 1
                email = payload["email"].lower()
            if email in seen_emails:
                skipped_dup += 1
                continue
            seen_emails.add(email)
            exists = StaffOnboardingLead.objects.filter(email__iexact=email).exists()
            if exists and not email.endswith(PLACEHOLDER_EMAIL_SUFFIX):
                skipped_dup += 1
                continue
            if apply:
                StaffOnboardingLead.objects.create(created_by=user, **payload)
            created += 1

        verb = "creat" if apply else "de creat (dry-run)"
        self.stdout.write(
            f"{verb}: {created} · duplicate/sărite: {skipped_dup} · fără email (placeholder): {placeholders}\n"
            f"surse: {cj_path.name} + {prim_path.name}"
        )

    def _cj_rows(self, path: Path) -> list[dict]:
        out = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                judet = (row.get("judet") or "").strip()
                email = _first_email(row.get("email_general_recomandat") or row.get("emailuri") or "")
                phone = _first_phone(row.get("telefoane") or "")
                cat = classify_cj(judet)
                if cat == StaffOnboardingLead.UAT_PMB:
                    org = "Primăria Municipiului București"
                    loc = "București"
                else:
                    org = f"Consiliul Județean {judet}"
                    loc = judet
                out.append(self._lead_payload(email, phone, judet, loc, org, cat, "CJ listă 2026-08-17"))
        return out

    def _prim_rows(self, path: Path) -> list[dict]:
        out = []
        with path.open(encoding="utf-8-sig", newline="") as f:
            for row in csv.DictReader(f):
                judet = (row.get("judet") or "").strip()
                loc_raw = (row.get("localitate") or "").strip()
                email = _first_email(row.get("email_general") or row.get("email_registratura") or "")
                phone = _first_phone(row.get("telefon") or "")
                cat = classify_primarie(loc_raw, judet)
                loc = _clean_localitate_name(loc_raw)
                if cat == StaffOnboardingLead.UAT_PMB:
                    org = "Primăria Municipiului București"
                else:
                    org = f"Primăria {loc or loc_raw}"
                addr = (row.get("adresa") or "").replace("\n", ", ")[:255]
                out.append(
                    self._lead_payload(
                        email,
                        phone,
                        judet,
                        loc,
                        org,
                        cat,
                        "primării geo-spatial.org dec 2020",
                        address=addr,
                    )
                )
        return out

    def _lead_payload(
        self,
        email: str,
        phone: str,
        judet: str,
        loc: str,
        org: str,
        cat: str,
        note: str,
        address: str = "",
    ) -> dict:
        payload = {
            "email": email,
            "phone": phone[:40],
            "display_name": org[:200],
            "org_display_name": org[:255],
            "company_legal_name": org[:255],
            "company_address": address,
            "account_kind": StaffOnboardingLead.KIND_ADAPOST,
            "collaborator_subtype": StaffOnboardingLead.COLLAB_ADPUB,
            "is_public_shelter": True,
            "uat_category": cat,
            "judet": judet[:120],
            "oras": loc[:120],
            "notes": note[:5000],
            "status": StaffOnboardingLead.ST_READY,
            "invite_mail_status": StaffOnboardingLead.INVITE_NEVER,
        }
        return normalize_lead_location_kwargs(payload)
