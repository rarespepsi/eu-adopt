"""Note + tur scurt la prima vizită pe pagină (user nou ≤ N zile)."""

from __future__ import annotations

from dataclasses import dataclass
from datetime import timedelta
from typing import Any

from django.conf import settings
from django.utils import timezone


@dataclass(frozen=True)
class OnboardingStep:
    selector: str
    text: str


@dataclass(frozen=True)
class OnboardingPage:
    page_key: str
    banner_title: str
    banner_text: str
    steps: tuple[OnboardingStep, ...]


ONBOARDING_PAGES: dict[str, OnboardingPage] = {
    "home": OnboardingPage(
        page_key="home",
        banner_title="Bine ai venit pe Acasă",
        banner_text=(
            "Pagina principală EU-Adopt: vezi animale promovate, accesezi meniul "
            "și poți reveni oricând aici după login."
        ),
        steps=(
            OnboardingStep("#A1", "Zona A1 — titlul și mesajul principal al site-ului."),
            OnboardingStep("#A2", "Grila A2 — anunțuri promovate spre adopție (Prioritatea 2)."),
            OnboardingStep(
                "#menu-main-menu",
                "Meniul de sus — Prietenul tău, Servicii, MyPet, Publicitate și restul secțiunilor.",
            ),
        ),
    ),
    "mypet": OnboardingPage(
        page_key="mypet",
        banner_title="MyPet — panoul tău",
        banner_text=(
            "Aici publici animale, vezi mesajele și gestionezi cererile de adopție. "
            "Completează fișa fiecărui animal cât mai mult posibil."
        ),
        steps=(
            OnboardingStep(
                ".mypet-btn-add",
                "Adaugă un pet — creezi un anunț nou (poze, date, publicare).",
            ),
            OnboardingStep(
                ".mypet-arc-filters",
                "Active / Adoptate — comută lista între animalele curente și cele adoptate.",
            ),
            OnboardingStep(
                ".mypet-species-filters",
                "Filtre specie — Câini, Pisici, Altele.",
            ),
            OnboardingStep(
                ".mypet-table-wrap",
                "Lista animalelor — click pe rând pentru fișă, mesaje sau acțiuni.",
            ),
        ),
    ),
    "publicitate_harta": OnboardingPage(
        page_key="publicitate_harta",
        banner_title="Publicitate — hartă tarife",
        banner_text=(
            "Alegi o casetă pe hartă, vezi detaliile în stânga și o adaugi în coș. "
            "În pre-lansare, publicitatea poate fi gratuită (limită per cont)."
        ),
        steps=(
            OnboardingStep(
                ".pub-top-tabs",
                "Tab-uri secțiuni — HOME, Prietenul tău, I Love etc. (tarife pe pagină).",
            ),
            OnboardingStep(
                ".pub-c2",
                "Harta — apasă pe o casetă liberă pentru a o selecta.",
            ),
            OnboardingStep(
                ".pub-c3",
                "Detalii slot — perioadă, preț și butonul Adaugă în coș.",
            ),
            OnboardingStep(
                ".pub-tab--pub-flow",
                "Coș publicitate — finalizezi comanda după ce adaugi sloturi.",
            ),
        ),
    ),
}


def user_onboarding_enabled() -> bool:
    return bool(getattr(settings, "USER_ONBOARDING_ENABLED", True))


def user_onboarding_new_user_days() -> int:
    try:
        return max(1, int(getattr(settings, "USER_ONBOARDING_NEW_USER_DAYS", 30)))
    except (TypeError, ValueError):
        return 30


def is_new_user_for_onboarding(user) -> bool:
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return False
    joined = getattr(user, "date_joined", None)
    if not joined:
        return False
    cutoff = timezone.now() - timedelta(days=user_onboarding_new_user_days())
    return joined >= cutoff


def onboarding_page_for_url_name(url_name: str) -> OnboardingPage | None:
    key = (url_name or "").strip()
    if not key:
        return None
    return ONBOARDING_PAGES.get(key)


def user_has_seen_onboarding_page(user, page_key: str) -> bool:
    from home.models import UserPageOnboardingSeen

    return UserPageOnboardingSeen.objects.filter(user=user, page_key=page_key).exists()


def mark_onboarding_page_seen(user, page_key: str) -> None:
    from home.models import UserPageOnboardingSeen

    UserPageOnboardingSeen.objects.get_or_create(user=user, page_key=page_key)


def onboarding_payload_for_request(request) -> dict[str, Any] | None:
    if not user_onboarding_enabled():
        return None
    user = getattr(request, "user", None)
    if not is_new_user_for_onboarding(user):
        return None
    rm = getattr(request, "resolver_match", None)
    url_name = getattr(rm, "url_name", None) if rm else None
    page = onboarding_page_for_url_name(url_name or "")
    if not page:
        return None
    if user_has_seen_onboarding_page(user, page.page_key):
        return None
    return {
        "page_key": page.page_key,
        "banner_title": page.banner_title,
        "banner_text": page.banner_text,
        "steps": [{"selector": s.selector, "text": s.text} for s in page.steps],
        "storage_key": f"euadopt_onboard_{page.page_key}",
        "site_guide_hint": "Ai întrebări? Apasă butonul Ghid EU-Adopt jos-dreapta.",
    }
