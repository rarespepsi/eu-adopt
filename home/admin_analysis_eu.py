"""
Analiză EU (superuser): hub piețe + KPI pe useri PF / login / adopții / I Love / mesaje.

Atribuire piață după UserProfile.country (ISO alpha-2):
- de → DE
- fr → FR
- es → ES
- com → orice altă țară non-RO (hub .com / alte țări)
- eu → suma DE+FR+ES+COM (tot ce nu e RO)
"""
from __future__ import annotations

from datetime import timedelta

from django.contrib.auth import get_user_model
from django.db.models import Count, Q
from django.utils import timezone

from home.models import (
    AccountProfile,
    AdoptionRequest,
    PetMessage,
    SiteLoginEvent,
    UserProfile,
    WishlistItem,
)

EU_MARKETS = ("es", "de", "fr", "com", "eu")

EU_MARKET_LABELS = {
    "es": "ES — Spania",
    "de": "DE — Germania",
    "fr": "FR — Franța",
    "com": "COM — Hub / alte țări",
    "eu": "EU — total (ES+DE+FR+COM)",
}

# Țări atribuite explicit piețelor de țară; restul non-RO → COM.
_MARKET_COUNTRIES = {
    "es": frozenset({"ES"}),
    "de": frozenset({"DE"}),
    "fr": frozenset({"FR"}),
}


def normalize_eu_market(code: str | None) -> str | None:
    c = (code or "").strip().lower()
    return c if c in EU_MARKETS else None


def _country_q_for_market(market: str) -> Q:
    """Q pe UserProfile.country pentru piața cerută."""
    if market == "eu":
        return ~Q(country__iexact="RO") & ~Q(country="")
    if market in _MARKET_COUNTRIES:
        countries = _MARKET_COUNTRIES[market]
        q = Q()
        for c in countries:
            q |= Q(country__iexact=c)
        return q
    # com: non-RO, non-empty, not DE/FR/ES
    q = ~Q(country="") & ~Q(country__iexact="RO")
    for c in ("DE", "FR", "ES"):
        q &= ~Q(country__iexact=c)
    return q


def eu_user_ids_for_market(market: str) -> list[int]:
    """ID-uri user (non-staff) cu profil pe piața respectivă."""
    User = get_user_model()
    country_q = _country_q_for_market(market)
    profile_user_ids = UserProfile.objects.filter(country_q).values_list("user_id", flat=True)
    return list(
        User.objects.filter(pk__in=profile_user_ids, is_staff=False, is_superuser=False).values_list(
            "pk", flat=True
        )
    )


def build_eu_market_analysis_context(market: str) -> dict:
    market = normalize_eu_market(market) or "eu"
    User = get_user_model()
    now = timezone.now()
    d1 = now - timedelta(days=1)
    d7 = now - timedelta(days=7)
    d30 = now - timedelta(days=30)

    user_ids = eu_user_ids_for_market(market)
    users_qs = User.objects.filter(pk__in=user_ids)
    total = users_qs.count()
    active = users_qs.filter(is_active=True).count()
    inactive = total - active

    with_profile = set(
        AccountProfile.objects.filter(user_id__in=user_ids).values_list("user_id", flat=True)
    )
    pf_explicit = AccountProfile.objects.filter(
        user_id__in=user_ids, role=AccountProfile.ROLE_PF
    ).count()
    # Fără profil = default PF
    pf_count = pf_explicit + sum(1 for uid in user_ids if uid not in with_profile)

    new_1d = users_qs.filter(date_joined__gte=d1).count()
    new_7d = users_qs.filter(date_joined__gte=d7).count()
    new_30d = users_qs.filter(date_joined__gte=d30).count()

    logins_qs = SiteLoginEvent.objects.filter(user_id__in=user_ids)
    login_1d = logins_qs.filter(logged_in_at__gte=d1).count()
    login_7d = logins_qs.filter(logged_in_at__gte=d7).count()
    login_30d = logins_qs.filter(logged_in_at__gte=d30).count()
    login_unique_7d = (
        logins_qs.filter(logged_in_at__gte=d7).values("user_id").distinct().count()
    )
    login_unique_30d = (
        logins_qs.filter(logged_in_at__gte=d30).values("user_id").distinct().count()
    )

    adoptions = AdoptionRequest.objects.filter(adopter_id__in=user_ids)
    adopt_by_status = {
        row["status"]: row["c"]
        for row in adoptions.values("status").annotate(c=Count("id"))
    }
    adopt_total = adoptions.count()
    adopt_pending = adopt_by_status.get(AdoptionRequest.STATUS_PENDING, 0)
    adopt_accepted = adopt_by_status.get(AdoptionRequest.STATUS_ACCEPTED, 0)
    adopt_rejected = adopt_by_status.get(AdoptionRequest.STATUS_REJECTED, 0)
    adopt_finalized = adopt_by_status.get(AdoptionRequest.STATUS_FINALIZED, 0)
    adopt_7d = adoptions.filter(created_at__gte=d7).count()
    adopt_30d = adoptions.filter(created_at__gte=d30).count()

    wishlist = WishlistItem.objects.filter(user_id__in=user_ids).count()
    messages_sent = PetMessage.objects.filter(sender_id__in=user_ids).count()
    messages_7d = PetMessage.objects.filter(sender_id__in=user_ids, created_at__gte=d7).count()

    # Ultimii useri (max 40)
    recent_users = []
    for u in users_qs.order_by("-date_joined")[:40]:
        prof = UserProfile.objects.filter(user_id=u.pk).only("country").first()
        last_login_ev = (
            SiteLoginEvent.objects.filter(user_id=u.pk)
            .order_by("-logged_in_at")
            .values_list("logged_in_at", flat=True)
            .first()
        )
        recent_users.append(
            {
                "id": u.pk,
                "username": u.username,
                "email": u.email,
                "country": (prof.country if prof else "") or "—",
                "is_active": u.is_active,
                "date_joined": u.date_joined,
                "last_login_event": last_login_ev,
                "last_login": u.last_login,
            }
        )

    # Distribuție țări (utile pe COM / EU)
    country_breakdown = list(
        UserProfile.objects.filter(user_id__in=user_ids)
        .exclude(country="")
        .values("country")
        .annotate(c=Count("id"))
        .order_by("-c")[:20]
    )

    return {
        "eu_market": market,
        "eu_market_label": EU_MARKET_LABELS.get(market, market.upper()),
        "eu_markets": [
            {"code": m, "label": EU_MARKET_LABELS[m], "active": m == market} for m in EU_MARKETS
        ],
        "kpi_users_total": total,
        "kpi_users_active": active,
        "kpi_users_inactive": inactive,
        "kpi_users_pf": pf_count,
        "kpi_new_1d": new_1d,
        "kpi_new_7d": new_7d,
        "kpi_new_30d": new_30d,
        "kpi_login_1d": login_1d,
        "kpi_login_7d": login_7d,
        "kpi_login_30d": login_30d,
        "kpi_login_unique_7d": login_unique_7d,
        "kpi_login_unique_30d": login_unique_30d,
        "kpi_adopt_total": adopt_total,
        "kpi_adopt_pending": adopt_pending,
        "kpi_adopt_accepted": adopt_accepted,
        "kpi_adopt_rejected": adopt_rejected,
        "kpi_adopt_finalized": adopt_finalized,
        "kpi_adopt_7d": adopt_7d,
        "kpi_adopt_30d": adopt_30d,
        "kpi_wishlist": wishlist,
        "kpi_messages_sent": messages_sent,
        "kpi_messages_7d": messages_7d,
        "recent_users": recent_users,
        "country_breakdown": country_breakdown,
    }


def build_eu_hub_context() -> dict:
    """Carduri sumar pe hub (câte useri per piață)."""
    cards = []
    for m in EU_MARKETS:
        ctx = build_eu_market_analysis_context(m)
        cards.append(
            {
                "code": m,
                "label": EU_MARKET_LABELS[m],
                "users_total": ctx["kpi_users_total"],
                "users_new_7d": ctx["kpi_new_7d"],
                "logins_7d": ctx["kpi_login_7d"],
                "adoptions_total": ctx["kpi_adopt_total"],
            }
        )
    return {"eu_hub_cards": cards, "eu_markets": EU_MARKETS}
