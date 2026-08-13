"""Prefixe telefon fix RO (cod zonă 02xx / 03xx) pe județe."""

from __future__ import annotations

import re

from home.ro_location import fold_key

# Județ canonic → (prefix 02…, prefix 03…)
_COUNTY_PREFIXES: dict[str, tuple[str, str]] = {
    "Alba": ("0258", "0358"),
    "Arad": ("0257", "0357"),
    "Argeș": ("0248", "0348"),
    "Bacău": ("0234", "0334"),
    "Bihor": ("0259", "0359"),
    "Bistrița-Năsăud": ("0263", "0363"),
    "Botoșani": ("0231", "0331"),
    "Brașov": ("0268", "0368"),
    "Brăila": ("0239", "0339"),
    "București": ("021", "031"),
    "Buzău": ("0238", "0338"),
    "Călărași": ("0242", "0342"),
    "Caraș-Severin": ("0255", "0355"),
    "Cluj": ("0264", "0364"),
    "Constanța": ("0241", "0341"),
    "Covasna": ("0267", "0367"),
    "Dâmbovița": ("0245", "0345"),
    "Dolj": ("0251", "0351"),
    "Galați": ("0236", "0336"),
    "Giurgiu": ("0246", "0346"),
    "Gorj": ("0253", "0353"),
    "Harghita": ("0266", "0366"),
    "Hunedoara": ("0254", "0354"),
    "Ialomița": ("0243", "0343"),
    "Iași": ("0232", "0332"),
    "Ilfov": ("021", "031"),
    "Maramureș": ("0262", "0362"),
    "Mehedinți": ("0252", "0352"),
    "Mureș": ("0265", "0365"),
    "Neamț": ("0233", "0333"),
    "Olt": ("0249", "0349"),
    "Prahova": ("0244", "0344"),
    "Satu Mare": ("0261", "0361"),
    "Sălaj": ("0260", "0360"),
    "Sibiu": ("0269", "0369"),
    "Suceava": ("0230", "0330"),
    "Teleorman": ("0247", "0347"),
    "Timiș": ("0256", "0356"),
    "Tulcea": ("0240", "0340"),
    "Vaslui": ("0235", "0335"),
    "Vâlcea": ("0250", "0350"),
    "Vrancea": ("0237", "0337"),
}


def landline_prefix_choices() -> list[tuple[str, str]]:
    """Opțiuni select: (prefix, 'Județ — 0xxx')."""
    out: list[tuple[str, str]] = []
    seen: set[str] = set()
    for county, (p02, p03) in sorted(_COUNTY_PREFIXES.items(), key=lambda x: x[0]):
        for pref in (p02, p03):
            if pref in seen:
                # București/Ilfov împart 021/031 — o singură linie per prefix
                continue
            seen.add(pref)
            label = f"{county} — {pref}"
            if pref in ("021", "031"):
                label = f"București / Ilfov — {pref}"
            out.append((pref, label))
    # Sortează după prefix numeric
    out.sort(key=lambda x: (len(x[0]), x[0]))
    return out


def default_landline_prefix_for_county(judet: str | None) -> str:
    key = fold_key(judet or "")
    for county, (p02, _p03) in _COUNTY_PREFIXES.items():
        if fold_key(county) == key:
            return p02
    return ""


def is_ro_mobile_number(phone: str | None) -> bool:
    """Acceptă 07xxxxxxxx / 7xxxxxxxx / +407xxxxxxxx / 407xxxxxxxx."""
    digits = re.sub(r"\D", "", phone or "")
    if digits.startswith("40") and len(digits) >= 11:
        digits = digits[2:]
    if digits.startswith("0") and len(digits) >= 10:
        digits = digits[1:]
    return len(digits) == 9 and digits.startswith("7")


def combine_landline(prefix: str | None, number: str | None) -> str:
    """Returnează '0232 212345' sau '' dacă lipsesc ambele părți utile."""
    pref = re.sub(r"\D", "", prefix or "")
    num = re.sub(r"\D", "", number or "")
    if not pref and not num:
        return ""
    if pref and not num:
        return ""
    if num and not pref:
        return ""
    # Evită dublarea prefixului dacă userul a tastat tot numărul
    if num.startswith(pref):
        num = num[len(pref) :]
    if num.startswith("0"):
        # uneori userul pune 0 local
        pass
    return f"{pref} {num}".strip()


def parse_landline_for_edit(stored: str | None) -> tuple[str, str]:
    """Din '0256 212345' → (prefix, număr) pentru formularul de cont."""
    raw = (stored or "").strip()
    if not raw:
        return "", ""
    digits = re.sub(r"\D", "", raw)
    if not digits:
        return "", ""
    prefixes = sorted({p for p, _ in landline_prefix_choices()}, key=len, reverse=True)
    for pref in prefixes:
        if digits.startswith(pref) and len(digits) > len(pref):
            return pref, digits[len(pref) :]
    parts = raw.split(None, 1)
    if len(parts) == 2:
        return re.sub(r"\D", "", parts[0]), re.sub(r"\D", "", parts[1])
    return "", digits
