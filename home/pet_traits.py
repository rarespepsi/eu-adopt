"""
Etichete UI pentru cele 15 trăsături „potrivire adoptator”, în funcție de specia din fișă.
Câmpurile din DB rămân aceleași; se schimbă doar textul afișat (câine vs pisică).
"""

from __future__ import annotations

TRAITS_ORDER: tuple[str, ...] = (
    "trait_jucaus",
    "trait_iubitor",
    "trait_protector",
    "trait_energic",
    "trait_linistit",
    "trait_bun_copii",
    "trait_bun_caini",
    "trait_bun_pisici",
    "trait_obisnuit_casa",
    "trait_obisnuit_lesa",
    "trait_nu_latla",
    "trait_apartament",
    "trait_se_adapteaza",
    "trait_tolereaza_singur",
    "trait_necesita_experienta",
)

_LABELS_DOG: dict[str, str] = {
    "trait_jucaus": "JUCĂUȘ",
    "trait_iubitor": "IUBITOR",
    "trait_protector": "PROTECTOR",
    "trait_energic": "ENERGIC",
    "trait_linistit": "LINIȘTIT",
    "trait_bun_copii": "BUN CU COPII",
    "trait_bun_caini": "BUN CU ALȚI CÂINI",
    "trait_bun_pisici": "BUN CU PISICI",
    "trait_obisnuit_casa": "OBIȘNUIT ÎN CASĂ",
    "trait_obisnuit_lesa": "OBIȘNUIT CU LESA",
    "trait_nu_latla": "NU LATRĂ EXCESIV",
    "trait_apartament": "POTRIVIT PENTRU APARTAMENT",
    "trait_se_adapteaza": "SE ADAPTEAZĂ UȘOR",
    "trait_tolereaza_singur": "TOLEREAZĂ SĂ STEA SINGUR",
    "trait_necesita_experienta": "NECESITĂ EXPERIENȚĂ CU CÂINI",
}

_LABELS_CAT: dict[str, str] = {
    **_LABELS_DOG,
    "trait_bun_caini": "BUN CU CÂINII",
    "trait_bun_pisici": "BUN CU ALTE PISICI",
    "trait_obisnuit_lesa": "OBIȘNUIT CU PLIMBAREA (HAM)",
    "trait_nu_latla": "NU MIAUNĂ EXCESIV",
    "trait_necesita_experienta": "NECESITĂ EXPERIENȚĂ CU PISICI",
}

# Pentru json_script / JS pe fișa MyPet (schimbare live la pill-uri).
TRAITS_LABELS_BY_SPECIES: dict[str, dict[str, str]] = {
    "dog": dict(_LABELS_DOG),
    "cat": dict(_LABELS_CAT),
}


def trait_label(species: str | None, field_name: str) -> str:
    s = (species or "").strip().lower()
    table = _LABELS_CAT if s == "cat" else _LABELS_DOG
    return table.get(field_name, field_name)
