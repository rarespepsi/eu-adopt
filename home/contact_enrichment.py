"""
Enrichment contact gratuit (email / telefon / website) — fără Google Places pentru email.

Ordine: website (home + contact) → Facebook (link/DDG) → DuckDuckGo → Bing.
Cache pe domeniu în notițe lead ([FREE_EMAIL_DOMAIN_CACHE]).
"""

from __future__ import annotations

import re
import time
import warnings
import urllib.parse
import urllib.request
from dataclasses import dataclass, field
from typing import Any

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email

USER_AGENT = "Mozilla/5.0 (compatible; EU-Adopt free-contact-enrich/1.0)"
EMAIL_RE = re.compile(
    r"[a-zA-Z0-9][a-zA-Z0-9._%+-]*@[a-zA-Z0-9][a-zA-Z0-9.-]+\.[a-zA-Z]{2,24}"
)
MAILTO_RE = re.compile(r"mailto:([a-zA-Z0-9._%+-]+@[a-zA-Z0-9.-]+\.[a-zA-Z]{2,24})", re.I)
WEB_FROM_NOTES_RE = re.compile(r"web=(https?://[^\s'\"—]+)", re.I)
FB_URL_RE = re.compile(
    r"https?://(?:www\.)?(?:facebook|fb)\.com/[a-zA-Z0-9._\-/?=&%]+",
    re.I,
)
PHONE_RO_RE = re.compile(
    r"(?<!\d)(?:\+40\s?)?(?:0\d{9,10}|7\d{8,9})(?:\s*/\s*0?\d{6,12})?(?!\d)"
)
WA_RE = re.compile(r"(?:wa\.me|whatsapp\.com)[^\s\"'<>]+", re.I)

CONTACT_PATHS = (
    "/contact",
    "/contact/",
    "/contacte",
    "/contacte/",
    "/despre",
    "/despre/",
    "/despre-noi",
    "/despre-noi/",
    "/team",
    "/team/",
    "/contact-us",
    "/contact-us/",
)

PRIORITY_LOCALS = ("contact", "office", "info", "cabinet", "programari", "receptie")

SKIP_EMAIL_SUBSTR = (
    "example.com",
    "wix.com",
    "sentry.io",
    "facebook.com",
    "fbcdn.net",
    "instagram.com",
    "google.com",
    "gstatic.com",
    "w3.org",
    "schema.org",
    "sentry.io",
    "cloudflare.com",
    "domain.com",
    "email.com",
    "cmvro.ro",
)

SKIP_LOCAL = frozenset(
    {
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
        "support",
    }
)

CACHE_TAG = "[FREE_EMAIL_DOMAIN_CACHE"
ENRICH_TAG = "[FREE_EMAIL_ENRICH"
DOMAIN_CACHE_RE = re.compile(
    r"\[FREE_EMAIL_DOMAIN_CACHE[^\]]*domain=([^\s\]]+)[^\]]*result=([^\s\]]+)",
    re.I,
)

# Economie estimată dacă s-ar fi folosit Places doar pentru email (nu se folosește).
PLACES_SEARCH_COST_USD = 0.032


@dataclass
class EnrichResult:
    email: str = ""
    confidence: str = ""  # high | medium | low
    source: str = ""  # website_home | website_contact | mailto | facebook | duckduckgo | bing
    website: str = ""
    phone: str = ""
    whatsapp: str = ""
    facebook: str = ""
    steps: list[str] = field(default_factory=list)
    cache_hit: bool = False
    api_calls_saved: int = 0


@dataclass
class EnrichStats:
    processed: int = 0
    emails_found: int = 0
    websites_found: int = 0
    phones_found: int = 0
    skipped_cached: int = 0
    skipped_has_email: int = 0
    places_calls_saved: int = 0


def email_ok(addr: str) -> bool:
    a = (addr or "").strip().lower()
    if not a or ".." in a or a.endswith("@lead-placeholder.invalid"):
        return False
    if any(x in a for x in SKIP_EMAIL_SUBSTR):
        return False
    local = a.split("@", 1)[0]
    if local in SKIP_LOCAL or len(local) < 2:
        return False
    if local.startswith(("test", "demo", "example", "sample")):
        return False
    if re.match(r"^[0-9._\-]+$", local):
        return False
    return True


def norm_phone(raw: str | None) -> str:
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


def domain_from_url(url: str) -> str:
    try:
        host = urllib.parse.urlparse(url).netloc.lower()
        return host[4:] if host.startswith("www.") else host
    except Exception:
        return ""


def urls_from_notes(notes: str) -> list[str]:
    seen: set[str] = set()
    out: list[str] = []
    for m in WEB_FROM_NOTES_RE.finditer(notes or ""):
        u = m.group(1).rstrip(".,;)")
        if u not in seen:
            seen.add(u)
            out.append(u)
    return out


def load_domain_cache(notes: str) -> dict[str, str]:
    """domain -> email sau '__none__'."""
    cache: dict[str, str] = {}
    for m in DOMAIN_CACHE_RE.finditer(notes or ""):
        dom, res = m.group(1).lower(), m.group(2).strip()
        cache[dom] = res
    return cache


def cache_line(domain: str, result: str) -> str:
    return f"{CACHE_TAG} domain={domain} result={result}]"


def pick_best_email(
    candidates: list[tuple[str, str, str]],
) -> tuple[str, str, str]:
    """candidates: (email, confidence, source)."""
    if not candidates:
        return "", "", ""
    scored: list[tuple[int, str, str, str]] = []
    conf_score = {"high": 3, "medium": 2, "low": 1}
    for em, conf, src in candidates:
        if not email_ok(em):
            continue
        local = em.split("@", 1)[0].lower()
        bonus = 0
        if local in PRIORITY_LOCALS:
            bonus += 2
        if "mailto" in src:
            bonus += 3
        if any(x in em.lower() for x in ("gmail.com", "yahoo.", "outlook.", "hotmail.")):
            bonus += 1
        scored.append((conf_score.get(conf, 0) + bonus, em, conf, src))
    if not scored:
        return "", "", ""
    scored.sort(reverse=True)
    return scored[0][1], scored[0][2], scored[0][3]


def fetch_html(url: str, timeout: int = 14) -> str:
    if not url.startswith("http"):
        url = "https://" + url
    req = urllib.request.Request(url, headers={"User-Agent": USER_AGENT}, method="GET")
    try:
        with urllib.request.urlopen(req, timeout=timeout) as resp:
            ctype = (resp.headers.get("Content-Type") or "").lower()
            if "html" not in ctype and "text" not in ctype and "xml" not in ctype:
                return ""
            return resp.read(400_000).decode("utf-8", errors="replace")
    except Exception:
        return ""


def extract_emails_from_html(
    html: str, confidence: str, source: str
) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for m in MAILTO_RE.finditer(html or ""):
        em = m.group(1).strip()
        if email_ok(em) and em.lower() not in seen:
            seen.add(em.lower())
            out.append((em, "high", f"{source}_mailto"))
    for em in EMAIL_RE.findall(html or ""):
        el = em.strip().lower()
        if el in seen or not email_ok(em):
            continue
        seen.add(el)
        out.append((em.strip(), confidence, source))
    return out


def scrape_website(base_url: str) -> tuple[list[tuple[str, str, str]], str, str, str]:
    """Home + contact paths. Returnează (email candidates, phone, whatsapp, facebook url)."""
    candidates: list[tuple[str, str, str]] = []
    phone = ""
    whatsapp = ""
    facebook = ""

    html_home = fetch_html(base_url)
    if not html_home:
        return candidates, phone, whatsapp, facebook

    candidates.extend(extract_emails_from_html(html_home, "high", "website_home"))

    for m in PHONE_RO_RE.finditer(html_home):
        p = norm_phone(m.group(0))
        if p and not phone:
            phone = p
    wa_m = WA_RE.search(html_home)
    if wa_m:
        whatsapp = wa_m.group(0)[:200]
    fb_m = FB_URL_RE.search(html_home)
    if fb_m:
        facebook = fb_m.group(0).split('"')[0].split("'")[0]

    parsed = urllib.parse.urlparse(base_url if "://" in base_url else "https://" + base_url)
    origin = f"{parsed.scheme}://{parsed.netloc}"

    for path in CONTACT_PATHS:
        page_url = origin + path
        html = fetch_html(page_url, timeout=10)
        if not html:
            continue
        candidates.extend(extract_emails_from_html(html, "medium", "website_contact"))
        if not phone:
            for m in PHONE_RO_RE.finditer(html):
                p = norm_phone(m.group(0))
                if p:
                    phone = p
                    break
        if not facebook:
            fb_m = FB_URL_RE.search(html)
            if fb_m:
                facebook = fb_m.group(0).split('"')[0]

    return candidates, phone, whatsapp, facebook


def ddg_search(queries: list[str], max_results: int = 8) -> str:
    try:
        warnings.filterwarnings(
            "ignore",
            message=".*renamed to.*ddgs",
            category=RuntimeWarning,
            module="duckduckgo_search",
        )
        from duckduckgo_search import DDGS
    except ImportError:
        return ""
    blob_parts: list[str] = []
    with DDGS() as ddgs:
        for q in queries:
            try:
                for r in ddgs.text(q, max_results=max_results) or []:
                    if isinstance(r, dict):
                        blob_parts.append((r.get("title") or "") + " " + (r.get("body") or ""))
            except Exception:
                continue
            time.sleep(0.25)
    return " ".join(blob_parts)


def bing_search_html(query: str) -> str:
    q = urllib.parse.quote_plus(query)
    url = f"https://www.bing.com/search?q={q}&setlang=ro"
    req = urllib.request.Request(
        url,
        headers={
            "User-Agent": USER_AGENT,
            "Accept-Language": "ro-RO,ro;q=0.9",
        },
    )
    try:
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read(300_000).decode("utf-8", errors="replace")
    except Exception:
        return ""


def search_snippet_emails(blob: str) -> list[tuple[str, str, str]]:
    out: list[tuple[str, str, str]] = []
    seen: set[str] = set()
    for em in EMAIL_RE.findall(blob or ""):
        if email_ok(em) and em.lower() not in seen:
            seen.add(em.lower())
            out.append((em.strip(), "low", "search_snippet"))
    return out


def enrich_facebook_via_search(name: str, loc: str, fb_url: str) -> list[tuple[str, str, str]]:
    queries = []
    if fb_url:
        queries.append(f"site:facebook.com {name} {loc} email contact")
    queries.append(f'"{name}" {loc} facebook email România')
    blob = ddg_search(queries, max_results=6)
    found = search_snippet_emails(blob)
    return [(e, "low", "facebook") for e, _, _ in found]


def build_business_name(lead: StaffOnboardingLead) -> str:
    org = (lead.org_display_name or "").strip()
    disp = (lead.display_name or "").strip()
    if org and org.lower() != disp.lower():
        return org
    return disp or org


def enrich_lead_free(
    lead: StaffOnboardingLead,
    *,
    use_ddg: bool = True,
    use_bing: bool = True,
    use_facebook: bool = True,
    domain_cache: dict[str, str] | None = None,
) -> EnrichResult:
    """
    Pipeline gratuit pentru un lead (fără Google Places).
    """
    res = EnrichResult()
    notes = lead.notes or ""
    local_cache = domain_cache if domain_cache is not None else load_domain_cache(notes)

    em_before = (lead.email or "").strip()
    if em_before and not is_placeholder_lead_email(em_before):
        return res

    name = build_business_name(lead)
    loc = (lead.oras or lead.judet or lead.company_oras or lead.company_judet or "").strip()
    all_candidates: list[tuple[str, str, str]] = []

    websites = urls_from_notes(notes)

    # --- Etapa 1–2: website scrape ---
    for site in websites[:3]:
        dom = domain_from_url(site)
        if dom and dom in local_cache:
            cached = local_cache[dom]
            res.cache_hit = True
            res.steps.append("cache_domain")
            if cached != "__none__" and email_ok(cached):
                all_candidates.append((cached, "high", "cache"))
            continue

        res.steps.append("website")
        res.website = site
        cands, ph, wa, fb = scrape_website(site)
        all_candidates.extend(cands)
        if ph and not res.phone:
            res.phone = ph
        if wa:
            res.whatsapp = wa
        if fb:
            res.facebook = fb

        if dom:
            best, _, _ = pick_best_email(all_candidates)
            local_cache[dom] = best if best else "__none__"

    # --- Etapa 3: Facebook ---
    if use_facebook and not pick_best_email(all_candidates)[0]:
        fb = res.facebook
        for m in FB_URL_RE.finditer(notes):
            fb = m.group(0)
            break
        if fb or name:
            res.steps.append("facebook")
            all_candidates.extend(enrich_facebook_via_search(name, loc, fb))
            if fb:
                res.facebook = fb

    # --- Etapa 4: DuckDuckGo ---
    if use_ddg and not pick_best_email(all_candidates)[0] and name:
        res.steps.append("ddg")
        dom = domain_from_url(websites[0]) if websites else ""
        queries = [
            f'"{name}" {loc} "@" email România',
            f'"{name}" {loc} contact email',
        ]
        if dom:
            queries.append(f"site:{dom} @")
        blob = ddg_search(queries)
        all_candidates.extend(search_snippet_emails(blob))

    # --- Etapa 5: Bing ---
    if use_bing and not pick_best_email(all_candidates)[0] and name:
        res.steps.append("bing")
        html = bing_search_html(f"{name} {loc} email contact site:.ro")
        all_candidates.extend(search_snippet_emails(html))
        time.sleep(0.5)

    email, conf, src = pick_best_email(all_candidates)
    if email:
        res.email = email[:254].lower()
        res.confidence = conf
        res.source = src
        res.api_calls_saved = 1  # ar fi fost 1 Places evitat

    return res


def enrich_note_line(result: EnrichResult, ts: str) -> str:
    return (
        f"{ENRICH_TAG} {ts}] steps={','.join(result.steps) or '—'} "
        f"email={result.email or '—'} conf={result.confidence or '—'} "
        f"src={result.source or '—'} web={result.website or '—'} "
        f"phone={result.phone or '—'} fb={result.facebook or '—'} "
        f"cache_hit={1 if result.cache_hit else 0}"
    )
