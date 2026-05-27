"""
Hotel / pensiune / cazare canină (pet) per județ — DDG + Bing, gratuit.

Tip colaborator: servicii | segment: hotel_pensiune_pet

  python manage.py import_pet_hotel_pensiune_ddg_by_judet --judet CJ --apply
  python manage.py import_pet_hotel_pensiune_ddg_by_judet --apply --max-per-judet 8
"""

from __future__ import annotations

import hashlib
import re
import time
import warnings
from datetime import datetime, timezone
from typing import Any

from django.core.management.base import BaseCommand

from home.contact_enrichment import PHONE_RO_RE, email_ok, norm_phone
from home.management.commands.import_grooming_ddg_by_judet import (
    JUDETE_RO,
    ORASE_EXTRA,
    _bing_search,
    _ddg_search,
    _norm_key,
    _strip_d,
)
from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX

_PET_KW = (
    "hotel canin",
    "pensiune canin",
    "cazare caini",
    "cazare câini",
    "cazare animale",
    "pet hotel",
    "dog hotel",
    "boarding",
    "canis hotel",
    "motel animale",
    "resort canin",
)

_BUSINESS_WORDS = (
    "hotel",
    "pensiune",
    "cazare",
    "boarding",
    "motel",
    "resort",
    "canin",
    "câini",
    "caini",
    "pet",
    "animale",
    "dog",
)

_SKIP_TITLE = (
    "wikipedia",
    "booking.com",
    "tripadvisor",
    "top 10",
    "cele mai",
    "blog",
    "forum",
    "youtube",
    "olx",
    "emag",
    "anunt",
    "job",
    "outlook",
    "microsoft",
    "sign in",
    "login",
)

_SKIP_HREF = (
    "booking.com",
    "tripadvisor.com",
    "wikipedia.",
    "facebook.com/login",
    "facebook.com/recover",
    "facebook.com/help",
    "facebook.com/policies",
    "youtube.com",
)

_FB_SKIP_PATH = (
    "/login",
    "/recover",
    "/help/",
    "/policies",
    "/watch",
    "/share",
    "/groups/",
    "/events/",
    "/marketplace",
    "/photo.php",
    "/story.php",
    "/photos/",
    "/videos/",
    "/reel/",
)


def _normalize_facebook_url(href: str) -> str:
    m = re.match(r"(https?://(?:www\.)?facebook\.com/[^/?#]+)", href.strip(), re.I)
    if m:
        return m.group(1).rstrip("/")
    return href.split("?")[0].rstrip("/")


def _is_facebook_page(href: str) -> bool:
    h = (href or "").lower()
    return "facebook.com" in h or "fb.com" in h


def _facebook_slug_name(href: str) -> str:
    m = re.search(r"(?:facebook|fb)\.com/(?:pages/[^/]+/(\d+)|profile\.php\?id=(\d+)|([^/?#]+))", href, re.I)
    if not m:
        return ""
    slug = (m.group(3) or "").strip()
    if not slug or slug.lower() in (
        "pages",
        "people",
        "watch",
        "groups",
        "events",
        "marketplace",
        "share",
        "login",
    ):
        return ""
    name = re.sub(r"[-_.]+", " ", slug).strip()
    if len(name) < 4:
        return ""
    low = name.lower()
    pet = ("canin", "cain", "hotel", "pensiune", "cazare", "pet", "animale", "dog", "boarding", "canis", "k9")
    if not any(p in low for p in pet):
        return ""
    return name[:200].title() if name.islower() else name[:200]


def _title_to_name(title: str, *, allow_facebook: bool = False) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    for sep in ("|", " - ", " – ", " — ", ":"):
        if sep in t:
            t = t.split(sep, 1)[0].strip()
    if len(t) < 4 or len(t) > 120:
        return ""
    low = t.lower()
    if any(x in low for x in _SKIP_TITLE):
        return ""
    if not any(w in low for w in _BUSINESS_WORDS):
        if not (allow_facebook and "facebook" in low):
            return ""
    return t[:200]


def _extract_facebook(
    results: list[dict[str, str]], jname: str, capital: str, city: str = ""
) -> list[dict[str, str]]:
    """Pagini Facebook din site:facebook.com … (DDG/Bing)."""
    from home.contact_enrichment import EMAIL_RE

    seen: set[str] = set()
    out: list[dict[str, str]] = []
    loc = {_norm_key(jname), _norm_key(capital), _norm_key(city or capital)}

    for r in results:
        href = (r.get("href") or "").strip()
        if not _is_facebook_page(href):
            continue
        if any(p in href.lower() for p in _FB_SKIP_PATH):
            continue
        href = _normalize_facebook_url(href)
        title = r["title"]
        blob = (title + " " + r["body"]).lower()
        slug_name = _facebook_slug_name(href)
        if not _pet_relevant(blob) and not slug_name:
            continue
        loc_hit = any(tok and tok in _norm_key(blob) for tok in loc)
        if not loc_hit and not slug_name:
            continue
        name = _title_to_name(title, allow_facebook=True) or slug_name
        if not name:
            continue
        key = _norm_key(href.split("?")[0])
        if key in seen:
            continue
        seen.add(key)
        phone = ""
        for m in PHONE_RO_RE.finditer(blob):
            p = norm_phone(m.group(0))
            if p:
                phone = p
                break
        email = ""
        for em in EMAIL_RE.findall(blob):
            if email_ok(em):
                email = em[:254].lower()
                break
        out.append(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "website": href if href.startswith("http") else "",
                "source": "facebook",
            }
        )
    return out


def _pet_relevant(blob: str) -> bool:
    low = blob.lower()
    if any(k in low for k in _PET_KW):
        return True
    pet = ("canin", "cain", "câini", "câine", "pet", "animale", "dog", "câini")
    if "hotel" in low and any(p in low for p in pet):
        return True
    if "pensiune" in low and any(p in low for p in pet):
        return True
    if "cazare" in low and any(p in low for p in pet):
        return True
    return "boarding" in low and any(p in low for p in pet)


def _extract(
    results: list[dict[str, str]], jname: str, capital: str, city: str = ""
) -> list[dict[str, str]]:
    from home.contact_enrichment import EMAIL_RE

    seen: set[str] = set()
    out: list[dict[str, str]] = []
    loc = {_norm_key(jname), _norm_key(capital), _norm_key(city or capital), "romania"}

    for r in results:
        title = r["title"]
        blob = (title + " " + r["body"]).lower()
        if not _pet_relevant(blob):
            continue
        loc_hit = any(tok and tok in _norm_key(blob) for tok in loc)
        if not loc_hit and not any(
            k in _norm_key(title) for k in ("hotel", "pensiune", "cazare", "boarding", "canin", "pet")
        ):
            continue
        href = r.get("href") or ""
        if href and any(s in href.lower() for s in _SKIP_HREF):
            continue
        name = _title_to_name(r["title"])
        if not name:
            continue
        key = _norm_key(name)
        if key in seen:
            continue
        seen.add(key)
        phone = ""
        for m in PHONE_RO_RE.finditer(blob):
            p = norm_phone(m.group(0))
            if p:
                phone = p
                break
        email = ""
        for em in EMAIL_RE.findall(blob):
            if email_ok(em):
                email = em[:254].lower()
                break
        out.append(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "website": href if href.startswith("http") else "",
                "source": "web",
            }
        )
    return out


def _judet_code(lead: StaffOnboardingLead) -> str:
    raw = _strip_d(lead.judet or lead.company_judet).lower()
    for code, name, _ in JUDETE_RO:
        if raw == _strip_d(name).lower() or raw == code.lower():
            return code
    for code, name, _ in JUDETE_RO:
        if _strip_d(name).lower() in raw:
            return code
    return ""


def _placeholder(code: str, name_key: str) -> str:
    h = hashlib.sha256(f"hotel:{code}:{name_key}".encode()).hexdigest()[:14]
    return f"ddg-hotel-{code.lower()}-{h}{PLACEHOLDER_EMAIL_SUFFIX}"[:254]


class Command(BaseCommand):
    help = "Import hotel/pensiune/cazare pet per județ (DDG+Bing, 0 Google)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--judet", default="")
        parser.add_argument("--max-per-judet", type=int, default=8)
        parser.add_argument("--sleep", type=float, default=2.0)

    def handle(self, *args: Any, **options: Any) -> None:
        apply_writes = bool(options["apply"])
        jf = (options.get("judet") or "").strip().upper()
        max_per = max(1, int(options["max_per_judet"]))
        sleep_j = max(0.5, float(options["sleep"]))

        judete = [j for j in JUDETE_RO if not jf or j[0] == jf]
        existing: set[tuple[str, str]] = set()
        existing_fb: set[str] = set()
        for lead in StaffOnboardingLead.objects.filter(
            collaborator_subtype=StaffOnboardingLead.COLLAB_SERVICII,
            notes__contains="import_pet_hotel_pensiune",
        ):
            c = _judet_code(lead)
            if c:
                existing.add((_norm_key(lead.display_name), c))
            for m in re.finditer(r"https?://(?:www\.)?(?:facebook|fb)\.com[^\s|]+", lead.notes or "", re.I):
                existing_fb.add(_norm_key(m.group(0).split("?")[0]))

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        created = skipped = 0

        self.stdout.write(
            f"Hotel/pensiune pet | județe={len(judete)} | apply={'DA' if apply_writes else 'NU'}"
        )

        for i, (code, jname, capital) in enumerate(judete):
            cities = [capital] + ORASE_EXTRA.get(code, [])[:3]
            local: dict[str, dict[str, str]] = {}
            queries_judet = [f"site:facebook.com hotel canin {jname} Romania"]
            for city in cities:
                city_queries = [
                    f"hotel canin {city}",
                    f"pensiune caini {city}",
                    f"cazare animale caini {city}",
                    f"pet hotel {city} Romania",
                    f"hotel canin {city} facebook",
                    f"pensiune caini {city} facebook",
                    f"site:facebook.com hotel canin {city}",
                    f"site:facebook.com pensiune caini {city}",
                    f"site:facebook.com cazare animale caini {city}",
                    f"site:facebook.com pet hotel {city}",
                ]
                for q in city_queries:
                    res = _ddg_search(q) + _bing_search(q)
                    for c in _extract(res, jname, capital, city=city):
                        k = _norm_key(c["name"])
                        if k not in local:
                            c["source_query"] = q
                            local[k] = c
                    for c in _extract_facebook(res, jname, capital, city=city):
                        fb_key = _norm_key((c.get("website") or "").split("?")[0])
                        k = fb_key or _norm_key(c["name"])
                        if k not in local:
                            c["source_query"] = q
                            local[k] = c
                    time.sleep(0.5)
            for q in queries_judet:
                res = _ddg_search(q) + _bing_search(q)
                for c in _extract_facebook(res, jname, capital, city=capital):
                    fb_key = _norm_key((c.get("website") or "").split("?")[0])
                    k = fb_key or _norm_key(c["name"])
                    if k not in local:
                        c["source_query"] = q
                        local[k] = c
                time.sleep(0.5)

            n_j = 0
            for c in local.values():
                if n_j >= max_per:
                    break
                key = (_norm_key(c["name"]), code)
                fb_url = (c.get("website") or "").split("?")[0]
                if fb_url and _is_facebook_page(fb_url) and _norm_key(fb_url) in existing_fb:
                    skipped += 1
                    continue
                if key in existing:
                    skipped += 1
                    continue
                email = c["email"] or _placeholder(code, key[0])
                src = c.get("source") or "web"
                notes = (
                    f"Sursă: DDG/Bing hotel-pensiune-cazare pet ({src}, gratuit).\n"
                    f"Județ: {jname} ({code}) | query={c.get('source_query')!r}\n"
                    f"web={c.get('website') or '—'}\n"
                    f"[import_pet_hotel_pensiune {stamp}]"
                )
                self.stdout.write(f"  [{code}] {c['name'][:55]!r}")
                if apply_writes:
                    StaffOnboardingLead.objects.create(
                        email=email,
                        phone=(c["phone"] or "")[:40],
                        display_name=c["name"],
                        org_display_name=c["name"][:255],
                        account_kind=StaffOnboardingLead.KIND_COLLAB,
                        collaborator_subtype=StaffOnboardingLead.COLLAB_SERVICII,
                        judet=jname,
                        oras=capital,
                        company_judet=jname,
                        company_oras=capital,
                        segments=["hotel_pensiune_pet"],
                        notes=notes,
                        status=StaffOnboardingLead.ST_READY,
                    )
                existing.add(key)
                if fb_url and _is_facebook_page(fb_url):
                    existing_fb.add(_norm_key(fb_url))
                n_j += 1
                created += 1

            self.stdout.write(self.style.SUCCESS(f"[{i+1}/{len(judete)}] {code}: +{n_j}"))
            time.sleep(sleep_j)

        self.stdout.write(self.style.SUCCESS(f"Gata. Create={created} skip={skipped}"))
