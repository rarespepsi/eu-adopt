"""Badge încredere: adăpost / ONG cu cont org activ pe EU-Adopt."""
from __future__ import annotations

from typing import Iterable

from django.contrib.auth import get_user_model

from home.models import AccountProfile, AnimalListing

User = get_user_model()


def user_has_org_trust_badge(user) -> bool:
    """Cont org activ, fără ștergere programată."""
    if user is None:
        return False
    if not getattr(user, "is_active", True):
        return False
    uid = getattr(user, "pk", None)
    if not uid:
        return False
    ap = AccountProfile.objects.filter(user_id=uid).first()
    if ap is None or ap.role != AccountProfile.ROLE_ORG:
        return False
    if ap.pending_deletion_requested_at:
        return False
    return True


def owner_ids_with_org_trust_badge(owner_ids: Iterable[int]) -> frozenset[int]:
    ids = {int(x) for x in owner_ids if x is not None}
    if not ids:
        return frozenset()
    qs = AccountProfile.objects.filter(
        user_id__in=ids,
        role=AccountProfile.ROLE_ORG,
        pending_deletion_requested_at__isnull=True,
        user__is_active=True,
    ).values_list("user_id", flat=True)
    return frozenset(qs)


def pet_shows_org_trust_badge(pet_or_dict) -> bool:
    if pet_or_dict is None:
        return False
    if isinstance(pet_or_dict, dict):
        if "show_org_trust_badge" in pet_or_dict:
            return bool(pet_or_dict.get("show_org_trust_badge"))
        oid = pet_or_dict.get("owner_id")
        if oid is None:
            return False
        return int(oid) in owner_ids_with_org_trust_badge([oid])
    if isinstance(pet_or_dict, AnimalListing):
        owner = getattr(pet_or_dict, "owner", None)
        if owner is not None:
            return user_has_org_trust_badge(owner)
        oid = getattr(pet_or_dict, "owner_id", None)
        if oid is None:
            return False
        return int(oid) in owner_ids_with_org_trust_badge([oid])
    if getattr(pet_or_dict, "show_org_trust_badge", None) is not None:
        return bool(getattr(pet_or_dict, "show_org_trust_badge"))
    owner = getattr(pet_or_dict, "owner", None)
    if owner is not None:
        return user_has_org_trust_badge(owner)
    oid = getattr(pet_or_dict, "owner_id", None)
    if oid is None:
        return False
    return int(oid) in owner_ids_with_org_trust_badge([oid])
