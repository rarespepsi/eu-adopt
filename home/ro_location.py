"""Județe și localități RO — formă canonică unică (diacritice + potrivire fără diacritice)."""

from __future__ import annotations

import json
import re
import unicodedata
from functools import lru_cache
from pathlib import Path

from django.conf import settings

_COUNTIES = (
    "Alba",
    "Arad",
    "Argeș",
    "Bacău",
    "Bihor",
    "Bistrița-Năsăud",
    "Botoșani",
    "Brăila",
    "Brașov",
    "București",
    "Buzău",
    "Călărași",
    "Caraș-Severin",
    "Cluj",
    "Constanța",
    "Covasna",
    "Dâmbovița",
    "Dolj",
    "Galați",
    "Giurgiu",
    "Gorj",
    "Harghita",
    "Hunedoara",
    "Ialomița",
    "Iași",
    "Ilfov",
    "Maramureș",
    "Mehedinți",
    "Mureș",
    "Neamț",
    "Olt",
    "Prahova",
    "Sălaj",
    "Satu Mare",
    "Sibiu",
    "Suceava",
    "Teleorman",
    "Timiș",
    "Tulcea",
    "Vâlcea",
    "Vaslui",
    "Vrancea",
)


def fold(s: str) -> str:
    s = unicodedata.normalize("NFKD", s or "")
    s = "".join(c for c in s if not unicodedata.combining(c))
    return re.sub(r"\s+", " ", s.lower()).strip()


def fold_key(s: str) -> str:
    """Cheie de potrivire: fără diacritice, spații/cratime normalizate."""
    s = fold(s)
    return re.sub(r"[\s\-_]+", " ", s).strip()


@lru_cache(maxsize=1)
def _county_by_key() -> dict[str, str]:
    return {fold_key(c): c for c in _COUNTIES}


@lru_cache(maxsize=1)
def _cities_data_path() -> Path:
    return Path(settings.BASE_DIR) / "static" / "data" / "ro_counties_cities.json"


@lru_cache(maxsize=1)
def _cities_by_county() -> dict[str, list[str]]:
    path = _cities_data_path()
    if not path.is_file():
        return {}
    data = json.loads(path.read_text(encoding="utf-8"))
    return {str(k): list(v) for k, v in data.items()}


@lru_cache(maxsize=64)
def _city_index_for_county(county: str) -> dict[str, str]:
    cities = _cities_by_county().get(county) or []
    out: dict[str, str] = {}
    for city in cities:
        k = fold_key(city)
        if k and k not in out:
            out[k] = city
    return out


def resolve_county(raw: str) -> str:
    """Returnează numele canonic al județului sau textul curățat dacă nu e în listă."""
    text = (raw or "").strip()
    if not text:
        return ""
    hit = _county_by_key().get(fold_key(text))
    return hit or text


def suggest_counties(raw: str, *, limit: int = 8) -> list[str]:
    text = fold_key(raw)
    if not text:
        return list(_COUNTIES)
    hits = [c for c in _COUNTIES if text in fold_key(c)]
    return hits[:limit] if hits else []


def resolve_locality(raw: str, county: str = "") -> str:
    """Returnează localitatea canonică din JSON (în județ dacă e dat)."""
    text = (raw or "").strip()
    if not text:
        return ""
    key = fold_key(text)
    county_canon = resolve_county(county) if county else ""
    if county_canon:
        hit = _city_index_for_county(county_canon).get(key)
        if hit:
            return hit
    if county_canon:
        return text
    # Fără județ: caută în toate județele (prima potrivire)
    for cname, cities in _cities_by_county().items():
        hit = _city_index_for_county(cname).get(key)
        if hit:
            return hit
    return text


def suggest_localities(raw: str, county: str = "", *, limit: int = 12) -> list[str]:
    county_canon = resolve_county(county) if county else ""
    cities = _cities_by_county().get(county_canon) or []
    text = fold_key(raw)
    if not text:
        return cities[:limit]
    hits = [c for c in cities if text in fold_key(c)]
    return hits[:limit] if hits else []


def normalize_location_pair(judet: str, oras: str) -> tuple[str, str]:
    j = resolve_county(judet)
    o = resolve_locality(oras, j)
    return j, o


def location_keys_match(a: str, b: str) -> bool:
    ka, kb = fold_key(a), fold_key(b)
    return bool(ka) and ka == kb


def lead_matches_location_filter(
    *,
    judet: str,
    company_judet: str,
    oras: str,
    company_oras: str,
    filter_judet: str,
    filter_oras: str,
) -> bool:
    fj = (filter_judet or "").strip()
    fo = (filter_oras or "").strip()
    if fj:
        fj_key = fold_key(resolve_county(fj))
        if not (
            location_keys_match(judet, fj)
            or location_keys_match(company_judet, fj)
            or (fj_key and (fold_key(judet) == fj_key or fold_key(company_judet) == fj_key))
        ):
            return False
    if fo:
        county_ctx = resolve_county(fj or judet or company_judet)
        fo_canon = resolve_locality(fo, county_ctx)
        fo_key = fold_key(fo_canon)
        for val in (oras, company_oras):
            if location_keys_match(val, fo_canon):
                return True
            if fo_key and fold_key(val) == fo_key:
                return True
        return False
    return True


def normalize_mutable_pair(data: dict, judet_key: str, oras_key: str) -> None:
    """Normalize județ/localitate keys in-place (missing keys ignored)."""
    if judet_key not in data and oras_key not in data:
        return
    j, o = normalize_location_pair(str(data.get(judet_key) or ""), str(data.get(oras_key) or ""))
    data[judet_key] = j
    data[oras_key] = o


def normalize_lead_location_kwargs(kwargs: dict) -> dict:
    normalize_mutable_pair(kwargs, "judet", "oras")
    normalize_mutable_pair(kwargs, "company_judet", "company_oras")
    return kwargs
