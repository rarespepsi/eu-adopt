"""
Reguli globale populare adăpost / ONG (ROLE_ORG).

Activ când EUADOPT_POPULATION_ONBOARDING=1 (implicit on dacă PRELAUNCH_MODE).
Vezi docs/POPULARE_ADAPOST_ONG.md
"""

from __future__ import annotations

from typing import Any

from django.conf import settings

from home.models import AccountProfile, AnimalListing


def is_population_onboarding_enabled() -> bool:
    return bool(getattr(settings, "POPULATION_ONBOARDING_ENABLED", False))


def population_animal_min() -> int:
    return int(getattr(settings, "POPULATION_ANIMAL_MIN", 2))


def population_animal_max() -> int:
    return int(getattr(settings, "POPULATION_ANIMAL_MAX", 5))


def _account_role(user) -> str | None:
    """Rol din DB (evită cache stale pe user.account_profile după signup)."""
    if not user or not getattr(user, "pk", None):
        return None
    return (
        AccountProfile.objects.filter(user_id=user.pk)
        .values_list("role", flat=True)
        .first()
    )


def is_org_population_user(user) -> bool:
    """Adăpost sau ONG în faza populare (ambele = ROLE_ORG)."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if not is_population_onboarding_enabled():
        return False
    return _account_role(user) == AccountProfile.ROLE_ORG


def is_staff_user(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    )


def is_superuser_full_access(user) -> bool:
    """
    Superuser: excepție permanentă — fără rol din profil în UI, acces vizual și funcțional
    ca toate tipurile de cont (PF / ONG / colaborator), inclusiv în faza populare.
    """
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and getattr(user, "is_superuser", False)
    )


def population_ui_restricted_for_user(user) -> bool:
    """Populare ascunde UI adopție/mesaje — superuser exceptat."""
    if is_superuser_full_access(user):
        return False
    return population_access_restricted()


def user_may_adopt_animals(user) -> bool:
    """Poate adopta / mesaje către owner. Superuser exceptat de rolul din profil."""
    if is_superuser_full_access(user):
        return True
    if not user or not getattr(user, "is_authenticated", False):
        return False
    ap = getattr(user, "account_profile", None)
    if ap:
        return bool(ap.can_adopt_animals)
    return True


def population_access_restricted() -> bool:
    """Populare + prelaunch: login și rute limitate."""
    if not is_population_onboarding_enabled():
        return False
    return bool(getattr(settings, "PRELAUNCH_MODE", False))


def is_population_superuser_only_login() -> bool:
    """Doar superuser se poate loga (până la deschiderea invitațiilor adăpost/ONG)."""
    return bool(
        population_access_restricted()
        and getattr(settings, "POPULATION_SUPERUSER_ONLY_LOGIN", False)
    )


def population_org_signup_allowed() -> bool:
    """Înregistrare organizație în prelaunch populare."""
    if not population_access_restricted():
        return True
    if is_population_superuser_only_login():
        return False
    return True


def user_may_login_during_population(user) -> tuple[bool, str]:
    if not population_access_restricted():
        return True, ""
    if is_population_superuser_only_login():
        if getattr(user, "is_superuser", False):
            return True, ""
        return (
            False,
            "În această etapă accesul este deschis doar pentru contul administrator (superuser).",
        )
    if is_staff_user(user):
        return True, ""
    if _account_role(user) == AccountProfile.ROLE_ORG:
        return True, ""
    return (
        False,
        "În etapa de populare accesul este deschis doar pentru adăposturi și ONG-uri "
        "invitate (link din email) și pentru echipa EU-Adopt.",
    )


# Rute blocate pentru adăpost/ONG logat în faza populare (adopții, shop, etc.)
POPULATION_ORG_BLOCKED_PREFIXES: tuple[str, ...] = (
    "/shop/",
    "/transport/",
    "/servicii/",
    "/i-love/",
    "/collab/",
    "/publicitate/",
    "/magazinul-meu/",
    "/adoption/",
    "/mypet/adoptiile-mele/",
    "/mypet/adoption/",
    "/mypet/messages/",
    "/cont/mesaje/",
    "/cont/oferte-adoptie/",
)


def is_population_blocked_path_for_org(path: str) -> bool:
    p = (path or "/").split("?", 1)[0]
    if not p.startswith("/"):
        p = "/" + p
    if "/adopt/request/" in p or p.endswith("/adopt/request/"):
        return True
    return p.startswith(POPULATION_ORG_BLOCKED_PREFIXES)


def population_redirect_for_org_user(user, path: str) -> str | None:
    """URL redirect dacă adăpost/ONG nu poate accesa path-ul în populare."""
    if not is_org_population_user(user) or is_staff_user(user) or is_superuser_full_access(user):
        return None
    if not is_population_blocked_path_for_org(path):
        return None
    return "/mypet/"


def org_published_animal_count(user) -> int:
    if not user or not user.is_authenticated:
        return 0
    return AnimalListing.objects.filter(owner=user, is_published=True).count()


def population_onboarding_complete(user) -> bool:
    if not is_org_population_user(user):
        return True
    return org_published_animal_count(user) >= population_animal_min()


def population_at_max_animals(user) -> bool:
    if not is_org_population_user(user):
        return False
    return org_published_animal_count(user) >= population_animal_max()


def check_org_can_add_animal(user) -> tuple[bool, str]:
    """Înainte de creare animal nou pentru ONG în faza populare."""
    if not is_org_population_user(user):
        return True, ""
    n = org_published_animal_count(user)
    mx = population_animal_max()
    if n >= mx:
        return (
            False,
            f"În etapa de populare puteți publica maximum {mx} animale. "
            "După lansarea oficială veți putea adăuga mai multe.",
        )
    return True, ""


def population_context_for_user(user) -> dict[str, Any]:
    active = is_org_population_user(user)
    n = org_published_animal_count(user) if user and user.is_authenticated else 0
    mn = population_animal_min()
    mx = population_animal_max()
    return {
        "population_org_active": active,
        "population_org_nav_reduced": active,
        "population_animal_count": n,
        "population_animal_min": mn,
        "population_animal_max": mx,
        "population_onboarding_complete": (not active) or n >= mn,
        "population_at_max_animals": active and n >= mx,
        "population_animals_until_min": max(0, mn - n) if active else 0,
        "population_animals_remaining": max(0, mx - n) if active else 0,
    }


def population_context_for_request(request) -> dict[str, Any]:
    user = getattr(request, "user", None)
    return population_context_for_user(user)
