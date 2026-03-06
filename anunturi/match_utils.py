"""
Logică simplă de potrivire (scor) pentru „Găsește-mi prietenul ideal”.
Fără AI: puncte pentru size/age/activity și pentru compatibilitate (kids/cat/dog) dacă câmpurile există pe Pet.
"""
from .models import Pet


def compute_matches(profile_or_dict, limit=12):
    """
    Returnează o listă de Pet (adoptable, neadoptate) ordonată descrescător după scor.
    profile_or_dict: fie un obiect UserMatchProfile, fie un dict cu aceleași chei (ex. din session).
    Dacă Pet nu are câmpuri prietenos_cu_copiii/ok_cu_pisici/ok_cu_alti_caini, acele puncte se ignoră.
    """
    if hasattr(profile_or_dict, "size_preference"):
        size_pref = (profile_or_dict.size_preference or "").strip() or None
        age_pref = (profile_or_dict.age_preference or "").strip() or None
        activity_pref = (profile_or_dict.activity_level or "").strip() or None
        has_kids = bool(profile_or_dict.has_kids)
        has_cat = bool(profile_or_dict.has_cat)
        has_dog = bool(profile_or_dict.has_dog)
    else:
        d = profile_or_dict or {}
        size_pref = (d.get("size_preference") or "").strip() or None
        age_pref = (d.get("age_preference") or "").strip() or None
        activity_pref = (d.get("activity_level") or "").strip() or None
        has_kids = bool(d.get("has_kids"))
        has_cat = bool(d.get("has_cat"))
        has_dog = bool(d.get("has_dog"))

    qs = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted"))
    if not qs:
        return [], 0

    # Scor simplu: +2 size, +2 age, +2 activity, +1 kids/cat/dog (câmpuri Pet existente)
    scored = []
    for pet in qs:
        score = 0
        if size_pref and size_pref != "any" and getattr(pet, "marime", None) == size_pref:
            score += 2
        elif size_pref == "any" or not size_pref:
            score += 2
        if age_pref and age_pref != "any":
            pet_age = getattr(pet, "varsta_aproximativa", None)
            if pet_age is not None:
                if age_pref == "puppy" and pet_age <= 1:
                    score += 2
                elif age_pref == "adult" and 2 <= pet_age <= 8:
                    score += 2
                elif age_pref == "senior" and pet_age >= 9:
                    score += 2
        elif age_pref == "any" or not age_pref:
            score += 2
        if activity_pref:
            need_active = getattr(pet, "necesita_miscare_multa", None)
            fam_activa = getattr(pet, "potrivit_familie_activa", None)
            if activity_pref == "low" and (need_active is False or (need_active is None and fam_activa is False)):
                score += 2
            elif activity_pref == "high" and (need_active is True or fam_activa is True):
                score += 2
            elif activity_pref == "medium":
                score += 2
        else:
            score += 2
        if has_kids and getattr(pet, "prietenos_cu_copiii", False):
            score += 1
        if has_cat and getattr(pet, "ok_cu_pisici", False):
            score += 1
        if has_dog and getattr(pet, "ok_cu_alti_caini", False):
            score += 1
        scored.append((score, pet))

    scored.sort(key=lambda x: (-x[0], -(x[1].data_adaugare.timestamp() if x[1].data_adaugare else 0)))
    return [p for _, p in scored[:limit]]
