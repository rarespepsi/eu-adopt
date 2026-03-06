"""
Email trimis către partener (colaborator) când un adoptator alege un cupon.
"""
import logging
from django.core.mail import send_mail
from django.conf import settings

logger = logging.getLogger(__name__)


def send_coupon_claim_email_to_partner(claim):
    """
    Trimite email către partener cu datele adoptatorului și cuponul ales.
    claim: instanță CouponClaim (cu user, partner, category).
    Returnează True dacă a trimis, False dacă partenerul nu are email sau eroare.
    """
    partner = claim.partner
    to_email = (partner.email or "").strip()
    if not to_email:
        return False
    user = claim.user
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Un adoptator a ales cuponul tău: {partner.name}"
    # Date adoptator din User + UserProfile
    nume = getattr(user, "get_full_name", lambda: "")() or (getattr(user, "username", "") or "")
    try:
        up = user.user_profile
        if not nume and (up.prenume or up.nume):
            nume = f"{up.prenume or ''} {up.nume or ''}".strip()
    except Exception:
        pass
    email_user = (user.email or "").strip()
    telefon = ""
    judet_loc = ""
    try:
        up = user.user_profile
        telefon = (getattr(up, "telefon", None) or getattr(user.profile, "phone", None) or "").strip()
        parts = []
        if getattr(up, "oras", None) and (up.oras or "").strip():
            parts.append((up.oras or "").strip())
        if getattr(up, "judet", None) and (up.judet or "").strip():
            try:
                parts.append(up.get_judet_display())
            except Exception:
                parts.append((up.judet or "").strip())
        if parts:
            judet_loc = ", ".join(parts)
    except Exception:
        try:
            telefon = (getattr(user.user_profile, "telefon", None) or getattr(user.profile, "phone", None) or "").strip()
        except Exception:
            pass
    body = f"""Bună ziua,

Adoptator EU-Adopt – cupon activ.

Un adoptator a ales cuponul/oferta dvs. din categoria „{partner.get_category_display()}”.

Date adoptator:
- Nume: {nume or '-'}
- Email: {email_user or '-'}
- Telefon: {telefon or '-'}
- Județ / localitate: {judet_loc or '-'}

Oferta selectată: {partner.offer_text or partner.name}

Reducerile și serviciile sunt gestionate direct de dvs. Adoptatorul vă poate contacta la datele pe care le-ați furnizat pe platformă.

Cu stimă,
Echipa EU-Adopt
"""
    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("send_coupon_claim_email_to_partner: trimis la %s pentru claim %s", to_email, claim.pk)
        return True
    except Exception as e:
        logger.exception("send_coupon_claim_email_to_partner: %s", e)
        return False


def send_coupon_confirmation_to_adoptor(claim):
    """
    Trimite email de confirmare adoptatorului după ce a ales un cupon.
    claim: instanță CouponClaim (cu user, partner).
    """
    user = claim.user
    to_email = (user.email or "").strip()
    if not to_email:
        return False
    partner = claim.partner
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = f"[EU-Adopt] Ai ales cuponul: {partner.name}"
    body = f"""Bună ziua,

Ai ales cuponul partenerului {partner.name} ({partner.get_category_display()}).

Oferta: {partner.offer_text or partner.name}
"""
    if partner.url:
        body += f"\nVezi oferta: {partner.url}\n"
    body += """
Poți prezenta acest cupon la partener conform condițiilor acestuia.

Cu plăcere,
Echipa EU-Adopt
"""
    try:
        send_mail(subject, body.strip(), from_email, [to_email], fail_silently=False)
        logger.info("send_coupon_confirmation_to_adoptor: trimis la %s pentru claim %s", to_email, claim.pk)
        return True
    except Exception as e:
        logger.exception("send_coupon_confirmation_to_adoptor: %s", e)
        return False
