"""Raport săptămânal bounce / inbound invitații Add USER."""

from __future__ import annotations

import logging
from datetime import timedelta

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from home.mail_helpers import send_mail_text_and_html
from home.models import StaffOnboardingInviteInbound, StaffOnboardingLead
from home.staff_invite_daily_report import staff_invite_report_recipients

logger = logging.getLogger(__name__)


def build_bounce_weekly_report_text(*, days: int = 7) -> str:
    days = max(1, min(int(days or 7), 90))
    since = timezone.now() - timedelta(days=days)
    inbound = (
        StaffOnboardingInviteInbound.objects.filter(received_at__gte=since)
        .values("kind")
        .annotate(c=Count("id"))
        .order_by("-c")
    )
    kind_map = {row["kind"]: row["c"] for row in inbound}
    bounced_total = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_BOUNCED
    ).count()
    bounced_recent = StaffOnboardingLead.objects.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_BOUNCED,
        updated_at__gte=since,
    ).count()

    samples = list(
        StaffOnboardingInviteInbound.objects.filter(
            received_at__gte=since,
            kind=StaffOnboardingInviteInbound.KIND_BOUNCE,
        )
        .select_related("lead")
        .order_by("-received_at")[:15]
    )

    lines = [
        f"Raport bounce / inbound invitații — ultimele {days} zile",
        "",
        f"Inbound bounce: {kind_map.get('bounce', 0)}",
        f"Inbound răspuns: {kind_map.get('reply', 0)}",
        f"Inbound opt-out: {kind_map.get('opt_out', 0)}",
        f"Inbound unknown: {kind_map.get('unknown', 0)}",
        "",
        f"Lead-uri marcate bounced (total): {bounced_total}",
        f"Lead-uri marcate bounced (ultimele {days} zile): {bounced_recent}",
        "",
    ]
    if samples:
        lines.append("Ultimele bounce-uri procesate:")
        for row in samples:
            em = (row.lead.email if row.lead_id else "") or "(fără lead)"
            lines.append(f"  - {row.received_at:%Y-%m-%d %H:%M} · {em} · {(row.subject or '')[:60]}")
    else:
        lines.append("Niciun bounce procesat în interval (rulează IMAP poll / backlog).")
    lines.append("")
    lines.append("— EU-Adopt · raport automat bounce")
    return "\n".join(lines)


def send_bounce_weekly_report(*, days: int = 7, dry_run: bool = False) -> str:
    body = build_bounce_weekly_report_text(days=days)
    if dry_run:
        logger.info("Dry-run bounce weekly report:\n%s", body)
        return body
    recipients = staff_invite_report_recipients()
    if not recipients:
        raise RuntimeError("Niciun destinatar raport (STAFF_INVITE_REPORT_EMAIL / CONTACT_NOTIFY_EMAIL).")
    subject = f"[EU-Adopt] Bounce invitații — ultimele {days} zile"
    send_mail_text_and_html(
        subject=subject,
        body_text=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        mail_kind="staff_invite_bounce_weekly",
    )
    return body
