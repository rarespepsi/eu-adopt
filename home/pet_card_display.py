"""Texte compacte pe carduri animale (localitate, sex M/F, vârstă din fișă)."""
from __future__ import annotations

from home.models import AnimalListing


def pet_card_sex_letter(sex: str | None) -> str:
    s = (sex or "").strip().lower()
    if s in ("m", "mascul", "male"):
        return "M"
    if s in ("f", "femela", "female", "femelă"):
        return "F"
    return ""


def pet_card_age_text(age_label: str | None) -> str:
    return (age_label or "").strip()


def _fields_from_pet(pet_or_dict) -> tuple[str, str, str]:
    if isinstance(pet_or_dict, AnimalListing):
        return (
            (pet_or_dict.sex or "").strip(),
            (pet_or_dict.age_label or "").strip(),
            (pet_or_dict.city or "").strip() or (pet_or_dict.county or "").strip(),
        )
    if isinstance(pet_or_dict, dict):
        sex = (pet_or_dict.get("sex") or "").strip()
        age = (
            pet_or_dict.get("varsta")
            or pet_or_dict.get("age_label")
            or ""
        )
        age = (age or "").strip()
        loc = (
            pet_or_dict.get("oras")
            or pet_or_dict.get("city")
            or pet_or_dict.get("localitate")
            or pet_or_dict.get("county")
            or ""
        )
        return sex, age, (loc or "").strip()
    sex = (getattr(pet_or_dict, "sex", None) or "").strip()
    age = (
        getattr(pet_or_dict, "age_label", None)
        or getattr(pet_or_dict, "varsta", None)
        or ""
    )
    age = (age or "").strip()
    loc = (
        getattr(pet_or_dict, "city", None)
        or getattr(pet_or_dict, "oras", None)
        or getattr(pet_or_dict, "county", None)
        or ""
    )
    return sex, age, (loc or "").strip()


def pet_card_meta_context(pet_or_dict) -> dict:
    sex_raw, age_raw, loc = _fields_from_pet(pet_or_dict)
    sex_letter = pet_card_sex_letter(sex_raw)
    age_text = pet_card_age_text(age_raw)
    return {
        "show_loc": bool(loc),
        "loc": loc,
        "show_sf": bool(sex_letter or age_text),
        "sex_letter": sex_letter,
        "age_text": age_text,
    }
