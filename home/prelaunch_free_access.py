"""Pre-lansare: publicitate + promovare A2 gratuite, limite per utilizator."""
from __future__ import annotations

import copy
from decimal import Decimal

from django.conf import settings
from django.utils import timezone

PRELAUNCH_FREE_BANNER = "Gratuit — etapă pre-lansare"


def publicitate_prelaunch_free_enabled() -> bool:
    explicit = getattr(settings, "PUBLICITATE_PRELAUNCH_FREE", None)
    if explicit is not None:
        return bool(explicit)
    return bool(getattr(settings, "PRELAUNCH_MODE", False))


def publicitate_max_slots_per_user() -> int:
    if not publicitate_prelaunch_free_enabled():
        return 0
    return max(1, int(getattr(settings, "PUBLICITATE_PRELAUNCH_MAX_SLOTS_PER_USER", 1)))


def promo_a2_max_per_user() -> int:
    if not publicitate_prelaunch_free_enabled():
        return 0
    return max(1, int(getattr(settings, "PROMO_A2_PRELAUNCH_MAX_PER_USER", 1)))


def collab_max_offers_per_user() -> int:
    if not publicitate_prelaunch_free_enabled():
        return 0
    return max(1, int(getattr(settings, "COLLAB_PRELAUNCH_MAX_OFFERS_PER_USER", 1)))


def promo_a2_price_lei() -> int:
    if publicitate_prelaunch_free_enabled():
        return 0
    return int(getattr(settings, "PROMO_A2_BASE_PRICE_LEI", 10))


def promo_a2_price_label() -> str:
    p = promo_a2_price_lei()
    if p <= 0:
        return "Gratuit (pre-lansare)"
    return f"{p} lei"


def publicitate_effective_price(base_price) -> int:
    if publicitate_prelaunch_free_enabled():
        return 0
    try:
        return int(base_price)
    except (TypeError, ValueError):
        return 0


def publicitate_effective_slot_map(slot_map: dict) -> dict:
    """Copie catalog cu prețuri 0 în pre-lansare."""
    if not publicitate_prelaunch_free_enabled():
        return slot_map
    out: dict = {}
    for section, rows in (slot_map or {}).items():
        out[section] = []
        for row in rows or []:
            item = copy.copy(row)
            item["price"] = 0
            out[section].append(item)
    return out


def publicitate_catalog_row_effective(section: str, code: str, slot_map: dict) -> dict | None:
    for row in slot_map.get(section) or []:
        if row.get("code") == code:
            item = copy.copy(row)
            item["price"] = publicitate_effective_price(row.get("price", 0))
            return item
    return None


def _publicitate_user_reserved_line_count(user) -> int:
    from home.models import PublicitateOrder, PublicitateOrderLine

    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return 0
    now = timezone.now()
    qs = PublicitateOrderLine.objects.filter(
        order__user=user,
        order__status__in=(
            PublicitateOrder.STATUS_PAID,
            PublicitateOrder.STATUS_PENDING,
        ),
    )
    active = qs.filter(ends_at__isnull=True) | qs.filter(ends_at__gte=now)
    return active.distinct().count()


def publicitate_user_slots_remaining(user) -> int | None:
    """None = fără limită; 0 = epuizat."""
    cap = publicitate_max_slots_per_user()
    if cap <= 0:
        return None
    used = _publicitate_user_reserved_line_count(user)
    return max(0, cap - used)


def publicitate_user_can_reserve_slots(user, additional_lines: int = 1) -> tuple[bool, str]:
    cap = publicitate_max_slots_per_user()
    if cap <= 0:
        return True, ""
    remaining = publicitate_user_slots_remaining(user)
    if remaining is None:
        return True, ""
    if additional_lines > cap:
        return False, f"În pre-lansare puteți rezerva maximum {cap} casetă publicitară per cont."
    if additional_lines > remaining:
        if remaining <= 0:
            return False, "Ați folosit deja caseta publicitară gratuită din pre-lansare (1 casetă/cont)."
        return False, f"Mai puteți rezerva doar {remaining} casetă/casete publicitară în pre-lansare."
    return True, ""


def promo_a2_user_orders_count(user) -> int:
    from home.models import PromoA2Order

    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return 0
    return PromoA2Order.objects.filter(
        payer_user=user,
        status=PromoA2Order.STATUS_PAID,
    ).count()


def promo_a2_user_can_order(user) -> tuple[bool, str]:
    cap = promo_a2_max_per_user()
    if cap <= 0:
        return True, ""
    used = promo_a2_user_orders_count(user)
    if used >= cap:
        return False, "În pre-lansare puteți activa o singură promovare A2 per cont."
    from home.models import SiteCartItem

    if SiteCartItem.objects.filter(user=user, kind=SiteCartItem.KIND_PROMO_A2).exists():
        if used + 1 > cap:
            return False, "În pre-lansare puteți activa o singură promovare A2 per cont."
    return True, ""


def collab_user_active_offers_count(user) -> int:
    from home.models import CollaboratorServiceOffer

    if not user or not getattr(user, "is_authenticated", False) or not user.is_authenticated:
        return 0
    return CollaboratorServiceOffer.objects.filter(collaborator=user, is_active=True).count()


def collab_user_can_create_offer(user) -> tuple[bool, str]:
    cap = collab_max_offers_per_user()
    if cap <= 0:
        return True, ""
    from home.models import CollaboratorServiceOffer

    total = CollaboratorServiceOffer.objects.filter(collaborator=user).count()
    if total >= cap:
        return False, "În pre-lansare puteți publica un singur serviciu/ofertă per cont."
    return True, ""
