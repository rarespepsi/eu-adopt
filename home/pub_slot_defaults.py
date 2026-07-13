"""Cover-uri default și link placeholder pentru sloturi live (până la material client)."""
from __future__ import annotations

import hashlib
from typing import Iterable
from urllib.parse import urlencode

from django.templatetags.static import static
from django.urls import reverse

PUB_COVER_COUNT = 30
PUB_COVER_STATIC_PREFIX = "images/pub/covers/"
EU_ADOPT_FACEBOOK_URL = (
    "https://www.facebook.com/people/EU-Adopt-Adoptii-Caini-si-Pisici/61588044314372/"
)


def pub_cover_static_path(slot_code: str) -> str:
    """Cale statică deterministă — același slot = aceeași imagine."""
    code = (slot_code or "").strip() or "?"
    digest = hashlib.md5(code.encode("utf-8")).hexdigest()
    idx = (int(digest[:8], 16) % PUB_COVER_COUNT) + 1
    return f"{PUB_COVER_STATIC_PREFIX}cover_{idx:02d}.svg"


def pub_cover_url(slot_code: str) -> str:
    return static(pub_cover_static_path(slot_code))


def pub_harta_url(section: str, slot_code: str) -> str:
    sect = (section or "home").strip().lower()
    code = (slot_code or "").strip()
    q = urlencode({"sect": sect, "slot": code})
    return f"{reverse('publicitate_harta')}?{q}"


def pub_slot_go_url(section: str, slot_code: str) -> str:
    """Link intern pentru tap mobil — redirect server către URL-ul slotului (extern)."""
    sect = (section or "home").strip().lower()
    code = (slot_code or "").strip()
    q = urlencode({"sect": sect, "slot": code})
    return f"{reverse('pub_slot_go')}?{q}"


def _creative_with_href(section: str, slot_code: str, data: dict) -> dict:
    out = dict(data)
    link = (out.get("link") or "").strip()
    if out.get("link_external"):
        out["href"] = pub_slot_go_url(section, slot_code)
    else:
        out["href"] = link or "#"
    return out


def pub_placeholder_link(section: str, slot_code: str) -> str:
    """Link temporar pentru casetele Publi. fără material client (închiriere = flux logat /publicitate/)."""
    del section, slot_code
    return EU_ADOPT_FACEBOOK_URL


def _link_is_external(link: str) -> bool:
    low = (link or "").strip().lower()
    return low.startswith("http://") or low.startswith("https://")


def pub_slot_outbound_url(link: str) -> str | None:
    """URL destinație validă pentru redirect Publi. (doar http/https)."""
    u = (link or "").strip()
    if not _link_is_external(u):
        return None
    return u


def pub_slot_live_creative(section: str, slot_code: str, note=None) -> dict:
    """
    Creative pentru afișare pe site live.
    Fără material client: cover default + link către pagina Facebook EU-Adopt.
    Cu material: imagine/video client; link client dacă e setat, altfel Facebook.
    """
    from .views import _pt_pub_slot_parse_note

    code = (slot_code or "").strip()
    sect = (section or "home").strip().lower()
    default_link = pub_placeholder_link(sect, code)
    default_img = pub_cover_url(code)
    parsed = _pt_pub_slot_parse_note(note) if note is not None else None

    if parsed and (parsed.get("img") or parsed.get("video")):
        link = (parsed.get("link") or "").strip() or default_link
        return _creative_with_href(
            sect,
            code,
            {
                "img": parsed.get("img") or "",
                "video": parsed.get("video") or "",
                "link": link,
                "alt": (parsed.get("alt") or "").strip() or "EU-Adopt pe Facebook",
                "price": (parsed.get("price") or "").strip(),
                "discount": (parsed.get("discount") or "").strip(),
                "is_default_cover": False,
                "link_external": _link_is_external(link),
            },
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
                "alt": "Publicitate",
                "price": (parsed.get("price") or "").strip(),
                "discount": (parsed.get("discount") or "").strip(),
                "is_default_cover": True,
                "link_external": _link_is_external(link),
            },
        )

    return _creative_with_href(
        sect,
        code,
        {
            "img": default_img,
            "video": "",
            "link": default_link,
            "alt": "EU-Adopt pe Facebook",
            "price": "",
            "discount": "",
            "is_default_cover": True,
            "link_external": True,
        },
    )


def pub_slot_fetch_notes(section: str, codes: Iterable[str]) -> dict:
    from home.models import ReclamaSlotNote

    code_list = [c for c in codes if (c or "").strip()]
    if not code_list:
        return {}
    try:
        return {
            n.slot_code: n
            for n in ReclamaSlotNote.objects.filter(section=section, slot_code__in=code_list)
        }
    except Exception:
        return {}


def pub_slots_creatives(section: str, codes: Iterable[str]) -> dict[str, dict]:
    notes = pub_slot_fetch_notes(section, codes)
    return {
        code: pub_slot_live_creative(section, code, notes.get(code))
        for code in codes
    }


def pub_slots_ordered(section: str, codes: Iterable[str]) -> list[dict]:
    creatives = pub_slots_creatives(section, codes)
    return [{"code": code, "creative": creatives[code]} for code in codes]
