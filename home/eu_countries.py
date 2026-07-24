"""
Țări pentru adopție EU (catalog ISO 3166-1 alpha-2).
Pas 1: filtru + câmp pe anunț/profil; cataloage județ/oraș rămân RO.
"""
from __future__ import annotations

# (cod, EN, RO) — ordine afișare (RO primul, apoi alfabetic EN)
EU_ADOPTION_COUNTRIES: tuple[tuple[str, str, str], ...] = (
    ("RO", "Romania", "România"),
    ("AT", "Austria", "Austria"),
    ("BE", "Belgium", "Belgia"),
    ("BG", "Bulgaria", "Bulgaria"),
    ("HR", "Croatia", "Croația"),
    ("CY", "Cyprus", "Cipru"),
    ("CZ", "Czechia", "Cehia"),
    ("DK", "Denmark", "Danemarca"),
    ("EE", "Estonia", "Estonia"),
    ("FI", "Finland", "Finlanda"),
    ("FR", "France", "Franța"),
    ("DE", "Germany", "Germania"),
    ("GR", "Greece", "Grecia"),
    ("HU", "Hungary", "Ungaria"),
    ("IE", "Ireland", "Irlanda"),
    ("IT", "Italy", "Italia"),
    ("LV", "Latvia", "Letonia"),
    ("LT", "Lithuania", "Lituania"),
    ("LU", "Luxembourg", "Luxemburg"),
    ("MT", "Malta", "Malta"),
    ("NL", "Netherlands", "Țările de Jos"),
    ("PL", "Poland", "Polonia"),
    ("PT", "Portugal", "Portugalia"),
    ("SK", "Slovakia", "Slovacia"),
    ("SI", "Slovenia", "Slovenia"),
    ("ES", "Spain", "Spania"),
    ("SE", "Sweden", "Suedia"),
    ("CH", "Switzerland", "Elveția"),
    ("NO", "Norway", "Norvegia"),
    ("GB", "United Kingdom", "Regatul Unit"),
)

COUNTRY_CODES: frozenset[str] = frozenset(c[0] for c in EU_ADOPTION_COUNTRIES)

# TLD euadopt.XX → cod țară (hint filtru)
TLD_TO_COUNTRY: dict[str, str] = {
    "de": "DE",
    "fr": "FR",
    "es": "ES",
    "it": "IT",
    "at": "AT",
    "nl": "NL",
    "be": "BE",
    "pl": "PL",
    "pt": "PT",
    "hu": "HU",
    "cz": "CZ",
    "sk": "SK",
    "bg": "BG",
    "hr": "HR",
    "gr": "GR",
    "ie": "IE",
    "se": "SE",
    "dk": "DK",
    "fi": "FI",
}


def normalize_country_code(raw: str | None) -> str:
    code = (raw or "").strip().upper()
    if code in COUNTRY_CODES:
        return code
    return ""


def country_label(code: str | None, *, english: bool = True) -> str:
    c = normalize_country_code(code)
    if not c:
        return ""
    for iso, en, ro in EU_ADOPTION_COUNTRIES:
        if iso == c:
            return en if english else ro
    return c


def country_choices(*, english: bool = True) -> list[tuple[str, str]]:
    return [(iso, en if english else ro) for iso, en, ro in EU_ADOPTION_COUNTRIES]


def default_country_hint_for_host(host: str | None) -> str:
    """
    Hint filtru PT: pe TLD țară (euadopt.de) → DE; pe hub .com → gol (toate);
    pe .ro nu se folosește (piață RO).
    """
    from home.eu_site import is_eu_hub_host, is_eu_site_host, normalize_host

    h = normalize_host(host)
    if not is_eu_site_host(h):
        return "RO"
    if is_eu_hub_host(h):
        return ""
    for tld, code in TLD_TO_COUNTRY.items():
        if h in (f"euadopt.{tld}", f"www.euadopt.{tld}"):
            return code if code in COUNTRY_CODES else ""
    return ""
