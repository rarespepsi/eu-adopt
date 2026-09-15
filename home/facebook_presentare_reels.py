"""
Redistribuire săptămânală a celor 2 video de prezentare EU-Adopt pe FB RO.
Luni → reel 1 · Miercuri → reel 2 (ora din cron, Europe/Bucharest).
"""
from __future__ import annotations

import logging
from dataclasses import dataclass

from home.facebook_page_post import post_to_facebook_page

logger = logging.getLogger(__name__)

SITE = "https://eu-adopt.ro/"


@dataclass(frozen=True)
class PresentareReel:
    key: str  # "lun" | "mie"
    reel_url: str
    label: str


# Memorate 15 sep 2026 — postări originale pe pagina RO.
PRESENTARE_REELS: tuple[PresentareReel, ...] = (
    PresentareReel(
        key="lun",
        reel_url="https://www.facebook.com/reel/1130799632607236/",
        label="prezentare (luni)",
    ),
    PresentareReel(
        key="mie",
        reel_url="https://www.facebook.com/reel/2150287002500386/",
        label="prezentare (miercuri)",
    ),
)


def reel_for_weekday(weekday: int) -> PresentareReel | None:
    """weekday: Monday=0 … Sunday=6 (datetime.weekday())."""
    if weekday == 0:
        return PRESENTARE_REELS[0]
    if weekday == 2:
        return PRESENTARE_REELS[1]
    return None


def reel_by_key(key: str) -> PresentareReel | None:
    k = (key or "").strip().lower()
    aliases = {"lun": "lun", "mon": "lun", "luni": "lun", "1": "lun", "mie": "mie", "wed": "mie", "miercuri": "mie", "2": "mie"}
    want = aliases.get(k)
    if not want:
        return None
    for r in PRESENTARE_REELS:
        if r.key == want:
            return r
    return None


def presentare_repost_message(reel: PresentareReel) -> str:
    return (
        "Dragi prieteni din teren —\n\n"
        "Adăposturi și ONG-uri, cabinete veterinare, saloane de grooming, magazine, "
        "hoteluri pentru animale, transportatori și primării:\n\n"
        "Vă invităm să urmăriți video-ul de prezentare EU-Adopt — ca să vedeți clar "
        "cum vă ajută platforma.\n\n"
        f"Video: {reel.reel_url}\n"
        f"Platformă: {SITE}\n\n"
        "Împreună le dăm animalelor fără stăpân o șansă reală.\n"
        "Echipa EU-Adopt\n\n"
        "#EUAdopt #Adaposturi #Primarii #CabineteVeterinare #Grooming #Adoptii"
    )


def post_presentare_reel(reel: PresentareReel, *, market: str = "ro"):
    """Postează pe FB (link către reel + mesaj). Returnează FacebookPostResult."""
    msg = presentare_repost_message(reel)
    return post_to_facebook_page(
        message=msg,
        link=reel.reel_url,
        image_url="",
        market=market,
    )
