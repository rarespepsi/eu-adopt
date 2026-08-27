"""
Val zilnic email outreach Radio (Analiza → Audio/TV).

Activare: EUADOPT_MEDIA_OUTREACH_CRON_ENABLED=1
Dimensiune: EUADOPT_MEDIA_OUTREACH_CRON_WAVE_SIZE (implicit = MAX_PER_DAY, ex. 20)
"""
from __future__ import annotations

import logging
from dataclasses import dataclass, field
from typing import Any

from django.conf import settings
from django.db.models import F

from home.media_outreach_invite import (
    media_outreach_can_send,
    media_outreach_daily_remaining,
    media_outreach_email_enabled,
    media_outreach_max_per_day,
    media_outreach_process_batch,
)
from home.models import MediaOutreachInviteLog, MediaOutreachProspect
from home.staff_invite_daily_wave import _cron_staff_user

logger = logging.getLogger(__name__)


def media_outreach_cron_enabled() -> bool:
    return bool(getattr(settings, "MEDIA_OUTREACH_CRON_ENABLED", False))


def media_outreach_cron_wave_size() -> int:
    raw = getattr(settings, "MEDIA_OUTREACH_CRON_WAVE_SIZE", None)
    if raw is None or int(raw or 0) <= 0:
        return media_outreach_max_per_day()
    return max(1, min(int(raw), media_outreach_max_per_day()))


@dataclass
class MediaRadioWaveResult:
    wave_limit: int = 0
    picked_count: int = 0
    stats: dict[str, Any] = field(default_factory=dict)
    skipped: bool = False
    skip_reason: str = ""

    @property
    def message(self) -> str:
        if self.skipped:
            return f"[Radio wave] SKIP: {self.skip_reason}"
        s = self.stats
        return (
            f"[Radio wave] limit={self.wave_limit} picked={self.picked_count} "
            f"sent={s.get('sent', 0)} sim={s.get('simulated', 0)} "
            f"blocked={s.get('blocked', 0)} err={s.get('error', 0)} "
            f"cap={s.get('daily_cap', 0)} smtp={media_outreach_email_enabled()}"
        )


def pick_radio_prospects_for_wave(*, wave_limit: int) -> list[MediaOutreachProspect]:
    """Radio eligibile: fără email gol; preferă never-sent, apoi cele mai vechi."""
    limit = max(1, int(wave_limit))
    remaining = media_outreach_daily_remaining()
    if remaining <= 0:
        return []
    limit = min(limit, remaining)

    qs = (
        MediaOutreachProspect.objects.filter(media_kind=MediaOutreachProspect.KIND_RADIO)
        .exclude(email="")
        .order_by(
            F("last_email_sent_at").asc(nulls_first=True),
            "judet",
            "outlet_name",
            "pk",
        )
    )
    picked: list[MediaOutreachProspect] = []
    for p in qs.iterator():
        ok, _reason = media_outreach_can_send(p)
        if not ok:
            continue
        picked.append(p)
        if len(picked) >= limit:
            break
    return picked


def run_media_outreach_radio_daily_wave(
    *,
    wave_limit: int | None = None,
    force: bool = False,
) -> MediaRadioWaveResult:
    if not force and not media_outreach_cron_enabled():
        return MediaRadioWaveResult(
            skipped=True,
            skip_reason="EUADOPT_MEDIA_OUTREACH_CRON_ENABLED nu e activ.",
        )

    limit = wave_limit if wave_limit is not None else media_outreach_cron_wave_size()
    limit = max(1, min(int(limit), media_outreach_max_per_day()))

    if media_outreach_daily_remaining() <= 0:
        return MediaRadioWaveResult(
            wave_limit=limit,
            skipped=True,
            skip_reason=f"plafon zilnic atins ({media_outreach_max_per_day()}/zi).",
            stats={"daily_cap": 1},
        )

    staff_user = _cron_staff_user()
    if not staff_user:
        return MediaRadioWaveResult(
            wave_limit=limit,
            skipped=True,
            skip_reason="lipsă cont staff pentru trimitere.",
        )

    picked = pick_radio_prospects_for_wave(wave_limit=limit)
    if not picked:
        return MediaRadioWaveResult(
            wave_limit=limit,
            picked_count=0,
            skipped=True,
            skip_reason="niciun prospect radio eligibil.",
        )

    stats = media_outreach_process_batch(
        staff_user,
        picked,
        max_count=len(picked),
        dispatch_kind=MediaOutreachInviteLog.DISPATCH_WAVE,
    )
    logger.info(
        "media_outreach_radio_wave limit=%s picked=%s stats=%s smtp=%s",
        limit,
        len(picked),
        stats,
        media_outreach_email_enabled(),
    )
    return MediaRadioWaveResult(
        wave_limit=limit,
        picked_count=len(picked),
        stats=stats,
        skipped=False,
    )
