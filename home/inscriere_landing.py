"""Formular scurt /inscriere/ — intrare din Facebook (și alte campanii)."""
from __future__ import annotations

from django.contrib.auth import get_user_model
from django.core.cache import cache
from django.core.exceptions import ValidationError
from django.core.validators import EmailValidator
from django.utils import timezone

from home.models import StaffOnboardingLead
from home.staff_onboarding_csv import is_placeholder_lead_email
from home.staff_onboarding_invite import (
    staff_invite_mark_landing_access,
    staff_invite_signup_redirect_url,
    staff_invite_sync_lead_with_site_user,
)

INSCRIERE_CATEGORY_CHOICES = (
    (StaffOnboardingLead.KIND_ADAPOST, "Adăpost"),
    (StaffOnboardingLead.KIND_ORG, "ONG / asociație"),
    (StaffOnboardingLead.KIND_COLLAB, "Colaborator (cabinet, magazin, servicii…)"),
    (StaffOnboardingLead.KIND_PF, "Persoană fizică (adoptator)"),
)

INSCRIERE_RATE_LIMIT_PER_HOUR = 8
INSCRIERE_SOURCE_NOTE = "Sursă: formular /inscriere/ (Facebook)"


def _inscriere_rate_limit_key(request) -> str:
    ip = (request.META.get("HTTP_X_FORWARDED_FOR") or "").split(",")[0].strip()
    if not ip:
        ip = request.META.get("REMOTE_ADDR") or "unknown"
    return f"inscriere_rate:{ip}"


def inscriere_rate_limited(request) -> bool:
    key = _inscriere_rate_limit_key(request)
    count = cache.get(key, 0)
    return int(count) >= INSCRIERE_RATE_LIMIT_PER_HOUR


def inscriere_bump_rate_limit(request) -> None:
    key = _inscriere_rate_limit_key(request)
    count = int(cache.get(key, 0) or 0) + 1
    cache.set(key, count, timeout=3600)


def _find_or_create_lead(email: str, category: str, phone: str, contact: str, now) -> StaffOnboardingLead:
    lead = (
        StaffOnboardingLead.objects.filter(email__iexact=email, imported_user__isnull=True)
        .order_by("-pk")
        .first()
    )
    if lead is None:
        return StaffOnboardingLead.objects.create(
            email=email,
            account_kind=category,
            phone=phone[:40],
            display_name=contact[:200],
            org_display_name=contact[:255] if category != StaffOnboardingLead.KIND_PF else "",
            status=StaffOnboardingLead.ST_READY,
            invite_mail_status=StaffOnboardingLead.INVITE_NEVER,
            is_public_shelter=False,
            consent_terms_at=now,
            consent_privacy_at=now,
            invite_staff_notes=INSCRIERE_SOURCE_NOTE,
        )
    lead.account_kind = category
    lead.phone = phone[:40]
    lead.display_name = contact[:200]
    if category != StaffOnboardingLead.KIND_PF:
        lead.org_display_name = contact[:255]
    lead.consent_terms_at = now
    lead.consent_privacy_at = now
    note = (lead.invite_staff_notes or "").strip()
    if "/inscriere/" not in note.lower():
        lead.invite_staff_notes = f"{note} | {INSCRIERE_SOURCE_NOTE}".strip(" |")
    lead.save()
    return lead


def process_inscriere_post(request) -> tuple[str | None, dict[str, str]]:
    errors: dict[str, str] = {}
    if inscriere_rate_limited(request):
        errors["__all__"] = "Prea multe încercări. Reîncercați peste o oră."
        return None, errors

    category = (request.POST.get("category") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    phone = (request.POST.get("phone") or "").strip()
    contact = (request.POST.get("contact") or "").strip()
    accept_termeni = request.POST.get("accept_termeni") == "on"
    accept_gdpr = request.POST.get("accept_gdpr") == "on"

    valid_kinds = {c[0] for c in INSCRIERE_CATEGORY_CHOICES}
    if category not in valid_kinds:
        errors["category"] = "Alegeți categoria contului."
    if not email:
        errors["email"] = "Email obligatoriu."
    else:
        try:
            EmailValidator()(email)
        except ValidationError:
            errors["email"] = "Adresă de email invalidă."
    if not phone:
        errors["phone"] = "Telefon obligatoriu."
    if category in (
        StaffOnboardingLead.KIND_ADAPOST,
        StaffOnboardingLead.KIND_ORG,
        StaffOnboardingLead.KIND_COLLAB,
    ) and not contact:
        errors["contact"] = "Persoana de contact este obligatorie."
    if not accept_termeni:
        errors["accept_termeni"] = "Trebuie să acceptați termenii și condițiile."
    if not accept_gdpr:
        errors["accept_gdpr"] = "Trebuie să acceptați prelucrarea datelor (GDPR)."

    if errors:
        return None, errors

    if is_placeholder_lead_email(email):
        errors["email"] = "Folosiți o adresă de email reală."
        return None, errors

    User = get_user_model()
    if User.objects.filter(email__iexact=email).exists():
        errors["email"] = "Există deja un cont cu acest email. Folosiți Intra în cont."
        return None, errors

    now = timezone.now()
    lead = _find_or_create_lead(email, category, phone, contact, now)

    if staff_invite_sync_lead_with_site_user(lead):
        errors["email"] = "Există deja un cont cu acest email."
        return None, errors

    staff_invite_mark_landing_access(lead)
    inscriere_bump_rate_limit(request)
    return staff_invite_signup_redirect_url(request, lead), {}
