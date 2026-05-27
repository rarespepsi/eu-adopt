"""
Import prospecte grooming per județ — căutare gratuită DuckDuckGo (fără Google Places).

Completează golurile naționale: saloane toaletare canină / grooming / pet grooming.

  python manage.py import_grooming_ddg_by_judet --judet CJ --limit 5
  python manage.py import_grooming_ddg_by_judet --apply
  python manage.py import_grooming_ddg_by_judet --apply --max-per-judet 12 --sleep 2
"""

from __future__ import annotations

import hashlib
import re
import time
import unicodedata
import warnings
from datetime import datetime, timezone
from typing import Any

from django.core.management.base import BaseCommand

from home.contact_enrichment import PHONE_RO_RE, email_ok, norm_phone
from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import PLACEHOLDER_EMAIL_SUFFIX

# (cod, nume județ, reședință pentru query)
JUDETE_RO: list[tuple[str, str, str]] = [
    ("AB", "Alba", "Alba Iulia"),
    ("AG", "Argeș", "Pitești"),
    ("AR", "Arad", "Arad"),
    ("BC", "Bacău", "Bacău"),
    ("BH", "Bihor", "Oradea"),
    ("BN", "Bistrița-Năsăud", "Bistrița"),
    ("BT", "Botoșani", "Botoșani"),
    ("BR", "Brăila", "Brăila"),
    ("BV", "Brașov", "Brașov"),
    ("BZ", "Buzău", "Buzău"),
    ("CS", "Caraș-Severin", "Reșița"),
    ("CL", "Călărași", "Călărași"),
    ("CJ", "Cluj", "Cluj-Napoca"),
    ("CT", "Constanța", "Constanța"),
    ("CV", "Covasna", "Sfântu Gheorghe"),
    ("DB", "Dâmbovița", "Târgoviște"),
    ("DJ", "Dolj", "Craiova"),
    ("GL", "Galați", "Galați"),
    ("GR", "Giurgiu", "Giurgiu"),
    ("GJ", "Gorj", "Târgu Jiu"),
    ("HR", "Harghita", "Miercurea Ciuc"),
    ("HD", "Hunedoara", "Deva"),
    ("IL", "Ialomița", "Slobozia"),
    ("IS", "Iași", "Iași"),
    ("IF", "Ilfov", "Buftea"),
    ("MM", "Maramureș", "Baia Mare"),
    ("MH", "Mehedinți", "Drobeta-Turnu Severin"),
    ("MS", "Mureș", "Târgu Mureș"),
    ("NT", "Neamț", "Piatra Neamț"),
    ("OT", "Olt", "Slatina"),
    ("PH", "Prahova", "Ploiești"),
    ("SM", "Satu Mare", "Satu Mare"),
    ("SJ", "Sălaj", "Zalău"),
    ("SB", "Sibiu", "Sibiu"),
    ("SV", "Suceava", "Suceava"),
    ("TR", "Teleorman", "Alexandria"),
    ("TM", "Timiș", "Timișoara"),
    ("TL", "Tulcea", "Tulcea"),
    ("VS", "Vaslui", "Vaslui"),
    ("VL", "Vâlcea", "Râmnicu Vâlcea"),
    ("VN", "Vrancea", "Focșani"),
    ("B", "București", "București"),
]

# Orașe suplimentare pentru căutări (acoperire mai bună decât doar reședința)
ORASE_EXTRA: dict[str, list[str]] = {
    "AB": ["Sebeș", "Aiud", "Blaj"],
    "AG": ["Câmpulung", "Curtea de Argeș", "Mioveni"],
    "AR": ["Ineu", "Lipova"],
    "BC": ["Onești", "Moinești", "Comănești"],
    "BH": ["Beiuș", "Salonta", "Marghita"],
    "BN": ["Beclean", "Năsăud"],
    "BT": ["Dorohoi", "Săveni"],
    "BR": ["Ianca", "Însurăței"],
    "BV": ["Făgăraș", "Săcele", "Râșnov"],
    "BZ": ["Râmnicu Sărat", "Nehoiu"],
    "CS": ["Caransebeș", "Moldova Nouă"],
    "CL": ["Oltenița", "Fundulea"],
    "CJ": ["Turda", "Dej", "Gherla"],
    "CT": ["Mangalia", "Medgidia", "Năvodari"],
    "CV": ["Târgu Secuiesc", "Baraolt"],
    "DB": ["Moreni", "Pucioasa"],
    "DJ": ["Băilești", "Calafat"],
    "GL": ["Tecuci", "Târgu Bujor"],
    "GR": ["Bolintin-Vale", "Mihăilești"],
    "GJ": ["Motru", "Rovinari"],
    "HR": ["Odorheiu Secuiesc", "Gheorgheni"],
    "HD": ["Hunedoara", "Petroșani", "Vulcan"],
    "IL": ["Fetești", "Urziceni", "Țăndărei"],
    "IS": ["Pașcani", "Hârlău", "Roman"],
    "IF": ["Buftea", "Otopeni", "Voluntari"],
    "MM": ["Sighet", "Borșa"],
    "MH": ["Orșova", "Vânju Mare"],
    "MS": ["Reghin", "Sighișoara", "Târnăveni"],
    "NT": ["Roman", "Bicaz"],
    "OT": ["Caracal", "Corabia"],
    "PH": ["Câmpina", "Sinaia", "Azuga"],
    "SM": ["Carei", "Tășnad"],
    "SJ": ["Jibou", "Șimleu Silvaniei"],
    "SB": ["Mediaș", "Cisnădie", "Avrig"],
    "SV": ["Fălticeni", "Rădăuți", "Câmpulung Moldovenesc"],
    "TR": ["Roșiorii de Vede", "Zimnicea"],
    "TM": ["Lugoj", "Jimbolia"],
    "TL": ["Babadag", "Măcin"],
    "VS": ["Bârlad", "Huși", "Murgeni"],
    "VL": ["Drăgășani", "Horezu"],
    "VN": ["Adjud", "Mărășești"],
    "B": ["Sector 1", "Sector 2", "Sector 3"],
}

_SKIP_TITLE = (
    "wikipedia",
    "top 10",
    "top 5",
    "cele mai",
    "lista ",
    "listă",
    "blog",
    "forum",
    "youtube",
    "olx",
    "emag",
    "publi24",
    "best ",
    "ghid ",
    "recenzii",
    "review",
    "anunt",
    "anunț",
    "job",
    "locuri de munca",
    "curs ",
    "scoala",
    "școală",
    "adopt",
    "adăpost",
    "cabinet veterinar",
    "clinica vet",
    "spital veterinar",
    "medic veterinar",
    "cmv ",
    "cmvi ",
    "outlook",
    "microsoft",
    "sign in",
    "moved permanently",
    "what is grooming",
    "webshop",
    "web shop",
    "sign up",
    "login",
    "password",
    "calendar",
    "courrier",
    "abuse",
    "trafficking",
    "barber",
    "barbershop",
    "coafor",
    "coafura",
    "coafură",
    "coafur",
    "frizerie in apropiere",
    "programari frizerie",
    "programări frizerie",
    "saloane de coafura",
    "saloane de coafură",
    "top saloane",
    "crisstylle",
    "salon prego",
    "infrumusetare",
    "înfrijorare",
    "manichiura",
    "unghii",
    "tuns barba",
    "tuns barb",
)

_PET_NAME_MARKERS = (
    "canin",
    "canina",
    "caini",
    "câini",
    "câine",
    "groom",
    "toalet",
    "patrupez",
    "dog salon",
    "pet salon",
    "salon cain",
    "salon canin",
    "frizerie canin",
    "frizer canin",
    "spa canin",
    "beauty pet",
    "ingrijire cain",
    "îngrijire câin",
    "animale",
    "pet grooming",
)

_SKIP_HREF = (
    "outlook.",
    "microsoft.",
    "wikipedia.",
    "facebook.com/login",
    "instagram.com",
    "youtube.com",
    "gov.ro",
    "edu.ro",
)

_BUSINESS_WORDS = (
    "salon",
    "frizer",
    "toalet",
    "groom",
    "pet",
    "canin",
    "câin",
    "caini",
    "câini",
    "animale",
    "dog",
    "spa ",
    "beauty",
    "cosmet",
    "tuns ",
    "patrupez",
)

_GROOM_KW = (
    "groom",
    "toalet",
    "tuns cain",
    "tunsare cain",
    "frizerie canin",
    "frizer canin",
    "pet salon",
    "salon canin",
    "salon caini",
    "salon câini",
    "dog salon",
    "îngrijire câini",
    "ingrijire caini",
    "spa câini",
    "spa canin",
    "beauty pet",
    "cosmetica anim",
    "patrupez",
    "toaletare cain",
)


def _strip_d(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def _norm_key(s: str) -> str:
    t = _strip_d(s).lower()
    t = re.sub(r"[^a-z0-9]+", " ", t)
    return re.sub(r"\s+", " ", t).strip()


def _judet_code_from_lead(lead: StaffOnboardingLead) -> str:
    raw = _strip_d(lead.judet or lead.company_judet).lower()
    for code, name, _ in JUDETE_RO:
        if raw == _strip_d(name).lower() or raw == code.lower():
            return code
    for code, name, _ in JUDETE_RO:
        if _strip_d(name).lower() in raw or raw in _strip_d(name).lower():
            return code
    return ""


def _placeholder_email(jud: str, name_key: str) -> str:
    h = hashlib.sha256(f"{jud}:{name_key}".encode()).hexdigest()[:14]
    return f"ddg-groom-{jud.lower()}-{h}{PLACEHOLDER_EMAIL_SUFFIX}"[:254]


def _title_to_name(title: str) -> str:
    t = re.sub(r"\s+", " ", (title or "").strip())
    for sep in ("|", " - ", " – ", " — ", ":"):
        if sep in t:
            t = t.split(sep, 1)[0].strip()
    if len(t) < 4 or len(t) > 120:
        return ""
    low = _strip_d(t).lower()
    if any(x in low for x in _SKIP_TITLE):
        return ""
    if low in ("grooming", "pet", "salon", "toaletare", "pet shop", "petshop", "petmart", "pet max"):
        return ""
    if any(x in low for x in ("barber", "frizerie in apropiere", "slobozia", "barbershop")):
        return ""
    if "coafor" in low and "canin" not in low and "cain" not in low and "pet" not in low:
        return ""
    ambiguous = ("frizer", "frizerie", "salon", "coafor", "barber")
    if any(a in low for a in ambiguous):
        if not any(p in low for p in _PET_NAME_MARKERS):
            return ""
    elif not any(w in low for w in _BUSINESS_WORDS):
        return ""
    return t[:200]


def _ddg_search(query: str, max_results: int = 12) -> list[dict[str, str]]:
    """DDG text: prefer pachetul `ddgs` (rezultate mai bune, inclusiv Facebook)."""

    def _run(ddgs_cls: Any) -> list[dict[str, str]]:
        rows: list[dict[str, str]] = []
        with ddgs_cls() as ddgs:
            for r in ddgs.text(query, region="ro-ro", max_results=max_results) or []:
                if isinstance(r, dict):
                    rows.append(
                        {
                            "title": (r.get("title") or "").strip(),
                            "body": (r.get("body") or "").strip(),
                            "href": (r.get("href") or "").strip(),
                        }
                    )
        return rows

    try:
        from ddgs import DDGS as DDGSNew

        out = _run(DDGSNew)
        if out:
            return out
    except Exception:
        pass
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
        return []


def _bing_search(query: str) -> list[dict[str, str]]:
    import urllib.parse
    import urllib.request

    url = "https://www.bing.com/search?q=" + urllib.parse.quote_plus(query) + "&setlang=ro"
    req = urllib.request.Request(
        url,
        headers={"User-Agent": "Mozilla/5.0 (compatible; EU-Adopt/1.0)", "Accept-Language": "ro-RO"},
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
        title = re.sub(r"<[^>]+>", "", m.group(2))
        body = re.sub(r"<[^>]+>", "", m.group(3))
        if any(s in href.lower() for s in _SKIP_HREF):
            continue
        out.append({"title": title.strip(), "body": body.strip(), "href": href})
    return out[:15]


def _extract_candidates(
    results: list[dict[str, str]], jud_name: str, capital: str
) -> list[dict[str, str]]:
    from home.contact_enrichment import EMAIL_RE

    seen: set[str] = set()
    cands: list[dict[str, str]] = []
    loc_tokens = {_norm_key(jud_name), _norm_key(capital), "romania", "românia"}

    for r in results:
        title = r["title"]
        body = r["body"]
        href = r.get("href") or ""
        blob = (title + " " + body).lower()
        if not any(k in blob for k in _GROOM_KW):
            continue
        title_norm = _norm_key(title)
        if any(a in title_norm for a in ("frizer", "salon", "coafor", "barber")):
            if not any(p in title_norm for p in _PET_NAME_MARKERS):
                continue
        loc_hit = any(tok and tok in _norm_key(blob) for tok in loc_tokens)
        if not loc_hit and not any(k in title_norm for k in ("toalet", "groom", "canin", "caini", "pet")):
            continue
        if href and any(s in href.lower() for s in _SKIP_HREF):
            continue
        name = _title_to_name(title)
        if not name:
            continue
        key = _norm_key(name)
        if key in seen or len(key) < 4:
            continue
        seen.add(key)

        phone = ""
        for m in PHONE_RO_RE.finditer(body + " " + title):
            p = norm_phone(m.group(0))
            if p:
                phone = p
                break

        email = ""
        for em in EMAIL_RE.findall(body + " " + title):
            if email_ok(em):
                email = em.strip().lower()[:254]
                break

        website = href if href.startswith("http") else ""

        cands.append(
            {
                "name": name,
                "phone": phone,
                "email": email,
                "website": website,
                "source_query": "",
            }
        )
    return cands


class Command(BaseCommand):
    help = "Import grooming per județ via DDG (gratuit, fără Places API)."

    def add_arguments(self, parser):
        parser.add_argument("--apply", action="store_true")
        parser.add_argument("--judet", default="", help="Cod județ (ex. CJ, B). Gol = toate.")
        parser.add_argument("--max-per-judet", type=int, default=12, help="Max lead-uri noi / județ.")
        parser.add_argument("--sleep", type=float, default=2.0, help="Pauză secunde între județe.")
        parser.add_argument("--limit", type=int, default=0, help="Max județe de procesat (0=toate).")

    def handle(self, *args: Any, **options: Any) -> None:
        apply_writes = bool(options["apply"])
        jud_filter = (options.get("judet") or "").strip().upper()
        max_per = max(1, int(options["max_per_judet"]))
        sleep_j = max(0.5, float(options["sleep"]))
        limit_j = int(options.get("limit") or 0)

        judete = [j for j in JUDETE_RO if not jud_filter or j[0] == jud_filter]
        if not judete:
            self.stdout.write(self.style.ERROR(f"Județ invalid: {jud_filter}"))
            return
        if limit_j > 0:
            judete = judete[:limit_j]

        existing_keys: set[tuple[str, str]] = set()
        for lead in StaffOnboardingLead.objects.filter(
            collaborator_subtype=StaffOnboardingLead.COLLAB_GROOMING
        ):
            code = _judet_code_from_lead(lead)
            if code:
                existing_keys.add((_norm_key(lead.display_name), code))

        stamp = datetime.now(timezone.utc).strftime("%Y-%m-%d %H:%M UTC")
        total_created = total_skip = 0

        self.stdout.write(
            f"Județe: {len(judete)} | apply={'DA' if apply_writes else 'NU'} | "
            f"max/județ={max_per} | grooming existente={len(existing_keys)}"
        )

        for i, (code, jname, capital) in enumerate(judete):
            cities = [capital] + ORASE_EXTRA.get(code, [])[:3]
            queries: list[str] = []
            for city in cities:
                queries.extend(
                    [
                        f"salon toaletare caini {city}",
                        f"frizerie canina {city}",
                        f"grooming caini {city}",
                        f"site:facebook.com salon toaletare caini {city}",
                    ]
                )
            queries.append(f'pet grooming salon {jname} Romania')

            local: dict[str, dict[str, str]] = {}
            for q in queries:
                results = _ddg_search(q) + _bing_search(q)
                for c in _extract_candidates(results, jname, capital):
                    k = _norm_key(c["name"])
                    if k not in local:
                        c["source_query"] = q
                        local[k] = c
                time.sleep(0.6)

            created_j = 0
            for c in list(local.values())[: max_per * 3]:
                if created_j >= max_per:
                    break
                key = (_norm_key(c["name"]), code)
                if key in existing_keys:
                    total_skip += 1
                    continue

                email = c["email"] or _placeholder_email(code, key[0])
                notes = (
                    f"Sursă: DuckDuckGo grooming-by-județ (fără cost Google).\n"
                    f"Județ: {jname} ({code}) | query={c.get('source_query')!r}\n"
                    f"web={c.get('website') or '—'}\n"
                    f"[import_grooming_ddg_judet {stamp}]"
                )

                self.stdout.write(
                    f"  [{code}] {c['name'][:55]!r} tel={c['phone'] or '—'} email={email.split('@')[0][:20]}…"
                )

                if apply_writes:
                    StaffOnboardingLead.objects.create(
                        created_by=None,
                        email=email,
                        phone=(c["phone"] or "")[:40],
                        display_name=c["name"],
                        org_display_name=c["name"][:255],
                        account_kind=StaffOnboardingLead.KIND_COLLAB,
                        collaborator_subtype=StaffOnboardingLead.COLLAB_GROOMING,
                        judet=jname,
                        oras=capital,
                        company_judet=jname,
                        company_oras=capital,
                        company_legal_name=c["name"][:255],
                        notes=notes,
                        status=StaffOnboardingLead.ST_READY,
                    )
                existing_keys.add(key)
                created_j += 1
                total_created += 1

            self.stdout.write(
                self.style.SUCCESS(
                    f"[{i+1}/{len(judete)}] {code} {jname}: +{created_j} noi "
                    f"(candidați DDG: {len(local)})"
                )
            )
            time.sleep(sleep_j)

        self.stdout.write(
            self.style.SUCCESS(
                f"Gata. Create: {total_created} | sărite (duplicat): {total_skip}"
                + (" (dry-run)" if not apply_writes else "")
            )
        )
