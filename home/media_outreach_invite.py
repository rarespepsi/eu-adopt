"""
Email outreach Audio/TV — același model operațional ca Add USER (cooldown, max sends, jurnal).
"""
from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from home.euadopt_public_contact import EUADOPT_PUBLIC_PHONE_DISPLAY
from home.models import MediaOutreachInviteLog, MediaOutreachProspect
from home.staff_invite_email_expand import is_plausible_invite_email
from home.staff_onboarding_csv import is_placeholder_lead_email

logger = logging.getLogger(__name__)

_TERMINAL = frozenset(
    {
        MediaOutreachProspect.ST_REPLIED,
        MediaOutreachProspect.ST_PARTNER,
        MediaOutreachProspect.ST_DNC,
    }
)


def media_outreach_email_enabled() -> bool:
    raw = getattr(settings, "MEDIA_OUTREACH_EMAIL_ENABLED", None)
    if raw is None:
        return bool(getattr(settings, "STAFF_INVITE_EMAIL_ENABLED", False))
    return bool(raw)


def media_outreach_cooldown_days(p: MediaOutreachProspect) -> int:
    if p.cooldown_days is not None and p.cooldown_days >= 0:
        return int(p.cooldown_days)
    return int(getattr(settings, "MEDIA_OUTREACH_COOLDOWN_DAYS", 7) or 7)


def media_outreach_max_sends(p: MediaOutreachProspect) -> int:
    return max(1, int(p.max_sends or getattr(settings, "MEDIA_OUTREACH_MAX_SENDS", 3) or 3))


def media_outreach_max_per_day() -> int:
    return int(getattr(settings, "MEDIA_OUTREACH_MAX_PER_DAY", 20) or 20)


def media_outreach_sent_count(p: MediaOutreachProspect) -> int:
    return MediaOutreachInviteLog.objects.filter(
        prospect=p, outcome=MediaOutreachInviteLog.OUTCOME_SENT
    ).count()


def media_outreach_sim_count(p: MediaOutreachProspect) -> int:
    return MediaOutreachInviteLog.objects.filter(
        prospect=p, outcome=MediaOutreachInviteLog.OUTCOME_DRY_RUN
    ).count()


def media_outreach_daily_remaining(now=None) -> int:
    now = now or timezone.now()
    start = now.astimezone(timezone.get_current_timezone()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    used = MediaOutreachInviteLog.objects.filter(
        sent_at__gte=start,
        outcome__in=(
            MediaOutreachInviteLog.OUTCOME_SENT,
            MediaOutreachInviteLog.OUTCOME_DRY_RUN,
        ),
    ).count()
    return max(0, media_outreach_max_per_day() - used)


def media_outreach_can_send(p: MediaOutreachProspect, now=None) -> tuple[bool, str]:
    now = now or timezone.now()
    em = (p.email or "").strip()
    if not em or is_placeholder_lead_email(em):
        return False, "fără email valid"
    if not is_plausible_invite_email(em):
        return False, "email invalid"
    if p.outreach_status in _TERMINAL:
        return False, p.get_outreach_status_display()
    sent_n = media_outreach_sent_count(p)
    max_n = media_outreach_max_sends(p)
    if sent_n >= max_n:
        return False, f"max {max_n} trimiteri"
    if sent_n > 0 and p.last_email_sent_at:
        cd = timedelta(days=media_outreach_cooldown_days(p))
        if (now - p.last_email_sent_at) < cd:
            return False, f"cooldown {media_outreach_cooldown_days(p)} zile"
    return True, ""


def media_outreach_on_cooldown(p: MediaOutreachProspect, now=None) -> bool:
    ok, reason = media_outreach_can_send(p, now)
    return (not ok) and reason.startswith("cooldown")


def media_outreach_subject_body(p: MediaOutreachProspect) -> tuple[str, str]:
    who = (p.contact_name or "").strip()
    greet = f"Stimată doamnă / Stimate domnule {who}," if who else "Stimată redacție,"
    outlet = (p.outlet_name or "").strip() or "redacția dumneavoastră"
    kind = p.get_media_kind_display()
    subject = f"EU-Adopt — propunere parteneriat editorial ({outlet})"
    body = (
        f"{greet}\n\n"
        f"Vă scriu din partea EU-Adopt (https://www.eu-adopt.ro/) — platformă națională "
        f"și europeană dedicată adopțiilor responsabile, gratuită pentru adăposturi "
        f"și parteneri din ecosistem.\n\n"
        f"Propunem un parteneriat editorial cu {outlet} ({kind}): "
        f"difuzare articol și/sau material audio-video despre adopții și rețeaua EU-Adopt, "
        f"fără cost pentru redacție.\n\n"
        f"Putem furniza un brief scurt, date, imagini și un interlocutor pentru interviu, "
        f"adaptat formatului dumneavoastră.\n\n"
        f"Dacă sunteți deschiși, răspundeți la acest email și revenim cu detaliile.\n\n"
        f"Cu respect,\n"
        f"Echipa EU-Adopt\n"
        f"https://www.eu-adopt.ro/\n"
        f"contact@eu-adopt.ro\n"
        f"Telefon / WhatsApp: {EUADOPT_PUBLIC_PHONE_DISPLAY}\n"
    )
    return subject, body


def media_outreach_annotate_row(p: MediaOutreachProspect, now=None) -> MediaOutreachProspect:
    """Atașează atribute pentru template (ca Add USER)."""
    now = now or timezone.now()
    can, reason = media_outreach_can_send(p, now)
    p.invite_can_send = can
    p.invite_block_reason = reason
    p.invite_on_cooldown = media_outreach_on_cooldown(p, now)
    p.invite_sent_count = media_outreach_sent_count(p)
    p.invite_sim_count = media_outreach_sim_count(p)
    p.invite_max_sends_display = media_outreach_max_sends(p)
    p.invite_cooldown_days_display = media_outreach_cooldown_days(p)
    p.invite_checkbox = can and bool((p.email or "").strip())
    return p


def media_outreach_process_one(
    staff_user,
    p: MediaOutreachProspect,
    *,
    dispatch_kind: str = MediaOutreachInviteLog.DISPATCH_MANUAL,
    now=None,
) -> str:
    now = now or timezone.now()
    ok, reason = media_outreach_can_send(p, now)
    if not ok:
        return "blocked"
    if media_outreach_daily_remaining(now) <= 0:
        return "daily_cap"

    em = (p.email or "").strip()
    subj, body = media_outreach_subject_body(p)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@eu-adopt.ro"
    mail_on = media_outreach_email_enabled()

    if mail_on:
        try:
            msg = EmailMultiAlternatives(
                subject=subj,
                body=body,
                from_email=from_email,
                to=[em],
                reply_to=[getattr(settings, "DEFAULT_FROM_EMAIL", from_email)],
            )
            msg.send(fail_silently=False)
        except Exception as exc:
            logger.exception("media_outreach_send prospect_id=%s", p.pk)
            MediaOutreachInviteLog.objects.create(
                prospect=p,
                sent_by=staff_user,
                to_email=em,
                subject=subj[:255],
                outcome=MediaOutreachInviteLog.OUTCOME_ERROR,
                error_message=str(exc)[:2000],
                dispatch_kind=dispatch_kind,
            )
            return "error"
        MediaOutreachInviteLog.objects.create(
            prospect=p,
            sent_by=staff_user,
            to_email=em,
            subject=subj[:255],
            outcome=MediaOutreachInviteLog.OUTCOME_SENT,
            dispatch_kind=dispatch_kind,
        )
        p.last_email_sent_at = now
        if p.outreach_status in (
            MediaOutreachProspect.ST_NEW,
            MediaOutreachProspect.ST_WA_READY,
            MediaOutreachProspect.ST_CONTACTED,
            "",
        ):
            p.outreach_status = MediaOutreachProspect.ST_EMAILED
        p.save(update_fields=["last_email_sent_at", "outreach_status", "updated_at"])
        return "sent"

    MediaOutreachInviteLog.objects.create(
        prospect=p,
        sent_by=staff_user,
        to_email=em,
        subject=subj[:255],
        outcome=MediaOutreachInviteLog.OUTCOME_DRY_RUN,
        dispatch_kind=dispatch_kind,
    )
    return "simulated"


def media_outreach_process_batch(staff_user, prospects, *, max_count: int | None = None) -> dict[str, int]:
    import time

    delay = int(getattr(settings, "MEDIA_OUTREACH_SEND_DELAY_SEC", 0) or 0)
    if delay <= 0:
        delay = int(getattr(settings, "STAFF_INVITE_SEND_DELAY_SEC", 0) or 0)
    limit = max_count if max_count is not None else 50
    stats = {"sent": 0, "simulated": 0, "blocked": 0, "error": 0, "daily_cap": 0}
    smtp_n = 0
    for p in prospects:
        if stats["sent"] + stats["simulated"] >= limit:
            break
        if media_outreach_daily_remaining() <= 0:
            stats["daily_cap"] += 1
            break
        if delay > 0 and smtp_n > 0:
            time.sleep(delay)
        result = media_outreach_process_one(staff_user, p)
        if result == "sent":
            stats["sent"] += 1
            smtp_n += 1
        elif result == "simulated":
            stats["simulated"] += 1
        elif result == "blocked":
            stats["blocked"] += 1
        elif result == "error":
            stats["error"] += 1
            smtp_n += 1
        elif result == "daily_cap":
            stats["daily_cap"] += 1
            break
    return stats


def media_outreach_stats_banner() -> dict:
    now = timezone.now()
    start = now.astimezone(timezone.get_current_timezone()).replace(
        hour=0, minute=0, second=0, microsecond=0
    )
    sent_today = MediaOutreachInviteLog.objects.filter(
        sent_at__gte=start, outcome=MediaOutreachInviteLog.OUTCOME_SENT
    ).count()
    sim_today = MediaOutreachInviteLog.objects.filter(
        sent_at__gte=start, outcome=MediaOutreachInviteLog.OUTCOME_DRY_RUN
    ).count()
    return {
        "email_enabled": media_outreach_email_enabled(),
        "cooldown_days": int(getattr(settings, "MEDIA_OUTREACH_COOLDOWN_DAYS", 7) or 7),
        "max_sends_default": int(getattr(settings, "MEDIA_OUTREACH_MAX_SENDS", 3) or 3),
        "daily_cap": media_outreach_max_per_day(),
        "daily_remaining": media_outreach_daily_remaining(now),
        "sent_today": sent_today,
        "sim_today": sim_today,
        "dispatch_today": sent_today + sim_today,
    }
