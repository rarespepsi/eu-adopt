"""
Adopție simplă: formular + email către adăpost/proprietar.

Activare:
- EUADOPT_SIMPLE_ADOPTION=1 → forțat on (site normal, fără pre-lansare)
- EUADOPT_SIMPLE_ADOPTION=0 → forțat off (flux complet)
- gol → ca soft-lock pre-lansare (comportament vechi)

Staff/superuser: flux complet (bypass).
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from django.conf import settings
from django.core.cache import cache
from django.urls import reverse

from home.mail_helpers import adoption_pet_public_email_lines, email_subject_for_user, send_mail_text_and_html
from home.models import AnimalListing, UserProfile
from home.prelaunch_soft_lock import (
    prelaunch_soft_lock_active_for_user,
    prelaunch_soft_lock_staff_bypass,
)


def population_simple_adoption_active_for_user(user) -> bool:
    """Formular email simplu vs flux complet adopție."""
    if not user or not getattr(user, "is_authenticated", False):
        return False
    if prelaunch_soft_lock_staff_bypass(user):
        return False
    explicit = getattr(settings, "SIMPLE_ADOPTION_ENABLED", None)
    if explicit is not None:
        return bool(explicit)
    return prelaunch_soft_lock_active_for_user(user)


def _strip_ro_local_leading_zero(country: str, local: str) -> str:
    """RO +40: în casetă afișăm 740…, nu 0740… (prefixul e deja în select)."""
    loc = (local or "").strip()
    if (country or "").strip() == "+40" and loc.startswith("0") and len(loc) > 1:
        return loc[1:]
    return loc


def _parse_phone_for_form(phone_str: str | None) -> tuple[str, str]:
    if not phone_str or not isinstance(phone_str, str):
        return "+40", ""
    s = phone_str.strip()
    if not s:
        return "+40", ""
    parts = s.split(None, 1)
    if len(parts) == 2 and parts[0].startswith("+"):
        country, local = parts[0], parts[1].strip()
        return country, _strip_ro_local_leading_zero(country, local)
    for prefix in ("+40", "+39", "+33", "+49", "+44"):
        if s.startswith(prefix):
            local = s[len(prefix) :].lstrip()
            return prefix, _strip_ro_local_leading_zero(prefix, local)
    if s.startswith("0"):
        return "+40", s[1:]
    return "+40", s


def adoption_form_prefill_for_user(user) -> dict[str, str]:
    """Câmpuri ca la modificare profil PF (account_edit_pf)."""
    prof = UserProfile.objects.filter(user=user).first()
    phone_country, phone = _parse_phone_for_form(prof.phone if prof else "")
    return {
        "last_name": (user.last_name or "").strip(),
        "first_name": (user.first_name or "").strip(),
        "email": (user.email or "").strip(),
        "phone_country": phone_country,
        "phone": phone,
        "judet": (prof.judet if prof else "") or "",
        "oras": (prof.oras if prof else "") or "",
    }


@dataclass
class PopulationAdoptionFormData:
    last_name: str
    first_name: str
    email: str
    phone_country: str
    phone: str
    judet: str
    oras: str
    mesaj: str
    accept_termeni: bool
    accept_gdpr: bool

    @property
    def phone_display(self) -> str:
        pc = (self.phone_country or "+40").strip()
        ph = _strip_ro_local_leading_zero(pc, (self.phone or "").strip())
        if not ph:
            return "—"
        if ph.startswith("+"):
            return ph
        return f"{pc} {ph}".strip()

    def adopter_lines(self) -> list[str]:
        lines = [
            f"Nume: {self.last_name}",
            f"Prenume: {self.first_name}",
            f"Email: {self.email}",
            f"Telefon: {self.phone_display}",
            f"Județ: {self.judet}",
            f"Oraș / localitate: {self.oras}",
        ]
        if (self.mesaj or "").strip():
            lines.append(f"Mesaj: {(self.mesaj or '').strip()}")
        return lines


def parse_population_adoption_form(post) -> tuple[PopulationAdoptionFormData | None, list[str]]:
    from home.ro_location import normalize_location_pair

    data = PopulationAdoptionFormData(
        last_name=(post.get("last_name") or "").strip(),
        first_name=(post.get("first_name") or "").strip(),
        email=(post.get("email") or "").strip().lower(),
        phone_country=(post.get("phone_country") or "+40").strip(),
        phone=_strip_ro_local_leading_zero(
            (post.get("phone_country") or "+40").strip(),
            (post.get("phone") or "").strip(),
        ),
        judet=(post.get("judet") or "").strip(),
        oras=(post.get("oras") or "").strip(),
        mesaj=(post.get("mesaj") or "").strip(),
        accept_termeni=post.get("accept_termeni") == "on",
        accept_gdpr=post.get("accept_gdpr") == "on",
    )
    data.judet, data.oras = normalize_location_pair(data.judet, data.oras)

    errors: list[str] = []
    if not data.last_name:
        errors.append("Numele este obligatoriu.")
    if not data.first_name:
        errors.append("Prenumele este obligatoriu.")
    if not data.email:
        errors.append("Emailul este obligatoriu.")
    if not data.phone:
        errors.append("Telefonul este obligatoriu.")
    if not data.judet:
        errors.append("Județul este obligatoriu.")
    if not data.oras:
        errors.append("Orașul / localitatea este obligatoriu.")
    if not data.accept_termeni:
        errors.append("Trebuie să accepți Termenii și condițiile.")
    if not data.accept_gdpr:
        errors.append("Trebuie să accepți Politica de confidențialitate (GDPR).")
    if len(data.mesaj) > 2000:
        errors.append("Mesajul este prea lung (max. 2000 caractere).")

    if errors:
        return None, errors
    return data, []


def _population_adopt_cache_key(user_id: int, pet_id: int) -> str:
    return f"pop_simple_adopt:{user_id}:{pet_id}"


def population_adoption_recently_sent(user_id: int, pet_id: int) -> bool:
    return bool(cache.get(_population_adopt_cache_key(user_id, pet_id)))


def _mark_population_adoption_sent(user_id: int, pet_id: int) -> None:
    cache.set(_population_adopt_cache_key(user_id, pet_id), 1, timeout=86400)


def send_population_adoption_emails(
    *,
    pet: AnimalListing,
    adopter_user,
    form: PopulationAdoptionFormData,
) -> tuple[bool, str]:
    """
    Trimite email proprietar + copie adoptator. Returnează (ok, error_message).
    """
    owner = pet.owner
    owner_email = (getattr(owner, "email", None) or "").strip()
    adopter_email = (form.email or "").strip()
    if not owner_email:
        return False, "Proprietarul anunțului nu are email configurat. Contactați EU-Adopt."
    if not adopter_email:
        return False, "Emailul este obligatoriu."

    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        pet_path = reverse("pets_single", args=[pet.pk])
    except Exception:
        pet_path = f"/pets/{pet.pk}/"
    pet_link = f"{site_base}{pet_path}" if site_base else pet_path
    pet_lines = adoption_pet_public_email_lines(pet)
    adopter_lines = form.adopter_lines()

    sub_owner = f"EU-Adopt: cerere de adopție pentru {pet_label} (etapă populare)"
    body_owner = (
        "Bună ziua,\n\n"
        f"Ați primit o cerere de adopție prin formularul EU-Adopt (etapa de populare) "
        f"pentru „{pet_label}”.\n\n"
        "DETALII ANIMAL:\n"
        + "\n".join(f"- {line}" for line in pet_lines)
        + "\n\n"
        "SOLICITANT:\n"
        + "\n".join(f"- {line}" for line in adopter_lines)
        + f"\n\nLink fișă animal: {pet_link}\n\n"
        "Contactați direct solicitantul pentru următorii pași.\n\n"
        "— EU-Adopt\n"
    )
    html_owner = (
        "<p>Bună ziua,</p>"
        f"<p>Ați primit o <strong>cerere de adopție</strong> prin formularul EU-Adopt "
        f"(etapa de populare) pentru <strong>{pet_label}</strong>.</p>"
        "<p><strong>Detalii animal</strong></p><ul>"
        + "".join(f"<li>{line}</li>" for line in pet_lines)
        + "</ul><p><strong>Solicitant</strong></p><ul>"
        + "".join(f"<li>{line}</li>" for line in adopter_lines)
        + f"</ul><p>Link fișă animal: <a href=\"{pet_link}\">{pet_link}</a></p>"
        "<p>Contactați direct solicitantul pentru următorii pași.</p>"
        "<p>— EU-Adopt</p>"
    )

    sub_adopter = f"EU-Adopt: cererea ta de adopție pentru {pet_label} a fost trimisă"
    body_adopter = (
        f"Bună ziua, {form.first_name} {form.last_name},\n\n"
        f"Am trimis cererea ta de adopție către proprietarul / adăpostul pentru „{pet_label}”.\n\n"
        "Rezumat animal:\n"
        + "\n".join(f"- {line}" for line in pet_lines)
        + f"\n\nFișă: {pet_link}\n\n"
        "Proprietarul te va contacta direct.\n\n"
        "— EU-Adopt\n"
    )
    html_adopter = (
        f"<p>Bună ziua, <strong>{form.first_name} {form.last_name}</strong>,</p>"
        f"<p>Am trimis cererea ta de adopție către proprietarul / adăpostul pentru "
        f"<strong>{pet_label}</strong>.</p>"
        "<p><strong>Rezumat animal</strong></p><ul>"
        + "".join(f"<li>{line}</li>" for line in pet_lines)
        + f"</ul><p>Fișă: <a href=\"{pet_link}\">{pet_link}</a></p>"
        "<p>Proprietarul te va contacta direct.</p>"
        "<p>— EU-Adopt</p>"
    )

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail_text_and_html(
            email_subject_for_user(owner.username, sub_owner),
            body_owner,
            from_email,
            [owner_email],
            html_owner,
            mail_kind="population_adoption_owner",
        )
        send_mail_text_and_html(
            email_subject_for_user(adopter_user.username, sub_adopter),
            body_adopter,
            from_email,
            [adopter_email],
            html_adopter,
            mail_kind="population_adoption_adopter",
        )
    except Exception:
        import logging

        logging.getLogger(__name__).exception(
            "population_adoption_email failed pet=%s adopter=%s",
            pet.pk,
            adopter_user.pk,
        )
        return False, "Nu am putut trimite emailul. Încercați din nou sau contactați EU-Adopt."

    _mark_population_adoption_sent(adopter_user.pk, pet.pk)
    return True, ""


def population_adoption_context_for_request(request) -> dict[str, Any]:
    user = getattr(request, "user", None)
    active = bool(user and user.is_authenticated and population_simple_adoption_active_for_user(user))
    ctx: dict[str, Any] = {
        "pet_adopt_simple_populare": active,
        "pet_adopt_inactive_populare": False,
        "pet_adopt_inactive_message": "",
    }
    if active:
        ctx["pet_adopt_form_prefill"] = adoption_form_prefill_for_user(user)
    return ctx
