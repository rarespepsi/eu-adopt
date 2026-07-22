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

# Host-uri implicite hub — principal fără cratimă (override: EUADOPT_EU_HUB_HOSTS=...).
_DEFAULT_EU_HUB_HOSTS = (
    "euadopt.com",
    "www.euadopt.com",
    "euadopt.eu",
    "www.euadopt.eu",
    "euadopt.org",
    "www.euadopt.org",
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
EU_SITE_BLOCKED_URL_NAMES = frozenset(
    {
        "servicii",
        "shop",
        "shop_comanda_personalizate",
        "shop_magazin_foto",
        "shop_magazin_foto_more",
        "transport",
        "transport_submit",
        "transport_dispatch_accept",
        "transport_dispatch_decline",
        "transport_dispatch_cancel_user",
        "transport_op_release_job",
        "transport_dispatch_rate",
        "transport_operator_panel",
        "transport_operator_job_detail",
        "transport_op_accept_pending",
        "transport_op_decline_pending",
        "signup_colaborator",
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
    "/transport/",
    "/collab/",
    "/publicitate/",
    "/reclama/",
    "/donatii/",
    "/custi/",
    "/signup/colaborator",
)


def pick_language_for_hub(request) -> str:
    forced = forced_locale_for_host(request.get_host())
    if forced:
        return forced
    session = getattr(request, "session", None)
    if session is not None:
        sess_lang = (session.get("django_language") or "").strip().lower()
        if sess_lang in EU_SITE_LANGUAGE_CODES:
            return sess_lang
    cookie_lang = (request.COOKIES.get(settings.LANGUAGE_COOKIE_NAME) or "").strip().lower()
    if cookie_lang in EU_SITE_LANGUAGE_CODES:
        return cookie_lang
    accept = (request.META.get("HTTP_ACCEPT_LANGUAGE") or "").split(",")[0].strip().lower()
    if accept:
        primary = accept.split("-")[0]
        if primary in EU_SITE_LANGUAGE_CODES:
            return primary
    return EU_SITE_DEFAULT_LANGUAGE


def path_blocked_on_eu_hub(path: str) -> bool:
    p = (path or "/").lower()
    for prefix in EU_SITE_BLOCKED_PATH_PREFIXES:
        if p.startswith(prefix):
            return True
    return False


def eu_site_context_for_request(request) -> dict[str, Any]:
    if not eu_product_skin_enabled():
        return {
            "eu_site_hub": False,
            "eu_site_active": False,
            "eu_site_lang": "",
            "eu_site_languages": [],
            "eu_nav_text": {},
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
            "eu_nav_text": {},
        }
    lang = get_language() or EU_SITE_DEFAULT_LANGUAGE
    if lang not in EU_SITE_LANGUAGE_CODES:
        lang = EU_SITE_DEFAULT_LANGUAGE
    from home.eu_nav_labels import eu_nav_label

    nav_keys = (
        "home",
        "pets",
        "shelters",
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
    )
    eu_nav_text = {k: eu_nav_label(lang, k) for k in nav_keys}

    return {
        "eu_site_hub": hub,
        "eu_site_active": eu,
        "eu_site_lang": lang,
        "eu_site_languages": EU_SITE_LANGUAGE_CHOICES,
        "eu_nav_text": eu_nav_text,
    }
