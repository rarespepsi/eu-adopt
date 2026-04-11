"""
Reset adopție rarespepsi → [seed] radu-cat-06 + profile Neamț / Piatra Neamț
(adoptator + colaboratori seed: cabinet, servicii dg1/dg2, magazin dm).

Rulare:
  python scripts/qa_reset_adoption_neamt.py              # reset cerere adopție + geo Neamț
  python scripts/qa_reset_adoption_neamt.py --geo-only   # doar profiluri (fără ștergere adopție)
"""
from __future__ import annotations

import argparse
import os
import sys

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")

import django

django.setup()

if hasattr(sys.stdout, "reconfigure"):
    try:
        sys.stdout.reconfigure(encoding="utf-8")
    except Exception:
        pass

from django.contrib.auth import get_user_model
from django.db.models import Q

from home.models import (
    AdoptionBonusSelection,
    AdoptionRequest,
    AnimalListing,
    CollaboratorServiceOffer,
    PetMessage,
    UserProfile,
)
from home.views import _sync_animal_adoption_state

User = get_user_model()

PET_NAME = "[seed] radu-cat-06"
ADOPTER_USERNAME = "rarespepsi"
OWNER_USERNAME = "radu"
COUNTY = "Neamț"
CITY = "Piatra Neamț"

# Un user colaborator per canal (aliniat la seed_portfolio / QA)
COLLAB_BY_KIND = {
    "nccristescu": CollaboratorServiceOffer.PARTNER_KIND_CABINET,
    "dg1": CollaboratorServiceOffer.PARTNER_KIND_SERVICII,
    "dm": CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN,
}

# Colaboratori cu oferte în grila Servicii — fără transportatori.
COLLAB_ALL_NEAMT = ("nccristescu", "dg1", "dg2", "dm")


def set_profile_geo(user: User, *, fill_personal: bool) -> None:
    prof, _ = UserProfile.objects.get_or_create(user=user)
    prof.company_judet = COUNTY
    prof.company_oras = CITY
    fields = ["company_judet", "company_oras", "updated_at"]
    if fill_personal:
        prof.judet = COUNTY
        prof.oras = CITY
        fields.extend(["judet", "oras"])
    prof.save(update_fields=fields)


def _run_geo_only() -> int:
    rares = User.objects.filter(username__iexact=ADOPTER_USERNAME).first()
    if not rares:
        print(f"Lipsește user {ADOPTER_USERNAME!r}")
        return 1
    set_profile_geo(rares, fill_personal=True)
    print(f"Profil {ADOPTER_USERNAME}: județ/oraș → {COUNTY} / {CITY}")
    for uname in COLLAB_ALL_NEAMT:
        u = User.objects.filter(username__iexact=uname).first()
        if not u:
            print(f"  (!) Lipsește colaborator {uname!r}")
            continue
        set_profile_geo(u, fill_personal=True)
        print(f"  {uname}: company + persoană → {COUNTY} / {CITY}")
    return 0


def main() -> int:
    parser = argparse.ArgumentParser(description="QA Neamț: reset adopție + aliniere geo sau doar geo.")
    parser.add_argument(
        "--geo-only",
        action="store_true",
        help="Doar setează județ/oraș pe adoptator și colaboratori (fără ștergere cereri adopție).",
    )
    args = parser.parse_args()

    if args.geo_only:
        return _run_geo_only()

    radu = User.objects.filter(username__iexact=OWNER_USERNAME).first()
    rares = User.objects.filter(username__iexact=ADOPTER_USERNAME).first()
    if not radu:
        print(f"Lipsește user {OWNER_USERNAME!r}")
        return 1
    if not rares:
        print(f"Lipsește user {ADOPTER_USERNAME!r}")
        return 1

    pet = AnimalListing.objects.filter(owner=radu, name=PET_NAME).first()
    if not pet:
        pet = AnimalListing.objects.filter(owner=radu, name__icontains="radu-cat-06").first()
    if not pet:
        print(f"Nu găsesc animal {PET_NAME!r} la owner {OWNER_USERNAME}")
        return 1

    ars = list(AdoptionRequest.objects.filter(animal=pet, adopter=rares))
    n_bonus = 0
    for ar in ars:
        n_bonus += AdoptionBonusSelection.objects.filter(adoption_request=ar).delete()[0]
    n_ar = AdoptionRequest.objects.filter(animal=pet, adopter=rares).delete()[0]
    n_msg = PetMessage.objects.filter(animal=pet).filter(
        Q(sender=rares, receiver=radu) | Q(sender=radu, receiver=rares)
    ).delete()[0]

    _sync_animal_adoption_state(pet)
    pet.refresh_from_db()
    print(
        f"Reset adopție: pet pk={pet.pk} {pet.name!r}; "
        f"șterse cereri={n_ar}, bonus_selections={n_bonus}, mesaje pet={n_msg}; "
        f"adoption_state acum={pet.adoption_state!r}"
    )

    # Adoptator ONG: județ folosit și din company_* în logică; setăm ambele ca să fie sigur.
    set_profile_geo(rares, fill_personal=True)
    print(f"Profil {ADOPTER_USERNAME}: județ/oraș → {COUNTY} / {CITY}")

    for uname in COLLAB_ALL_NEAMT:
        u = User.objects.filter(username__iexact=uname).first()
        if not u:
            print(f"  (!) Lipsește colaborator {uname!r} — sar peste geo")
            continue
        # Colaborator: company_* folosit la inimioare; judet/oras la fel ca să nu rămână valori vechi (ex. București) care derutează.
        set_profile_geo(u, fill_personal=True)
        print(f"  {uname}: company + persoană → {COUNTY} / {CITY}")

    for uname in COLLAB_BY_KIND:
        u = User.objects.filter(username__iexact=uname).first()
        if not u:
            continue
        kind = COLLAB_BY_KIND[uname]
        off = (
            CollaboratorServiceOffer.objects.filter(
                collaborator=u, partner_kind=kind, is_active=True
            )
            .order_by("-created_at")
            .first()
        )
        if off:
            print(f"  {uname} ({kind}): ofertă activă pk={off.pk} — geo colaborator {COUNTY}/{CITY}")
        else:
            print(f"  (!) {uname}: nu există ofertă activă pentru {kind}")

    return 0


if __name__ == "__main__":
    raise SystemExit(main())
