"""Val zilnic invitații Add USER — alternare Grupa A / B (cron)."""

from __future__ import annotations

import logging
from dataclasses import dataclass

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.http import QueryDict
from django.test import RequestFactory

from home.models import StaffOnboardingLead, StaffOnboardingInviteLog
from home.staff_onboarding_invite import (
    staff_invite_build_result_message,
    staff_invite_can_send,
    staff_invite_daily_remaining,
    staff_invite_email_enabled,
    staff_invite_process_batch,
)
from home.staff_invite_email_expand import staff_invite_expand_picked_leads
from home.views import _staff_onboarding_leads_filtered_qs_from_querydict

logger = logging.getLogger(__name__)

STAFF_INVITE_CRON_REGION_CACHE_KEY = "euadopt:staff_invite_cron:last_region_group"


@dataclass
class DailyWaveResult:
    region_group: str
    account_kind: str
    wave_limit: int
    picked_count: int
    expanded_count: int
    stats: dict[str, int]
    skipped: bool
    skip_reason: str = ""

    @property
    def message(self) -> str:
        if self.skipped:
            return f"Val zilnic oprit: {self.skip_reason}"
        base = staff_invite_build_result_message(self.stats, wave=True)
        return (
            f"Grupa {self.region_group.upper()} · {self.account_kind}: "
            f"{self.picked_count} rânduri, {self.expanded_count} destinatari. {base}"
        )


def staff_invite_cron_enabled() -> bool:
    return bool(getattr(settings, "STAFF_INVITE_CRON_ENABLED", False))


def staff_invite_cron_wave_size() -> int:
    return int(getattr(settings, "STAFF_INVITE_CRON_WAVE_SIZE", 25) or 25)


def staff_invite_cron_account_kind() -> str:
    kind = (getattr(settings, "STAFF_INVITE_CRON_ACCOUNT_KIND", "adapost") or "adapost").strip()
    if kind in (
        StaffOnboardingLead.KIND_PF,
        StaffOnboardingLead.KIND_ORG,
        StaffOnboardingLead.KIND_COLLAB,
        StaffOnboardingLead.KIND_ADAPOST,
    ):
        return kind
    return StaffOnboardingLead.KIND_ADAPOST


def next_region_group_for_cron() -> str:
    """Alternă A ↔ B; prima rulare (fără cache) → A (după Grupa B manuală)."""
    last = cache.get(STAFF_INVITE_CRON_REGION_CACHE_KEY)
    if last == "a":
        return "b"
    if last == "b":
        return "a"
    return "a"


def mark_region_group_used(region_group: str) -> None:
    grp = (region_group or "").strip().lower()
    if grp in ("a", "b"):
        cache.set(STAFF_INVITE_CRON_REGION_CACHE_KEY, grp, timeout=60 * 60 * 24 * 400)


def _cron_staff_user():
    User = get_user_model()
    return (
        User.objects.filter(username__iexact="rares", is_staff=True).first()
        or User.objects.filter(is_superuser=True).first()
        or User.objects.filter(is_staff=True).first()
    )


def pick_leads_for_daily_wave(
    *,
    region_group: str,
    account_kind: str,
    wave_limit: int,
) -> list[StaffOnboardingLead]:
    qd = QueryDict(
        f"account_kind={account_kind}&region_group={region_group}&invite_first_only=1"
    )
    qs = _staff_onboarding_leads_filtered_qs_from_querydict(qd)
    qs = qs.filter(invite_mail_status=StaffOnboardingLead.INVITE_NEVER)
    picked: list[StaffOnboardingLead] = []
    for lead in qs.order_by("judet", "oras", "pk").iterator():
        if staff_invite_can_send(lead)[0]:
            picked.append(lead)
        if len(picked) >= wave_limit:
            break
    return picked


def run_staff_invite_daily_wave(
    *,
    region_group: str | None = None,
    account_kind: str | None = None,
    wave_limit: int | None = None,
    force: bool = False,
) -> DailyWaveResult:
    if not force and not staff_invite_cron_enabled():
        return DailyWaveResult(
            region_group=region_group or "",
            account_kind=account_kind or "",
            wave_limit=0,
            picked_count=0,
            expanded_count=0,
            stats={},
            skipped=True,
            skip_reason="EUADOPT_STAFF_INVITE_CRON_ENABLED nu e activ.",
        )

    grp = (region_group or next_region_group_for_cron()).strip().lower()
    if grp not in ("a", "b"):
        grp = "a"
    kind = account_kind or staff_invite_cron_account_kind()
    limit = wave_limit if wave_limit is not None else staff_invite_cron_wave_size()
    limit = max(1, min(int(limit), int(getattr(settings, "STAFF_LEAD_INVITE_MAX_BATCH", 100))))

    if staff_invite_daily_remaining() <= 0:
        return DailyWaveResult(
            region_group=grp,
            account_kind=kind,
            wave_limit=limit,
            picked_count=0,
            expanded_count=0,
            stats={"daily_cap": 1},
            skipped=True,
            skip_reason=f"plafon zilnic atins ({getattr(settings, 'STAFF_LEAD_INVITE_MAX_PER_DAY', 30)}/zi).",
        )

    staff_user = _cron_staff_user()
    if not staff_user:
        return DailyWaveResult(
            region_group=grp,
            account_kind=kind,
            wave_limit=limit,
            picked_count=0,
            expanded_count=0,
            stats={},
            skipped=True,
            skip_reason="lipsă cont staff pentru trimitere.",
        )

    picked = pick_leads_for_daily_wave(
        region_group=grp,
        account_kind=kind,
        wave_limit=limit,
    )
    expanded = staff_invite_expand_picked_leads(picked)

    request = RequestFactory().get("/", HTTP_HOST="www.eu-adopt.ro", secure=True)
    stats = staff_invite_process_batch(
        request,
        staff_user,
        expanded,
        dispatch_kind=StaffOnboardingInviteLog.DISPATCH_WAVE,
        max_count=len(expanded),
    )

    if picked and (stats.get("sent") or stats.get("simulated")):
        mark_region_group_used(grp)

    logger.info(
        "staff_invite_daily_wave grp=%s kind=%s picked=%s expanded=%s stats=%s smtp=%s",
        grp,
        kind,
        len(picked),
        len(expanded),
        stats,
        staff_invite_email_enabled(),
    )

    return DailyWaveResult(
        region_group=grp,
        account_kind=kind,
        wave_limit=limit,
        picked_count=len(picked),
        expanded_count=len(expanded),
        stats=stats,
        skipped=False,
    )
