"""
Trimitere emailuri EU-Adopt — template HTML + text, logging SMTP clar.

Parole și user SMTP: exclusiv din settings (.env via decouple).
"""

from __future__ import annotations

import logging
from typing import Any

from django.conf import settings
from django.core.mail import EmailMultiAlternatives
from django.template import TemplateDoesNotExist
from django.template.loader import render_to_string

from .mail_helpers import (
    adoption_pet_public_email_lines,
    email_subject_for_user,
    send_mail_text_and_html,
)

logger = logging.getLogger(__name__)

# Tipuri template: templates/email/<kind>.html și .txt
MAIL_ACCOUNT_ACTIVATION = "account_activation"
MAIL_PASSWORD_RESET = "password_reset"
MAIL_ADOPTION_CONFIRMATION = "adoption_confirmation"
MAIL_TRANSPORT_FORM = "transport_form"
MAIL_CONTACT_STAFF = "contact_staff"
MAIL_CONTACT_ONG = "contact_ong"
MAIL_TEST = "test_smtp"

_DEFAULT_SUBJECTS = {
    MAIL_ACCOUNT_ACTIVATION: "Activează contul – EU-Adopt",
    MAIL_PASSWORD_RESET: "Resetare parolă – EU-Adopt",
    MAIL_ADOPTION_CONFIRMATION: "Cererea ta de adopție – EU-Adopt",
    MAIL_TRANSPORT_FORM: "Cerere transport înregistrată – EU-Adopt",
    MAIL_CONTACT_STAFF: "[Contact EU-Adopt] Mesaj nou",
    MAIL_CONTACT_ONG: "[Contact ONG / Adăpost] Mesaj nou – EU-Adopt",
    MAIL_TEST: "EU-Adopt SMTP Test",
}


def get_from_email() -> str:
    """Expeditor: DEFAULT_FROM_EMAIL din .env."""
    return (getattr(settings, "DEFAULT_FROM_EMAIL", "") or "").strip() or (
        getattr(settings, "EMAIL_HOST_USER", "") or ""
    )


def get_contact_notify_email() -> str:
    """Destinatar notificări formular Contact (implicit același cont SMTP)."""
    return (getattr(settings, "CONTACT_NOTIFY_EMAIL", "") or "").strip() or get_from_email()


def _render_pair(kind: str, context: dict[str, Any]) -> tuple[str, str]:
    ctx = {
        "site_name": "EU-Adopt",
        "site_url": (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/"),
        "support_email": get_from_email(),
        **context,
    }
    html_name = f"email/{kind}.html"
    txt_name = f"email/{kind}.txt"
    try:
        html_body = render_to_string(html_name, ctx)
    except TemplateDoesNotExist:
        html_body = ""
    try:
        body_text = render_to_string(txt_name, ctx)
    except TemplateDoesNotExist:
        body_text = ""
    if not body_text.strip() and html_body:
        from django.utils.html import strip_tags

        body_text = strip_tags(html_body)
    return body_text.strip(), html_body.strip()


def log_smtp_error(kind: str, exc: Exception, *, to: list[str] | None = None) -> None:
    """Log structurat pentru erori SMTP (fără parolă)."""
    recipients = ", ".join(to or [])
    logger.error(
        "SMTP send failed kind=%s host=%s port=%s user=%s tls=%s ssl=%s to=[%s] error_type=%s error=%s",
        kind,
        getattr(settings, "EMAIL_HOST", ""),
        getattr(settings, "EMAIL_PORT", ""),
        getattr(settings, "EMAIL_HOST_USER", ""),
        getattr(settings, "EMAIL_USE_TLS", False),
        getattr(settings, "EMAIL_USE_SSL", False),
        recipients,
        type(exc).__name__,
        exc,
        exc_info=True,
    )


def send_euadopt_email(
    kind: str,
    to: list[str] | str,
    context: dict[str, Any] | None = None,
    *,
    subject: str | None = None,
    username: str | None = None,
    attachments: list[tuple[str, bytes, str]] | None = None,
    fail_silently: bool = False,
) -> bool:
    """
    Trimite email cu template HTML + text/plain.

    attachments: listă de (filename, content_bytes, mimetype)
    Returnează True la succes.
    """
    if isinstance(to, str):
        to_list = [to.strip()] if to.strip() else []
    else:
        to_list = [str(x).strip() for x in (to or []) if str(x).strip()]
    if not to_list:
        logger.warning("send_euadopt_email skipped kind=%s: no recipients", kind)
        return False

    ctx = dict(context or {})
    body_text, html_body = _render_pair(kind, ctx)
    base_subj = (subject or _DEFAULT_SUBJECTS.get(kind) or "EU-Adopt").strip()
    full_subj = email_subject_for_user(username, base_subj) if username else base_subj
    from_email = get_from_email()

    try:
        if attachments:
            from email.utils import make_msgid

            from .mail_helpers import _message_id_domain

            headers = {"Message-ID": make_msgid(domain=_message_id_domain())}
            if kind:
                headers["X-EUAdopt-Mail"] = kind[:120]
            msg = EmailMultiAlternatives(
                subject=full_subj,
                body=body_text or "(Mesaj HTML — deschide în clientul de email.)",
                from_email=from_email,
                to=to_list,
                headers=headers,
            )
            if html_body:
                msg.attach_alternative(html_body, "text/html")
            for fname, content, mime in attachments:
                msg.attach(fname, content, mime)
            msg.send(fail_silently=False)
        else:
            send_mail_text_and_html(
                full_subj,
                body_text,
                from_email,
                to_list,
                html_body or None,
                mail_kind=kind,
            )
        logger.info(
            "SMTP sent kind=%s to=%s subject=%r",
            kind,
            ",".join(to_list),
            full_subj,
        )
        return True
    except Exception as exc:
        log_smtp_error(kind, exc, to=to_list)
        if fail_silently:
            return False
        raise


def send_account_activation_email(
    user,
    verify_url: str,
    *,
    resend: bool = False,
    fail_silently: bool = False,
) -> bool:
    subj = "Verificare email – EU-Adopt (retrimis)" if resend else "Verificare email – EU-Adopt"
    return send_euadopt_email(
        MAIL_ACCOUNT_ACTIVATION,
        user.email,
        {
            "verify_url": verify_url,
            "username": user.username,
            "resend": resend,
        },
        subject=subj,
        username=user.username,
        fail_silently=fail_silently,
    )


def send_password_reset_email(user, reset_url: str, *, fail_silently: bool = False) -> bool:
    return send_euadopt_email(
        MAIL_PASSWORD_RESET,
        user.email,
        {"reset_url": reset_url, "username": user.username},
        username=user.username,
        fail_silently=fail_silently,
    )


def send_adoption_confirmation_email(ar, *, fail_silently: bool = False) -> bool:
    from django.urls import reverse

    pet = ar.animal
    adopter = ar.adopter
    if not (adopter.email or "").strip():
        return False
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        pet_path = reverse("pets_single", args=[pet.pk])
    except Exception:
        pet_path = f"/pets/{pet.pk}/"
    pet_link = f"{site_base}{pet_path}" if site_base else pet_path
    summary_lines = adoption_pet_public_email_lines(pet)
    return send_euadopt_email(
        MAIL_ADOPTION_CONFIRMATION,
        adopter.email,
        {
            "pet_label": pet_label,
            "pet_link": pet_link,
            "summary_lines": summary_lines,
            "adopter_name": (f"{adopter.first_name} {adopter.last_name}").strip() or adopter.username,
        },
        subject=f"Cererea ta de adopție pentru {pet_label}",
        username=adopter.username,
        fail_silently=fail_silently,
    )


def send_transport_form_email(
    request,
    tvr,
    *,
    job=None,
    cancel_url: str = "",
    fail_silently: bool = False,
) -> bool:
    user = tvr.user
    if not user or not (user.email or "").strip():
        return False
    from .transport_dispatch import _tvr_summary_lines

    summary = _tvr_summary_lines(tvr)
    from .models import TransportDispatchJob

    has_dispatch = bool(job and job.status == TransportDispatchJob.STATUS_OPEN)
    return send_euadopt_email(
        MAIL_TRANSPORT_FORM,
        user.email,
        {
            "username": user.username,
            "tvr_id": tvr.pk,
            "job_id": job.pk if job else None,
            "summary_lines": summary.splitlines(),
            "cancel_url": cancel_url,
            "has_dispatch": has_dispatch,
        },
        username=user.username,
        fail_silently=fail_silently,
    )


def send_contact_notification_email(entry, *, is_ong: bool = False, fail_silently: bool = False) -> bool:
    from .models import ContactMessage

    topic_label = dict(ContactMessage.TOPIC_CHOICES).get(entry.topic, entry.topic)
    kind = MAIL_CONTACT_ONG if is_ong else MAIL_CONTACT_STAFF
    ctx = {
        "full_name": entry.full_name,
        "email": entry.email,
        "phone": entry.phone or "—",
        "topic_label": topic_label,
        "subject": entry.subject,
        "message": entry.message,
        "ip_address": entry.ip_address or "—",
        "has_attachment": bool(entry.attachment),
        "is_ong": is_ong,
    }
    to = get_contact_notify_email()
    attachments = None
    if entry.attachment:
        try:
            entry.attachment.open("rb")
            content = entry.attachment.read()
            entry.attachment.close()
            fname = entry.attachment.name.split("/")[-1] if entry.attachment.name else "atasament"
            attachments = [(fname, content, "application/octet-stream")]
        except Exception as exc:
            logger.warning("contact attachment read failed id=%s: %s", entry.pk, exc)

    subj = f"[Contact EU-Adopt] {entry.subject}"
    if is_ong:
        subj = f"[Contact ONG / Adăpost] {entry.subject}"

    return send_euadopt_email(
        kind,
        to,
        ctx,
        subject=subj,
        attachments=attachments,
        fail_silently=fail_silently,
    )


def send_test_email(to: str = "rarespepsi@yahoo.com") -> bool:
    return send_euadopt_email(
        MAIL_TEST,
        to,
        {"message": "SMTP Zoho funcționează corect din Django."},
        subject="EU-Adopt SMTP Test",
    )
