"""
Afișare i18n pentru valori de pe fișa animal (talie, da/nu, vârstă etc.).
Valorile din DB rămân RO; doar eticheta vizibilă pe site EU (EN/DE/FR/ES).
"""
from __future__ import annotations

import re
import unicodedata

_YES_NO: dict[str, dict[str, str]] = {
    "en": {"da": "Yes", "nu": "No", "nu stiu": "Don't know"},
    "de": {"da": "Ja", "nu": "Nein", "nu stiu": "Weiss nicht"},
    "fr": {"da": "Oui", "nu": "Non", "nu stiu": "Je ne sais pas"},
    "es": {"da": "Sí", "nu": "No", "nu stiu": "No sé"},
}

_SIZE: dict[str, dict[str, str]] = {
    "en": {"mica": "Small", "medie": "Medium", "mare": "Large"},
    "de": {"mica": "Klein", "medie": "Mittel", "mare": "Gross"},
    "fr": {"mica": "Petit", "medie": "Moyen", "mare": "Grand"},
    "es": {"mica": "Pequeño", "medie": "Mediano", "mare": "Grande"},
}

_COLOR: dict[str, dict[str, str]] = {
    "en": {
        "negru": "Black",
        "alb": "White",
        "maro": "Brown",
        "gri": "Grey",
        "galben": "Yellow",
        "rosu": "Red",
        "portocaliu": "Orange",
        "crem": "Cream",
        "bej": "Beige",
        "bejue": "Beige",
        "tigrat": "Tabby",
        "bicolor": "Bicolor",
        "tricolor": "Tricolor",
        "mix": "Mixed",
        "mixt": "Mixed",
        "roscat": "Ginger",
        "patat": "Spotted",
        "alta culoare": "Other colour",
    },
    "de": {
        "negru": "Schwarz",
        "alb": "Weiss",
        "maro": "Braun",
        "gri": "Grau",
        "galben": "Gelb",
        "rosu": "Rot",
        "portocaliu": "Orange",
        "crem": "Creme",
        "bej": "Beige",
        "bejue": "Beige",
        "tigrat": "Getigert",
        "bicolor": "Zweifarbig",
        "tricolor": "Dreifarbig",
        "mix": "Gemischt",
        "mixt": "Gemischt",
        "roscat": "Rotbraun",
        "patat": "Gefleckt",
        "alta culoare": "Andere Farbe",
    },
    "fr": {
        "negru": "Noir",
        "alb": "Blanc",
        "maro": "Marron",
        "gri": "Gris",
        "galben": "Jaune",
        "rosu": "Rouge",
        "portocaliu": "Orange",
        "crem": "Crème",
        "bej": "Beige",
        "bejue": "Beige",
        "tigrat": "Tigré",
        "bicolor": "Bicolore",
        "tricolor": "Tricolore",
        "mix": "Mixte",
        "mixt": "Mixte",
        "roscat": "Roux",
        "patat": "Tacheté",
        "alta culoare": "Autre couleur",
    },
    "es": {
        "negru": "Negro",
        "alb": "Blanco",
        "maro": "Marrón",
        "gri": "Gris",
        "galben": "Amarillo",
        "rosu": "Rojo",
        "portocaliu": "Naranja",
        "crem": "Crema",
        "bej": "Beige",
        "bejue": "Beige",
        "tigrat": "Atigrado",
        "bicolor": "Bicolor",
        "tricolor": "Tricolor",
        "mix": "Mixto",
        "mixt": "Mixto",
        "roscat": "Pelirrojo",
        "patat": "Manchado",
        "alta culoare": "Otro color",
    },
}


def _fold(s: str) -> str:
    s = (s or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def _norm_lang(lang: str | None) -> str:
    code = (lang or "en").strip().lower().split("-")[0]
    if code in _YES_NO:
        return code
    return "en"


def _format_age(key: str, lang: str) -> str | None:
    if key == "<1 an":
        return {
            "en": "<1 year",
            "de": "<1 Jahr",
            "fr": "<1 an",
            "es": "<1 año",
        }.get(lang, "<1 year")
    if key == "1 an":
        return {
            "en": "1 year",
            "de": "1 Jahr",
            "fr": "1 an",
            "es": "1 año",
        }.get(lang, "1 year")
    m = re.fullmatch(r"(\d+)\s*ani", key)
    if m:
        n = m.group(1)
        return {
            "en": f"{n} years",
            "de": f"{n} Jahre",
            "fr": f"{n} ans",
            "es": f"{n} años",
        }.get(lang, f"{n} years")
    m = re.fullmatch(r"(\d+)\+\s*ani", key)
    if m:
        n = m.group(1)
        return {
            "en": f"{n}+ years",
            "de": f"{n}+ Jahre",
            "fr": f"{n}+ ans",
            "es": f"{n}+ años",
        }.get(lang, f"{n}+ years")
    m = re.fullmatch(r"(\d+)\s*luni?", key)
    if m:
        n = m.group(1)
        if lang == "de":
            return "1 Monat" if n == "1" else f"{n} Monate"
        if lang == "fr":
            return "1 mois" if n == "1" else f"{n} mois"
        if lang == "es":
            return "1 mes" if n == "1" else f"{n} meses"
        return f"{n} month" if n == "1" else f"{n} months"
    return None


def pet_field_value(raw: str | None, lang: str | None = "en") -> str:
    """
    Traduce valori tipice de select/afișare pe fișă în limba cerută.
    Dacă nu recunoaștem textul, îl lăsăm neschimbat.
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""

    lang = _norm_lang(lang)
    key = _fold(text)

    yn = _YES_NO[lang]
    if key in yn:
        return yn[key]
    sz = _SIZE[lang]
    if key in sz:
        return sz[key]
    col = _COLOR[lang]
    if key in col:
        return col[key]

    age = _format_age(key, lang)
    if age is not None:
        return age

    m = re.fullmatch(r"([\d.,]+)\s*kile", key)
    if m:
        return f"{m.group(1)} kg"

    return text


def pet_field_value_en(raw: str | None) -> str:
    """Compat: EN (folosit în teste / call sites vechi)."""
    return pet_field_value(raw, "en")
