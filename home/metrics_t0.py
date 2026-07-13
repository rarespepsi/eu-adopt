"""T₀ campanie — contorizare de la o dată fixă (înregistrări, logări, lead-uri /inscriere/)."""

from __future__ import annotations

import logging
from datetime import datetime

from django.conf import settings
from django.contrib.auth import get_user_model
from django.utils import timezone

logger = logging.getLogger(__name__)

INSCRIERE_LEAD_NOTE_MARKER = "/inscriere/"


def metrics_t0_start() -> datetime | None:
    """Începutul zilei T₀ în fusul proiectului (00:00 local)."""
    raw = (getattr(settings, "METRICS_T0_DATE", None) or "").strip()
    if not raw:
        return None
    try:
        y, m, d = (int(x) for x in raw.split("-", 2))
        naive = datetime(y, m, d, 0, 0, 0)
        return timezone.make_aware(naive, timezone.get_current_timezone())
    except (TypeError, ValueError):
        logger.warning("metrics_t0_invalid_date raw=%r", raw)
        return None


def metrics_t0_enabled() -> bool:
    return metrics_t0_start() is not None


def record_site_login_event(user, source: str) -> None:
    """Înregistrează login reușit (nu aruncă excepții). Staff/superuser sunt ignorați."""
    if not user or not getattr(user, "pk", None):
        return
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return
    t0 = metrics_t0_start()
    if t0 is None:
        return
    try:
        from home.models import SiteLoginEvent

        allowed = {c[0] for c in SiteLoginEvent.SOURCE_CHOICES}
        src = (source or SiteLoginEvent.SOURCE_LOGIN).strip()
        if src not in allowed:
            src = SiteLoginEvent.SOURCE_LOGIN
        SiteLoginEvent.objects.create(user=user, source=src)
    except Exception:
        logger.exception("metrics_t0_record_login_failed user_id=%s", getattr(user, "pk", None))


def metrics_t0_staff_context() -> dict:
    """KPI-uri staff de la T₀ pentru Analiză / Prezență."""
    t0 = metrics_t0_start()
    if t0 is None:
        return {"metrics_t0_enabled": False}

    User = get_user_model()
    from home.models import SiteLoginEvent, StaffOnboardingLead

    users_qs = User.objects.filter(is_staff=False, date_joined__gte=t0)
    logins_qs = SiteLoginEvent.objects.filter(logged_in_at__gte=t0, user__is_staff=False).exclude(
        user__is_superuser=True
    )
    inscriere_qs = StaffOnboardingLead.objects.filter(
        created_at__gte=t0,
        invite_staff_notes__icontains=INSCRIERE_LEAD_NOTE_MARKER,
    )

    label = timezone.localtime(t0).strftime("%d.%m.%Y")

    return {
        "metrics_t0_enabled": True,
        "metrics_t0_label": label,
        "metrics_t0_date_iso": t0.date().isoformat(),
        "metrics_t0_new_users": users_qs.count(),
        "metrics_t0_new_users_active": users_qs.filter(is_active=True).count(),
        "metrics_t0_login_events": logins_qs.count(),
        "metrics_t0_login_unique_users": logins_qs.values("user_id").distinct().count(),
        "metrics_t0_inscriere_leads": inscriere_qs.count(),
    }
