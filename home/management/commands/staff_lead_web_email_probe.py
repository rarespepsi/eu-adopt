"""
Probă: caută adrese de email pe web (DuckDuckGo) pentru prospecte StaffOnboardingLead
doar când emailul curent e gol sau e adresa provizorie @lead-placeholder.invalid.

Nu modifică lead-uri care au deja un email „real” (altul decât placeholder).

Exemplu (doar afișare, fără scriere în DB):
  python manage.py staff_lead_web_email_probe --limit 100

Probă cu scriere (max 100 lead-uri, ~2s pauză între căutări):
  python manage.py staff_lead_web_email_probe --limit 100 --apply

Opțional: --sleep 2.5  (secunde între interogări DDG)
"""

from __future__ import annotations

import re
import time
import warnings
from datetime import datetime, timezone
from urllib.parse import quote_plus

from django.core.management.base import BaseCommand
from django.db.models import Q

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email

_EMAIL_RE = re.compile(r"[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,24}")

# Domenii frecvent irelevante în snippet-uri SERP
_SKIP_EMAIL_SUBSTR = (
    "example.com",
    "example.org",
    "test.com",
    "localhost",
    "sentry.io",
    "w3.org",
    "schema.org",
    "googleusercontent.com",
    "gstatic.com",
    "facebook.com",
    "fbcdn.net",
    "instagram.com",
    "wikipedia.org",
    "cmvro.ro",
)

_SKIP_LOCAL = (
    "noreply",
    "no-reply",
    "donotreply",
    "do-not-reply",
    "mailer-daemon",
    "postmaster",
    "webmaster",
    "privacy",
    "abuse",
    "newsletter",
)


def _email_ok(addr: str) -> bool:
    a = (addr or "").strip().lower()
    if not a or ".." in a:
        return False
    if a.endswith(("@lead-placeholder.invalid",)):
        return False
    if any(x in a for x in _SKIP_EMAIL_SUBSTR):
        return False
    local = a.split("@", 1)[0]
    if local in _SKIP_LOCAL or local.startswith("img") or local.startswith("image"):
        return False
    bad_local = ("beispiel", "example", "sample", "demo")
    if any(b in local for b in bad_local):
        return False
    if local.startswith(("test", "demo")) and len(local) <= 12:
        return False
    return True


def _build_query(lead: StaffOnboardingLead) -> str:
    parts = []
    org = (lead.org_display_name or "").strip()
    disp = (lead.display_name or "").strip()
    if org and org.lower() != disp.lower():
        parts.append(org)
    elif disp:
        parts.append(disp)
    cui = (lead.company_cui or "").strip()
    if cui:
        parts.append(f"CUI {cui}")
    jud = (lead.judet or "").strip()
    if jud:
        parts.append(jud)
    addr = (lead.company_address or "").strip()
    if addr and len(addr) < 120:
        parts.append(addr)
    base = " ".join(parts) if parts else disp or "veterinar"
    return f'{base} contact email România'


def _extract_emails(text: str) -> list[str]:
    if not text:
        return []
    found = _EMAIL_RE.findall(text)
    out: list[str] = []
    seen: set[str] = set()
    for e in found:
        el = e.strip().lower()
        if el in seen or not _email_ok(el):
            continue
        seen.add(el)
        out.append(e.strip())
    return out


def _pick_email(snippets: list[str]) -> tuple[str | None, list[str]]:
    """Prima adresă acceptată în ordinea apariției în snippet-uri DDG."""
    all_candidates: list[str] = []
    for sn in snippets:
        for em in _extract_emails(sn):
            if em.lower() not in [x.lower() for x in all_candidates]:
                all_candidates.append(em)
    if not all_candidates:
        return None, []
    return all_candidates[0], all_candidates


class Command(BaseCommand):
    help = "Probă DDG: caută email pentru prospecte cu placeholder / email gol (nu atinge emailuri reale)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Număr maxim de lead-uri procesate.")
        parser.add_argument(
            "--apply",
            action="store_true",
            help="Scrie în DB: setează email dacă s-a găsit candidat + adaugă linie în notițe.",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=2.0,
            help="Pauză în secunde între căutări (comportament politicos față de DDG).",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Include și lead-uri care au deja o linie [WEB_EMAIL_PROBE] în notițe.",
        )

    def handle(self, *args, **options):
        try:
            warnings.filterwarnings(
                "ignore",
                message=".*renamed to.*ddgs",
                category=RuntimeWarning,
                module="duckduckgo_search",
            )
            from duckduckgo_search import DDGS
        except ImportError as e:
            self.stdout.write(self.style.ERROR("Lipsește pachetul duckduckgo-search. Rulează: pip install duckduckgo-search"))
            raise SystemExit(1) from e

        limit = max(1, int(options["limit"]))
        apply_writes = bool(options["apply"])
        sleep_s = max(0.5, float(options["sleep"]))
        force = bool(options["force"])

        qs = StaffOnboardingLead.objects.filter(
            Q(email__iendswith="@lead-placeholder.invalid") | Q(email=""),
        ).order_by("pk")
        if not force:
            qs = qs.exclude(notes__contains="[WEB_EMAIL_PROBE")

        leads = list(qs[:limit])
        if not leads:
            self.stdout.write(self.style.WARNING("Niciun lead eligibil (placeholder/gol, sau deja probat — folosește --force)."))
            return

        self.stdout.write(
            f"Lead-uri de procesat: {len(leads)} (apply={'DA' if apply_writes else 'NU, dry-run'}) sleep={sleep_s}s"
        )
        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        found_n = 0
        err_n = 0

        for i, lead in enumerate(leads):
            em_before = (lead.email or "").strip()
            if em_before and not is_placeholder_lead_email(em_before):
                self.stdout.write(self.style.WARNING(f"skip pk={lead.pk} (email real neașteptat în queryset)"))
                continue

            query = _build_query(lead)
            snippets: list[str] = []
            try:
                with DDGS() as ddgs:
                    for r in ddgs.text(query, max_results=10) or []:
                        if isinstance(r, dict):
                            snippets.append((r.get("title") or "") + " " + (r.get("body") or ""))
            except Exception as ex:
                err_n += 1
                self.stdout.write(self.style.ERROR(f"pk={lead.pk} DDG err: {ex}"))
                time.sleep(sleep_s)
                continue

            chosen, candidates = _pick_email(snippets)
            gurl = "https://duckduckgo.com/?q=" + quote_plus(query)
            note_line = (
                f"[WEB_EMAIL_PROBE {ts}] query={query!r} "
                f"candidat={chosen or '—'} "
                f"altele={candidates[:5]!r} "
                f"ddg={gurl}"
            )

            self.stdout.write(f"[{i+1}/{len(leads)}] pk={lead.pk} {lead.display_name[:50]!r} -> {chosen or 'NIMIC'}")

            if apply_writes:
                note = (lead.notes or "").strip()
                if note:
                    note = note + "\n" + note_line
                else:
                    note = note_line
                if len(note) > 12000:
                    note = note[-11900:] + "\n…(notă trunchiată)\n" + note_line

                update_fields: list[str] = ["notes"]
                if chosen:
                    lead.email = chosen[:254]
                    update_fields.append("email")
                    found_n += 1
                lead.notes = note
                lead.save(update_fields=update_fields)

            time.sleep(sleep_s)

        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. Procesate {len(leads)} | email setate (apply): {found_n} | erori DDG: {err_n}"
            )
        )
