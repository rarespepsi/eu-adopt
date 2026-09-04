"""
Mail săptămânal (duminică): mulțumire pentru membrii noi + îndemn recomandare colaboratori.

O singură trimitere per user (UserProfile.weekly_thanks_sent_at).
"""
from __future__ import annotations

import logging
from datetime import datetime, timedelta
from html import escape
from zoneinfo import ZoneInfo

from django.conf import settings
from django.contrib.auth.models import User
from django.db.models import Q
from django.urls import reverse
from django.utils import timezone

from home.euadopt_public_contact import (
    EUADOPT_PUBLIC_PHONE_DISPLAY,
    EUADOPT_PUBLIC_PHONE_E164,
)
from home.mail_helpers import email_subject_for_user, send_mail_text_and_html
from home.models import UserLegalConsent, UserProfile

logger = logging.getLogger(__name__)

RO_TZ = ZoneInfo("Europe/Bucharest")
MAIL_KIND = "weekly-new-member-thanks"


def weekly_thanks_email_enabled() -> bool:
    raw = getattr(settings, "WEEKLY_NEW_MEMBER_THANKS_EMAIL_ENABLED", None)
    if raw is None:
        return True  # implicit ON în producție după deploy; cron are flag separat
    return bool(raw)


def _site_base() -> str:
    return (getattr(settings, "SITE_BASE_URL", "") or "https://eu-adopt.ro").rstrip("/")


def _absolute(path: str) -> str:
    if path.startswith("http"):
        return path
    return f"{_site_base()}{path}"


def week_window_for_sunday_run(now=None) -> tuple[datetime, datetime]:
    """
    La rularea de duminică: de la luni (acum 7–13 zile, catch-up) până acum.
    Catch-up: include și pe cei intrați duminica trecută după cron.
    """
    now = now or timezone.now()
    local = timezone.localtime(now, RO_TZ)
    # Luni săptămâna curentă 00:00 RO
    monday = (local.date() - timedelta(days=local.weekday()))
    monday_dt = datetime(monday.year, monday.month, monday.day, 0, 0, 0, tzinfo=RO_TZ)
    catchup_start = monday_dt - timedelta(days=7)
    return catchup_start, now


def _marketing_opted_out_ids(user_ids: list[int]) -> set[int]:
    """Ultimul consimțământ marketing = refuz → skip."""
    if not user_ids:
        return set()
    opted = set()
    # Ultimul rând per user pentru marketing
    latest = (
        UserLegalConsent.objects.filter(
            user_id__in=user_ids,
            consent_type=UserLegalConsent.CONSENT_MARKETING,
        )
        .order_by("user_id", "-created_at", "-id")
    )
    seen = set()
    for row in latest.iterator(chunk_size=500):
        if row.user_id in seen:
            continue
        seen.add(row.user_id)
        if not row.accepted:
            opted.add(row.user_id)
    return opted


def candidates_queryset(now=None):
    start, end = week_window_for_sunday_run(now)
    # Profil fără flag; dacă lipsește profilul, îl creăm la send
    qs = (
        User.objects.filter(
            is_active=True,
            is_staff=False,
            is_superuser=False,
            date_joined__gte=start,
            date_joined__lte=end,
        )
        .exclude(Q(email__isnull=True) | Q(email__exact=""))
        .filter(
            Q(profile__isnull=True)
            | Q(profile__weekly_thanks_sent_at__isnull=True)
        )
        .distinct()
        .order_by("date_joined", "id")
    )
    return qs, start, end


def _greeting_name(user: User) -> str:
    full = (user.get_full_name() or "").strip()
    if full:
        return full.split()[0]
    un = (user.username or "").strip()
    return un or "prietene"


def build_thanks_bodies(user: User) -> tuple[str, str, str]:
    who = _greeting_name(user)
    collab_url = _absolute(reverse("signup_colaborator"))
    org_url = _absolute(reverse("signup_organizatie"))
    serv_url = _absolute(reverse("servicii"))
    site = _site_base()
    phone = f"{EUADOPT_PUBLIC_PHONE_DISPLAY} ({EUADOPT_PUBLIC_PHONE_E164})"

    subject = email_subject_for_user(
        user.username,
        "Mulțumim că ești pe EU-Adopt — împreună creștem rețeaua",
    )

    body = (
        f"Bună ziua, {who},\n\n"
        f"Îți mulțumim că te-ai alăturat comunității EU-Adopt. "
        f"Apreciem încrederea și faptul că ești aici pentru animale.\n\n"
        f"Cum poți ajuta și mai mult\n"
        f"Te rugăm să ne recomanzi către cabinete veterinare, saloane de grooming, "
        f"transportatori de animale de companie, farmacii veterinare sau magazine de specialitate "
        f"din zona ta.\n\n"
        f"De ce contează\n"
        f"La fiecare adopție realizată în județul lor, adoptatorul este îndrumat către "
        f"ofertele colaboratorilor activi din zonă (pe platformă și în comunicările după adopție). "
        f"E suficientă o singură ofertă publicată pe site ca să fie vizibili.\n\n"
        f"Linkuri utile:\n"
        f"- Înregistrare colaborator: {collab_url}\n"
        f"- Înregistrare adăpost / ONG: {org_url}\n"
        f"- Servicii (oferte): {serv_url}\n"
        f"- Site: {site}/\n\n"
        f"Îți mulțumim încă o dată — împreună dăm mai multe șanse animalelor să găsească o casă.\n\n"
        f"Cu respect,\n"
        f"Echipa EU-Adopt\n"
        f"{site}/\n"
        f"Telefon / WhatsApp: {phone}\n"
        f"contact@eu-adopt.ro\n"
    )

    html = (
        f"<p>Bună ziua, {escape(who)},</p>"
        f"<p>Îți mulțumim că te-ai alăturat comunității <strong>EU-Adopt</strong>. "
        f"Apreciem încrederea și faptul că ești aici pentru animale.</p>"
        f"<p><strong>Cum poți ajuta și mai mult</strong><br>"
        f"Te rugăm să ne recomanzi către <strong>cabinete veterinare</strong>, "
        f"<strong>saloane de grooming</strong>, <strong>transportatori</strong> de animale de companie, "
        f"<strong>farmacii veterinare</strong> sau <strong>magazine de specialitate</strong> din zona ta.</p>"
        f"<p><strong>De ce contează</strong><br>"
        f"La fiecare adopție realizată în județul lor, adoptatorul este îndrumat către "
        f"ofertele colaboratorilor activi din zonă (pe platformă și în comunicările după adopție). "
        f"E suficientă <strong>o singură ofertă</strong> publicată pe site ca să fie vizibili.</p>"
        f"<p>Linkuri utile:</p><ul>"
        f"<li><a href=\"{escape(collab_url)}\">Înregistrare colaborator</a></li>"
        f"<li><a href=\"{escape(org_url)}\">Înregistrare adăpost / ONG</a></li>"
        f"<li><a href=\"{escape(serv_url)}\">Servicii (oferte)</a></li>"
        f"<li><a href=\"{escape(site)}/\">eu-adopt.ro</a></li>"
        f"</ul>"
        f"<p>Îți mulțumim încă o dată — împreună dăm mai multe șanse animalelor să găsească o casă.</p>"
        f"<p>Cu respect,<br><strong>Echipa EU-Adopt</strong><br>"
        f"<a href=\"{escape(site)}/\">{escape(site)}/</a><br>"
        f"Telefon / WhatsApp: {escape(phone)}<br>"
        f"<a href=\"mailto:contact@eu-adopt.ro\">contact@eu-adopt.ro</a></p>"
    )
    return subject, body, html


def ensure_profile(user: User) -> UserProfile:
    try:
        return user.profile
    except UserProfile.DoesNotExist:
        return UserProfile.objects.create(user=user)


def send_weekly_thanks_to_user(user: User, *, dry_run: bool = False) -> str:
    """
    Returnează: sent | skipped_no_email | skipped_already | skipped_opt_out | dry_run | error
    """
    em = (user.email or "").strip()
    if not em:
        return "skipped_no_email"
    profile = ensure_profile(user)
    if profile.weekly_thanks_sent_at:
        return "skipped_already"
    if user.id in _marketing_opted_out_ids([user.id]):
        return "skipped_opt_out"

    subject, body, html = build_thanks_bodies(user)
    if dry_run:
        return "dry_run"

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "") or "contact@eu-adopt.ro"
    try:
        send_mail_text_and_html(
            subject,
            body,
            from_email,
            [em],
            html_body=html,
            mail_kind=MAIL_KIND,
        )
    except Exception:
        logger.exception("weekly_thanks send failed user_id=%s email=%s", user.pk, em)
        return "error"

    profile.weekly_thanks_sent_at = timezone.now()
    profile.save(update_fields=["weekly_thanks_sent_at", "updated_at"])
    return "sent"


def process_weekly_thanks(*, dry_run: bool = False, force: bool = False, now=None) -> dict:
    """
    force=True: rulează indiferent de ziua săptămânii (test manual).
    Altfel: doar duminică (Europe/Bucharest).
    """
    now = now or timezone.now()
    local = timezone.localtime(now, RO_TZ)
    if not force and local.weekday() != 6:  # Sunday
        return {
            "ok": False,
            "reason": f"not_sunday (local weekday={local.weekday()} date={local.date()})",
            "sent": 0,
        }
    if not weekly_thanks_email_enabled() and not dry_run:
        return {"ok": False, "reason": "disabled", "sent": 0}

    qs, start, end = candidates_queryset(now)
    users = list(qs.select_related("profile")[:2000])
    opted = _marketing_opted_out_ids([u.id for u in users])
    stats = {
        "ok": True,
        "start": start.isoformat(),
        "end": end.isoformat(),
        "candidates": len(users),
        "sent": 0,
        "dry_run": 0,
        "skipped_already": 0,
        "skipped_opt_out": 0,
        "skipped_no_email": 0,
        "error": 0,
    }
    for u in users:
        if u.id in opted:
            stats["skipped_opt_out"] += 1
            continue
        result = send_weekly_thanks_to_user(u, dry_run=dry_run)
        key = result if result in stats else "error"
        if key == "sent":
            stats["sent"] += 1
        elif key == "dry_run":
            stats["dry_run"] += 1
        elif key in stats:
            stats[key] += 1
        else:
            stats["error"] += 1
    return stats
