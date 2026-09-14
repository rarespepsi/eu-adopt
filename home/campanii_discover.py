"""
Descoperire gratuită campanii sterilizare (fără Google API plătit, fără scrape Facebook).

Căutare: DuckDuckGo (pachet ddgs) + fallback Bing HTML.
Candidații se salvează în CampanieDiscoverHit; auto-publicarea e în campanii_discover_publish.
"""
from __future__ import annotations

import csv
import logging
import re
import time
import urllib.error
import urllib.request
import warnings
from dataclasses import asdict, dataclass
from datetime import date
from pathlib import Path
from typing import Any, Iterable
from urllib.parse import urlparse

from home.campanii_ro import CampaniiJudet, campanii_count_by_code, campanii_judete
from home.ro_location import fold_key

logger = logging.getLogger(__name__)

_SKIP_HOST = (
    "eu-adopt.ro",
    "youtube.com",
    "youtu.be",
    "instagram.com",
    "tiktok.com",
    "play.google.com",
    "apps.apple.com",
    "wikipedia.org",
)

_JUNK_HOST = (
    "litoralulromanesc.ro",
    "directbooking.ro",
    "booking.com",
    "tripadvisor.",
    "romedic.ro",
    "markday.ro",
    "bonacibo.ro",
    "mlive.md",
    "romaniafashion.ro",
)

_JUNK_PATH_RE = re.compile(
    r"(hotel|cazare|parcare-gratuita|/tag/|/category/|/search/|"
    r"evenimente/categorie|post_type=tribe_events|/organizer/|"
    r"facebook\.com/groups/|Sterilizari\.gratuite\.in\.Romania)",
    re.I,
)

_CAMP_KW = (
    "steriliz",
    "sterilizare",
    "castrar",
    "castrare",
    "campanie",
    "gratuit",
    "gratuită",
    "gratuita",
)

_DATE_RE = re.compile(
    r"\b(\d{1,2})[./\-](\d{1,2})[./\-](20\d{2})\b|\b(20\d{2})[./\-](\d{1,2})[./\-](\d{1,2})\b"
)
_EN_MDY = re.compile(
    r"\b(Jan|Feb|Mar|Apr|May|Jun|Jul|Aug|Sep|Sept|Oct|Nov|Dec)[a-z]*\.?\s+"
    r"(\d{1,2})(?:st|nd|rd|th)?,?\s+(20\d{2})\b",
    re.I,
)
_MONTH_YEAR = re.compile(
    r"\b(ianuarie|februarie|martie|aprilie|mai|iunie|iulie|august|septembrie|octombrie|noiembrie|decembrie|"
    r"january|february|march|april|june|july|september|october|november|december|"
    r"jan|feb|mar|apr|may|jun|jul|aug|sep|sept|oct|nov|dec)"
    r"\.?\s+(\d{1,2})?(?:st|nd|rd|th)?,?\s*(20\d{2})\b",
    re.I,
)
_MONTHS = {
    "ianuarie": 1,
    "februarie": 2,
    "martie": 3,
    "aprilie": 4,
    "mai": 5,
    "iunie": 6,
    "iulie": 7,
    "august": 8,
    "septembrie": 9,
    "octombrie": 10,
    "noiembrie": 11,
    "decembrie": 12,
    "january": 1,
    "february": 2,
    "march": 3,
    "april": 4,
    "june": 6,
    "july": 7,
    "september": 9,
    "october": 10,
    "november": 11,
    "december": 12,
    "jan": 1,
    "feb": 2,
    "mar": 3,
    "apr": 4,
    "may": 5,
    "jun": 6,
    "jul": 7,
    "aug": 8,
    "sep": 9,
    "sept": 9,
    "oct": 10,
    "nov": 11,
    "dec": 12,
}
_OG_IMAGE_RE = re.compile(
    r'<meta[^>]+property=["\']og:image["\'][^>]+content=["\']([^"\']+)["\']',
    re.I,
)
_OG_IMAGE_RE2 = re.compile(
    r'<meta[^>]+content=["\']([^"\']+)["\'][^>]+property=["\']og:image["\']',
    re.I,
)


@dataclass
class CampanieCandidate:
    judet: str
    judet_slug: str
    judet_code: str
    title: str
    url: str
    snippet: str
    source: str  # ddg | bing
    query: str
    image_url: str = ""
    guessed_dates: str = ""


def empty_campanii_judete() -> list[CampaniiJudet]:
    """Județe fără nicio campanie vizibilă pe hartă."""
    counts = campanii_count_by_code()
    return [j for j in campanii_judete() if j.code and int(counts.get(j.code, 0) or 0) == 0]


def _web_search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    rows = _ddg_search(query, max_results=max_results)
    if rows:
        for r in rows:
            r["source"] = "ddg"
        return rows
    rows = _bing_search(query)
    for r in rows:
        r["source"] = "bing"
    return rows


def _ddg_search(query: str, max_results: int = 10) -> list[dict[str, str]]:
    def _run(ddgs_cls: Any) -> list[dict[str, str]]:
        out: list[dict[str, str]] = []
        with ddgs_cls() as ddgs:
            for r in ddgs.text(query, region="ro-ro", max_results=max_results) or []:
                if not isinstance(r, dict):
                    continue
                out.append(
                    {
                        "title": (r.get("title") or "").strip(),
                        "body": (r.get("body") or "").strip(),
                        "href": (r.get("href") or "").strip(),
                    }
                )
        return out

    try:
        from ddgs import DDGS as DDGSNew

        out = _run(DDGSNew)
        if out:
            return out
    except Exception:
        logger.debug("ddgs search failed for %s", query, exc_info=True)
    try:
        warnings.filterwarnings(
            "ignore",
            message=".*renamed to.*ddgs",
            category=RuntimeWarning,
            module="duckduckgo_search",
        )
        from duckduckgo_search import DDGS

        return _run(DDGS)
    except Exception:
        logger.debug("duckduckgo_search failed for %s", query, exc_info=True)
        return []


def _bing_search(query: str) -> list[dict[str, str]]:
    import urllib.parse

    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query) + "&setlang=ro"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EU-Adopt-campanii/1.0)",
            "Accept-Language": "ro-RO,ro;q=0.9",
        },
    )
    try:
        html = urllib.request.urlopen(req, timeout=18).read().decode("utf-8", errors="replace")
    except Exception:
        return []
    out: list[dict[str, str]] = []
    for m in re.finditer(
        r'<li class="b_algo"[^>]*>.*?<a href="([^"]+)"[^>]*>(.*?)</a>.*?<p>(.*?)</p>',
        html,
        re.DOTALL | re.I,
    ):
        href = m.group(1).strip()
        title = re.sub(r"<[^>]+>", "", m.group(2)).strip()
        body = re.sub(r"<[^>]+>", "", m.group(3)).strip()
        out.append({"title": title, "body": body, "href": href})
    return out[:12]


def _host_ok(url: str) -> bool:
    low = (url or "").lower()
    if not low.startswith("http"):
        return False
    return not any(h in low for h in _SKIP_HOST)


def is_junk_campaign_url(url: str) -> bool:
    """URL-uri care nu merită candidați / auto-publish."""
    if not _host_ok(url):
        return True
    low = (url or "").lower()
    if any(h in low for h in _JUNK_HOST):
        return True
    if _JUNK_PATH_RE.search(low):
        return True
    try:
        p = urlparse(url)
        host = (p.netloc or "").lower()
        path = (p.path or "").rstrip("/") or "/"
    except Exception:
        return True
    # smeura: doar evenimente concrete
    if "smeura.com" in host:
        if "/event/" not in path:
            return True
    # homepage-uri goale
    if path in ("/", "") and "smeura" not in host:
        if any(x in host for x in ("animed.ro", "impactnews24", "sterilizari-gratuite.ro")):
            return True
    return False


def _looks_like_campaign(title: str, body: str) -> bool:
    blob = fold_key(f"{title} {body}")
    return any(k in blob for k in _CAMP_KW)


def _safe_date(y: int, m: int, d: int) -> date | None:
    try:
        return date(y, m, d)
    except ValueError:
        try:
            return date(y, m, 1)
        except ValueError:
            return None


def parse_campaign_dates(text: str) -> list[date]:
    """Extrage date calendaristice din text (RO/EN + URL /YYYY/MM/DD/)."""
    out: list[date] = []
    for m in _DATE_RE.finditer(text or ""):
        g = m.groups()
        if g[0] and g[1] and g[2]:
            d, mo, y = int(g[0]), int(g[1]), int(g[2])
            if mo > 12 and d <= 12:
                d, mo = mo, d
            dt = _safe_date(y, mo, d)
            if dt:
                out.append(dt)
        elif g[3] and g[4] and g[5]:
            dt = _safe_date(int(g[3]), int(g[4]), int(g[5]))
            if dt:
                out.append(dt)
    for m in _EN_MDY.finditer(text or ""):
        mon = _MONTHS.get(m.group(1).lower()[:3]) or _MONTHS.get(m.group(1).lower())
        if mon:
            dt = _safe_date(int(m.group(3)), mon, int(m.group(2)))
            if dt:
                out.append(dt)
    for m in _MONTH_YEAR.finditer(text or ""):
        mon = _MONTHS.get(m.group(1).lower())
        if mon:
            day = int(m.group(2) or 1)
            dt = _safe_date(int(m.group(3)), mon, day)
            if dt:
                out.append(dt)
    for m in re.finditer(r"/(20\d{2})/(\d{1,2})/(\d{1,2})/", text or ""):
        dt = _safe_date(int(m.group(1)), int(m.group(2)), int(m.group(3)))
        if dt:
            out.append(dt)
    seen: set[date] = set()
    uniq: list[date] = []
    for d in out:
        if d not in seen:
            seen.add(d)
            uniq.append(d)
    return uniq


def _guess_dates(text: str) -> str:
    found = [d.strftime("%d.%m.%Y") for d in parse_campaign_dates(text)]
    return "; ".join(found[:4])


def build_queries(judet: CampaniiJudet, *, include_smeura: bool = True) -> list[str]:
    name = judet.name
    capital = (judet.main_cities[0] if judet.main_cities else name) or name
    year = date.today().year
    qs = [
        f'campanie sterilizare "{name}" {year}',
        f'sterilizare gratuita {capital} {name}',
        f'campanie sterilizare caini pisici {name}',
    ]
    if include_smeura:
        qs.append(f"site:smeura.com event sterilizare {name}")
        qs.append(f"site:smeura.com/event {capital}")
    return qs


def fetch_og_image(page_url: str, *, timeout: int = 12) -> str:
    """Extrage og:image dintr-o pagină publică (gratuit)."""
    if not _host_ok(page_url) or is_junk_campaign_url(page_url):
        return ""
    low = page_url.lower()
    if "facebook.com" in low or "fb.me" in low:
        return ""
    req = urllib.request.Request(
        page_url,
        headers={
            "User-Agent": "Mozilla/5.0 (compatible; EU-Adopt-campanii/1.0)",
            "Accept": "text/html,application/xhtml+xml",
            "Accept-Language": "ro-RO,ro;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            html = resp.read(250_000).decode("utf-8", errors="replace")
    except (urllib.error.URLError, TimeoutError, OSError, ValueError):
        return ""
    m = _OG_IMAGE_RE.search(html) or _OG_IMAGE_RE2.search(html)
    if not m:
        return ""
    img = (m.group(1) or "").strip().replace("&#038;", "&")
    if img.startswith("//"):
        img = "https:" + img
    if not img.startswith("http"):
        return ""
    return img[:500]


def discover_for_judet(
    judet: CampaniiJudet,
    *,
    max_per_query: int = 8,
    sleep_s: float = 1.2,
    include_smeura: bool = True,
    fetch_images: bool = False,
) -> list[CampanieCandidate]:
    seen_urls: set[str] = set()
    out: list[CampanieCandidate] = []
    for q in build_queries(judet, include_smeura=include_smeura):
        results = _web_search(q, max_results=max_per_query)
        time.sleep(max(0.0, float(sleep_s)))
        for r in results:
            href = (r.get("href") or "").strip()
            title = (r.get("title") or "").strip()
            body = (r.get("body") or "").strip()
            if not href or href in seen_urls:
                continue
            if not _host_ok(href) or is_junk_campaign_url(href):
                continue
            if not _looks_like_campaign(title, body):
                continue
            seen_urls.add(href)
            img = ""
            if fetch_images:
                img = fetch_og_image(href)
                time.sleep(0.4)
            out.append(
                CampanieCandidate(
                    judet=judet.name,
                    judet_slug=judet.slug,
                    judet_code=judet.code,
                    title=title[:240],
                    url=href[:500],
                    snippet=body[:400],
                    source=(r.get("source") or "ddg")[:12],
                    query=q[:200],
                    image_url=img,
                    guessed_dates=_guess_dates(f"{title} {body} {href}"),
                )
            )
    return out


def _resolve_targets(
    judet_slugs: Iterable[str] | None,
    *,
    empty_only: bool,
    limit_judete: int,
) -> list[CampaniiJudet]:
    if judet_slugs:
        wanted = {fold_key(s.replace("-", " ")) for s in judet_slugs}
        targets = [
            j
            for j in campanii_judete()
            if fold_key(j.slug.replace("-", " ")) in wanted or fold_key(j.name) in wanted
        ]
    elif empty_only:
        targets = empty_campanii_judete()
    else:
        targets = list(campanii_judete())
    if limit_judete and limit_judete > 0:
        targets = targets[: int(limit_judete)]
    return targets


def discover_empty_judete(
    *,
    judet_slugs: Iterable[str] | None = None,
    limit_judete: int = 0,
    max_per_query: int = 8,
    sleep_s: float = 1.2,
    include_smeura: bool = True,
    fetch_images: bool = False,
) -> list[CampanieCandidate]:
    targets = _resolve_targets(
        judet_slugs,
        empty_only=not bool(judet_slugs),
        limit_judete=limit_judete,
    )
    all_rows: list[CampanieCandidate] = []
    for j in targets:
        all_rows.extend(
            discover_for_judet(
                j,
                max_per_query=max_per_query,
                sleep_s=sleep_s,
                include_smeura=include_smeura,
                fetch_images=fetch_images,
            )
        )
    return all_rows


def discover_all_judete(
    *,
    limit_judete: int = 0,
    max_per_query: int = 6,
    sleep_s: float = 1.0,
    include_smeura: bool = True,
    fetch_images: bool = False,
) -> list[CampanieCandidate]:
    """Scan pe toate județele RO (nu doar goale)."""
    targets = _resolve_targets(None, empty_only=False, limit_judete=limit_judete)
    all_rows: list[CampanieCandidate] = []
    for j in targets:
        all_rows.extend(
            discover_for_judet(
                j,
                max_per_query=max_per_query,
                sleep_s=sleep_s,
                include_smeura=include_smeura,
                fetch_images=fetch_images,
            )
        )
    return all_rows


def write_candidates_csv(path: Path, rows: list[CampanieCandidate]) -> Path:
    path.parent.mkdir(parents=True, exist_ok=True)
    fields = [
        "judet",
        "judet_slug",
        "judet_code",
        "title",
        "url",
        "snippet",
        "image_url",
        "guessed_dates",
        "source",
        "query",
    ]
    with path.open("w", encoding="utf-8", newline="") as f:
        w = csv.DictWriter(f, fieldnames=fields)
        w.writeheader()
        for row in rows:
            w.writerow({k: asdict(row).get(k, "") for k in fields})
    return path
