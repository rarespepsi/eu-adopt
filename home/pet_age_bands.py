"""
Mapare internă: etichete de vârstă din fișă («<1 an», «1 an», …) ↔ coduri țintă (puppy/young/adult/senior)
folosite la oferte / filtre. Nu definește etichete UI; e doar echivalare în program.

**Pisică** — aliniere la *2021 AAHA/AAFP Feline Life Stage Guidelines* (rezumat pe ani):
  Kitten ≈ naștere–1 an → în grila noastră coarse: doar «<1 an» (sub 1 an întreg);
  Young adult 1–6 ani; Mature adult 7–10 ani; Senior 10+ ani.
  Vezi: https://www.aaha.org/resources/2021-aaha-aafp-feline-life-stage-guidelines/feline-life-stage-definitions/

**Câine** — aliniere la *AAHA Canine Life Stage Guidelines (2019)* (stadii nuanțate după rasă;
  aici le proiectăm pe pași de 1 an din baza de date):
  Puppy: în ghid „până la sfârșitul creșterii rapide” (luni); la noi: un singur bucket «<1 an».
  Young adult: în ghid până la maturare fizică/socială „în majoritatea câinilor spre 3–4 ani”;
  pe etichetele noastre: 1–4 ani → tânăr.
  Matur adult: după tânăr și înainte de senior.
  Senior: ultima parte din viață, dependent de talie; folosim praguri uzuale pe talie
  (mare 7+, medie 8+, mică 10+). Talie lipsă → tratată ca medie în filtre.
  Vezi: https://www.aaha.org/resources/life-stage-canine-2019/canine-life-stage-definitions/

**Alte specii**: aceeași scară ca pisica (fallback).
"""

from __future__ import annotations

from django.db.models import Q

# Etichetele folosite în AnimalListing.age_label / filtre PT / MyPet
AGE_LABELS_ORDERED: tuple[str, ...] = (
    "<1 an",
    "1 an",
    "2 ani",
    "3 ani",
    "4 ani",
    "5 ani",
    "6 ani",
    "7 ani",
    "8 ani",
    "9 ani",
    "10+ ani",
)

# Identice cu valorile din CollaboratorServiceOffer.target_age_band
ALL = "all"
PUPPY = "puppy"
YOUNG = "young"
ADULT = "adult"
SENIOR = "senior"

BAND_CHOICES_UI: tuple[tuple[str, str], ...] = (
    (ALL, "— Toate categoriile —"),
    (PUPPY, "Pui"),
    (YOUNG, "Tânăr"),
    (ADULT, "Adult"),
    (SENIOR, "Senior"),
)

BAND_FILTER_GET_VALUES: frozenset[str] = frozenset({PUPPY, YOUNG, ADULT, SENIOR})


def age_label_to_min_years(age_label: str) -> int | None:
    """Limită inferioară în ani pentru comparații; None dacă nu recunoaștem eticheta."""
    s = (age_label or "").strip()
    if not s:
        return None
    if s == "<1 an":
        return 0
    if s == "10+ ani":
        return 10
    if s.endswith(" ani"):
        core = s[: -len(" ani")]
        if core.isdigit():
            return int(core)
    if s.endswith(" an"):
        core = s[: -len(" an")]
        if core.isdigit():
            return int(core)
    return None


def _dog_senior_threshold_years(size: str | None) -> int:
    sz = (size or "").strip().lower()
    if sz == "mare":
        return 7
    if sz == "mica":
        return 10
    return 8


def age_label_to_band(age_label: str, species: str, size: str | None = None) -> str:
    """
    Returnează cod bandă (puppy/young/adult/senior/all).
    all = eticheta lipsă sau necunoscută.
    """
    y = age_label_to_min_years(age_label)
    if y is None:
        return ALL
    sp = (species or "").strip().lower()
    if sp == "cat" or sp == "other":
        if y == 0:
            return PUPPY
        if y <= 6:
            return YOUNG
        if y <= 9:
            return ADULT
        return SENIOR
    # dog
    if y == 0:
        return PUPPY
    if y <= 4:
        return YOUNG
    th = _dog_senior_threshold_years(size)
    if y >= th:
        return SENIOR
    return ADULT


def labels_for_band_cat(band: str) -> list[str]:
    return [lab for lab in AGE_LABELS_ORDERED if age_label_to_band(lab, "cat", None) == band]


def labels_for_band_dog(band: str, size: str) -> list[str]:
    return [lab for lab in AGE_LABELS_ORDERED if age_label_to_band(lab, "dog", size) == band]


def animal_matches_target_age_band(
    age_label: str,
    species: str,
    size: str | None,
    target_band: str,
) -> bool:
    """Potrivire cu o ofertă: target_band „all” trece mereu."""
    tb = (target_band or "").strip().lower()
    if not tb or tb == ALL:
        return True
    return age_label_to_band(age_label, species, size) == tb


_LISTING_SIZE_TO_TARGET: dict[str, str] = {
    "mica": "small",
    "medie": "medium",
    "mare": "large",
}


def animal_listing_matches_collab_offer_targets(offer, listing) -> bool:
    """
    Returnează True dacă câmpurile țintă ale ofertei (target_species/size/sex/age/steril)
    coincid cu fișa AnimalListing (vârsta folosește maparea ani ↔ categorie din acest modul).
    `offer` poate fi CollaboratorServiceOffer sau orice obiect cu aceleași atribute.
    """
    ts = (getattr(offer, "target_species", None) or ALL).strip().lower()
    ls = (getattr(listing, "species", None) or "").strip().lower()
    if ts != ALL:
        if ls == "dog" and ts != "dog":
            return False
        if ls == "cat" and ts != "cat":
            return False
        if ls == "other":
            return False

    tz = (getattr(offer, "target_size", None) or ALL).strip().lower()
    if tz != ALL:
        raw_sz = (getattr(listing, "size", None) or "").strip().lower()
        if ls in ("cat", "other") and not raw_sz:
            # Fișele de pisică/altceva adesea nu au talie; nu excludem după talie.
            pass
        else:
            mapped = _LISTING_SIZE_TO_TARGET.get(raw_sz)
            if mapped != tz:
                return False

    tx = (getattr(offer, "target_sex", None) or ALL).strip().lower()
    if tx != ALL:
        lsex = (getattr(listing, "sex", None) or "").strip().lower()
        offer_sex = {"m": "male", "f": "female"}.get(lsex)
        if offer_sex != tx:
            return False

    if not animal_matches_target_age_band(
        getattr(listing, "age_label", None) or "",
        ls,
        getattr(listing, "size", None),
        getattr(offer, "target_age_band", None) or ALL,
    ):
        return False

    tst = (getattr(offer, "target_sterilized", None) or ALL).strip().lower()
    if tst != ALL:
        st = (getattr(listing, "sterilizat", None) or "").strip().lower()
        if st == "da" and tst != "yes":
            return False
        if st == "nu" and tst != "no":
            return False
        if st not in ("da", "nu"):
            return False

    return True


def build_age_band_filter_q(band: str, species_filter: str, marime_filter: str) -> Q | None:
    """
    Construiește Q pentru AnimalListing.
    None = fără restricție de categorie vârstă.
    """
    bband = (band or "").strip().lower()
    if not bband or bband == ALL or bband not in BAND_FILTER_GET_VALUES:
        return None

    sp = (species_filter or "").strip().lower()
    mar = (marime_filter or "").strip().lower()

    def q_cat() -> Q:
        labs = labels_for_band_cat(bband)
        return Q(species="cat", age_label__in=labs)

    def q_other() -> Q:
        labs = labels_for_band_cat(bband)
        return Q(species="other", age_label__in=labs)

    def q_dog() -> Q:
        sizes_known = ("mica", "medie", "mare")
        q = Q()
        if mar in sizes_known:
            q = Q(species="dog", size__iexact=mar, age_label__in=labels_for_band_dog(bband, mar))
        else:
            for sz in sizes_known:
                q |= Q(species="dog", size__iexact=sz, age_label__in=labels_for_band_dog(bband, sz))
            med_labs = labels_for_band_dog(bband, "medie")
            q |= Q(species="dog", age_label__in=med_labs) & ~(
                Q(size__iexact="mica") | Q(size__iexact="medie") | Q(size__iexact="mare")
            )
        return q

    if sp == "dog":
        return q_dog()
    if sp == "cat":
        return q_cat()
    if sp == "other":
        return q_other()
    return q_dog() | q_cat() | q_other()
