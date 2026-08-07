"""Desfacere câmp email cu 2–3 adrese → lead-uri trimitere invitație."""

from __future__ import annotations

import re

from django.core.exceptions import ValidationError
from django.core.validators import validate_email

from home.models import StaffOnboardingLead
from home.staff_lead_contact_normalize import normalize_lead_phone, split_phone_field as split_phone_field_norm

EMAIL_SPLIT_RE = re.compile(r"[\s/;,|]+")


def is_plausible_invite_email(em: str | None) -> bool:
    """Filtru rapid + validate_email (respinge ex. babeni@://e-adm.com)."""
    value = (em or "").strip().lower()
    if not value or "@" not in value or "://" in value or " " in value:
        return False
    local, _, domain = value.partition("@")
    if not local or not domain or "." not in domain:
        return False
    if domain.startswith(".") or domain.endswith(".") or ".." in domain:
        return False
    try:
        validate_email(value)
    except ValidationError:
        return False
    return True


def split_email_field(raw: str | None) -> list[str]:
    out: list[str] = []
    seen: set[str] = set()
    for part in EMAIL_SPLIT_RE.split((raw or "").strip()):
        em = part.strip().lower()
        if not is_plausible_invite_email(em):
            continue
        if em not in seen:
            seen.add(em)
            out.append(em)
    return out


def clone_lead_for_email(source: StaffOnboardingLead, email: str) -> StaffOnboardingLead:
    existing = StaffOnboardingLead.objects.filter(email__iexact=email).first()
    if existing:
        return existing
    phones = split_phone_field_norm(source.phone)
    phone_val = phones[0][:40] if phones else (source.phone or "")[:40]
    return StaffOnboardingLead.objects.create(
        email=email,
        phone=phone_val,
        display_name=source.display_name,
        org_display_name=source.org_display_name,
        username_suggested=source.username_suggested,
        first_name=source.first_name,
        last_name=source.last_name,
        company_legal_name=source.company_legal_name,
        company_cui=source.company_cui,
        company_cui_has_ro=source.company_cui_has_ro,
        company_address=source.company_address,
        company_reg_com=source.company_reg_com,
        company_representative=source.company_representative,
        company_judet=source.company_judet,
        company_oras=source.company_oras,
        is_public_shelter=source.is_public_shelter,
        account_kind=source.account_kind,
        collaborator_subtype=source.collaborator_subtype,
        vet_prospect_kind=source.vet_prospect_kind,
        judet=source.judet,
        oras=source.oras,
        segments=list(source.segments or []),
        marketing_emails_requested=source.marketing_emails_requested,
        status=source.status,
        notes=(source.notes or "") + f"\n[split din lead #{source.pk}]",
        created_by=source.created_by,
    )


def staff_invite_expand_lead_send_targets(lead: StaffOnboardingLead) -> list[StaffOnboardingLead]:
    """Lead cu N emailuri în câmp → N leaduri (primul rămâne pe pk original)."""
    normalize_lead_phone(lead, save=True)
    emails = split_email_field(lead.email)
    if not emails:
        return [lead]
    targets: list[StaffOnboardingLead] = []
    for i, em in enumerate(emails):
        if i == 0:
            if (lead.email or "").strip().lower() != em:
                StaffOnboardingLead.objects.filter(pk=lead.pk).update(email=em)
                lead.refresh_from_db()
            targets.append(lead)
        else:
            clone = clone_lead_for_email(lead, em)
            normalize_lead_phone(clone, save=True)
            targets.append(clone)
    return targets


def staff_invite_expand_picked_leads(leads: list[StaffOnboardingLead]) -> list[StaffOnboardingLead]:
    expanded: list[StaffOnboardingLead] = []
    seen_pks: set[int] = set()
    for lead in leads:
        for target in staff_invite_expand_lead_send_targets(lead):
            if target.pk in seen_pks:
                continue
            seen_pks.add(target.pk)
            expanded.append(target)
    return expanded
