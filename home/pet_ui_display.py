"""
Afișare EN pentru valori de pe fișa animal (talie, da/nu, vârstă etc.).
Valorile din DB rămân RO; doar eticheta vizibilă pe site EU.
"""
from __future__ import annotations

import re
import unicodedata

_YES_NO = {
    "da": "Yes",
    "nu": "No",
    "nu stiu": "Don't know",
}

_SIZE = {
    "mica": "Small",
    "medie": "Medium",
    "mare": "Large",
}

_COLOR = {
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
}


def _fold(s: str) -> str:
    """lower + fără diacritice, pentru potrivire robustă."""
    s = (s or "").strip().lower()
    nfkd = unicodedata.normalize("NFKD", s)
    return "".join(c for c in nfkd if not unicodedata.combining(c))


def pet_field_value_en(raw: str | None) -> str:
    """
    Traduce valori tipice de select/afișare pe fișă.
    Dacă nu recunoaștem textul, îl lăsăm neschimbat (ex. nume localitate, text liber).
    """
    if raw is None:
        return ""
    text = str(raw).strip()
    if not text:
        return ""

    key = _fold(text)
    if key in _YES_NO:
        return _YES_NO[key]
    if key in _SIZE:
        return _SIZE[key]
    if key in _COLOR:
        return _COLOR[key]

    # Vârstă: "<1 an", "1 an", "2 ani" … "10+ ani"
    if key == "<1 an":
        return "<1 year"
    if key == "1 an":
        return "1 year"
    m = re.fullmatch(r"(\d+)\s*ani", key)
    if m:
        return f"{m.group(1)} years"
    m = re.fullmatch(r"(\d+)\+\s*ani", key)
    if m:
        return f"{m.group(1)}+ years"
    m = re.fullmatch(r"(\d+)\s*luni?", key)
    if m:
        n = m.group(1)
        return f"{n} month" if n == "1" else f"{n} months"

    # Greutate: "8 kile" → "8 kg"; "8 kg" rămâne
    m = re.fullmatch(r"([\d.,]+)\s*kile", key)
    if m:
        return f"{m.group(1)} kg"

    return text
