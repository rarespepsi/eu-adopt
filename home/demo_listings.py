"""
Identificare anunțuri animal demonstrative (fără adopție reală).

- prefix [seed] (scripts/seed_portfolio.py)
- proprietari lista EUADOPT_DEMO_ANIMAL_OWNER_USERNAMES (implicit: rarespepsi — vitrină lansare)
"""

from __future__ import annotations

from django.conf import settings

from home.models import AnimalListing

SEED_ANIMAL_NAME_PREFIX = "[seed] "


def demo_animal_owner_usernames() -> frozenset[str]:
    raw = getattr(settings, "EUADOPT_DEMO_ANIMAL_OWNER_USERNAMES", ("rarespepsi",))
    if isinstance(raw, str):
        parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    else:
        parts = [str(p).strip().lower() for p in raw if str(p).strip()]
    return frozenset(parts)


def demo_owner_keywords() -> tuple[str, ...]:
    """
    Fallback robust pentru conturi demo create intern.
    Dacă owner-ul conține aceste fragmente, anunțul e tratat ca DEMO.
    """
    raw = getattr(
        settings,
        "EUADOPT_DEMO_ANIMAL_OWNER_KEYWORDS",
        ("demo", "[seed]", "seed_"),
    )
    if isinstance(raw, str):
        parts = [p.strip().lower() for p in raw.split(",") if p.strip()]
    else:
        parts = [str(p).strip().lower() for p in raw if str(p).strip()]
    return tuple(parts)


def is_demo_animal_listing(listing: AnimalListing | None) -> bool:
    if not listing:
        return False
    name = (getattr(listing, "name", None) or "").strip()
    if name.startswith(SEED_ANIMAL_NAME_PREFIX) or name.startswith("[seed]"):
        return True
    owner_id = getattr(listing, "owner_id", None)
    if not owner_id:
        return False
    owners = demo_animal_owner_usernames()
    if not owners:
        return False
    from django.contrib.auth import get_user_model

    username = (
        get_user_model()
        .objects.filter(pk=owner_id)
        .values_list("username", flat=True)
        .first()
    )
    uname = (username or "").strip().lower()
    if not uname:
        return False
    if uname in owners:
        return True
    keywords = demo_owner_keywords()
    return any(k and k in uname for k in keywords)


DEMO_ADOPTION_INACTIVE_MESSAGE = (
    "Acest animal este demonstrativ (DEMO) și nu poate fi dat spre adopție."
)
