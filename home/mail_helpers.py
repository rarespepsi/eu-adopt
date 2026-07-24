"""Helper-e minime pentru emailuri transmise către utilizatori."""

import logging
from email.utils import make_msgid

from django.conf import settings
from django.core.mail import EmailMultiAlternatives

logger = logging.getLogger(__name__)


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
    reply_to: list | None = None,
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
    rt = [str(x).strip() for x in (reply_to or []) if str(x).strip()]
    msg = EmailMultiAlternatives(
        subject=subject,
        body=body_text or "",
        from_email=from_email,
        to=to,
        headers=headers,
        reply_to=rt or None,
    )
    if html_body:
        msg.attach_alternative(html_body, "text/html")
    try:
        msg.send(fail_silently=False)
    except Exception as exc:
        logger.error(
            "SMTP send_mail_text_and_html failed kind=%s host=%s port=%s user=%s to=%s: %s",
            mail_kind or "—",
            getattr(settings, "EMAIL_HOST", ""),
            getattr(settings, "EMAIL_PORT", ""),
            getattr(settings, "EMAIL_HOST_USER", ""),
            ",".join(to),
            exc,
            exc_info=True,
        )
        raise


def adoption_pet_public_email_lines(pet) -> list[str]:
    """Rezumat din fișă (date publice) pentru email adoptator."""
    species_map = {"dog": "Câine", "cat": "Pisică", "other": "Alt"}
    lines = []
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    lines.append(f"Nume: {pet_label}")
    lines.append(f"Specie: {species_map.get(pet.species, pet.species or '—')}")
    if pet.age_label:
        lines.append(f"Vârstă: {pet.age_label}")
    if pet.size:
        lines.append(f"Talie: {pet.size}")
    if pet.sex:
        lines.append(f"Sex: {pet.sex}")
    loc = ", ".join(x for x in (pet.county, pet.city) if x)
    if loc:
        lines.append(f"Zonă: {loc}")
    if pet.color:
        lines.append(f"Culoare: {pet.color}")
    if pet.greutate_aprox:
        lines.append(f"Greutate (aprox.): {pet.greutate_aprox}")
    if pet.sterilizat:
        lines.append(f"Sterilizat: {pet.sterilizat}")
    if pet.vaccinat:
        lines.append(f"Vaccinat: {pet.vaccinat}")
    if pet.cip:
        lines.append(f"CIP: {pet.cip}")
    if (pet.cine_sunt or "").strip():
        cs = (pet.cine_sunt or "").strip().replace("\n", " ")
        if len(cs) > 400:
            cs = cs[:397] + "..."
        lines.append(f"Descriere: {cs}")
    sp_low = (pet.species or "").strip().lower()
    if sp_low not in ("dog", "cat") and (pet.detalii_animal or "").strip():
        da = (pet.detalii_animal or "").strip().replace("\n", " ")
        if len(da) > 400:
            da = da[:397] + "..."
        lines.append(f"Detalii animal: {da}")
    return lines
