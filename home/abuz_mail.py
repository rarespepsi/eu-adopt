"""Trimitere sesizări abuz către organe competente (via EU-Adopt SMTP)."""

from __future__ import annotations

import logging
from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMessage

from home.abuz_contacts import resolve_abuz_recipients
from home.mail_helpers import _message_id_domain

logger = logging.getLogger(__name__)


def _staff_fallback_inbox() -> str:
    raw = (getattr(settings, "STAFF_INVITE_REPORT_EMAIL", None) or "").strip()
    if raw:
        return raw.split(",")[0].strip()
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if "<" in from_email and ">" in from_email:
        return from_email.split("<", 1)[1].split(">", 1)[0].strip()
    return from_email


def build_abuz_mail_bodies(report, recipient: dict) -> tuple[str, str]:
    attention = (recipient.get("attention_line") or "").strip()
    dest_label = (recipient.get("label") or "").strip()
    username = getattr(report.user, "username", "") or "—"
    name = (report.reporter_name or "").strip() or "—"
    is_bpa = "bpa" in dest_label.lower() or "poli" in dest_label.lower()

    if is_bpa:
        subject_line = (
            f"PETIȚIE: În atenția Biroului pentru Protecția Animalelor — "
            f"Județul {report.judet} — {name}"
        )
    else:
        subject_line = (
            f"PETIȚIE: În atenția DSVSA — Județul {report.judet} — {name}"
        )

    loc = (getattr(report, "incident_location", None) or "").strip() or "—"
    domicile = (getattr(report, "reporter_domicile", None) or "").strip() or "—"
    when = (getattr(report, "incident_when", None) or "").strip()

    text = (
        f"{attention}\n\n"
        f"DOMNULE INSPECTOR ȘEF / DOMNULE DIRECTOR,\n\n"
        f"Subsemnatul/a {name.upper()}, cu domiciliul în {domicile},\n"
        f"posesor al adresei de e-mail {report.reporter_email} și al nr. de telefon "
        f"{report.reporter_phone or '—'},\n"
        f"vă înaintez prezenta sesizare.\n\n"
        f"Această sesizare a fost transmisă prin intermediul platformei EU-Adopt "
        f"(https://eu-adopt.ro), de către utilizatorul înregistrat pe site "
        f"(username: {username}).\n\n"
        f"--- DETALII SESIZARE ---\n"
        f"Destinatar solicitat: {dest_label}\n"
        f"Județ: {report.judet}\n"
        f"Locația faptei: {loc}\n"
    )
    if when:
        text += f"Data / ora aproximativă: {when}\n"
    text += (
        f"\nDescrierea faptei:\n{report.description}\n\n"
        f"------------------------\n\n"
        f"Menționez că am luat la cunoștință prevederile legale privind falsul în "
        f"declarații și declar pe propria răspundere că datele transmise sunt reale.\n\n"
        f"=== Notă EU-Adopt ===\n"
        f"EU-Adopt intermediază transmisia. Nu verificăm și nu ne asumăm veridicitatea "
        f"sau corectitudinea conținutului — răspunderea pentru afirmații aparține "
        f"sesizorului. Organul competent decide următorii pași.\n\n"
        f"Solicit număr de înregistrare și comunicarea răspunsului la adresa de e-mail "
        f"a reclamantului: {report.reporter_email}\n\n"
        f"Cu respect,\n{name}\n"
    )
    return subject_line, text


def send_abuse_report_emails(report) -> tuple[str, str, str]:
    """
    Trimite mailurile pentru un AbuseReport.
    Returnează (status, sent_to_csv, log_text).
    """
    from home.abuz_contacts import abuz_contact_by_slug
    from home.models import AbuseReport

    row = abuz_contact_by_slug(report.judet_slug)
    if row is None:
        return AbuseReport.STATUS_FAILED, "", "Județ necunoscut."

    recipients = resolve_abuz_recipients(row, report.destinatie)
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "contact@eu-adopt.ro"
    reply_to = [report.reporter_email] if report.reporter_email else None
    staff_inbox = _staff_fallback_inbox()

    sent_emails: list[str] = []
    logs: list[str] = []
    pending_any = False
    failed_any = False

    for rec in recipients:
        email = (rec.get("email") or "").strip()
        subject, body = build_abuz_mail_bodies(report, rec)
        target = email
        note = ""
        if not target:
            pending_any = True
            if staff_inbox:
                target = staff_inbox
                note = " (pending contact — copie inbox EU-Adopt)"
                subject = "[PENDING CONTACT] " + subject
            else:
                logs.append(f"{rec.get('label')}: fără email organ și fără inbox staff.")
                continue

        try:
            msg = EmailMessage(
                subject=subject,
                body=body,
                from_email=from_email,
                to=[target],
                reply_to=reply_to,
                headers={
                    "Message-ID": make_msgid(domain=_message_id_domain()),
                    "X-EUAdopt-Mail": "abuse-report",
                },
            )
            if report.media:
                try:
                    report.media.open("rb")
                    name = (report.media.name or "atasament").rsplit("/", 1)[-1]
                    msg.attach(name, report.media.read())
                except Exception as exc:
                    logs.append(f"atașament eșuat: {exc}")
                finally:
                    try:
                        report.media.close()
                    except Exception:
                        pass
            msg.send(fail_silently=False)
            sent_emails.append(target)
            logs.append(f"OK → {target} [{rec.get('label')}]{note}")
        except Exception as exc:
            failed_any = True
            logger.exception("Abuse report mail failed to=%s", target)
            logs.append(f"FAIL → {target}: {exc}")

    log_text = "\n".join(logs)
    sent_csv = ", ".join(sent_emails)

    if sent_emails and not pending_any and not failed_any:
        status = AbuseReport.STATUS_SENT
    elif sent_emails and (pending_any or failed_any):
        status = AbuseReport.STATUS_PARTIAL
    elif pending_any and not sent_emails:
        status = AbuseReport.STATUS_PENDING_CONTACT
    elif failed_any:
        status = AbuseReport.STATUS_FAILED
    else:
        status = AbuseReport.STATUS_PENDING_CONTACT

    return status, sent_csv, log_text
