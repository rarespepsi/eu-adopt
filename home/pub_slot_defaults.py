"""Cover-uri default și link placeholder pentru sloturi live (până la material client)."""
from __future__ import annotations

import hashlib
from typing import Iterable
from urllib.parse import urlencode

from django.templatetags.static import static
from django.urls import reverse

from home.pub_markets import (
    PUB_MARKET_RO,
    localize_pub_link_for_market,
    normalize_pub_market,
)

PUB_COVER_COUNT = 30
PUB_COVER_STATIC_PREFIX = "images/pub/covers/"

# Placeholder live: poze animale (până la material client) — set curat 6 imagini distincte
PUB_ANIMAL_COVER_COUNT = 6
PUB_ANIMAL_COVER_PREFIX = "images/pub/animals/"
PUB_ANIMAL_COVER_FILES = tuple(f"pub_animale_{n:02d}_a.jpg" for n in range(1, 7))


def pub_animal_cover_static_path(index: int) -> str:
    """index 1..PUB_ANIMAL_COVER_COUNT"""
    i = max(1, min(int(index), PUB_ANIMAL_COVER_COUNT)) - 1
    return f"{PUB_ANIMAL_COVER_PREFIX}{PUB_ANIMAL_COVER_FILES[i]}"


def pub_cover_static_path(slot_code: str) -> str:
    """Cale statică deterministă — același slot = aceeași imagine."""
    code = (slot_code or "").strip() or "?"
    digest = hashlib.md5(code.encode("utf-8")).hexdigest()
    idx = (int(digest[:8], 16) % PUB_ANIMAL_COVER_COUNT) + 1
    return pub_animal_cover_static_path(idx)


def pub_cover_url(slot_code: str) -> str:
    return static(pub_cover_static_path(slot_code))


# Casete rezervate Campanii pe .ro — imagine + link hartă (nu catalog public)
RO_CAMPAIGN_PUB_CODES = frozenset({"A5.3", "P4.3", "TDR.3", "IL.L1"})
RO_CAMPAIGN_PUB_IMAGE = "images/campanii/campanii-gratuite-pub.png"

# HOME coloană stânga — casete EU-Adopt (nu se închiriază; link pagini dedicate)
RO_INTERNAL_HOME_PUB = {
    "A5.1": {
        "image": "images/home/a5-pierdute-gasite.png",
        "url_name": "animale_pierdute",
        "alt": "Animale pierdute sau găsite",
    },
    "A5.2": {
        "image": "images/home/a5-semnaleaza-abuz.png",
        "url_name": "semnaleaza_abuz",
        "alt": "Semnalează un abuz",
    },
}
RO_INTERNAL_HOME_PUB_CODES = frozenset(RO_INTERNAL_HOME_PUB.keys())


def pub_harta_url(section: str, slot_code: str) -> str:
    sect = (section or "home").strip().lower()
    code = (slot_code or "").strip()
    q = urlencode({"sect": sect, "slot": code})
    return f"{reverse('publicitate_harta')}?{q}"


def pub_slot_go_url(section: str, slot_code: str, market: str = PUB_MARKET_RO) -> str:
    """Link intern pentru tap mobil — redirect server către URL-ul slotului (extern)."""
    sect = (section or "home").strip().lower()
    code = (slot_code or "").strip()
    q = urlencode({"sect": sect, "slot": code, "m": normalize_pub_market(market)})
    return f"{reverse('pub_slot_go')}?{q}"


def _link_is_external(link: str) -> bool:
    low = (link or "").strip().lower()
    return low.startswith("http://") or low.startswith("https://")


def normalize_pub_outbound_link(raw: str) -> str:
    """
    Acceptă http://, https://, www.… și căi interne /…
    www.facebook.com → https://www.facebook.com
    """
    u = (raw or "").strip()
    if not u:
        return ""
    # Cale internă site
    if u.startswith("/") and not u.startswith("//"):
        if ".." in u or "\x00" in u:
            return ""
        return u
    low = u.lower()
    if low.startswith("http://") or low.startswith("https://"):
        return u
    if low.startswith("//"):
        return "https:" + u
    if low.startswith("www."):
        return "https://" + u
    # host fără schemă (ex. facebook.com/page) — doar dacă arată a domeniu
    if "." in u and " " not in u and not u.startswith("."):
        return "https://" + u
    return u


def pub_slot_outbound_url(link: str) -> str | None:
    """URL destinație validă pentru redirect Publi. (doar http/https)."""
    u = normalize_pub_outbound_link(link)
    if not _link_is_external(u):
        return None
    return u


def _pick_localized_alt(parsed: dict, lang: str | None) -> str:
    """alt_i18n / i18n[lang].alt / alt — limba activă a vizitei."""
    code = (lang or "").split("-")[0].lower() if lang else ""
    alt_map = parsed.get("alt_i18n")
    if isinstance(alt_map, dict) and code:
        v = (alt_map.get(code) or alt_map.get("en") or "").strip()
        if v:
            return v
    i18n = parsed.get("i18n")
    if isinstance(i18n, dict) and code:
        pack = i18n.get(code) or i18n.get("en")
        if isinstance(pack, dict):
            v = (pack.get("alt") or "").strip()
            if v:
                return v
        elif isinstance(pack, str) and pack.strip():
            return pack.strip()
    return (parsed.get("alt") or "").strip() or "Publicitate"


def _creative_with_href(section: str, slot_code: str, data: dict, market: str = PUB_MARKET_RO) -> dict:
    out = dict(data)
    mkt = normalize_pub_market(market)
    link = localize_pub_link_for_market(
        normalize_pub_outbound_link((out.get("link") or "").strip()), mkt
    )
    out["link"] = link
    if link and _link_is_external(link):
        out["link_external"] = True
        out["href"] = pub_slot_go_url(section, slot_code, mkt)
        out["has_link"] = True
    elif link:
        out["link_external"] = False
        out["href"] = link
        out["has_link"] = True
    else:
        out["link_external"] = False
        out["href"] = ""
        out["has_link"] = False
    return out


def pub_placeholder_link(section: str, slot_code: str) -> str:
    """Fără link implicit — sloturile goale rămân neclickabile până la material client."""
    del section, slot_code
    return ""


def pub_slot_live_creative(
    section: str,
    slot_code: str,
    note=None,
    *,
    market: str = PUB_MARKET_RO,
    lang: str | None = None,
) -> dict:
    """
    Creative pentru afișare pe site live.
    Fără material client: cover default, fără link.
    Cu material: imagine/video client + link client (dacă e setat).
    Pe .ro, sloturile Campanii (A5.3 / P4.3 / TDR.3 / IL.L1) = afiș + link hartă.
    Pe .ro, A5.1 / A5.2 = casete EU-Adopt (pierdute / abuz) — nu catalog PUB.
    """
    from .views import _pt_pub_slot_parse_note

    code = (slot_code or "").strip()
    sect = (section or "home").strip().lower()
    mkt = normalize_pub_market(market)

    if sect == "home" and code in RO_INTERNAL_HOME_PUB_CODES and mkt == PUB_MARKET_RO:
        cfg = RO_INTERNAL_HOME_PUB[code]
        return _creative_with_href(
            sect,
            code,
            {
                "img": static(cfg["image"]),
                "video": "",
                "link": reverse(cfg["url_name"]),
                "alt": cfg["alt"],
                "caption": "",
                "price": "",
                "discount": "",
                "is_default_cover": False,
                "is_internal_home_pub": True,
            },
            market=mkt,
        )

    if code in RO_CAMPAIGN_PUB_CODES and mkt == PUB_MARKET_RO:
        return _creative_with_href(
            sect,
            code,
            {
                "img": static(RO_CAMPAIGN_PUB_IMAGE),
                "video": "",
                "link": reverse("publicitate_campanii_ro"),
                "alt": "Campanii gratuite de sterilizare",
                "caption": "",
                "price": "",
                "discount": "",
                "is_default_cover": False,
                "is_campaign_pub": True,
            },
            market=mkt,
        )

    default_img = pub_cover_url(code)
    parsed = _pt_pub_slot_parse_note(note) if note is not None else None

    if parsed and (parsed.get("img") or parsed.get("video")):
        link = (parsed.get("link") or "").strip()
        caption = (parsed.get("caption") or "").strip()[:200]
        alt = _pick_localized_alt(parsed, lang)
        if not alt or alt in ("Publicitate", "Reclamă", "EU-Adopt"):
            if caption:
                alt = caption
        return _creative_with_href(
            sect,
            code,
            {
                "img": parsed.get("img") or "",
                "video": parsed.get("video") or "",
                "link": link,
                "alt": alt,
                "caption": caption,
                "price": (parsed.get("price") or "").strip(),
                "discount": (parsed.get("discount") or "").strip(),
                "is_default_cover": False,
            },
            market=mkt,
        )

    if parsed and (parsed.get("link") or "").strip():
        link = (parsed.get("link") or "").strip()
        return _creative_with_href(
            sect,
            code,
            {
                "img": default_img,
                "video": "",
                "link": link,
                "alt": _pick_localized_alt(parsed, lang) if parsed.get("alt") or parsed.get("alt_i18n") else "Publicitate",
                "caption": (parsed.get("caption") or "").strip()[:200],
                "price": (parsed.get("price") or "").strip(),
                "discount": (parsed.get("discount") or "").strip(),
                "is_default_cover": True,
            },
            market=mkt,
        )

    return _creative_with_href(
        sect,
        code,
        {
            "img": default_img,
            "video": "",
            "link": "",
            "alt": "EU-Adopt",
            "caption": "",
            "price": "",
            "discount": "",
            "is_default_cover": True,
        },
        market=mkt,
    )


def pub_slot_fetch_notes(
    section: str,
    codes: Iterable[str],
    *,
    market: str = PUB_MARKET_RO,
) -> dict:
    from home.models import ReclamaSlotNote

    code_list = [c for c in codes if (c or "").strip()]
    if not code_list:
        return {}
    mkt = normalize_pub_market(market)
    try:
        return {
            n.slot_code: n
            for n in ReclamaSlotNote.objects.filter(
                section=section, slot_code__in=code_list, market=mkt
            )
        }
    except Exception:
        return {}


def pub_slots_creatives(
    section: str,
    codes: Iterable[str],
    *,
    market: str = PUB_MARKET_RO,
    lang: str | None = None,
) -> dict[str, dict]:
    notes = pub_slot_fetch_notes(section, codes, market=market)
    return {
        code: pub_slot_live_creative(section, code, notes.get(code), market=market, lang=lang)
        for code in codes
    }


def pub_slots_ordered(
    section: str,
    codes: Iterable[str],
    *,
    market: str = PUB_MARKET_RO,
    lang: str | None = None,
) -> list[dict]:
    creatives = pub_slots_creatives(section, codes, market=market, lang=lang)
    return [{"code": code, "creative": creatives[code]} for code in codes]
