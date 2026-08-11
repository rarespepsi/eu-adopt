"""
Piețe Facebook EU-Adopt (RO/DE/FR/ES/COM).

Tokenurile stau doar în .env (Page token sau System User token ulterior —
aceeași cheie de env, fără schimbare de cod).
"""
from __future__ import annotations

from dataclasses import dataclass

from django.conf import settings

FACEBOOK_MARKETS: tuple[str, ...] = ("ro", "de", "fr", "es", "com")
# Mirror FB: doar din RO către aceste piețe (niciodată invers).
FACEBOOK_MIRROR_TARGET_MARKETS: tuple[str, ...] = ("de", "fr", "es", "com")

MARKET_LANG: dict[str, str] = {
    "ro": "ro",
    "de": "de",
    "fr": "fr",
    "es": "es",
    "com": "en",
}

MARKET_LANG_NAME: dict[str, str] = {
    "ro": "Romanian",
    "de": "German",
    "fr": "French",
    "es": "Spanish",
    "com": "English",
}


@dataclass(frozen=True)
class FacebookMarketCreds:
    market: str
    page_id: str
    # Nu loga / nu afișa tokenul.
    access_token: str

    @property
    def configured(self) -> bool:
        return bool(self.page_id and self.access_token)


def facebook_auto_post_enabled() -> bool:
    return bool(getattr(settings, "FACEBOOK_AUTO_POST_ENABLED", False))


def facebook_graph_version() -> str:
    v = (getattr(settings, "FACEBOOK_GRAPH_API_VERSION", "") or "v21.0").strip()
    return v if v.startswith("v") else f"v{v}"


def facebook_max_posts_per_day() -> int:
    return max(1, int(getattr(settings, "FACEBOOK_MAX_POSTS_PER_DAY", 10) or 10))


def facebook_ro_mirror_enabled() -> bool:
    return bool(getattr(settings, "FACEBOOK_RO_MIRROR_ENABLED", False))


def facebook_ro_mirror_max_per_run() -> int:
    return max(1, int(getattr(settings, "FACEBOOK_RO_MIRROR_MAX_PER_RUN", 10) or 10))


def _env_page_id(market: str) -> str:
    m = (market or "").strip().lower()
    if m == "ro":
        # Compat: EUADOPT_FACEBOOK_PAGE_ID sau _RO
        return (
            (getattr(settings, "FACEBOOK_PAGE_ID_RO", "") or "").strip()
            or (getattr(settings, "FACEBOOK_PAGE_ID", "") or "").strip()
        )
    return (getattr(settings, f"FACEBOOK_PAGE_ID_{m.upper()}", "") or "").strip()


def _env_token(market: str) -> str:
    m = (market or "").strip().lower()
    if m == "ro":
        return (
            (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN_RO", "") or "").strip()
            or (getattr(settings, "FACEBOOK_PAGE_ACCESS_TOKEN", "") or "").strip()
        )
    return (getattr(settings, f"FACEBOOK_PAGE_ACCESS_TOKEN_{m.upper()}", "") or "").strip()


def market_creds(market: str) -> FacebookMarketCreds:
    m = (market or "").strip().lower()
    return FacebookMarketCreds(
        market=m,
        page_id=_env_page_id(m),
        access_token=_env_token(m),
    )


def configured_markets(*, for_mirror_targets: bool = False) -> list[str]:
    """Piețe cu page_id + token setate. RO e inclusă dacă auto-post e activ."""
    if for_mirror_targets:
        candidates = FACEBOOK_MIRROR_TARGET_MARKETS
    else:
        if not facebook_auto_post_enabled():
            return []
        candidates = FACEBOOK_MARKETS
    out: list[str] = []
    for m in candidates:
        if market_creds(m).configured:
            out.append(m)
    return out


def market_lang(market: str) -> str:
    return MARKET_LANG.get((market or "").strip().lower(), "en")
