"""Signup EU simplu (PF) — doar pe hub/țări EU, fără impact pe .ro."""

from __future__ import annotations

# ISO țară → prefix telefon (E.164)
COUNTRY_TO_PHONE_PREFIX: dict[str, str] = {
    "RO": "+40",
    "AT": "+43",
    "BE": "+32",
    "BG": "+359",
    "HR": "+385",
    "CY": "+357",
    "CZ": "+420",
    "DK": "+45",
    "EE": "+372",
    "FI": "+358",
    "FR": "+33",
    "DE": "+49",
    "GR": "+30",
    "HU": "+36",
    "IE": "+353",
    "IT": "+39",
    "LV": "+371",
    "LT": "+370",
    "LU": "+352",
    "MT": "+356",
    "NL": "+31",
    "PL": "+48",
    "PT": "+351",
    "SK": "+421",
    "SI": "+386",
    "ES": "+34",
    "SE": "+46",
    "CH": "+41",
    "NO": "+47",
    "GB": "+44",
}


def phone_prefix_for_country(code: str | None) -> str:
    c = (code or "").strip().upper()
    return COUNTRY_TO_PHONE_PREFIX.get(c, "+49")


def default_eu_signup_country(request) -> str:
    """Hint țară: TLD (.de→DE) sau limba hub; pe .com poate fi gol."""
    from home.eu_countries import TLD_TO_COUNTRY, default_country_hint_for_host, normalize_country_code

    host_hint = default_country_hint_for_host(request.get_host())
    if host_hint:
        return host_hint
    lang = (getattr(request, "eu_site_lang", None) or "").strip().lower()
    if lang in TLD_TO_COUNTRY:
        return TLD_TO_COUNTRY[lang]
    return normalize_country_code("") or ""


def is_eu_simple_signup_request(request) -> bool:
    return bool(getattr(request, "eu_site_active", False))
