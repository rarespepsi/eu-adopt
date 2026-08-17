"""Pre-lansare: blocare soft Shop, donații, plăți comerciale (staff poate testa)."""

from __future__ import annotations

from django.conf import settings

from home.models import SiteCartItem

PRELAUNCH_SOFT_LOCK_BANNER = (
    "Etapa pre-lansare: Shop, donații și plățile comerciale sunt temporar închise. "
    "Publicitatea și promovarea A2 sunt gratuite ca să învățați platforma."
)

PRELAUNCH_SOFT_MESSAGES = {
    "shop": (
        "Shop-ul (produse, magazin foto, personalizate inclusiv autocar/cuști) "
        "se deschide după lansare. Acum puteți folosi publicitatea gratuită și înscrierea partenerilor."
    ),
    "donatii": (
        "Donațiile și formularele fiscale online se activează după lansare. "
        "În pre-lansare ne concentrăm pe popularea platformei."
    ),
    "custi": (
        "Pagina cuști / autocar este temporar închisă în pre-lansare. "
        "Reveniți după lansarea oficială."
    ),
    "checkout": (
        "Coșul conține articole comerciale (shop, servicii plătite) care nu pot fi finalizate "
        "în pre-lansare. Eliminați-le sau așteptați lansarea."
    ),
    "cart_add": (
        "Nu puteți adăuga acest articol în coș în pre-lansare. "
        "Shop-ul și ofertele plătite se deschid după lansare."
    ),
    "adopt": (
        "Butonul „Vreau să adopt” este inactiv în perioada de populare. "
        "Adopțiile online se deschid după lansarea oficială."
    ),
}

PRELAUNCH_SOFT_MESSAGE_UI_KEYS: dict[str, str] = {
    "shop": "prelaunch_msg_shop",
    "donatii": "prelaunch_msg_donatii",
    "custi": "prelaunch_msg_custi",
    "checkout": "prelaunch_msg_checkout",
    "cart_add": "prelaunch_msg_cart_add",
    "adopt": "prelaunch_msg_adopt",
}

# În pre-lansare rămân permise doar publicitate + promovare A2 (gratuite).
PRELAUNCH_SOFT_ALLOWED_CART_KINDS = frozenset(
    {
        SiteCartItem.KIND_PUBLICITATE,
        SiteCartItem.KIND_PROMO_A2,
    }
)

PRELAUNCH_SOFT_BLOCKED_CART_KINDS = frozenset(
    {
        SiteCartItem.KIND_SHOP,
        SiteCartItem.KIND_SHOP_CUSTOM,
        SiteCartItem.KIND_SHOP_FOTO,
        SiteCartItem.KIND_SERVICII_OFFER,
    }
)

# Hint scurt la prima vizită (cheie localStorage → mesaj RO; pe EU → eu_ui).
PRELAUNCH_FIRST_HINTS: dict[str, str] = {
    "mypet": "MyPet: adaugă animale publicate, apoi poți promova gratuit un câine în HOME (1 promovare/cont).",
    "publicitate_harta": "Publicitate: alege o casetă pe hartă, adaugă în coș și activează gratuit (1 casetă/cont în pre-lansare).",
    "publicitate_cos": "Coș publicitate: transferă în Coș general → Plată → activare gratuită.",
    "collab_offers_control": "Oferte partener: publici servicii/produse din Magazinul meu; fără plafon de număr.",
    "pets_all": "Prietenul tău: răsfoiește anunțuri; din fișă poți promova un animal în grila Acasă.",
    "i_love_cos": "Coș: în pre-lansare finalizează doar publicitate sau promovare A2 (gratuit).",
}

PRELAUNCH_FIRST_HINT_UI_KEYS: dict[str, str] = {
    "mypet": "prelaunch_hint_mypet",
    "publicitate_harta": "prelaunch_hint_publicitate_harta",
    "publicitate_cos": "prelaunch_hint_publicitate_cos",
    "collab_offers_control": "prelaunch_hint_collab_offers",
    "pets_all": "prelaunch_hint_pets_all",
    "i_love_cos": "prelaunch_hint_i_love_cos",
}


def prelaunch_monetization_soft_lock_enabled() -> bool:
    explicit = getattr(settings, "PRELAUNCH_MONETIZATION_SOFT_LOCK", None)
    if explicit is not None:
        return bool(explicit)
    return bool(getattr(settings, "PRELAUNCH_MODE", False))


def prelaunch_soft_lock_staff_bypass(user) -> bool:
    return bool(
        user
        and getattr(user, "is_authenticated", False)
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
    )


def prelaunch_soft_lock_active_for_user(user) -> bool:
    if not prelaunch_monetization_soft_lock_enabled():
        return False
    if prelaunch_soft_lock_staff_bypass(user):
        return False
    return True


def prelaunch_cart_kind_soft_blocked(kind: str) -> bool:
    return (kind or "").strip() in PRELAUNCH_SOFT_BLOCKED_CART_KINDS


def prelaunch_checkout_lines_soft_blocked(lines: list[dict]) -> bool:
    for row in lines or []:
        if prelaunch_cart_kind_soft_blocked((row.get("kind") or "").strip()):
            return True
    return False


def prelaunch_soft_message(request, area: str) -> str:
    ro = PRELAUNCH_SOFT_MESSAGES.get(area) or PRELAUNCH_SOFT_LOCK_BANNER
    ui_key = PRELAUNCH_SOFT_MESSAGE_UI_KEYS.get(area, "prelaunch_banner_body")
    if request is not None:
        from home.eu_ui_labels import eu_or_ro

        return eu_or_ro(request, ui_key, ro)
    return ro


def prelaunch_first_hint_for_url_name(url_name: str, request=None) -> str | None:
    if not prelaunch_monetization_soft_lock_enabled():
        return None
    key = (url_name or "").strip()
    ro = PRELAUNCH_FIRST_HINTS.get(key)
    if not ro:
        return None
    ui_key = PRELAUNCH_FIRST_HINT_UI_KEYS.get(key)
    if request is not None and ui_key:
        from home.eu_ui_labels import eu_or_ro

        return eu_or_ro(request, ui_key, ro)
    return ro


def prelaunch_soft_lock_redirect(request, area: str, *, redirect_name: str = "mypet"):
    """Redirect prietenos (soft) — nu 403."""
    from django.contrib import messages
    from django.shortcuts import redirect
    from django.urls import reverse

    msg = prelaunch_soft_message(request, area)
    messages.info(request, msg)
    try:
        target = reverse(redirect_name)
    except Exception:
        target = reverse("mypet")
    return redirect(target)
