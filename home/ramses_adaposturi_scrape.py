"""
Parsare pagina https://asociatiaramses.ro/adaposturi/ (WordPress + Elementor)
→ rânduri compatibile cu CSV Add USER (același model ca registru-caini.ro).

Structură: pentru fiecare adăpost, un widget text-editor cu <h5> titlu,
urmat de icon-list cu <li> (adresă / telefon / email — ordine variabilă).
Tab-urile „private / publice” sunt în containere .adaposturi-private / .adaposturi-publice.
"""

from __future__ import annotations

import re
import time
import urllib.error
from typing import Iterator

from bs4 import BeautifulSoup, Tag

from home.models import StaffOnboardingLead
from home.registru_caini_scrape import (
    COUNTY_PAGES,
    RegistruShelterRow,
    UA,
    _email_from,
    _fold,
    _localitate_heuristic,
    _phones_from,
    fetch_url,
)

RAMSES_ADAPOSTURI_URL = "https://asociatiaramses.ro/adaposturi/"

_FOOTER_SUBSTR = frozenset(
    {
        "termeni",
        "politica de confidentialitate",
        "politica de cookies",
        "gdpr",
        "contul meu",
    }
)


def _ramses_section_pub_priv(ul: Tag) -> str:
    """'pub' | 'priv' după containerul tab-ului; implicit privat dacă nu găsim."""
    node: Tag | None = ul
    for _ in range(28):
        if node is None:
            break
        cls = " ".join(node.get("class") or [])
        if "adaposturi-publice" in cls:
            return "pub"
        if "adaposturi-private" in cls:
            return "priv"
        node = getattr(node, "parent", None)
    return "priv"


def _title_for_ramses_icon_list(ul: Tag) -> str:
    """Titlul din <h5> din widget-ul text-editor imediat înainte de icon-list."""
    wc = ul.find_parent(class_="elementor-widget-container")
    if not wc:
        return ""
    widget = wc.parent
    if not widget or not getattr(widget, "name", None):
        return ""
    prev = widget.find_previous_sibling()
    while prev is not None:
        if prev.name == "div" and prev.get("class") and "elementor-widget-text-editor" in prev.get("class", []):
            h5 = prev.select_one("h5")
            if h5:
                return h5.get_text(" ", strip=True)
            return ""
        prev = prev.find_previous_sibling()
    return ""


def _digits_only(s: str) -> str:
    return re.sub(r"\D+", "", s or "")


def _looks_like_phone_line(s: str) -> bool:
    t = (s or "").strip()
    if not t:
        return False
    if _phones_from(t):
        return True
    d = _digits_only(t)
    return len(d) >= 9 and t[0] == "0"


def _split_icon_list_texts(texts: list[str]) -> tuple[str, str, str]:
    """Întoarce (adresa_comasată, telefon, email) din liniile listei."""
    emails: list[str] = []
    phones: list[str] = []
    rest: list[str] = []
    for raw in texts:
        t = (raw or "").strip()
        if not t:
            continue
        em = _email_from(t)
        if em:
            emails.append(em)
            continue
        if _looks_like_phone_line(t):
            ph = _phones_from(t) or _digits_only(t)[:40]
            if ph:
                phones.append(ph)
            continue
        rest.append(t)
    email = emails[0] if emails else ""
    phone = phones[0] if phones else ""
    addr = " | ".join(rest).strip()
    return addr, phone, email


def _guess_judet(address: str, title: str) -> str:
    """Euristică: nume județ în text, București (sector), câteva orașe → județ."""
    blob = _fold(f"{address} {title}")
    if not blob:
        return ""
    if "sector" in blob or "bucuresti" in blob:
        return "București"
    labels = [lab for _, lab, _ in COUNTY_PAGES]
    for lab in sorted(labels, key=len, reverse=True):
        if _fold(lab) in blob:
            return lab
    if "ilfov" in blob or "clinceni" in blob or "otopeni" in blob or "voluntari" in blob:
        return "Ilfov"
    # orașe frecvente fără numele județului în adresă
    hints = (
        ("ploiesti", "Prahova"),
        ("targu jiu", "Gorj"),
        ("tg-jiu", "Gorj"),
        ("târgu jiu", "Gorj"),
        ("craiova", "Dolj"),
        ("oradea", "Bihor"),
        ("timisoara", "Timiș"),
        ("timișoara", "Timiș"),
        ("constanta", "Constanța"),
        ("constanța", "Constanța"),
        ("iasi", "Iași"),
        ("iași", "Iași"),
        ("cluj-napoca", "Cluj"),
        ("cluj napoca", "Cluj"),
        ("brasov", "Brașov"),
        ("brașov", "Brașov"),
        ("sibiu", "Sibiu"),
        ("galati", "Galați"),
        ("galați", "Galați"),
        ("bacau", "Bacău"),
        ("bacău", "Bacău"),
        ("focsani", "Vrancea"),
        ("focșani", "Vrancea"),
        ("salonta", "Bihor"),
        ("resita", "Caraș-Severin"),
        ("reșița", "Caraș-Severin"),
        ("cernavoda", "Constanța"),
        ("cernavodă", "Constanța"),
        ("tomești", "Iași"),
        ("tomesti", "Iași"),
    )
    for key, jud in hints:
        if key in blob:
            return jud
    return ""


def _is_footer_icon_list(texts: list[str]) -> bool:
    j = _fold(" ".join(texts))
    return any(m in j for m in _FOOTER_SUBSTR)


def parse_ramses_adaposturi_html(html: str, page_url: str = RAMSES_ADAPOSTURI_URL) -> list[RegistruShelterRow]:
    soup = BeautifulSoup(html, "html.parser")
    rows: list[RegistruShelterRow] = []
    seen_fp: set[str] = set()

    for ul in soup.select("ul.elementor-icon-list-items"):
        texts = []
        for li in ul.select("li.elementor-icon-list-item"):
            span = li.select_one(".elementor-icon-list-text")
            texts.append(span.get_text(" ", strip=True) if span else li.get_text(" ", strip=True))
        if _is_footer_icon_list(texts):
            continue
        title = _title_for_ramses_icon_list(ul)
        if not title or len(title) < 2:
            continue

        addr, phone, email = _split_icon_list_texts(texts)
        if not addr and not phone and not email:
            continue

        section = _ramses_section_pub_priv(ul)
        if section == "pub":
            tip_sub = StaffOnboardingLead.COLLAB_ADPUB
            pub = "1"
        else:
            tip_sub = StaffOnboardingLead.COLLAB_ADPRV
            pub = ""

        jud = _guess_judet(addr, title)
        loc = _localitate_heuristic(addr) if addr else ""
        rep = ""
        if phone and email:
            rep = f"Contact listă Ramses ({phone})"

        adresa = (addr or "").strip()
        if not adresa and phone:
            adresa = phone.strip()[:255]

        fp = f"ramses|{_fold(title)}|{_fold(adresa)}|{section}"
        if fp in seen_fp:
            continue
        seen_fp.add(fp)

        note_parts = [
            "Sursă: asociatiaramses.ro/adaposturi/ (Asociația Ramses)",
            f"URL: {page_url}",
            f"Secțiune listă: {'public' if section == 'pub' else 'privat'}",
            f"fingerprint={fp}",
        ]
        nota = " | ".join(note_parts)

        rows.append(
            RegistruShelterRow(
                county_slug="ramses",
                judet_label=jud[:120] if jud else "",
                page_url=page_url,
                title=title.strip()[:255],
                adresa=adresa[:255],
                telefon=(phone or "")[:40],
                email=(email or "")[:254],
                tip_colaborator=tip_sub,
                adapost_public=pub,
                localitate=(loc or "")[:120],
                reprezentant=(rep or "")[:255],
                nota_interna=nota[:5000],
                fingerprint=fp,
            )
        )

    return rows


def iter_ramses_rows(delay_sec: float = 0.0) -> Iterator[tuple[str, str, list[RegistruShelterRow]]]:
    """
    O singură „pagină” (tot județele sunt agregate pe site).
    Yield: (slug, label, rows) — slug fix 'ramses', label descriptiv.
    """
    try:
        html = fetch_url(RAMSES_ADAPOSTURI_URL)
    except (urllib.error.HTTPError, OSError):
        yield "ramses", "Ramses (toate)", []
        return
    if len(html) < 5000:
        yield "ramses", "Ramses (toate)", []
        return
    rows = parse_ramses_adaposturi_html(html, RAMSES_ADAPOSTURI_URL)
    yield "ramses", "Ramses (toate)", rows
    if delay_sec > 0:
        time.sleep(delay_sec)
