"""Helper-e minime pentru emailuri transmise către utilizatori."""

from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMultiAlternatives


def email_subject_for_user(username: str | None, subject: str) -> str:
    """
    Prefixează subiectul cu [username] destinatarului (același inbox pe mai multe conturi).
    """
    u = (username or "").strip() or "?"
    base = (subject or "").strip()
    return f"[{u}] {base}"


def _message_id_domain() -> str:
    """Domeniu FQDN pentru Message-ID (evită mesaje „lipite” la același inbox)."""
    dom = (getattr(settings, "EMAIL_MESSAGE_ID_DOMAIN", None) or "").strip()
    if dom:
        return dom
    for h in getattr(settings, "ALLOWED_HOSTS", ()) or ():
        h = (h or "").strip()
        if h and h != "*":
            return h
    return "euadopt.local"


def send_mail_text_and_html(
    subject: str,
    body_text: str,
    from_email: str,
    recipient_list: list,
    html_body: str | None = None,
    *,
    mail_kind: str = "",
) -> None:
    """
    Trimite un singur mesaj SMTP cu Message-ID unic.

    La probe cu aceeași adresă pe mai multe conturi, furnizorii (ex. Yahoo) pot
    ascunde un mesaj dacă par duplicate; Message-ID distinct + antet X-EUAdopt-Mail
    ajută la livrare și la filtrare în client.
    """
    headers: dict[str, str] = {"Message-ID": make_msgid(domain=_message_id_domain())}
    if mail_kind:
        headers["X-EUAdopt-Mail"] = mail_kind[:120]
    to = [str(x).strip() for x in (recipient_list or []) if str(x).strip()]
    if not to:
        return
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text or "",
        from_email=from_email,
        to=to,
        headers=headers,
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    msg.send(fail_silently=False)
