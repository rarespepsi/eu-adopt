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

_LABELS_DOG_EN: dict[str, str] = {
    "trait_jucaus": "PLAYFUL",
    "trait_iubitor": "AFFECTIONATE",
    "trait_protector": "PROTECTIVE",
    "trait_energic": "ENERGETIC",
    "trait_linistit": "CALM",
    "trait_bun_copii": "GOOD WITH CHILDREN",
    "trait_bun_caini": "GOOD WITH OTHER DOGS",
    "trait_bun_pisici": "GOOD WITH CATS",
    "trait_obisnuit_casa": "HOUSE-TRAINED",
    "trait_obisnuit_lesa": "USED TO A LEASH",
    "trait_nu_latla": "DOES NOT BARK EXCESSIVELY",
    "trait_apartament": "SUITABLE FOR APARTMENT",
    "trait_se_adapteaza": "ADAPTS EASILY",
    "trait_tolereaza_singur": "TOLERATES BEING ALONE",
    "trait_necesita_experienta": "NEEDS EXPERIENCE WITH DOGS",
}

_LABELS_CAT_EN: dict[str, str] = {
    **_LABELS_DOG_EN,
    "trait_bun_caini": "GOOD WITH DOGS",
    "trait_bun_pisici": "GOOD WITH OTHER CATS",
    "trait_obisnuit_lesa": "USED TO WALKS (HARNESS)",
    "trait_nu_latla": "DOES NOT MEOW EXCESSIVELY",
    "trait_necesita_experienta": "NEEDS EXPERIENCE WITH CATS",
}

# Pentru json_script / JS pe fișa MyPet (schimbare live la pill-uri).
TRAITS_LABELS_BY_SPECIES: dict[str, dict[str, str]] = {
    "dog": dict(_LABELS_DOG),
    "cat": dict(_LABELS_CAT),
}


def _use_english_traits() -> bool:
    try:
        from django.utils.translation import get_language

        lang = (get_language() or "").strip().lower()
        return lang.startswith("en")
    except Exception:
        return False


def trait_label(species: str | None, field_name: str, *, english: bool | None = None) -> str:
    s = (species or "").strip().lower()
    use_en = _use_english_traits() if english is None else bool(english)
    if use_en:
        table = _LABELS_CAT_EN if s == "cat" else _LABELS_DOG_EN
    else:
        table = _LABELS_CAT if s == "cat" else _LABELS_DOG
    return table.get(field_name, field_name)


def traits_labels_for_species(species: str | None, *, english: bool | None = None) -> dict[str, str]:
    s = (species or "").strip().lower()
    use_en = _use_english_traits() if english is None else bool(english)
    if use_en:
        return dict(_LABELS_CAT_EN if s == "cat" else _LABELS_DOG_EN)
    return dict(_LABELS_CAT if s == "cat" else _LABELS_DOG)
