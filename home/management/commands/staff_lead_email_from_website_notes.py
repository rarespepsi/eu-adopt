"""
Email de pe website-uri deja salvate în notes (ex. [GOOGLE_PLACES_PROBE … web=https://…]).
Fără Google Places API — doar HTTP către site.

  python manage.py staff_lead_email_from_website_notes --limit 50
  python manage.py staff_lead_email_from_website_notes --limit 1000 --apply
"""

from __future__ import annotations

import re
import time
from datetime import datetime, timezone
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email

# Import reutilizare scrape (fără apel Places)
from home.management.commands.staff_lead_google_places_probe import _fetch_website_email

PROBE_TAG = "[WEBSITE_EMAIL_FROM_NOTES"
_WEB_RE = re.compile(r"web=(https?://[^\s'\"—]+)", re.IGNORECASE)


def _urls_from_notes(notes: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in _WEB_RE.finditer(notes or ""):
        u = m.group(1).rstrip(".,;)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


class Command(BaseCommand):
    help = "Extrage email de pe URL-uri web= din notes (0 cost Google)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=500)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--force", action="store_true", help="Re-probează chiar dacă există tag în notes.")
        parser.add_argument("--sleep", type=float, default=0.4, help="Pauză secunde între request-uri HTTP.")

    def handle(self, *args: Any, **options: Any) -> None:
        limit = max(1, int(options["limit"]))
        apply_writes = bool(options["apply"])
        force = bool(options["force"])
        sleep_s = max(0.1, float(options["sleep"]))

        qs = StaffOnboardingLead.objects.filter(
            Q(email__iendswith="@lead-placeholder.invalid") | Q(email=""),
        ).filter(notes__regex=r"web=https?://")
        if not force:
            qs = qs.exclude(notes__contains=PROBE_TAG)

        leads = list(qs.order_by("pk")[:limit])
        if not leads:
            self.stdout.write(self.style.WARNING("Niciun lead cu web= în notes (sau deja procesat)."))
            return

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        found_n = err_n = skip_n = 0

        self.stdout.write(
            f"Procesez {len(leads)} lead-uri | apply={'DA' if apply_writes else 'NU'} | 0 USD Google"
        )

        for i, lead in enumerate(leads):
            urls = _urls_from_notes(lead.notes or "")
            if not urls:
                skip_n += 1
                continue

            email_new = None
            used_url = ""
            for url in urls:
                try:
                    email_new = _fetch_website_email(url)
                except Exception:
                    err_n += 1
                    continue
                if email_new:
                    used_url = url
                    break

            self.stdout.write(
                f"[{i+1}/{len(leads)}] pk={lead.pk} {lead.display_name[:45]!r} "
                f"url={used_url[:50] if used_url else '—'} -> {email_new or '—'}"
            )

            note_line = (
                f"{PROBE_TAG} {ts}] url={used_url or urls[0]!r} "
                f"email={email_new or '—'}"
            )

            if apply_writes:
                note = (lead.notes or "").strip()
                lead.notes = (note + "\n" + note_line if note else note_line)[:12000]
                upd = ["notes"]
                if email_new:
                    lead.email = email_new
                    upd.append("email")
                    found_n += 1
                lead.save(update_fields=upd)

            time.sleep(sleep_s)

        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. Procesate {len(leads)} | email găsite: {found_n} | "
                f"sărite fără URL: {skip_n} | erori: {err_n}"
                + (" (dry-run)" if not apply_writes else "")
            )
        )
