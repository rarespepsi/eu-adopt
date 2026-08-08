"""Val zilnic invitații Add USER — alternare Grupa A / B (cron).

Slot morning (10:00): adăposturi (implicit).
Slot afternoon (16:00): colaboratori cabinet + magazin/farmacie + grooming.
"""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from urllib.parse import urlencode

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.db.models import Q
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
from home.staff_invite_email_expand import (
    UNSENDABLE_EMAIL_REASONS,
    staff_invite_expand_picked_leads,
    staff_invite_retire_unsendable_email,
)
from home.views import _staff_onboarding_leads_filtered_qs_from_querydict

logger = logging.getLogger(__name__)

STAFF_INVITE_CRON_REGION_CACHE_KEY = "euadopt:staff_invite_cron:last_region_group"
STAFF_INVITE_CRON_PM_REGION_CACHE_KEY = "euadopt:staff_invite_cron:pm:last_region_group"

WAVE_SLOT_MORNING = "morning"
WAVE_SLOT_AFTERNOON = "afternoon"

# Cabinete + magazine/farmacii + grooming (lista colaboratori, fără transport).
DEFAULT_PM_COLLAB_SUBTYPES = (
    StaffOnboardingLead.COLLAB_CABINET,
    StaffOnboardingLead.COLLAB_MAGAZIN,
    StaffOnboardingLead.COLLAB_GROOMING,
)


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
    wave_slot: str = WAVE_SLOT_MORNING
    collab_subtypes: list[str] = field(default_factory=list)

    @property
    def message(self) -> str:
        if self.skipped:
            return f"Val zilnic oprit: {self.skip_reason}"
        base = staff_invite_build_result_message(self.stats, wave=True)
        slot_label = "AM" if self.wave_slot == WAVE_SLOT_MORNING else "PM"
        extras = ""
        if self.collab_subtypes:
            extras = f" · subtypes={','.join(self.collab_subtypes)}"
        return (
            f"[{slot_label}] Grupa {self.region_group.upper()} · {self.account_kind}{extras}: "
            f"{self.picked_count} rânduri, {self.expanded_count} destinatari. {base}"
        )


def staff_invite_cron_enabled() -> bool:
    return bool(getattr(settings, "STAFF_INVITE_CRON_ENABLED", False))


def staff_invite_cron_wave_size() -> int:
    return int(getattr(settings, "STAFF_INVITE_CRON_WAVE_SIZE", 25) or 25)


def staff_invite_cron_pm_wave_size() -> int:
    return int(getattr(settings, "STAFF_INVITE_CRON_PM_WAVE_SIZE", 25) or 25)


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


def staff_invite_cron_pm_account_kind() -> str:
    kind = (
        getattr(settings, "STAFF_INVITE_CRON_PM_ACCOUNT_KIND", StaffOnboardingLead.KIND_COLLAB)
        or StaffOnboardingLead.KIND_COLLAB
    ).strip()
    if kind in (
        StaffOnboardingLead.KIND_PF,
        StaffOnboardingLead.KIND_ORG,
        StaffOnboardingLead.KIND_COLLAB,
        StaffOnboardingLead.KIND_ADAPOST,
    ):
        return kind
    return StaffOnboardingLead.KIND_COLLAB


def staff_invite_cron_pm_collab_subtypes() -> list[str]:
    raw = (getattr(settings, "STAFF_INVITE_CRON_PM_COLLAB_SUBTYPES", "") or "").strip()
    allowed = {
        StaffOnboardingLead.COLLAB_CABINET,
        StaffOnboardingLead.COLLAB_SERVICII,
        StaffOnboardingLead.COLLAB_MAGAZIN,
        StaffOnboardingLead.COLLAB_GROOMING,
        StaffOnboardingLead.COLLAB_TRANSPORT,
    }
    if not raw:
        return list(DEFAULT_PM_COLLAB_SUBTYPES)
    out: list[str] = []
    for part in raw.replace(";", ",").split(","):
        sub = part.strip().lower()
        if sub == "cv":
            sub = StaffOnboardingLead.COLLAB_CABINET
        if sub in allowed and sub not in out:
            out.append(sub)
    return out or list(DEFAULT_PM_COLLAB_SUBTYPES)


def _region_cache_key(wave_slot: str) -> str:
    if wave_slot == WAVE_SLOT_AFTERNOON:
        return STAFF_INVITE_CRON_PM_REGION_CACHE_KEY
    return STAFF_INVITE_CRON_REGION_CACHE_KEY


def next_region_group_for_cron(wave_slot: str = WAVE_SLOT_MORNING) -> str:
    """Alternă A ↔ B; prima rulare (fără cache) → A."""
    last = cache.get(_region_cache_key(wave_slot))
    if last == "a":
        return "b"
    if last == "b":
        return "a"
    return "a"


def mark_region_group_used(region_group: str, wave_slot: str = WAVE_SLOT_MORNING) -> None:
    grp = (region_group or "").strip().lower()
    if grp in ("a", "b"):
        cache.set(_region_cache_key(wave_slot), grp, timeout=60 * 60 * 24 * 400)


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
    collab_subtypes: list[str] | None = None,
) -> list[StaffOnboardingLead]:
    params = {
        "account_kind": account_kind,
        "region_group": region_group,
        "invite_first_only": "1",
    }
    qd = QueryDict(urlencode(params))
    qs = _staff_onboarding_leads_filtered_qs_from_querydict(qd)
    qs = qs.filter(invite_mail_status=StaffOnboardingLead.INVITE_NEVER)
    if account_kind == StaffOnboardingLead.KIND_COLLAB and collab_subtypes:
        subtype_q = Q(collaborator_subtype__in=collab_subtypes)
        if StaffOnboardingLead.COLLAB_CABINET in collab_subtypes:
            subtype_q |= Q(collaborator_subtype=StaffOnboardingLead.COLLAB_CV)
        qs = qs.filter(subtype_q)
    picked: list[StaffOnboardingLead] = []
    for lead in qs.order_by("judet", "oras", "pk").iterator():
        ok, reason = staff_invite_can_send(lead)
        if ok:
            picked.append(lead)
        elif reason in UNSENDABLE_EMAIL_REASONS:
            # Scoate din pool și continuă până umpli valul cu adrese valide.
            staff_invite_retire_unsendable_email(lead)
        if len(picked) >= wave_limit:
            break
    return picked


def run_staff_invite_daily_wave(
    *,
    region_group: str | None = None,
    account_kind: str | None = None,
    wave_limit: int | None = None,
    force: bool = False,
    wave_slot: str = WAVE_SLOT_MORNING,
    collab_subtypes: list[str] | None = None,
) -> DailyWaveResult:
    slot = (wave_slot or WAVE_SLOT_MORNING).strip().lower()
    if slot not in (WAVE_SLOT_MORNING, WAVE_SLOT_AFTERNOON):
        slot = WAVE_SLOT_MORNING

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
            wave_slot=slot,
        )

    grp = (region_group or next_region_group_for_cron(slot)).strip().lower()
    if grp not in ("a", "b"):
        grp = "a"

    if slot == WAVE_SLOT_AFTERNOON:
        kind = account_kind or staff_invite_cron_pm_account_kind()
        limit = wave_limit if wave_limit is not None else staff_invite_cron_pm_wave_size()
        subtypes = list(collab_subtypes) if collab_subtypes is not None else staff_invite_cron_pm_collab_subtypes()
    else:
        kind = account_kind or staff_invite_cron_account_kind()
        limit = wave_limit if wave_limit is not None else staff_invite_cron_wave_size()
        subtypes = list(collab_subtypes) if collab_subtypes else []

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
            skip_reason=f"plafon zilnic atins ({getattr(settings, 'STAFF_LEAD_INVITE_MAX_PER_DAY', 55)}/zi).",
            wave_slot=slot,
            collab_subtypes=subtypes,
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
            wave_slot=slot,
            collab_subtypes=subtypes,
        )

    picked = pick_leads_for_daily_wave(
        region_group=grp,
        account_kind=kind,
        wave_limit=limit,
        collab_subtypes=subtypes or None,
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

    # Avansăm A↔B după orice încercare reală (inclusiv pool doar cu invalide scoase / SMTP erori).
    mark_region_group_used(grp, slot)

    logger.info(
        "staff_invite_daily_wave slot=%s grp=%s kind=%s subtypes=%s picked=%s expanded=%s stats=%s smtp=%s",
        slot,
        grp,
        kind,
        subtypes,
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
        wave_slot=slot,
        collab_subtypes=subtypes,
    )
