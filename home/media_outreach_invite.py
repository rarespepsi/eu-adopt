"""
Email outreach Audio/TV — același model operațional ca Add USER (cooldown, max sends, jurnal).

Valul curent de email = doar RADIO (spot audio atașat). TV = clip video separat (mai târziu).
"""
from __future__ import annotations

import logging
import re
from datetime import timedelta
from pathlib import Path

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.utils import timezone

from home.euadopt_public_contact import (
    EUADOPT_PUBLIC_PHONE_DISPLAY,
    EUADOPT_PUBLIC_PHONE_E164,
)
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

# Spot radio MASTER (~33s) — atașat la emailurile către posturi radio.
# Canon: eu-adopt-spot-radio-master.mp3 (copiat și peste *-alina.mp3 pentru compat).
RADIO_SPOT_REL = Path("static") / "audio" / "eu-adopt-spot-radio-master.mp3"
RADIO_SPOT_FILENAME = "EU-Adopt-spot-radio.mp3"

_EMAIL_LOCAL_CLEAN_RE = re.compile(r"[^a-zA-ZăâîșțĂÂÎȘȚ\-_.]+")


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


def media_outreach_radio_spot_path() -> Path | None:
    """Cale absolută către MP3-ul spot radio (static din repo)."""
    base = Path(getattr(settings, "BASE_DIR", Path.cwd()))
    candidates = [
        base / RADIO_SPOT_REL,
        base / "static" / "audio" / "eu-adopt-spot-radio-30s-alina.mp3",
        base / "staticfiles" / "audio" / "eu-adopt-spot-radio-master.mp3",
        base / "staticfiles" / "audio" / "eu-adopt-spot-radio-30s-alina.mp3",
    ]
    for path in candidates:
        if path.is_file():
            return path
    return None


def media_outreach_greeting_name(p: MediaOutreachProspect) -> str:
    """Nume din DB (contact) → outlet → local-part email → gol."""
    who = (p.contact_name or "").strip()
    if who:
        return who
    outlet = (p.outlet_name or "").strip()
    if outlet:
        return outlet
    em = (p.email or "").strip()
    if em and "@" in em:
        local = em.split("@", 1)[0]
        local = _EMAIL_LOCAL_CLEAN_RE.sub(" ", local).replace(".", " ").replace("_", " ").strip()
        parts = [w for w in local.split() if len(w) > 1]
        if parts and not any(ch.isdigit() for ch in "".join(parts)):
            return " ".join(w[:1].upper() + w[1:].lower() for w in parts[:3])
    return ""


def media_outreach_can_send(p: MediaOutreachProspect, now=None) -> tuple[bool, str]:
    now = now or timezone.now()
    # Emailul curent = doar radio (spot audio). TV / press = alte materiale.
    if (p.media_kind or "").strip().lower() != MediaOutreachProspect.KIND_RADIO:
        return False, "doar radio (spot audio)"
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
    who = media_outreach_greeting_name(p)
    outlet = (p.outlet_name or "").strip() or "postul dumneavoastră"
    greet = f"Bună ziua, {who}," if who else "Bună ziua,"
    subject = f"Colaborare EU-Adopt × {outlet} — difuzare spot ↔ promovare pe platformă"
    phone_line = f"{EUADOPT_PUBLIC_PHONE_DISPLAY} ({EUADOPT_PUBLIC_PHONE_E164})"
    body = (
        f"{greet}\n\n"
        f"Sunt Adrian, de la EU-Adopt — o platformă națională (și cu deschidere europeană) "
        f"dedicată animalelor de companie, construită pe o misiune de tip ONG: să legăm "
        f"adăposturi, organizații, oameni și parteneri din teren, fără costuri de bază "
        f"pentru cei care salvează și îngrijesc animale.\n\n"
        f"Ce facem, pe scurt\n"
        f"Pe eu-adopt.ro aducem într-un singur loc:\n"
        f"- adopție și anunțuri de animale;\n"
        f"- adăposturi și ONG-uri;\n"
        f"- cabinete / clinici veterinare, farmacii, grooming, transport și alte servicii din România;\n"
        f"- utilități pentru public (inclusiv semnale despre animale pierdute / găsite).\n\n"
        f"Ajutăm gratuit adăposturile, ONG-urile și mediul de afaceri din domeniu să fie vizibile — "
        f"pentru că impactul real se vede când oamenii știu unde să caute și pe cine să contacteze.\n\n"
        f"De ce vă scriem\n"
        f"Dorim să promovăm platforma către publicul {outlet} — oameni care iubesc animalele "
        f"și pot adopta, ajuta sau colabora. Avem un spot radio scurt (~33 secunde) pregătit "
        f"(atașat acestui email).\n\n"
        f"Despre spot\n"
        f"Spotul transmite misiunea EU-Adopt și invitația pe eu-adopt.ro. "
        f"Dacă doriți, putem ajusta textul sau lungimea după cerințele postului.\n\n"
        f"Propunere de colaborare (barter)\n"
        f"În schimbul a câteva difuzări ale spotului EU-Adopt (program și frecvență de discutat "
        f"împreună), oferim:\n"
        f"- reclamă gratuită a postului pe site (vizibilitate pe platformă);\n"
        f"- afișarea postului ca partener EU-Adopt (mențiune / spațiu dedicat partenerilor media).\n\n"
        f"Nu cerem buget de media — vrem un parteneriat corect, cu beneficiu reciproc: "
        f"voi ajutați un proiect cu misiune socială să ajungă la oameni; noi vă dăm vizibilitate "
        f"în comunitatea animalelor din România.\n\n"
        f"Dacă sunteți de acord cu colaborarea, vă rugăm să ne trimiteți pe email "
        f"(răspuns la acest mesaj):\n\n"
        f"1) Programul sau o pre-programare de difuzare a spotului "
        f"(zile, ore aproximative, număr de difuzări) — ca să putem urmări campania.\n\n"
        f"2) Separat: sigla / imaginea postului (PNG sau JPG, clară) și linkul oficial "
        f"al postului — le vom afișa în benzile cursive cu colaboratorii / partenerii "
        f"media de pe eu-adopt.ro.\n\n"
        f"Pe baza acestora putem confirma colaborarea pe email. Pentru o perioadă mai lungă "
        f"sau difuzări regulate, putem formaliza într-un acord scurt de parteneriat media (barter).\n\n"
        f"Linkuri utile:\n"
        f"- Site: https://eu-adopt.ro/\n"
        f"- Animale pierdute / găsite: https://eu-adopt.ro/animale-pierdute/\n"
        f"- Semnalează abuz: https://eu-adopt.ro/semnaleaza-abuz/\n"
        f"- Prietenul tău (adopții): https://eu-adopt.ro/pets/\n\n"
        f"Dacă ideea vi se potrivește, rămân disponibil pentru un telefon scurt sau un email de răspuns. "
        f"Spotul este atașat (MP3, ~33 secunde).\n\n"
        f"Cu respect și mulțumiri,\n"
        f"Adrian\n"
        f"EU-Adopt · https://eu-adopt.ro/\n"
        f"Telefon / WhatsApp: {phone_line}\n"
        f"contact@eu-adopt.ro\n"
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
    spot = media_outreach_radio_spot_path()

    if mail_on:
        try:
            msg = EmailMultiAlternatives(
                subject=subj,
                body=body,
                from_email=from_email,
                to=[em],
                reply_to=[getattr(settings, "DEFAULT_FROM_EMAIL", from_email)],
            )
            if spot is not None:
                msg.attach_file(str(spot), mimetype="audio/mpeg")
            else:
                logger.warning("media_outreach: spot radio lipsă (fără atașament) prospect_id=%s", p.pk)
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
        error_message="" if spot else "simulare fără atașament (spot lipsă pe disk)",
    )
    return "simulated"


def media_outreach_process_batch(
    staff_user,
    prospects,
    *,
    max_count: int | None = None,
    dispatch_kind: str = MediaOutreachInviteLog.DISPATCH_MANUAL,
) -> dict[str, int]:
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
        result = media_outreach_process_one(staff_user, p, dispatch_kind=dispatch_kind)
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
