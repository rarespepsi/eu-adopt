"""
Parsare pagini județ de pe registru-caini.ro → rânduri CSV (antet Add USER).

Nu se bazează pe lista de linkuri de pe /adaposturi/ (are href-uri greșite);
URL-urile sunt o listă canonică. Identificarea înregistrărilor se face din
titlul blocului + câmpurile din <ul> (în special „Adresa adapostului”).
"""

from __future__ import annotations

import re
import time
import unicodedata
import urllib.error
import urllib.request
from dataclasses import dataclass
from typing import Iterator

from bs4 import BeautifulSoup, NavigableString, Tag

from home.models import StaffOnboardingLead

BASE = "https://registru-caini.ro"

# Slug canonic în URL + etichetă județ în CSV (fără a ne încrede în meniul principal).
COUNTY_PAGES: tuple[tuple[str, str, str], ...] = (
    ("alba", "Alba", f"{BASE}/adaposturi/alba/"),
    ("arad", "Arad", f"{BASE}/adaposturi/arad/"),
    ("arges", "Argeș", f"{BASE}/adaposturi/arges/"),
    ("bacau", "Bacău", f"{BASE}/adaposturi/bacau/"),
    ("bihor", "Bihor", f"{BASE}/adaposturi/bihor/"),
    ("bistrita-nasaud", "Bistrița-Năsăud", f"{BASE}/adaposturi/bistrita-nasaud/"),
    ("botosani", "Botoșani", f"{BASE}/adaposturi/botosani/"),
    ("brasov", "Brașov", f"{BASE}/adaposturi/brasov/"),
    ("braila", "Brăila", f"{BASE}/adaposturi/braila/"),
    ("buzau", "Buzău", f"{BASE}/adaposturi/buzau/"),
    ("caras-severin", "Caraș-Severin", f"{BASE}/adaposturi/caras-severin/"),
    ("calarasi", "Călărași", f"{BASE}/adaposturi/calarasi/"),
    ("cluj", "Cluj", f"{BASE}/adaposturi/cluj/"),
    ("constanta", "Constanța", f"{BASE}/adaposturi/constanta/"),
    ("covasna", "Covasna", f"{BASE}/adaposturi/covasna/"),
    ("dambovita", "Dâmbovița", f"{BASE}/adaposturi/dambovita/"),
    ("dolj", "Dolj", f"{BASE}/adaposturi/dolj/"),
    ("galati", "Galați", f"{BASE}/adaposturi/galati/"),
    ("giurgiu", "Giurgiu", f"{BASE}/adaposturi/giurgiu/"),
    ("gorj", "Gorj", f"{BASE}/adaposturi/gorj/"),
    ("harghita", "Harghita", f"{BASE}/adaposturi/harghita/"),
    ("hunedoara", "Hunedoara", f"{BASE}/adaposturi/hunedoara/"),
    ("ialomita", "Ialomița", f"{BASE}/adaposturi/ialomita/"),
    ("iasi", "Iași", f"{BASE}/adaposturi/iasi/"),
    ("ilfov", "Ilfov", f"{BASE}/adaposturi/ilfov/"),
    ("maramures", "Maramureș", f"{BASE}/adaposturi/maramures/"),
    ("mehedinti", "Mehedinți", f"{BASE}/adaposturi/mehedinti/"),
    ("mures", "Mureș", f"{BASE}/adaposturi/mures/"),
    ("neamt", "Neamț", f"{BASE}/adaposturi/neamt/"),
    ("olt", "Olt", f"{BASE}/adaposturi/olt/"),
    ("prahova", "Prahova", f"{BASE}/adaposturi/prahova/"),
    ("satu-mare", "Satu Mare", f"{BASE}/adaposturi/satu-mare/"),
    ("salaj", "Sălaj", f"{BASE}/adaposturi/salaj/"),
    ("sibiu", "Sibiu", f"{BASE}/adaposturi/sibiu/"),
    ("suceava", "Suceava", f"{BASE}/adaposturi/suceava/"),
    ("teleorman", "Teleorman", f"{BASE}/adaposturi/teleorman/"),
    ("timis", "Timiș", f"{BASE}/timis/"),
    ("tulcea", "Tulcea", f"{BASE}/adaposturi/tulcea/"),
    ("vaslui", "Vaslui", f"{BASE}/adaposturi/vaslui/"),
    ("valcea", "Vâlcea", f"{BASE}/adaposturi/valcea/"),
    ("vrancea", "Vrancea", f"{BASE}/adaposturi/vrancea/"),
    ("bucuresti", "București", f"{BASE}/adaposturi/bucuresti/"),
)

UA = (
    "Mozilla/5.0 (Windows NT 10.0; Win64; x64) AppleWebKit/537.36 "
    "(KHTML, like Gecko) Chrome/120.0.0.0 Safari/537.36"
)

_EMAIL_RE = re.compile(r"[\w.+-]+@[\w.-]+\.[A-Za-z]{2,}")
_PHONE_RE = re.compile(
    r"(?:\+40\s?)?(?:0(?:2|3)\d{8,9}|07\d{8}|0[89]\d{7,8})(?:\s*/\s*0?\d{6,10})?",
    re.IGNORECASE,
)


def _fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def _norm_li_label(label: str) -> str:
    return _fold(label.replace(":", "").strip())


def _title_before_ul(ul: Tag) -> str:
    """Titlul adăpostului: <span>…<strong>…</strong> înainte de <ul> (skip whitespace)."""
    cur: Tag | NavigableString | None = ul.previous_sibling
    steps = 0
    while cur is not None and steps < 30:
        steps += 1
        nxt = cur.previous_sibling
        if isinstance(cur, NavigableString):
            cur = nxt
            continue
        if isinstance(cur, Tag):
            if cur.name == "h2":
                break
            if cur.name == "span":
                st = cur.find("strong")
                if st:
                    t = st.get_text(" ", strip=True)
                    if t and len(t) > 2 and "ADAPOSTURI DIN" not in t.upper():
                        return t
        cur = nxt
    return ""


def _parse_ul_block(ul: Tag) -> dict[str, str]:
    out: dict[str, str] = {}
    for li in ul.find_all("li", recursive=False):
        raw = li.get_text(" ", strip=True)
        if ":" not in raw:
            continue
        head, _, tail = raw.partition(":")
        key = _norm_li_label(head)
        tail = tail.strip()
        if "adresa" in key and "adapost" in key:
            out["adresa"] = tail
        elif "responsabil" in key and "adopt" in key:
            out["responsabil"] = tail
        elif "tipul" in key and "adapost" in key:
            out["tip"] = tail
        elif "capacitate" in key:
            out["capacitate"] = tail
        elif "program" in key:
            out["program"] = tail
        elif "promovare" in key:
            out["promovare"] = tail
    return out


def _phones_from(text: str) -> str:
    found = _PHONE_RE.findall(text or "")
    if not found:
        return ""
    return found[0].replace(" ", "")[:40]


def _email_from(text: str) -> str:
    m = _EMAIL_RE.search(text or "")
    return (m.group(0) if m else "").strip()[:254]


def _tip_colab_and_public(tip_raw: str) -> tuple[str, str]:
    t = _fold(tip_raw)
    if "public" in t:
        return StaffOnboardingLead.COLLAB_ADPUB, "1"
    if "privat" in t:
        return StaffOnboardingLead.COLLAB_ADPRV, ""
    return "", ""


def _localitate_heuristic(adresa: str) -> str:
    a = (adresa or "").strip()
    if not a:
        return ""
    first = a.split(",")[0].strip()
    for prefix in (
        "municipiul ",
        "municipiu ",
        "orasul ",
        "orașul ",
        "localitatea ",
        "loc. ",
        "sat ",
        "comuna ",
        "com. ",
    ):
        low = first.lower()
        if low.startswith(prefix):
            return first[len(prefix) :].strip()[:120]
    return first[:120]


@dataclass
class RegistruShelterRow:
    county_slug: str
    judet_label: str
    page_url: str
    title: str
    adresa: str
    telefon: str
    email: str
    tip_colaborator: str
    adapost_public: str
    localitate: str
    reprezentant: str
    nota_interna: str
    fingerprint: str

    def to_csv_dict(self) -> dict[str, str]:
        org = (self.title or "").strip()[:255]
        disp = org or self.judet_label
        return {
            "email": self.email,
            "telefon": self.telefon,
            "tip_cont": StaffOnboardingLead.KIND_ADAPOST,
            "tip_colaborator": self.tip_colaborator,
            "prenume": "",
            "nume": "",
            "denumire_afisata_contact": disp[:200],
            "username_propus": "",
            "judet": self.judet_label[:120],
            "localitate": self.localitate[:120],
            "denumire_organizatie": org,
            "denumire_legala": "",
            "cui": "",
            "cui_cu_ro": "",
            "reg_com": "",
            "adresa_firma": (self.adresa or "")[:255],
            "reprezentant_legal": (self.reprezentant or "")[:255],
            "judet_firma": "",
            "localitate_firma": "",
            "adapost_public_ong": self.adapost_public,
            "segmente": "noutati_ong_adapost",
            "marketing_email_viitor": "",
            "nota_interna": self.nota_interna[:5000],
            "stare": StaffOnboardingLead.ST_READY,
        }


def _fields_from_plain_lines(plain: str) -> dict[str, str]:
    lines = [x.strip() for x in plain.split("\n") if x.strip()]
    out: dict[str, str] = {}
    i = 0
    while i < len(lines):
        line = lines[i]
        key_raw = ""
        tail = ""
        if line.endswith(":") and line.count(":") == 1:
            key_raw = line[:-1].strip()
            i += 1
            tail = lines[i] if i < len(lines) else ""
        elif ":" in line:
            key_raw, _, tail = line.partition(":")
            key_raw, tail = key_raw.strip(), tail.strip()
        else:
            i += 1
            continue
        key = _norm_li_label(key_raw)
        tail = (tail or "").strip()
        if "adresa" in key and "adapost" in key:
            out["adresa"] = tail
        elif "responsabil" in key and "adopt" in key:
            out["responsabil"] = tail
        elif "tipul" in key and "adapost" in key:
            out["tip"] = tail
        elif "capacitate" in key:
            out["capacitate"] = tail
        elif "program" in key:
            out["program"] = tail
        elif "promovare" in key:
            out["promovare"] = tail
        i += 1
    return out


def _p_html_with_continuation(p: Tag) -> tuple[str, Tag | None]:
    h = str(p)
    nxt: Tag | None = None
    if "Adresa adapostului" in h and "Capacitatea maxima de cazare in adapost" not in h:
        cand = p.find_next_sibling("p")
        if cand and "Tipul adapostului" in str(cand) and "Adresa adapostului" not in str(cand):
            h += str(cand)
            nxt = cand
    return h, nxt


def _parse_p_span_fields(p: Tag) -> dict[str, str]:
    """Un singur <span> cu <br /> (Brașov) sau întreg <p> cu mai multe span-uri (Buzău)."""
    html, _ = _p_html_with_continuation(p)
    frag = re.sub(r"(?is)<br\s*/?>", "\n", html)
    mini = BeautifulSoup(frag, "html.parser")
    plain = mini.get_text("\n", strip=True)
    return _fields_from_plain_lines(plain)


def _title_before_p_detail(p: Tag) -> str:
    """Titlu din <p> anterior (doar nume adăpost), nu linia cu adresă."""
    cur: Tag | NavigableString | None = p.previous_sibling
    steps = 0
    while cur is not None and steps < 20:
        steps += 1
        prev = cur.previous_sibling
        if isinstance(cur, NavigableString):
            cur = prev
            continue
        if isinstance(cur, Tag) and cur.name == "p":
            st = cur.find("strong")
            if st:
                t = st.get_text(" ", strip=True)
                if t and "ADAPOSTURI DIN" not in t.upper() and "Adresa adapostului" not in t:
                    return t
            cur = prev
            continue
        cur = prev
    return ""


def _title_for_detail_p(p: Tag) -> str:
    """Titlu din primul span al aceluiași <p> (Buzău) sau din <p> anterior (Brașov)."""
    for sp in p.find_all("span", recursive=False):
        st = sp.find("strong")
        if not st:
            continue
        t = st.get_text(" ", strip=True)
        if not t or "ADAPOSTURI DIN" in t.upper():
            continue
        if "Adresa adapostului" in t:
            break
        return t
    return _title_before_p_detail(p)


def _shelter_row_from_fields(
    county_slug: str,
    judet_label: str,
    page_url: str,
    fields: dict[str, str],
    title: str,
    seen_fp: set[str],
) -> RegistruShelterRow | None:
    adresa = (fields.get("adresa") or "").strip()
    if not adresa:
        return None
    title = (title or "").strip() or (fields.get("promovare") or "Adăpost")[:255]

    resp = fields.get("responsabil") or ""
    email = _email_from(resp)
    phone = _phones_from(resp) or _phones_from(adresa)
    tip_sub, pub = _tip_colab_and_public(fields.get("tip") or "")
    loc = _localitate_heuristic(adresa)
    rep = _EMAIL_RE.sub("", resp).strip() if email else (resp or "").strip()
    rep = re.sub(r"\(\s*\)", "", rep)
    rep = re.sub(r"\s*;\s*$", "", rep)
    rep = re.sub(r"\s*,\s*$", "", rep)
    rep = re.sub(r"\s+", " ", rep).strip()[:255]

    fp = f"{county_slug}|{_fold(title)}|{_fold(adresa)}"
    if fp in seen_fp:
        return None
    seen_fp.add(fp)

    extra = []
    if fields.get("capacitate"):
        extra.append(f"Capacitate: {fields['capacitate']}")
    if fields.get("program"):
        extra.append(f"Program: {fields['program'][:200]}")
    note_parts = [
        f"Sursă: registru-caini.ro",
        f"URL județ: {page_url}",
        f"fingerprint={fp}",
    ]
    if extra:
        note_parts.append("; ".join(extra))
    nota = " | ".join(note_parts)

    return RegistruShelterRow(
        county_slug=county_slug,
        judet_label=judet_label,
        page_url=page_url,
        title=title,
        adresa=adresa,
        telefon=phone,
        email=email,
        tip_colaborator=tip_sub,
        adapost_public=pub,
        localitate=loc,
        reprezentant=rep,
        nota_interna=nota,
        fingerprint=fp,
    )


def parse_county_html(html: str, county_slug: str, judet_label: str, page_url: str) -> list[RegistruShelterRow]:
    soup = BeautifulSoup(html, "html.parser")
    content = soup.find(id="content")
    if not content:
        content = soup.select_one("div.page-content")
    if not content:
        return []

    rows: list[RegistruShelterRow] = []
    seen_fp: set[str] = set()

    for ul in content.find_all("ul"):
        blob = ul.get_text(" ", strip=True)
        if "Adresa adapostului" not in blob and "Adresa adăpostului" not in blob:
            continue
        fields = _parse_ul_block(ul)
        title = _title_before_ul(ul)
        r = _shelter_row_from_fields(county_slug, judet_label, page_url, fields, title, seen_fp)
        if r:
            rows.append(r)

    skip_p_ids: set[int] = set()
    for p in content.find_all("p"):
        if id(p) in skip_p_ids:
            continue
        if "Adresa adapostului" not in str(p):
            continue
        _, cont = _p_html_with_continuation(p)
        if cont is not None:
            skip_p_ids.add(id(cont))
        fields = _parse_p_span_fields(p)
        if not fields.get("adresa"):
            continue
        title = _title_for_detail_p(p)
        r = _shelter_row_from_fields(county_slug, judet_label, page_url, fields, title, seen_fp)
        if r:
            rows.append(r)

    return rows


def fetch_url(url: str, timeout: int = 45) -> str:
    req = urllib.request.Request(url, headers={"User-Agent": UA, "Accept-Language": "ro-RO,ro;q=0.9,en;q=0.8"})
    with urllib.request.urlopen(req, timeout=timeout) as resp:
        raw = resp.read()
    return raw.decode("utf-8", errors="replace")


def iter_county_rows(
    delay_sec: float = 1.25,
    slugs_filter: set[str] | None = None,
) -> Iterator[tuple[str, str, str, list[RegistruShelterRow]]]:
    """
    Yields (county_slug, judet_label, page_url, rows) per județ.
    """
    for slug, label, page_url in COUNTY_PAGES:
        if slugs_filter is not None and slug not in slugs_filter:
            continue
        try:
            html = fetch_url(page_url)
        except urllib.error.HTTPError:
            yield slug, label, page_url, []
            time.sleep(delay_sec)
            continue
        except OSError:
            yield slug, label, page_url, []
            time.sleep(delay_sec)
            continue
        if "WAF Forbidden" in html[:800] or len(html) < 2000:
            yield slug, label, page_url, []
            time.sleep(delay_sec)
            continue
        rows = parse_county_html(html, slug, label, page_url)
        yield slug, label, page_url, rows
        time.sleep(delay_sec)


def rows_to_csv_lines(all_rows: list[RegistruShelterRow]) -> list[dict[str, str]]:
    return [r.to_csv_dict() for r in all_rows]
