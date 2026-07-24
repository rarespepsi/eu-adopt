"""
Transport pe hub EU: cerere → inbox staff (fără dispatch colaboratori).

Destinație: transport@eu-adopt.ro — gestiune manuală + reply către solicitant.
"""
from __future__ import annotations

import logging

from django.conf import settings
from django.urls import reverse

from home.mail_helpers import send_mail_text_and_html

logger = logging.getLogger(__name__)

TRANSPORT_EU_INBOX = "transport@eu-adopt.ro"


def send_eu_transport_request_to_inbox(request, tvr) -> bool:
    """
    Trimite detaliile cererii la transport@eu-adopt.ro.
    Reply-To = emailul utilizatorului (dacă există), ca reply-ul să meargă la el.
    Returnează True dacă mailul a fost trimis.
    """
    to = (getattr(settings, "TRANSPORT_EU_INBOX_EMAIL", None) or TRANSPORT_EU_INBOX).strip()
    if not to:
        logger.error("transport EU inbox empty; tvr_id=%s", getattr(tvr, "pk", None))
        return False

    user = getattr(tvr, "user", None)
    username = getattr(user, "username", "") or "—"
    user_email = (getattr(user, "email", None) or "").strip()
    phone = ""
    try:
        prof = getattr(user, "profile", None) if user else None
        phone = (getattr(prof, "phone", None) or "").strip() if prof else ""
    except Exception:
        phone = ""

    related = getattr(tvr, "related_animal", None)
    pet_line = "—"
    if related is not None:
        pet_line = f"#{related.pk} {getattr(related, 'name', '') or ''}".strip()
        try:
            path = reverse("pets_single", args=[related.pk])
            pet_line = f"{pet_line} — {request.build_absolute_uri(path)}"
        except Exception:
            pass

    lines = [
        "EU-Adopt — new transport request (EU hub)",
        f"Request id: {tvr.pk}",
        f"User: {username}",
        f"Email: {user_email or '—'}",
        f"Phone: {phone or '—'}",
        "",
        f"Destination country: {(tvr.country or 'RO').upper()}",
        f"County: {tvr.judet}",
        f"City / place: {tvr.oras}",
        f"Pick-up: {tvr.plecare}",
        f"Drop-off: {tvr.sosire}",
        f"Date: {tvr.data_raw or '—'}",
        f"Time: {tvr.ora_raw or '—'}",
        f"Animals: {tvr.nr_caini}",
        f"Route: {tvr.route_scope}",
        f"Urgency: {tvr.urgency_window}",
        f"Related pet: {pet_line}",
        "",
        "Reply to this email to contact the requester (Reply-To set when email is known).",
    ]
    body = "\n".join(lines)
    subject = f"[EU transport #{tvr.pk}] {username} — {(tvr.country or 'RO').upper()} {tvr.oras}"
    reply_to = [user_email] if user_email else None
    try:
        send_mail_text_and_html(
            subject,
            body,
            settings.DEFAULT_FROM_EMAIL,
            [to],
            mail_kind="transport_eu_inbox",
            reply_to=reply_to,
        )
        return True
    except Exception:
        logger.exception("transport EU inbox mail failed tvr_id=%s", getattr(tvr, "pk", None))
        return False
