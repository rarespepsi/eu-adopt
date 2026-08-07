"""
Hub EU (.com / .eu / .org): același Django + DB, meniu adopție, limbi europene.
"""
from __future__ import annotations

import os
from typing import Any

from django.conf import settings
from django.utils.translation import get_language

# Limbi oficiale UE + engleză (hub). Cod Django → nume afișat în selector.
EU_SITE_LANGUAGE_CHOICES: tuple[tuple[str, str], ...] = (
    ("en", "English"),
    ("bg", "Български"),
    ("hr", "Hrvatski"),
    ("cs", "Čeština"),
    ("da", "Dansk"),
    ("nl", "Nederlands"),
    ("et", "Eesti"),
    ("fi", "Suomi"),
    ("fr", "Français"),
    ("de", "Deutsch"),
    ("el", "Ελληνικά"),
    ("hu", "Magyar"),
    ("ga", "Gaeilge"),
    ("it", "Italiano"),
    ("lv", "Latviešu"),
    ("lt", "Lietuvių"),
    ("mt", "Malti"),
    ("pl", "Polski"),
    ("pt", "Português"),
    ("ro", "Română"),
    ("sk", "Slovenčina"),
    ("sl", "Slovenščina"),
    ("es", "Español"),
    ("sv", "Svenska"),
)

EU_SITE_LANGUAGE_CODES = frozenset(code for code, _ in EU_SITE_LANGUAGE_CHOICES)

EU_SITE_DEFAULT_LANGUAGE = "en"

# Variantă B — hub .com: limbile de circulație EU (selector + UI pack complet).
EU_HUB_UI_LANGUAGE_CODES: frozenset[str] = frozenset(
    {"en", "de", "fr", "es", "it", "pl", "nl", "pt", "ro"}
)

EU_HUB_UI_LANGUAGE_CHOICES: tuple[tuple[str, str], ...] = tuple(
    (code, label) for code, label in EU_SITE_LANGUAGE_CHOICES if code in EU_HUB_UI_LANGUAGE_CODES
)

# Cod țară ISO pentru steag PNG (flagcdn) — nu emoji (pe Windows apar ca inițiale).
EU_SITE_FLAG_ISO: dict[str, str] = {
    "en": "gb",
    "bg": "bg",
    "hr": "hr",
    "cs": "cz",
    "da": "dk",
    "nl": "nl",
    "et": "ee",
    "fi": "fi",
    "fr": "fr",
    "de": "de",
    "el": "gr",
    "hu": "hu",
    "ga": "ie",
    "it": "it",
    "lv": "lv",
    "lt": "lt",
    "mt": "mt",
    "pl": "pl",
    "pt": "pt",
    "ro": "ro",
    "sk": "sk",
    "sl": "si",
    "es": "es",
    "sv": "se",
}


def eu_flag_iso_for_lang(lang: str | None) -> str:
    code = (lang or EU_SITE_DEFAULT_LANGUAGE).split("-")[0].lower()
    return EU_SITE_FLAG_ISO.get(code, "eu")


def eu_flag_img_url(lang: str | None) -> str:
    iso = eu_flag_iso_for_lang(lang)
    return f"https://flagcdn.com/20x15/{iso}.png"


# Host-uri hub EU — doar .com (override: EUADOPT_EU_HUB_HOSTS=...).
# .eu / .org fac 301 → .com (vezi euadopt_domains).
_DEFAULT_EU_HUB_HOSTS = (
    "euadopt.com",
    "www.euadopt.com",
)

# Domenii cu cratimă → redirect 301 (registru home.euadopt_domains; excepție: eu-adopt.ro).
EU_COUNTRY_TLD_LOCALE: dict[str, str] = {
    "de": "de",
    "fr": "fr",
    "es": "es",
}


def eu_hub_hosts() -> frozenset[str]:
    raw = (os.environ.get("EUADOPT_EU_HUB_HOSTS") or "").strip()
    if raw:
        parts = [h.strip().lower() for h in raw.split(",") if h.strip()]
        return frozenset(parts)
    return frozenset(_DEFAULT_EU_HUB_HOSTS)


def normalize_host(host: str | None) -> str:
    h = (host or "").strip().lower()
    if ":" in h:
        h = h.split(":", 1)[0]
    return h


def is_eu_hub_host(host: str | None) -> bool:
    return normalize_host(host) in eu_hub_hosts()


def hyphen_redirect_target_host(host: str | None) -> str | None:
    from home.euadopt_domains import hyphen_redirect_map

    h = normalize_host(host)
    return hyphen_redirect_map().get(h)


def is_eu_country_host(host: str | None) -> bool:
    h = normalize_host(host)
    if not h:
        return False
    for tld in EU_COUNTRY_TLD_LOCALE:
        if h in (f"euadopt.{tld}", f"www.euadopt.{tld}"):
            return True
    return False


def forced_locale_for_host(host: str | None) -> str | None:
    """None = hub cu selector; altfel cod limba forțat (.de, .fr, .es)."""
    h = normalize_host(host)
    if not h or is_eu_hub_host(h):
        return None
    for tld, loc in EU_COUNTRY_TLD_LOCALE.items():
        if h in (f"euadopt.{tld}", f"www.euadopt.{tld}"):
            return loc if loc in EU_SITE_LANGUAGE_CODES else EU_SITE_DEFAULT_LANGUAGE
    return None


def eu_product_skin_enabled() -> bool:
    return bool(getattr(settings, "EUADOPT_EU_PRODUCT_SKIN", False))


def is_eu_site_host(host: str | None) -> bool:
    if not eu_product_skin_enabled():
        return False
    return is_eu_hub_host(host) or is_eu_country_host(host)


# Rute RO-only: redirect Acasă pe hub EU (staff Django admin rămâne pe /admin/).
# Transport e PERMIS pe EU (flux normal + sponsorizare autocar).
# Adăpost/ONG e BLOCAT pe EU (doar pe .ro).
EU_SITE_BLOCKED_URL_NAMES = frozenset(
    {
        "servicii",
        "shop",
        "shop_comanda_personalizate",
        "shop_magazin_foto",
        "shop_magazin_foto_more",
        "shelter_directory",
        "shelter_detail",
        "signup_colaborator",
        "signup_organizatie",
        "inscriere",
        "publicitate_harta",
        "publicitate_cos",
        "publicitate_my_orders",
        "reclama_staff",
        "i_love_cos",
        "i_love_cos_checkout",
        "i_love_cos_istoric",
    }
)

EU_SITE_BLOCKED_PATH_PREFIXES = (
    "/shop/",
    "/servicii/",
    "/adaposturi/",
    "/collab/",
    "/publicitate/",
    "/reclama/",
    # /donatii/ — accesibil pe EU pentru traducere / preview (lansare publică mai târziu)
    "/signup/colaborator",
    "/signup/organizatie",
)


def pick_language_for_hub(request) -> str:
    """
    Hub (.com): EN implicit; selector cu limbile EU_HUB_UI (cookie/sesiune/Accept-Language).
    Țară (.de/.fr/.es): limba TLD, exceptând schimbare manuală (eu_lang_manual).
    """
    host = request.get_host()
    forced = forced_locale_for_host(host)
    session = getattr(request, "session", None)
    sess_lang = ""
    if session is not None:
        sess_lang = (session.get("django_language") or "").strip().lower()
    cookie_lang = (request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) or "").strip().lower()

    allowed = EU_HUB_UI_LANGUAGE_CODES if is_eu_hub_host(host) else EU_SITE_LANGUAGE_CODES

    if forced:
        manual = bool(session and session.get("eu_lang_manual"))
        if manual:
            # Cookie from set_language is authoritative after a manual switch
            if cookie_lang in allowed:
                return cookie_lang
            if sess_lang in allowed:
                return sess_lang
        return forced

    # Hub (.com): cookie first (set_language), then session, then Accept-Language
    if cookie_lang in allowed:
        return cookie_lang
    if sess_lang in allowed:
        return sess_lang
    accept = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").split(",")[0].strip().lower()
    if accept:
        primary = accept.split("-")[0]
        if primary in allowed:
            return primary
    return EU_SITE_DEFAULT_LANGUAGE


RO_CANONICAL_HOST = "eu-adopt.ro"
HREFLANG_HOSTS: tuple[tuple[str, str], ...] = (
    ("ro", "eu-adopt.ro"),
    ("en", "euadopt.com"),
    ("de", "euadopt.de"),
    ("fr", "euadopt.fr"),
    ("es", "euadopt.es"),
)


def seo_canonical_url(request) -> str:
    """
    Canonical anti-duplicate: URL echivalent pe eu-adopt.ro
    (aceeași bază / aceleași animale), indiferent de hostul vizitat.
    """
    path = request.path or "/"
    return f"https://{RO_CANONICAL_HOST}{path}"


def seo_hreflang_alternates(request) -> list[dict[str, str]]:
    path = request.path or "/"
    out = [{"hreflang": code, "href": f"https://{host}{path}"} for code, host in HREFLANG_HOSTS]
    out.append({"hreflang": "x-default", "href": f"https://euadopt.com{path}"})
    return out


def path_blocked_on_eu_hub(path: str) -> bool:
    p = (path or "/").lower()
    for prefix in EU_SITE_BLOCKED_PATH_PREFIXES:
        if p.startswith(prefix):
            return True
    return False


def eu_site_context_for_request(request) -> dict[str, Any]:
    from home.eu_procedures import procedures_context

    if not eu_product_skin_enabled():
        return {
            "eu_site_hub": False,
            "eu_site_active": False,
            "eu_site_lang": "",
            "eu_site_languages": [],
            "eu_site_flag_url": "",
            "eu_nav_text": {},
            "eu_ui": {},
            "eu_force_english": False,
            **procedures_context(eu_active=False),
        }
    host = request.get_host()
    hub = is_eu_hub_host(host)
    eu = hub or forced_locale_for_host(host) is not None
    if not eu:
        return {
            "eu_site_hub": False,
            "eu_site_active": False,
            "eu_site_lang": "",
            "eu_site_languages": [],
            "eu_site_flag_url": "",
            "eu_nav_text": {},
            "eu_ui": {},
            "eu_force_english": False,
            **procedures_context(eu_active=False),
        }
    lang = get_language() or EU_SITE_DEFAULT_LANGUAGE
    if lang not in EU_SITE_LANGUAGE_CODES:
        lang = EU_SITE_DEFAULT_LANGUAGE
    # Prefer middleware-resolved language when available
    picked = None
    try:
        picked = pick_language_for_hub(request)
    except Exception:
        picked = None
    if picked and picked in EU_SITE_LANGUAGE_CODES:
        if hub and picked not in EU_HUB_UI_LANGUAGE_CODES:
            picked = EU_SITE_DEFAULT_LANGUAGE
        lang = picked
    elif hub and lang not in EU_HUB_UI_LANGUAGE_CODES:
        lang = EU_SITE_DEFAULT_LANGUAGE
    from home.eu_nav_labels import eu_nav_label
    from home.eu_ui_labels import eu_ui_pack

    nav_keys = (
        "home",
        "pets",
        "transport",
        "mypet",
        "ilove",
        "login_cta",
        "logout",
        "terms",
        "contact",
        "on_site",
        "adopted",
        "search_ph",
        "lang_label",
        "open_menu",
        "close_menu",
        "eu_blocked",
    )
    nav_lang = lang
    eu_nav_text = {k: eu_nav_label(nav_lang, k) for k in nav_keys}
    lang_choices = EU_HUB_UI_LANGUAGE_CHOICES if hub else EU_SITE_LANGUAGE_CHOICES

    return {
        "eu_site_hub": hub,
        "eu_site_active": eu,
        "eu_site_lang": nav_lang,
        "eu_site_languages": lang_choices,
        "eu_site_flag_url": eu_flag_img_url(nav_lang),
        "eu_nav_text": eu_nav_text,
        "eu_ui": eu_ui_pack(lang) if eu else {},
        "eu_force_english": False,
        **procedures_context(eu_active=eu),
    }
