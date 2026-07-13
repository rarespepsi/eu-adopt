"""
Înregistrare prezență site + statistici pentru Analiză / Prezență (staff).
"""
from __future__ import annotations

import hashlib
import logging
from datetime import timedelta

from django.db.models import F, Sum
from django.utils import timezone

from .models import (
    SitePresenceActive,
    SitePresenceDaily,
    SitePresenceDaySession,
    SitePresenceDayUser,
)

logger = logging.getLogger(__name__)

ONLINE_WINDOW_MINUTES = 15
PRESENCE_TRACKED_METHODS = frozenset({"GET", "HEAD"})


def _session_hash(session_key: str) -> str:
    return hashlib.sha256(session_key.encode("utf-8")).hexdigest()


def should_record_site_presence(request) -> bool:
    path = (request.path or "").lower()
    if not path or path.startswith("/static/") or path.startswith("/media/"):
        return False
    if path.endswith((".ico", ".png", ".jpg", ".jpeg", ".webp", ".svg", ".css", ".js", ".map")):
        return False
    if (request.method or "GET").upper() not in PRESENCE_TRACKED_METHODS:
        return False
    return True


def record_site_presence(request) -> None:
    """Actualizează agregate zilnice și sesiuni active; nu aruncă excepții."""
    if not should_record_site_presence(request):
        return
    try:
        session = getattr(request, "session", None)
        if session is None:
            return
        if not session.session_key:
            session.save()
        session_key = session.session_key
        if not session_key:
            return

        session_hash = _session_hash(session_key)
        now = timezone.now()
        today = timezone.localdate()
        user = getattr(request, "user", None)
        user_id = int(user.pk) if user is not None and user.is_authenticated else None

        SitePresenceActive.objects.update_or_create(
            session_hash=session_hash,
            defaults={"last_seen": now, "user_id": user_id},
        )

        daily, _ = SitePresenceDaily.objects.get_or_create(
            date=today,
            defaults={
                "page_views": 0,
                "unique_visitors": 0,
                "unique_logged_in": 0,
            },
        )
        SitePresenceDaily.objects.filter(pk=daily.pk).update(page_views=F("page_views") + 1)

        _, created_sess = SitePresenceDaySession.objects.get_or_create(
            day=today,
            session_hash=session_hash,
        )
        if created_sess:
            SitePresenceDaily.objects.filter(pk=daily.pk).update(
                unique_visitors=F("unique_visitors") + 1
            )

        if user_id:
            _, created_user = SitePresenceDayUser.objects.get_or_create(
                day=today,
                user_id=user_id,
            )
            if created_user:
                SitePresenceDaily.objects.filter(pk=daily.pk).update(
                    unique_logged_in=F("unique_logged_in") + 1
                )
    except Exception:
        logger.exception("site_presence_record_failed")


def _cleanup_stale_active(threshold) -> None:
    SitePresenceActive.objects.filter(last_seen__lt=threshold - timedelta(hours=2)).delete()


def _distinct_visitors_since(day_start) -> int:
    return (
        SitePresenceDaySession.objects.filter(day__gte=day_start)
        .values("session_hash")
        .distinct()
        .count()
    )


def _distinct_logged_since(day_start) -> int:
    return (
        SitePresenceDayUser.objects.filter(day__gte=day_start)
        .values("user_id")
        .distinct()
        .count()
    )


def _sum_page_views_since(day_start) -> int:
    return (
        SitePresenceDaily.objects.filter(date__gte=day_start).aggregate(
            total=Sum("page_views")
        )["total"]
        or 0
    )


def staff_analysis_presence_page_context() -> dict:
    """KPI-uri pentru /admin-analysis/prezenta/."""
    now = timezone.now()
    today = timezone.localdate()
    threshold = now - timedelta(minutes=ONLINE_WINDOW_MINUTES)
    _cleanup_stale_active(threshold)

    daily = SitePresenceDaily.objects.filter(date=today).first()
    week_start = today - timedelta(days=6)
    month_start = today.replace(day=1)
    year_start = today.replace(month=1, day=1)

    recent_days = []
    for offset in range(6, -1, -1):
        d = today - timedelta(days=offset)
        row = SitePresenceDaily.objects.filter(date=d).first()
        recent_days.append(
            {
                "date": d,
                "label": d.strftime("%d.%m"),
                "visitors": row.unique_visitors if row else 0,
                "page_views": row.page_views if row else 0,
                "logged_in": row.unique_logged_in if row else 0,
                "is_today": offset == 0,
            }
        )

    ctx = {
        "presence_online_window": ONLINE_WINDOW_MINUTES,
        "presence_online_visitors": SitePresenceActive.objects.filter(
            last_seen__gte=threshold
        ).count(),
        "presence_online_logged_in": SitePresenceActive.objects.filter(
            last_seen__gte=threshold,
            user_id__isnull=False,
        ).count(),
        "presence_checked_at": now,
        "presence_today_visitors": daily.unique_visitors if daily else 0,
        "presence_today_page_views": daily.page_views if daily else 0,
        "presence_today_logged_in": daily.unique_logged_in if daily else 0,
        "presence_week_visitors": _distinct_visitors_since(week_start),
        "presence_week_page_views": _sum_page_views_since(week_start),
        "presence_week_logged_in": _distinct_logged_since(week_start),
        "presence_month_visitors": _distinct_visitors_since(month_start),
        "presence_month_page_views": _sum_page_views_since(month_start),
        "presence_month_logged_in": _distinct_logged_since(month_start),
        "presence_year_visitors": _distinct_visitors_since(year_start),
        "presence_year_page_views": _sum_page_views_since(year_start),
        "presence_year_logged_in": _distinct_logged_since(year_start),
        "presence_recent_days": recent_days,
    }
    from home.metrics_t0 import metrics_t0_staff_context

    ctx.update(metrics_t0_staff_context())
    return ctx
