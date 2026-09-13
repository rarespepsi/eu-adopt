"""
Descoperire gratuită campanii sterilizare (fără Google API plătit, fără scrape Facebook).

Căutare: DuckDuckGo (pachet ddgs) + fallback Bing HTML.
Output: candidați (titlu, url, snippet, județ) — NU creează CampanieSterilizare automat
(afișul e obligatoriu pe model; publicarea rămâne manuală / după confirmare).
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


def _looks_like_campaign(title: str, body: str) -> bool:
    blob = fold_key(f"{title} {body}")
    return any(k in blob for k in _CAMP_KW)


def _guess_dates(text: str) -> str:
    found: list[str] = []
    for m in _DATE_RE.finditer(text or ""):
        g = m.groups()
        if g[0] and g[1] and g[2]:
            found.append(f"{g[0]}.{g[1]}.{g[2]}")
        elif g[3] and g[4] and g[5]:
            found.append(f"{g[5]}.{g[4]}.{g[3]}")
    # unique keep order
    seen: set[str] = set()
    out: list[str] = []
    for d in found:
        if d not in seen:
            seen.add(d)
            out.append(d)
    return "; ".join(out[:4])


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
        qs.append(f"site:smeura.com sterilizare {name}")
        qs.append(f"site:smeura.com campanie {capital}")
    return qs


def fetch_og_image(page_url: str, *, timeout: int = 12) -> str:
    """Extrage og:image dintr-o pagină publică (gratuit)."""
    if not _host_ok(page_url):
        return ""
    # Facebook public share pages usually block; skip known hard hosts
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
    img = (m.group(1) or "").strip()
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
            if not _host_ok(href):
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
                    guessed_dates=_guess_dates(f"{title} {body}"),
                )
            )
    return out


def discover_empty_judete(
    *,
    judet_slugs: Iterable[str] | None = None,
    limit_judete: int = 0,
    max_per_query: int = 8,
    sleep_s: float = 1.2,
    include_smeura: bool = True,
    fetch_images: bool = False,
) -> list[CampanieCandidate]:
    if judet_slugs:
        wanted = {fold_key(s.replace("-", " ")) for s in judet_slugs}
        targets = [
            j
            for j in campanii_judete()
            if fold_key(j.slug.replace("-", " ")) in wanted or fold_key(j.name) in wanted
        ]
    else:
        targets = empty_campanii_judete()
    if limit_judete and limit_judete > 0:
        targets = targets[: int(limit_judete)]
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
