"""
Completează telefon (+ opțional email de pe site) pentru prospecte StaffOnboardingLead
folosind Google Places API (New) — cheie server: EUADOPT_GOOGLE_PLACES_SERVER_API_KEY.

Cost control (implicit):
- Google Places DOAR dacă telefonul e gol (nu reinterogăm doar pentru email).
- Nu suprascrie email „real” (non-placeholder) sau telefon existent (decât --force-phone).
- Marchează lead-uri probate în notes; fără --force nu reprobează.
- Email DOAR de pe website (Places → websiteUri → scrape); nu din Places/DDG snippet.

Exemplu:
  python manage.py staff_lead_google_places_probe --subtype grooming --limit 20
  python manage.py staff_lead_google_places_probe --subtype grooming --limit 500 --apply --fetch-email-from-website
"""

from __future__ import annotations

import json
import random
import re
import time
import warnings
import urllib.error
import urllib.request
from datetime import datetime, timezone
from pathlib import Path
from typing import Any

from django.conf import settings
from django.core.management.base import BaseCommand, CommandError
from django.db.models import Q

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email

PLACES_SEARCH_URL = "https://places.googleapis.com/v1/places:searchText"
_FIELD_MASK = (
    "places.id,places.displayName,places.formattedAddress,"
    "places.nationalPhoneNumber,places.internationalPhoneNumber,places.websiteUri"
)

# Text Search (New) — ajustează după factura ta Google Cloud (SKU / volum).
PLACES_SEARCH_COST_USD = 0.032

CHECKPOINT_EVERY = 50
CHECKPOINT_PATH = Path("database/exports/places_probe_checkpoint.json")

_EMAIL_RE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,24}"
)
_PHONE_RO_RE = re.compile(
    r"(?<!\d)(?:\+40\s?)?(?:0\d{9,10}|7\d{8,9})(?:\s*/\s*0?\d{6,12})?(?!\d)"
)

_SKIP_EMAIL_SUBSTR = (
    "example.com",
    "wix.com",
    "sentry.io",
    "facebook.com",
    "instagram.com",
    "google.com",
    "gstatic.com",
    "w3.org",
)


def _norm_phone(raw: str | None) -> str:
    if not raw:
        return ""
    t = re.sub(r"[\s().-]", "", (raw or "").strip())
    if t.startswith("+40"):
        t = "0" + t[3:]
    elif t.startswith("40") and len(t) >= 11:
        t = "0" + t[2:]
    digits = re.sub(r"\D", "", t)
    if len(digits) < 9:
        return ""
    if digits.startswith("40") and len(digits) >= 11:
        digits = "0" + digits[2:]
    if not digits.startswith("0"):
        return ""
    return digits[:40]


def _build_text_query(lead: StaffOnboardingLead) -> str:
    name = (lead.display_name or lead.org_display_name or "").strip()
    loc = (lead.oras or lead.judet or lead.company_oras or lead.company_judet or "").strip()
    parts = [name, loc, "România"]
    return " ".join(p for p in parts if p)


def _email_ok(addr: str) -> bool:
    a = (addr or "").strip().lower()
    if not a or ".." in a or a.endswith("@lead-placeholder.invalid"):
        return False
    if any(x in a for x in _SKIP_EMAIL_SUBSTR):
        return False
    local = a.split("@", 1)[0]
    if local.startswith(("test", "demo", "example")):
        return False
    return True


def _extract_emails_from_html(html: str) -> list[str]:
    found = _EMAIL_RE.findall(html or "")
    out: list[str] = []
    seen: set[str] = set()
    for e in found:
        el = e.strip().lower()
        if el in seen or not _email_ok(el):
            continue
        seen.add(el)
        out.append(e.strip())
    return out


class PlacesApiError(Exception):
    def __init__(self, code: int, message: str, referrer_blocked: bool = False):
        super().__init__(message)
        self.code = code
        self.referrer_blocked = referrer_blocked


def _places_search(api_key: str, text_query: str, timeout: int = 25) -> dict[str, Any] | None:
    body = json.dumps(
        {
            "textQuery": text_query,
            "regionCode": "RO",
            "languageCode": "ro",
            "maxResultCount": 1,
        },
        ensure_ascii=False,
    ).encode("utf-8")
    req = urllib.request.Request(
        PLACES_SEARCH_URL,
        data=body,
        headers={
            "Content-Type": "application/json",
            "X-Goog-Api-Key": api_key,
            "X-Goog-FieldMask": _FIELD_MASK,
        },
        method="POST",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            data = json.loads(resp.read().decode("utf-8", errors="replace"))
    except urllib.error.HTTPError as e:
        err_body = e.read().decode("utf-8", errors="replace")[:800]
        blocked = "REFERRER_BLOCKED" in err_body or "referer" in err_body.lower()
        raise PlacesApiError(e.code, err_body, referrer_blocked=blocked) from e
    places = data.get("places") or []
    if not places:
        return None
    p0 = places[0]
    disp = p0.get("displayName") or {}
    return {
        "source": "google_places",
        "confidence": "high",
        "name": (disp.get("text") if isinstance(disp, dict) else str(disp)) or "",
        "address": (p0.get("formattedAddress") or "").strip(),
        "phone": _norm_phone(
            p0.get("nationalPhoneNumber") or p0.get("internationalPhoneNumber") or ""
        ),
        "website": (p0.get("websiteUri") or "").strip(),
        "place_id": (p0.get("id") or "").strip(),
        "source_url": PLACES_SEARCH_URL,
    }


def _places_search_with_retry(
    api_key: str, text_query: str, retries: int = 3, base_sleep: float = 1.0
) -> tuple[dict[str, Any] | None, int, PlacesApiError | None]:
    """Returnează (place, api_calls, last_error)."""
    last_err: PlacesApiError | None = None
    calls = 0
    for attempt in range(retries):
        try:
            calls += 1
            return _places_search(api_key, text_query), calls, None
        except PlacesApiError as ex:
            last_err = ex
            if attempt + 1 >= retries:
                break
            time.sleep(base_sleep * (2**attempt))
        except Exception:
            if attempt + 1 >= retries:
                break
            time.sleep(base_sleep * (2**attempt))
    return None, calls, last_err


def _ddg_contact_search(query: str) -> dict[str, Any] | None:
    """Fallback telefon când Places e blocat — fără email din snippet (cost/reguli)."""
    try:
        warnings.filterwarnings(
            "ignore",
            message=".*renamed to.*ddgs",
            category=RuntimeWarning,
            module="duckduckgo_search",
        )
        from duckduckgo_search import DDGS
    except ImportError:
        return None
    snippets: list[str] = []
    with DDGS() as ddgs:
        for r in ddgs.text(query + " telefon contact România", max_results=8) or []:
            if isinstance(r, dict):
                snippets.append((r.get("title") or "") + " " + (r.get("body") or ""))
    blob = " ".join(snippets)
    phones: list[str] = []
    for m in _PHONE_RO_RE.finditer(blob):
        p = _norm_phone(m.group(0))
        if p and p not in phones:
            phones.append(p)
    return {
        "source": "duckduckgo",
        "confidence": "low",
        "name": "",
        "address": "",
        "phone": phones[0] if phones else "",
        "website": "",
        "place_id": "",
        "source_url": "duckduckgo:text",
    }


def _fetch_website_email(url: str, timeout: int = 12) -> str | None:
    if not url or not url.startswith("http"):
        return None
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; EU-Adopt contact-probe/1.0)"},
        method="GET",
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text" not in ctype:
                return None
            html = resp.read(350_000).decode("utf-8", errors="replace")
    except Exception:
        return None
    emails = _extract_emails_from_html(html)
    for em in emails:
        if _email_ok(em):
            return em[:254].lower()
    return None


def _eligible_places_queryset(subtype: str, force: bool):
    """Places API: doar lead-uri fără telefon (și neprobabile, dacă nu --force)."""
    qs = StaffOnboardingLead.objects.filter(phone="")
    if subtype:
        qs = qs.filter(collaborator_subtype=subtype)
    if not force:
        qs = qs.exclude(notes__contains="[GOOGLE_PLACES_PROBE")
    return qs.order_by("pk")


def _write_checkpoint(stats: dict[str, Any]) -> None:
    CHECKPOINT_PATH.parent.mkdir(parents=True, exist_ok=True)
    payload = {**stats, "saved_at": datetime.now(timezone.utc).isoformat()}
    CHECKPOINT_PATH.write_text(json.dumps(payload, ensure_ascii=False, indent=2), encoding="utf-8")


class Command(BaseCommand):
    help = (
        "Google Places (doar telefon lipsă): telefon + opțional email de pe site. "
        "Cost control: fără apel Places dacă telefonul există deja."
    )

    def add_arguments(self, parser):
        parser.add_argument("--limit", type=int, default=100, help="Max lead-uri procesate.")
        parser.add_argument("--apply", action="store_true", help="Scrie în DB.")
        parser.add_argument(
            "--subtype",
            default="",
            help="Filtru collaborator_subtype (ex. grooming, transport, magazin). Gol = toate.",
        )
        parser.add_argument(
            "--fetch-email-from-website",
            action="store_true",
            help="Dacă Places dă website și emailul e placeholder, caută email pe homepage.",
        )
        parser.add_argument(
            "--force-phone",
            action="store_true",
            help="Rescrie telefonul chiar dacă există deja.",
        )
        parser.add_argument(
            "--force",
            action="store_true",
            help="Re-probează și dacă există deja [GOOGLE_PLACES_PROBE] în notițe.",
        )
        parser.add_argument(
            "--sleep",
            type=float,
            default=None,
            help="Pauză fixă secunde între lead-uri. Implicit: random 0.1–0.3.",
        )
        parser.add_argument(
            "--ddg-fallback",
            action="store_true",
            default=True,
            help="Dacă Places e blocat (referrer), folosește DuckDuckGo pentru telefon.",
        )
        parser.add_argument(
            "--no-ddg-fallback",
            action="store_false",
            dest="ddg_fallback",
            help="Nu folosi DuckDuckGo când Places eșuează.",
        )
        parser.add_argument(
            "--legacy-eligibility",
            action="store_true",
            help="(Deprecated) Include și lead-uri cu telefon dar email placeholder — cost mare.",
        )

    def handle(self, *args: Any, **options: Any) -> None:
        api_key = (getattr(settings, "GOOGLE_PLACES_SERVER_API_KEY", "") or "").strip()
        if not api_key:
            raise CommandError(
                "Lipsește EUADOPT_GOOGLE_PLACES_SERVER_API_KEY în .env (cheie server, fără referrer)."
            )

        limit = max(1, int(options["limit"]))
        apply_writes = bool(options["apply"])
        subtype = (options.get("subtype") or "").strip().lower()
        fetch_web_email = bool(options.get("fetch_email_from_website"))
        force_phone = bool(options.get("force_phone"))
        force = bool(options.get("force"))
        ddg_fallback = bool(options.get("ddg_fallback"))
        fixed_sleep = options.get("sleep")
        legacy = bool(options.get("legacy_eligibility"))
        places_blocked_warned = False

        if legacy:
            qs = StaffOnboardingLead.objects.filter(
                Q(email__iendswith="@lead-placeholder.invalid")
                | Q(email="")
                | Q(phone="")
            )
            if subtype:
                qs = qs.filter(collaborator_subtype=subtype)
            if not force:
                qs = qs.exclude(notes__contains="[GOOGLE_PLACES_PROBE")
            qs = qs.order_by("pk")
            self.stdout.write(
                self.style.WARNING(
                    "--legacy-eligibility: apel Places și pentru lead-uri cu telefon (cost mare)."
                )
            )
        else:
            qs = _eligible_places_queryset(subtype, force)

        leads = list(qs[:limit])
        if not leads:
            self.stdout.write(
                self.style.WARNING(
                    "Niciun lead eligibil (telefon gol + neprobat). "
                    "Pentru doar email: staff_lead_web_email_probe sau scrape din notes."
                )
            )
            return

        skipped_has_phone = 0
        if not legacy:
            skipped_has_phone = (
                StaffOnboardingLead.objects.filter(~Q(phone=""))
                .exclude(notes__contains="[GOOGLE_PLACES_PROBE")
                .filter(
                    Q(email__iendswith="@lead-placeholder.invalid") | Q(email="")
                )
            )
            if subtype:
                skipped_has_phone = skipped_has_phone.filter(collaborator_subtype=subtype)
            skipped_has_phone = skipped_has_phone.count()

        self.stdout.write(
            f"Procesez {len(leads)} lead-uri (Places: telefon gol) | apply={'DA' if apply_writes else 'NU'} | "
            f"subtype={subtype or 'toate'} | email-from-site={'DA' if fetch_web_email else 'NU'} | "
            f"sărite (au telefon, lipsă email): ~{skipped_has_phone}"
        )

        ts = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        stats: dict[str, Any] = {
            "processed": 0,
            "phones_found": 0,
            "emails_found": 0,
            "api_calls": 0,
            "errors": 0,
            "completed": 0,
            "last_pk": None,
        }

        for i, lead in enumerate(leads):
            query = _build_text_query(lead)
            place: dict[str, Any] | None = None
            api_calls_this = 0

            if not (lead.phone or "").strip() or force_phone:
                place, api_calls_this, places_err = _places_search_with_retry(api_key, query)
                stats["api_calls"] += api_calls_this
                if place is None and places_err is not None:
                    if places_err.referrer_blocked and ddg_fallback:
                        if not places_blocked_warned:
                            places_blocked_warned = True
                            self.stdout.write(
                                self.style.WARNING(
                                    "Places API blocat pe server — fallback DuckDuckGo (doar telefon)."
                                )
                            )
                        place = _ddg_contact_search(query)
                    else:
                        stats["errors"] += 1
                        self.stdout.write(
                            self.style.ERROR(f"pk={lead.pk} Places {places_err.code}: {places_err}")
                        )
                        stats["processed"] += 1
                        self._sleep_between(fixed_sleep)
                        continue
            else:
                stats["processed"] += 1
                continue

            phone_new = ""
            email_new = None
            website = ""
            place_name = ""
            src = ""
            confidence = ""
            source_url = ""
            if place:
                src = place.get("source") or "google_places"
                confidence = place.get("confidence") or (
                    "high" if src == "google_places" else "low"
                )
                phone_new = place.get("phone") or ""
                website = place.get("website") or ""
                place_name = place.get("name") or ""
                source_url = place.get("source_url") or ""

            em_before = (lead.email or "").strip()
            can_set_email = not em_before or is_placeholder_lead_email(em_before)
            email_src = ""
            if fetch_web_email and can_set_email and website:
                email_new = _fetch_website_email(website)
                if email_new:
                    email_src = "website_scrape"
                    confidence = "medium" if confidence != "high" else confidence

            note_line = (
                f"[GOOGLE_PLACES_PROBE {ts}] src={src} conf={confidence} "
                f"q={query!r} place={place_name!r} phone={phone_new or '—'} "
                f"web={website or '—'} email={email_new or '—'} "
                f"email_src={email_src or '—'} src_url={source_url or '—'}"
            )

            self.stdout.write(
                f"[{i+1}/{len(leads)}] pk={lead.pk} {lead.display_name[:45]!r} "
                f"tel={phone_new or '—'} email={email_new or '—'}"
            )

            if apply_writes:
                upd: list[str] = []
                note = (lead.notes or "").strip()
                lead.notes = (note + "\n" + note_line if note else note_line)[:12000]
                upd.append("notes")

                ph_old = (lead.phone or "").strip()
                if phone_new and (force_phone or not ph_old):
                    lead.phone = phone_new
                    upd.append("phone")
                    stats["phones_found"] += 1

                if email_new and can_set_email:
                    lead.email = email_new
                    upd.append("email")
                    stats["emails_found"] += 1

                lead.save(update_fields=upd)
                if phone_new or email_new:
                    stats["completed"] += 1
            else:
                if phone_new:
                    stats["phones_found"] += 1
                if email_new:
                    stats["emails_found"] += 1

            stats["processed"] += 1
            stats["last_pk"] = lead.pk

            if stats["processed"] % CHECKPOINT_EVERY == 0:
                stats["cost_est_usd"] = round(stats["api_calls"] * PLACES_SEARCH_COST_USD, 4)
                _write_checkpoint(stats)
                self.stdout.write(
                    self.style.NOTICE(
                        f"Checkpoint {stats['processed']} | last_pk={lead.pk} | "
                        f"API calls={stats['api_calls']}"
                    )
                )

            self._sleep_between(fixed_sleep)

        stats["cost_est_usd"] = round(stats["api_calls"] * PLACES_SEARCH_COST_USD, 4)
        _write_checkpoint(stats)

        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. Procesate {stats['processed']} | completate (tel/email): {stats['completed']} | "
                f"telefoane: {stats['phones_found']} | emailuri site: {stats['emails_found']} | "
                f"apeluri Places: {stats['api_calls']} | cost est. ~${stats['cost_est_usd']} USD | "
                f"sărite (au telefon, email lipsă): ~{skipped_has_phone} | erori: {stats['errors']}"
                + (" (apply=NU, dry-run)" if not apply_writes else "")
            )
        )

    def _sleep_between(self, fixed_sleep: float | None) -> None:
        if fixed_sleep is not None:
            time.sleep(max(0.05, float(fixed_sleep)))
        else:
            time.sleep(random.uniform(0.1, 0.3))
