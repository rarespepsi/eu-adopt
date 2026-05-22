"""
Enrichment email GRATUIT (fără Google Places pentru email).

Ordine: website (home + contact) → Facebook/DDG → Bing.
Cache domeniu în notes. Places API nu e apelat.

  python manage.py staff_lead_free_email_enrich --limit 20
  python manage.py staff_lead_free_email_enrich --limit 500 --apply
  python manage.py staff_lead_free_email_enrich --limit 100 --apply --website-only
"""

from __future__ import annotations

import json
import random
import time
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.core.management.base import BaseCommand
from django.db.models import Q

from home.contact_enrichment import (
    ENRICH_TAG,
    PLACES_SEARCH_COST_USD,
    cache_line,
    domain_from_url,
    enrich_lead_free,
    enrich_note_line,
    urls_from_notes,
)
from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email as _is_ph

CHECKPOINT_EVERY = 50
CHECKPOINT_PATH = Path("database/exports/free_email_enrich_checkpoint.json")


class Command(BaseCommand):
    help = "Email enrichment gratuit: site, contact, Facebook, DDG, Bing (0 Places)."

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100)
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--force", action="store_true", help="Re-rulează chiar dacă există FREE_EMAIL_ENRICH.")
        parser.add_argument(
            "--website-only",
            action="store_true",
            help="Doar scrape website (fără DDG/Bing/Facebook search).",
        )
        parser.add_argument(
            "--no-website-priority",
            action="store_true",
            help="Nu prioritiza lead-uri cu web= în notes.",
        )
        parser.add_argument("--sleep", type=float, default=None, help="Pauză fixă; implicit random 0.2–0.5.")

    def handle(self, *args: Any, **options: Any) -> None:
        limit = max(1, int(options["limit"]))
        apply_writes = bool(options["apply"])
        force = bool(options["force"])
        website_only = bool(options.get("website_only"))
        fixed_sleep = options.get("sleep")

        qs = StaffOnboardingLead.objects.filter(
            Q(email__iendswith="@lead-placeholder.invalid") | Q(email=""),
        )
        if not force:
            qs = qs.exclude(notes__contains=ENRICH_TAG)

        if not options.get("no_website_priority"):
            with_web = qs.filter(notes__regex=r"web=https?://").order_by("pk")[:limit]
            leads = list(with_web)
            if len(leads) < limit:
                rest = limit - len(leads)
                ids = [l.pk for l in leads]
                extra = list(qs.exclude(pk__in=ids).order_by("pk")[:rest])
                leads.extend(extra)
        else:
            leads = list(qs.order_by("pk")[:limit])

        if not leads:
            self.stdout.write(self.style.WARNING("Niciun lead eligibil."))
            return

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        stats = {
            "processed": 0,
            "emails_found": 0,
            "websites_used": 0,
            "phones_found": 0,
            "skipped_cached": 0,
            "places_calls_saved": 0,
        }
        global_domain_cache: dict[str, str] = {}

        self.stdout.write(
            f"Procesez {len(leads)} | apply={'DA' if apply_writes else 'NU'} | "
            f"mod={'website-only' if website_only else 'full'} | 0 USD Google Places"
        )

        for i, lead in enumerate(leads):
            em_before = (lead.email or "").strip()
            if em_before and not _is_ph(em_before):
                continue

            sites = urls_from_notes(lead.notes or "")
            if sites:
                stats["websites_used"] += 1

            result = enrich_lead_free(
                lead,
                use_ddg=not website_only,
                use_bing=not website_only,
                use_facebook=not website_only,
                domain_cache=global_domain_cache,
            )

            if result.cache_hit:
                stats["skipped_cached"] += 1
            if result.email:
                stats["emails_found"] += 1
                stats["places_calls_saved"] += 1
            if result.phone:
                stats["phones_found"] += 1

            self.stdout.write(
                f"[{i+1}/{len(leads)}] pk={lead.pk} {lead.display_name[:40]!r} "
                f"steps={','.join(result.steps) or '—'} "
                f"email={result.email or '—'} conf={result.confidence or '—'}"
            )

            if apply_writes:
                note = (lead.notes or "").strip()
                lines = [enrich_note_line(result, ts)]
                for site in sites[:1]:
                    dom = domain_from_url(site)
                    if dom and dom in global_domain_cache:
                        lines.append(
                            cache_line(dom, global_domain_cache[dom])
                        )
                lead.notes = (note + "\n" + "\n".join(lines) if note else "\n".join(lines))[:14000]
                upd = ["notes"]
                if result.email:
                    lead.email = result.email
                    upd.append("email")
                if result.phone and not (lead.phone or "").strip():
                    lead.phone = result.phone
                    upd.append("phone")
                lead.save(update_fields=upd)

            stats["processed"] += 1

            if stats["processed"] % CHECKPOINT_EVERY == 0:
                stats["money_saved_usd"] = round(
                    stats["places_calls_saved"] * PLACES_SEARCH_COST_USD, 2
                )
                CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
                CHECKPOINT_PATH.write_text(
                    json.dumps({**stats, "last_pk": lead.pk}, indent=2),
                    encoding="utf-8",
                )

            self._sleep(fixed_sleep)

        money_saved = round(stats["places_calls_saved"] * PLACES_SEARCH_COST_USD, 2)
        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. Procesate {stats['processed']} | emailuri: {stats['emails_found']} | "
                f"site-uri folosite: {stats['websites_used']} | telefoane noi: {stats['phones_found']} | "
                f"cache skip: {stats['skipped_cached']} | Places evitate (est.): "
                f"{stats['places_calls_saved']} (~${money_saved} USD)"
                + (" dry-run" if not apply_writes else "")
            )
        )

    def _sleep(self, fixed: float | None) -> None:
        if fixed is not None:
            time.sleep(max(0.1, float(fixed)))
        else:
            time.sleep(random.uniform(0.2, 0.5))
