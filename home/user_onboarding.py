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
    # —— Faza 2 ——
    "pets_all": OnboardingPage(
        page_key="pets_all",
        banner_title="Prietenul tău — animale spre adopție",
        banner_text=(
            "Răsfoiești anunțurile publicate de adăposturi și asociații. "
            "Filtrezi după preferințe și deschizi fișa animalului pentru detalii."
        ),
        steps=(
            OnboardingStep("#P1", "Banda de sus — mesaje și noutăți de pe platformă."),
            OnboardingStep(
                "#P4",
                "Filtre și acțiuni — Găsește-mi perechea, Filtre (județ, vârstă, talie), Ajută un suflet.",
            ),
            OnboardingStep(
                "#P2",
                "Grila de animale — click pe card pentru fișă; inimioara salvează în I Love.",
            ),
            OnboardingStep(
                "#menu-main-menu",
                "Meniul navbar — acces rapid la MyPet, Servicii, Transport etc.",
            ),
        ),
    ),
    "servicii": OnboardingPage(
        page_key="servicii",
        banner_title="Servicii — parteneri EU-Adopt",
        banner_text=(
            "Găsești cabinete veterinare, magazine și saloane. "
            "Filtrezi după județ/oraș și specie, apoi deschizi oferta."
        ),
        steps=(
            OnboardingStep(
                "#sw-judet",
                "Filtre geo — Județ și Oraș/Loc; Resetează șterge selecția.",
            ),
            OnboardingStep(
                ".sw-s2-mid-tabs",
                "Tab-uri: Cabinete, Magazine, Saloane — categorii de oferte.",
            ),
            OnboardingStep(
                ".sw-s2-1-grid",
                "Grila oferte — click pe imagine sau card pentru detalii și coș I Love.",
            ),
            OnboardingStep(
                "#S1",
                "Banda S1 — promoții și informații parteneri.",
            ),
        ),
    ),
    "i_love": OnboardingPage(
        page_key="i_love",
        banner_title="I Love — favoritele tale",
        banner_text=(
            "Animalele marcate cu inimioară apar aici. "
            "Poți reveni la fișă, trimite mesaje sau promova un anunț."
        ),
        steps=(
            OnboardingStep(
                ".ilove-wire__head",
                "Titlu pagină — lista animalelor salvate cu inimioară.",
            ),
            OnboardingStep(
                ".ilove-pets-grid",
                "Carduri animale — click pentru fișă; plicul deschide mesajele.",
            ),
            OnboardingStep(
                ".ilove-wire__col--left",
                "Casete publicitate stânga — promoții parteneri (dacă sunt active).",
            ),
        ),
    ),
    # —— Faza finală (restul navbar + fluxuri partener) ——
    "transport": OnboardingPage(
        page_key="transport",
        banner_title="Transport — mutare animale",
        banner_text=(
            "Cerere de transport pentru adopție sau alte deplasări. "
            "Completezi locurile, data și detaliile; transportatorii răspund din platformă."
        ),
        steps=(
            OnboardingStep(
                "#T1",
                "Formular cerere — plecare, destinație, dată, detalii animal.",
            ),
            OnboardingStep(
                "#T2",
                "Informații și status — urmărești cererea ta sau ofertele transportatorilor.",
            ),
            OnboardingStep(
                "#T3",
                "Zone auxiliare — linkuri utile, donații cuști/autocar (când sunt active).",
            ),
        ),
    ),
    "shop": OnboardingPage(
        page_key="shop",
        banner_title="Shop EU-Adopt",
        banner_text=(
            "Produse pentru animale: câini, pisici, accesorii. "
            "Poți accesa și magazinul foto ONG sau donațiile din banda de sus."
        ),
        steps=(
            OnboardingStep(
                ".shw-sh1",
                "Banda SH1 — Shop Poze ONG și link donații Ajută un suflet.",
            ),
            OnboardingStep(
                ".shop-tabs",
                "Tab-uri specie — Câini, Pisici, Accesorii.",
            ),
            OnboardingStep(
                ".shop-grid",
                "Produse — click pe card pentru detalii și coș (după lansare).",
            ),
        ),
    ),
    "publicitate_cos": OnboardingPage(
        page_key="publicitate_cos",
        banner_title="Coș publicitate",
        banner_text=(
            "Verifici sloturile alese, perioadele și treci la plată / activare. "
            "În pre-lansare poate fi activare gratuită."
        ),
        steps=(
            OnboardingStep(
                ".pub-top-tabs",
                "Schimbi secțiunea hărții (HOME, PT, I Love…) pentru alte sloturi.",
            ),
            OnboardingStep(
                ".pub-c3",
                "Rezumat slot selectat — modifici perioada sau cantitatea.",
            ),
            OnboardingStep(
                ".pub-tab--pub-flow",
                "Navigare — înapoi la hartă tarife sau comenzile mele.",
            ),
        ),
    ),
    "collab_offers_control": OnboardingPage(
        page_key="collab_offers_control",
        banner_title="Magazinul meu — oferte",
        banner_text=(
            "Panoul colaborator: publici și gestionezi oferte/servicii/produse."
        ),
        steps=(
            OnboardingStep(
                ".mylvet-btn-add",
                "Adaugă ofertă — formular nou (poze, preț, valabilitate).",
            ),
            OnboardingStep(
                "#collabOferteFiltersBar",
                "Filtre listă — caută după titlu sau starea ofertei.",
            ),
            OnboardingStep(
                ".collab-oferte-table",
                "Tabel oferte — activează/dezactivează, editează sau șterge.",
            ),
            OnboardingStep(
                "#magazinOpenInboxBtn",
                "Mesaje — solicitări „Vreau oferta” de la utilizatori.",
            ),
        ),
    ),
    "pets_single": OnboardingPage(
        page_key="pets_single",
        banner_title="Fișa animalului",
        banner_text=(
            "Detalii complete: poze, trăsături, mesaje către adăpost. "
            "Din fișă poți cere adopția (când e activă) sau salva cu inimioara."
        ),
        steps=(
            OnboardingStep(
                "#petCardTitle",
                "Titlu fișă — numele animalului și identificare rapidă.",
            ),
            OnboardingStep(
                ".mypet-fisa-col-photos",
                "Galerie foto/video — click pe imagine pentru mărire (pinch pe mobil).",
            ),
            OnboardingStep(
                "#petAdoptCorner",
                "Adopție — buton cerere (dacă e activ); altfel vezi starea anunțului.",
            ),
            OnboardingStep(
                "#petCardBackBtn",
                "Înapoi la listă — revii la Prietenul tău sau pagina anterioară.",
            ),
        ),
    ),
    "i_love_cos": OnboardingPage(
        page_key="i_love_cos",
        banner_title="Coș I Love / general",
        banner_text=(
            "Coșul reunește oferte Servicii și publicitate. "
            "În pre-lansare finalizezi doar articole gratuite (pub / promovare)."
        ),
        steps=(
            OnboardingStep(
                "#menu-main-menu",
                "Meniul site — revii la paginile unde ai adăugat produse.",
            ),
            OnboardingStep(
                "#main_content",
                "Conținut coș — verifici liniile și mergi la plată când e disponibilă.",
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
    from home.eu_ui_labels import eu_or_ro

    title_key = f"onboard_{page.page_key}_title"
    text_key = f"onboard_{page.page_key}_text"
    return {
        "page_key": page.page_key,
        "banner_title": eu_or_ro(request, title_key, page.banner_title),
        "banner_text": eu_or_ro(request, text_key, page.banner_text),
        "steps": [
            {
                "selector": s.selector,
                "text": eu_or_ro(request, f"onboard_{page.page_key}_s{i}", s.text),
            }
            for i, s in enumerate(page.steps, start=1)
        ],
        "storage_key": f"euadopt_onboard_{page.page_key}",
        "site_guide_hint": eu_or_ro(
            request,
            "onboard_guide_hint",
            "Ai întrebări? Apasă butonul Ghid EU-Adopt jos-dreapta.",
        ),
    }
