"""
Control invitații email Add USER — Faza A (log, stări) + Faza B (șabloane, valuri, plafon zilnic).

Trimiterea SMTP este dezactivată implicit (mod tehnic); activare: EUADOPT_STAFF_INVITE_EMAIL_ENABLED=1.
"""
from __future__ import annotations

import logging
from datetime import timedelta
from typing import Any
from urllib.parse import quote

from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.urls import reverse
from django.utils import timezone

from home.mail_helpers import _message_id_domain
from home.models import StaffOnboardingLead, StaffOnboardingInviteLog
from home.staff_onboarding_csv import is_placeholder_lead_email
from home.staff_onboarding_invite_inbound import staff_invite_reply_to_address

STAFF_INVITE_GET_PARAM = "inv"
STAFF_LEAD_INVITE_MAX_SENDS_DEFAULT = 3

_INVITE_TERMINAL_STATUSES = frozenset(
    {
        StaffOnboardingLead.INVITE_REPLIED,
        StaffOnboardingLead.INVITE_SIGNED_UP,
        StaffOnboardingLead.INVITE_BOUNCED,
        StaffOnboardingLead.INVITE_OPT_OUT,
        StaffOnboardingLead.INVITE_DO_NOT_CONTACT,
    }
)

_DISPATCH_OUTCOMES = (
    StaffOnboardingInviteLog.OUTCOME_SENT,
    StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
)


def staff_invite_email_enabled() -> bool:
    return bool(getattr(settings, "STAFF_INVITE_EMAIL_ENABLED", False))


def staff_invite_cooldown_days(lead: StaffOnboardingLead) -> int:
    if lead.invite_cooldown_days is not None and lead.invite_cooldown_days >= 0:
        return int(lead.invite_cooldown_days)
    return int(getattr(settings, "STAFF_LEAD_INVITE_COOLDOWN_DAYS", 14))


def staff_invite_max_sends(lead: StaffOnboardingLead) -> int:
    n = lead.invite_max_sends
    if n is None or n < 1:
        return STAFF_LEAD_INVITE_MAX_SENDS_DEFAULT
    return int(n)


def staff_invite_max_per_day() -> int:
    return int(getattr(settings, "STAFF_LEAD_INVITE_MAX_PER_DAY", 30))


def staff_invite_wave_default_size() -> int:
    return int(getattr(settings, "STAFF_LEAD_INVITE_WAVE_DEFAULT", 20))


def _day_start(now=None):
    now = now or timezone.now()
    if timezone.is_aware(now):
        return now.replace(hour=0, minute=0, second=0, microsecond=0)
    return now.replace(hour=0, minute=0, second=0, microsecond=0)


def staff_invite_today_dispatch_count(now=None) -> int:
    """Trimiteri reale + simulări azi (contra plafonului zilnic)."""
    start = _day_start(now)
    return StaffOnboardingInviteLog.objects.filter(
        sent_at__gte=start,
        outcome__in=_DISPATCH_OUTCOMES,
    ).count()


def staff_invite_daily_remaining(now=None) -> int:
    return max(0, staff_invite_max_per_day() - staff_invite_today_dispatch_count(now))


def staff_invite_sent_count(lead: StaffOnboardingLead) -> int:
    return StaffOnboardingInviteLog.objects.filter(
        lead_id=lead.pk,
        outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
    ).count()


def staff_invite_simulated_count(lead: StaffOnboardingLead) -> int:
    return StaffOnboardingInviteLog.objects.filter(
        lead_id=lead.pk,
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
    ).count()


def staff_invite_display_status(lead: StaffOnboardingLead) -> str:
    if lead.imported_user_id:
        return StaffOnboardingLead.INVITE_SIGNED_UP
    return (lead.invite_mail_status or StaffOnboardingLead.INVITE_NEVER).strip() or StaffOnboardingLead.INVITE_NEVER


def staff_invite_can_send(lead: StaffOnboardingLead, now=None) -> tuple[bool, str]:
    now = now or timezone.now()
    em = (lead.email or "").strip()
    if not em or is_placeholder_lead_email(em):
        return False, "fără email valid"
    if lead.imported_user_id:
        return False, "cont creat"
    st = staff_invite_display_status(lead)
    if st in _INVITE_TERMINAL_STATUSES:
        labels = dict(StaffOnboardingLead.INVITE_MAIL_STATUS_CHOICES)
        return False, labels.get(st, st)
    sent_n = staff_invite_sent_count(lead)
    max_n = staff_invite_max_sends(lead)
    if sent_n >= max_n:
        return False, f"max {max_n} trimiteri"
    if lead.invite_email_last_sent_at:
        cd = timezone.timedelta(days=staff_invite_cooldown_days(lead))
        if (now - lead.invite_email_last_sent_at) < cd:
            return False, f"cooldown {staff_invite_cooldown_days(lead)} zile"
    return True, ""


def staff_invite_filter_eligible_qs(qs, now=None):
    now = now or timezone.now()
    pks: list[int] = []
    for lead in qs.iterator():
        if staff_invite_can_send(lead, now)[0]:
            pks.append(lead.pk)
    if not pks:
        return qs.none()
    return qs.filter(pk__in=pks)


def staff_invite_count_eligible(qs, now=None) -> int:
    n = 0
    for lead in qs.iterator():
        if staff_invite_can_send(lead, now)[0]:
            n += 1
    return n


def staff_invite_template_key(lead: StaffOnboardingLead) -> str:
    if lead.account_kind == StaffOnboardingLead.KIND_ADAPOST:
        return "adapost"
    if lead.account_kind == StaffOnboardingLead.KIND_ORG:
        return "ong"
    if lead.account_kind == StaffOnboardingLead.KIND_COLLAB:
        sub = (lead.collaborator_subtype or "").strip()
        if sub in (StaffOnboardingLead.COLLAB_CABINET, StaffOnboardingLead.COLLAB_CV):
            return "cabinet"
        if sub == StaffOnboardingLead.COLLAB_SERVICII:
            return "servicii"
        if sub == StaffOnboardingLead.COLLAB_GROOMING:
            return "grooming"
        if sub == StaffOnboardingLead.COLLAB_TRANSPORT:
            return "transport"
        if sub == StaffOnboardingLead.COLLAB_MAGAZIN:
            return "magazin"
    if lead.account_kind == StaffOnboardingLead.KIND_PF:
        return "pf"
    return "default"


def _invite_signup_url(request, lead: StaffOnboardingLead) -> str:
    if lead.account_kind == StaffOnboardingLead.KIND_PF:
        signup_path = reverse("signup_pf")
    elif lead.account_kind in (StaffOnboardingLead.KIND_ORG, StaffOnboardingLead.KIND_ADAPOST):
        signup_path = reverse("signup_organizatie")
    else:
        signup_path = reverse("signup_colaborator")
    if not (lead.consent_invite_token or "").strip():
        lead.save(update_fields=["consent_invite_token", "updated_at"])
    inv_tok = (lead.consent_invite_token or "").strip()
    signup_url = request.build_absolute_uri(signup_path)
    if inv_tok:
        signup_url = f"{signup_url}?{STAFF_INVITE_GET_PARAM}={quote(inv_tok, safe='')}"
    return signup_url


def staff_invite_subject_body(request, lead: StaffOnboardingLead) -> tuple[str, str, str]:
    """Subiect, corp, cheie șablon."""
    template_key = staff_invite_template_key(lead)
    kind_label = lead.get_account_kind_display()
    org_line = ""
    if (lead.org_display_name or "").strip():
        org_line = f" pentru {lead.org_display_name.strip()}"
    signup_url = _invite_signup_url(request, lead)
    terms_url = request.build_absolute_uri(reverse("termeni"))
    privacy_url = request.build_absolute_uri(reverse("politica_confidentialitate"))
    loc_bits = [x for x in (lead.judet, lead.oras) if (x or "").strip()]
    loc_line = f" ({', '.join(loc_bits)})" if loc_bits else ""

    if template_key == "adapost":
        subject = "EU-ADOPT — invitație adăpost: publicare animale pentru adopție"
        intro = (
            f"Bună ziua{org_line},\n\n"
            f"Vă contactăm din EU-ADOPT{loc_line} în legătură cu listarea animalelor "
            f"disponibile pentru adopție pe platforma noastră.\n"
            f"După crearea contului veți putea adăuga fișe în zona MyPet (poze, județ, date medicale).\n"
        )
    elif template_key == "ong":
        subject = "EU-ADOPT — invitație ONG / asociație: adopții și vizibilitate"
        intro = (
            f"Bună ziua{org_line},\n\n"
            f"Vă invităm să vă înregistrați organizația pe EU-ADOPT{loc_line} "
            f"pentru a publica animale și a primi cereri de adopție structurate.\n"
        )
    elif template_key == "cabinet":
        subject = "EU-ADOPT — invitație cabinet veterinar (colaborator)"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă invităm să vă înregistrați cabinetul veterinar{loc_line} ca partener EU-ADOPT "
            f"(oferte, vizibilitate în zona Servicii, legătură cu adoptatorii din județ).\n"
        )
    elif template_key == "servicii":
        subject = "EU-ADOPT — invitație partener servicii (cazare, pensiune etc.)"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă invităm să vă înregistrați serviciul{loc_line} pe EU-ADOPT ca partener colaborator "
            f"(publicare oferte în catalogul Servicii).\n"
        )
    elif template_key == "grooming":
        subject = "EU-ADOPT — invitație salon grooming / îngrijire"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă invităm să vă înregistrați activitatea de grooming{loc_line} pe EU-ADOPT "
            f"(oferte vizibile adoptatorilor).\n"
        )
    elif template_key == "transport":
        subject = "EU-ADOPT — invitație transportator animale"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă invităm să vă înregistrați ca transportator autorizat{loc_line} pe EU-ADOPT "
            f"(cereri de transport din fluxul dedicat platformei).\n"
        )
    elif template_key == "magazin":
        subject = "EU-ADOPT — invitație magazin / produse animale"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă invităm să vă înregistrați magazinul{loc_line} ca partener EU-ADOPT "
            f"(oferte produse în zona Servicii).\n"
        )
    else:
        subject = f"EU-ADOPT — invitație completare cont ({kind_label})"
        intro = (
            f"Bună ziua,\n\n"
            f"Vă scriem din EU-ADOPT în legătură cu înregistrarea ca utilizator ({kind_label}){loc_line}.\n"
        )

    body = (
        f"{intro}\n"
        f"Formular creare cont (link personal — asociază automat invitația):\n{signup_url}\n\n"
        f"Documente legale:\n"
        f"- Termeni și condiții: {terms_url}\n"
        f"- Politica de confidențialitate (GDPR): {privacy_url}\n\n"
        f"Dacă nu doriți să fiți contactat, răspundeți la acest email cu „nu contacta”.\n\n"
        f"Cu stimă,\nEchipa EU-ADOPT\n"
    )
    return subject, body, template_key


def staff_invite_campaign_stats(now=None) -> dict[str, Any]:
    now = now or timezone.now()
    start_day = _day_start(now)
    start_week = start_day - timedelta(days=7)
    logs = StaffOnboardingInviteLog.objects.all()
    sent_today = logs.filter(sent_at__gte=start_day, outcome=StaffOnboardingInviteLog.OUTCOME_SENT).count()
    sim_today = logs.filter(sent_at__gte=start_day, outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN).count()
    sent_week = logs.filter(
        sent_at__gte=start_week,
        outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
    ).count()
    sim_week = logs.filter(
        sent_at__gte=start_week,
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
    ).count()
    signed_up = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
    ).count()
    invited_ever = (
        StaffOnboardingLead.objects.filter(
            invite_logs__outcome__in=_DISPATCH_OUTCOMES,
        )
        .distinct()
        .count()
    )
    return {
        "sent_today": sent_today,
        "sim_today": sim_today,
        "dispatch_today": sent_today + sim_today,
        "sent_week": sent_week,
        "sim_week": sim_week,
        "daily_cap": staff_invite_max_per_day(),
        "daily_remaining": staff_invite_daily_remaining(now),
        "signed_up": signed_up,
        "invited_ever": invited_ever,
    }


def staff_invite_on_real_send(lead: StaffOnboardingLead, now=None) -> None:
    now = now or timezone.now()
    lead.invite_email_last_sent_at = now
    if lead.invite_mail_status in (StaffOnboardingLead.INVITE_NEVER, "", None):
        lead.invite_mail_status = StaffOnboardingLead.INVITE_SENT
    if lead.status == StaffOnboardingLead.ST_READY:
        lead.status = StaffOnboardingLead.ST_INVITED
    lead.save(
        update_fields=[
            "invite_email_last_sent_at",
            "invite_mail_status",
            "status",
            "updated_at",
        ]
    )


def _staff_invite_send_smtp(from_email: str, to_email: str, subject: str, body: str, lead: StaffOnboardingLead) -> str:
    """Trimite invitația cu Reply-To + Message-ID; returnează Message-ID."""
    msg_id = make_msgid(domain=_message_id_domain())
    headers = {
        "Message-ID": msg_id,
        "X-EUAdopt-Lead-Id": str(lead.pk),
        "X-EUAdopt-Mail": "staff-onboarding-invite",
    }
    reply_to = staff_invite_reply_to_address(lead.pk)
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body,
        from_email=from_email,
        to=[to_email],
        reply_to=[reply_to],
        headers=headers,
    )
    msg.send(fail_silently=False)
    return msg_id


def staff_invite_mark_signed_up(lead_pk: int, user_id: int) -> None:
    StaffOnboardingLead.objects.filter(pk=lead_pk, imported_user__isnull=True).update(
        imported_user_id=user_id,
        status=StaffOnboardingLead.ST_IMPORTED,
        invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
    )


def staff_invite_process_one(
    request,
    staff_user,
    lead: StaffOnboardingLead,
    *,
    dispatch_kind: str = StaffOnboardingInviteLog.DISPATCH_MANUAL,
    now=None,
) -> str:
    """
    Procesează un lead. Returnează: sent | simulated | blocked | error | daily_cap
    """
    now = now or timezone.now()
    ok, _reason = staff_invite_can_send(lead, now)
    if not ok:
        return "blocked"
    if staff_invite_daily_remaining(now) <= 0:
        return "daily_cap"
    em = (lead.email or "").strip()
    subj, body, template_key = staff_invite_subject_body(request, lead)
    mail_enabled = staff_invite_email_enabled()
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@eu-adopt.ro"
    log = logging.getLogger(__name__)
    if mail_enabled:
        try:
            msg_id = _staff_invite_send_smtp(from_email, em, subj, body, lead)
        except Exception as exc:
            log.exception("staff_invite_send lead_id=%s", lead.pk)
            StaffOnboardingInviteLog.objects.create(
                lead=lead,
                sent_by=staff_user,
                to_email=em,
                subject=subj[:255],
                outcome=StaffOnboardingInviteLog.OUTCOME_ERROR,
                error_message=str(exc)[:2000],
                template_key=template_key,
                dispatch_kind=dispatch_kind,
            )
            return "error"
        StaffOnboardingInviteLog.objects.create(
            lead=lead,
            sent_by=staff_user,
            to_email=em,
            subject=subj[:255],
            outcome=StaffOnboardingInviteLog.OUTCOME_SENT,
            template_key=template_key,
            dispatch_kind=dispatch_kind,
            message_id=msg_id[:255],
        )
        staff_invite_on_real_send(lead, now)
        return "sent"
    StaffOnboardingInviteLog.objects.create(
        lead=lead,
        sent_by=staff_user,
        to_email=em,
        subject=subj[:255],
        outcome=StaffOnboardingInviteLog.OUTCOME_DRY_RUN,
        template_key=template_key,
        dispatch_kind=dispatch_kind,
    )
    return "simulated"


def staff_invite_process_batch(
    request,
    staff_user,
    leads,
    *,
    dispatch_kind: str = StaffOnboardingInviteLog.DISPATCH_MANUAL,
    max_count: int | None = None,
) -> dict[str, int]:
    max_batch = int(getattr(settings, "STAFF_LEAD_INVITE_MAX_BATCH", 100))
    limit = max_batch if max_count is None else min(max_count, max_batch)
    stats = {
        "sent": 0,
        "simulated": 0,
        "blocked": 0,
        "error": 0,
        "daily_cap": 0,
        "invalid": 0,
    }
    processed = 0
    for lead in leads:
        if processed >= limit:
            break
        if staff_invite_daily_remaining() <= 0:
            stats["daily_cap"] += 1
            break
        result = staff_invite_process_one(
            request,
            staff_user,
            lead,
            dispatch_kind=dispatch_kind,
            now=timezone.now(),
        )
        if result == "sent":
            stats["sent"] += 1
            processed += 1
        elif result == "simulated":
            stats["simulated"] += 1
            processed += 1
        elif result == "blocked":
            stats["blocked"] += 1
        elif result == "error":
            stats["error"] += 1
        elif result == "daily_cap":
            stats["daily_cap"] += 1
            break
    return stats


def staff_invite_build_result_message(stats: dict[str, int], *, wave: bool = False) -> str:
    mail_enabled = staff_invite_email_enabled()
    prefix = "Val invitații: " if wave else ""
    parts = []
    if mail_enabled:
        if stats.get("sent"):
            parts.append(f"{prefix}trimise {stats['sent']} email.")
    else:
        if stats.get("simulated"):
            parts.append(
                f"{prefix}simulare {stats['simulated']} în jurnal (SMTP dezactivat — mod tehnic)."
            )
    if stats.get("sent") and mail_enabled and not parts:
        parts.append(f"{prefix}0 trimise.")
    if stats.get("blocked"):
        parts.append(f"blocate: {stats['blocked']}")
    if stats.get("error"):
        parts.append(f"erori: {stats['error']}")
    if stats.get("daily_cap"):
        parts.append(f"plafon zilnic ({staff_invite_max_per_day()}/zi) atins")
    if not parts:
        return f"{prefix}nicio invitație procesată."
    return " ".join(parts)
