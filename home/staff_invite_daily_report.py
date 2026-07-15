"""Raport zilnic email — invitații Add USER trimise ieri (Europe/Bucharest)."""

from __future__ import annotations

import logging
from dataclasses import dataclass, field
from datetime import date, datetime, timedelta
from typing import Any
from zoneinfo import ZoneInfo

from django.conf import settings
from django.db.models import Count
from django.utils import timezone

from home.mail_helpers import send_mail_text_and_html
from home.models import (
    StaffOnboardingInviteLog,
    StaffOnboardingInviteInbound,
    StaffOnboardingLead,
)
from home.staff_onboarding_invite import staff_invite_campaign_stats

logger = logging.getLogger(__name__)

RO_TZ = ZoneInfo("Europe/Bucharest")


@dataclass
class InviteDayReport:
    report_date: date
    total_logs: int = 0
    sent_ok: int = 0
    errors: int = 0
    dry_run: int = 0
    dispatch_wave: int = 0
    dispatch_manual: int = 0
    unique_emails_ok: int = 0
    leads_marked_sent: int = 0
    leads_signed_up: int = 0
    inbound: dict[str, int] = field(default_factory=dict)
    time_start: str = ""
    time_end: str = ""
    error_rows: list[dict[str, str]] = field(default_factory=list)
    campaign: dict[str, Any] = field(default_factory=dict)

    @property
    def date_label(self) -> str:
        return self.report_date.strftime("%d.%m.%Y")


def staff_invite_report_enabled() -> bool:
    return bool(getattr(settings, "STAFF_INVITE_REPORT_ENABLED", False))


def staff_invite_report_recipients() -> list[str]:
    raw = (getattr(settings, "STAFF_INVITE_REPORT_EMAIL", None) or "").strip()
    if not raw:
        raw = (getattr(settings, "CONTACT_NOTIFY_EMAIL", None) or "").strip()
    if not raw:
        raw = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    # DEFAULT_FROM_EMAIL may be "Name <email@>"
    if "<" in raw and ">" in raw:
        raw = raw.split("<", 1)[1].split(">", 1)[0].strip()
    return [x.strip() for x in raw.split(",") if x.strip()]


def yesterday_ro(now=None) -> date:
    now = now or timezone.now()
    local = now.astimezone(RO_TZ)
    return (local - timedelta(days=1)).date()


def day_bounds_ro(for_date: date) -> tuple[datetime, datetime]:
    start = datetime(for_date.year, for_date.month, for_date.day, 0, 0, 0, tzinfo=RO_TZ)
    end = start + timedelta(days=1)
    return start, end


def build_staff_invite_day_report(for_date: date | None = None, now=None) -> InviteDayReport:
    now = now or timezone.now()
    for_date = for_date or yesterday_ro(now)
    start, end = day_bounds_ro(for_date)

    logs = StaffOnboardingInviteLog.objects.filter(sent_at__gte=start, sent_at__lt=end)
    by_outcome = dict(
        logs.values("outcome").annotate(c=Count("id")).values_list("outcome", "c")
    )
    by_dispatch = dict(
        logs.values("dispatch_kind").annotate(c=Count("id")).values_list("dispatch_kind", "c")
    )

    error_rows: list[dict[str, str]] = []
    for row in logs.filter(outcome=StaffOnboardingInviteLog.OUTCOME_ERROR).order_by("sent_at"):
        error_rows.append(
            {
                "time": row.sent_at.astimezone(RO_TZ).strftime("%H:%M"),
                "lead_id": str(row.lead_id),
                "email": row.to_email,
                "message": (row.error_message or "")[:200],
            }
        )

    ok_emails = set(
        logs.filter(outcome=StaffOnboardingInviteLog.OUTCOME_SENT).values_list("to_email", flat=True)
    )

    leads_day = StaffOnboardingLead.objects.filter(
        invite_email_last_sent_at__gte=start,
        invite_email_last_sent_at__lt=end,
    )
    signed_up = leads_day.filter(
        invite_mail_status=StaffOnboardingLead.INVITE_SIGNED_UP,
    ).count()

    inbound_qs = StaffOnboardingInviteInbound.objects.filter(
        received_at__gte=start, received_at__lt=end
    )
    inbound = dict(
        inbound_qs.values("kind").annotate(c=Count("id")).values_list("kind", "c")
    ) if inbound_qs.exists() else {}

    first_ts = logs.order_by("sent_at").values_list("sent_at", flat=True).first()
    last_ts = logs.order_by("-sent_at").values_list("sent_at", flat=True).first()

    report = InviteDayReport(
        report_date=for_date,
        total_logs=logs.count(),
        sent_ok=by_outcome.get(StaffOnboardingInviteLog.OUTCOME_SENT, 0),
        errors=by_outcome.get(StaffOnboardingInviteLog.OUTCOME_ERROR, 0),
        dry_run=by_outcome.get(StaffOnboardingInviteLog.OUTCOME_DRY_RUN, 0),
        dispatch_wave=by_dispatch.get(StaffOnboardingInviteLog.DISPATCH_WAVE, 0),
        dispatch_manual=by_dispatch.get(StaffOnboardingInviteLog.DISPATCH_MANUAL, 0),
        unique_emails_ok=len(ok_emails),
        leads_marked_sent=leads_day.count(),
        leads_signed_up=signed_up,
        inbound=inbound,
        error_rows=error_rows,
        campaign=staff_invite_campaign_stats(now),
    )
    if first_ts:
        report.time_start = first_ts.astimezone(RO_TZ).strftime("%H:%M")
        report.time_end = (last_ts or first_ts).astimezone(RO_TZ).strftime("%H:%M")
    return report


def format_staff_invite_day_report_text(report: InviteDayReport) -> str:
    lines = [
        f"Raport invitații Add USER — {report.date_label} (Europe/Bucharest)",
        "",
        f"Total încercări: {report.total_logs}",
        f"Trimise OK (SMTP): {report.sent_ok}",
        f"Erori SMTP: {report.errors}",
        f"Simulări: {report.dry_run}",
        f"Val (wave): {report.dispatch_wave} · Manual: {report.dispatch_manual}",
    ]
    if report.time_start:
        lines.append(f"Interval trimiteri: {report.time_start} – {report.time_end}")
    lines.extend(
        [
            f"Emailuri unice trimise OK: {report.unique_emails_ok}",
            f"Lead-uri marcate trimise: {report.leads_marked_sent}",
            f"Înscrieri noi din lot: {report.leads_signed_up}",
        ]
    )
    if report.inbound:
        parts = [f"{k}={v}" for k, v in sorted(report.inbound.items())]
        lines.append(f"Inbound (răspuns/bounce): {', '.join(parts)}")
    if report.error_rows:
        lines.append("")
        lines.append("Erori:")
        for err in report.error_rows:
            lines.append(f"  [{err['time']}] lead {err['lead_id']} · {err['email']}")
            if err["message"]:
                lines.append(f"    {err['message']}")
    camp = report.campaign or {}
    lines.extend(
        [
            "",
            "Campanie (total, la trimiterea raportului):",
            f"  Invitați vreodată: {camp.get('invited_ever', '—')}",
            f"  Conturi create: {camp.get('registered_total', '—')}",
            f"  Răspunsuri: {camp.get('replied_total', '—')}",
            f"  Bounce: {camp.get('bounced_total', '—')}",
            f"  Plafon rămas azi: {camp.get('daily_remaining', '—')} / {camp.get('daily_cap', '—')}",
        ]
    )
    lines.append("")
    lines.append("— EU-Adopt · raport automat")
    return "\n".join(lines)


def send_staff_invite_daily_report(
    for_date: date | None = None,
    *,
    force: bool = False,
    dry_run: bool = False,
) -> InviteDayReport:
    if not force and not staff_invite_report_enabled():
        raise RuntimeError("Raport zilnic invitații dezactivat (EUADOPT_STAFF_INVITE_REPORT_ENABLED).")

    report = build_staff_invite_day_report(for_date=for_date)
    body = format_staff_invite_day_report_text(report)

    if dry_run:
        logger.info("Dry-run raport invitații %s:\n%s", report.date_label, body)
        return report

    recipients = staff_invite_report_recipients()
    if not recipients:
        raise RuntimeError("Niciun destinatar raport (STAFF_INVITE_REPORT_EMAIL / CONTACT_NOTIFY_EMAIL).")

    subject = (
        f"[EU-Adopt] Invitații {report.date_label} — "
        f"{report.sent_ok} trimise"
        + (f", {report.errors} erori" if report.errors else "")
    )
    send_mail_text_and_html(
        subject=subject,
        body_text=body,
        from_email=settings.DEFAULT_FROM_EMAIL,
        recipient_list=recipients,
        mail_kind="staff_invite_daily_report",
    )
    logger.info(
        "Raport invitații %s trimis către %s (%s OK, %s erori)",
        report.date_label,
        ",".join(recipients),
        report.sent_ok,
        report.errors,
    )
    return report
