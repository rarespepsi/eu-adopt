"""
Ștergere cont cu perioadă de grație (14 zile) + finalizare soft (fără User.delete() în producție).
"""
from __future__ import annotations

import time
from typing import TYPE_CHECKING

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.db import transaction
from django.urls import reverse
from django.utils import timezone

from .mail_helpers import email_subject_for_user
from .models import (
    AccountProfile,
    AnimalListing,
    CollaboratorServiceOffer,
)

if TYPE_CHECKING:
    from django.contrib.auth.models import AbstractUser

User = get_user_model()

ACCOUNT_DELETION_GRACE_DAYS = 14


def account_has_pending_deletion(ap: AccountProfile | None) -> bool:
    if not ap or not ap.pending_deletion_grace_until:
        return False
    if ap.pending_deletion_finalized_at:
        return False
    return timezone.now() < ap.pending_deletion_grace_until


def account_deletion_grace_expired(ap: AccountProfile | None) -> bool:
    if not ap or not ap.pending_deletion_grace_until or not ap.pending_deletion_requested_at:
        return False
    if ap.pending_deletion_finalized_at:
        return False
    return timezone.now() >= ap.pending_deletion_grace_until


def clear_pending_deletion(ap: AccountProfile) -> None:
    ap.pending_deletion_requested_at = None
    ap.pending_deletion_grace_until = None
    ap.save()


def schedule_account_deletion(user: AbstractUser, ap: AccountProfile) -> timezone.datetime:
    now = timezone.now()
    until = now + timezone.timedelta(days=ACCOUNT_DELETION_GRACE_DAYS)
    ap.pending_deletion_requested_at = now
    ap.pending_deletion_grace_until = until
    ap.save()
    return until


def send_deletion_scheduled_email(*, user: AbstractUser, grace_until: timezone.datetime) -> None:
    if not (user.email or "").strip():
        return
    account_url = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/") + reverse("account")
    plain = (
        f"Bună ziua,\n\n"
        f"Am înregistrat cererea ta de ștergere a contului EU-Adopt.\n\n"
        f"Perioada de grație: {ACCOUNT_DELETION_GRACE_DAYS} zile (până la {grace_until.strftime('%d.%m.%Y %H:%M')}). "
        f"În acest interval te poți autentifica și poți anula cererea din pagina Cont.\n\n"
        f"După această dată contul va fi dezactivat definitiv, iar datele personale vor fi anonimizate sau ascise "
        f"conform politicii platformei (inclusiv pentru istoric ONG/colaborator).\n\n"
        f"Pagina Cont: {account_url}\n\n"
        f"Dacă nu ai solicitat ștergerea, autentifică-te și anulează cererea din Cont."
    )
    html = (
        f"<p>Bună ziua,</p>"
        f"<p>Am înregistrat <strong>cererea ta de ștergere</strong> a contului EU-Adopt.</p>"
        f"<p><strong>Perioada de grație: {ACCOUNT_DELETION_GRACE_DAYS} zile</strong> "
        f"(până la <strong>{grace_until.strftime('%d.%m.%Y %H:%M')}</strong>). "
        f"În acest interval te poți autentifica și poți <strong>anula cererea</strong> din pagina Cont.</p>"
        f"<p>După această dată contul va fi <strong>dezactivat definitiv</strong>, iar datele personale vor fi "
        f"anonimizate sau ascise conform politicii platformei.</p>"
        f'<p><a href="{account_url}">Deschide pagina Cont</a></p>'
        f"<p>Dacă nu ai solicitat ștergerea, autentifică-te și anulează cererea din Cont.</p>"
    )
    try:
        send_mail(
            subject=email_subject_for_user(user.username, "Ștergere cont programată – EU-Adopt"),
            message=plain,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=True,
            html_message=html,
        )
    except Exception:
        pass


def _anon_username_for_deleted(pk: int) -> str:
    return f"deleted_{pk}_{int(time.time())}"


def finalize_pending_account(user: AbstractUser) -> str:
    """
    După expirarea grației: dezactivare + ascundere publică + anonimizare.
    Nu apelează User.delete() (păstrează integritatea istoricului adopții/mesaje).
    Returnează un scurt mesaj de tip pentru logging (pf_soft, org_soft, ...).
    """
    ap = getattr(user, "account_profile", None)
    profile = getattr(user, "profile", None)
    role = ap.role if ap else AccountProfile.ROLE_PF

    with transaction.atomic():
        user.is_active = False
        user.first_name = ""
        user.last_name = ""
        user.email = f"deleted_{user.pk}_{int(time.time())}@anon.invalid"
        user.username = _anon_username_for_deleted(user.pk)
        user.set_unusable_password()
        user.save()

        if profile:
            profile.phone = ""
            profile.judet = ""
            profile.oras = ""
            profile.company_display_name = ""
            profile.company_legal_name = ""
            profile.company_cui = ""
            profile.company_address = ""
            profile.company_representative = ""
            profile.company_reg_com = ""
            profile.company_judet = ""
            profile.company_oras = ""
            profile.donation_cnp = ""
            profile.donation_address = ""
            profile.save()

        AnimalListing.objects.filter(owner=user).update(is_published=False)
        CollaboratorServiceOffer.objects.filter(collaborator=user).update(is_active=False)

        if ap:
            ap.pending_deletion_finalized_at = timezone.now()
            ap.save()

    return f"{role}_soft_finalized"
