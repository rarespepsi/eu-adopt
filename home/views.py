"""
Home views. Layout HOME înghețat: v. HOME_SLOTS.md
A0=navbar, A1=hero, A2=grid 4×3, A3=mission bar, A4=footer, A5=left sidebar (3), A6=right sidebar (3).
REGULĂ: Orice modificare în home (punct, virgulă, orice) doar cu aprobarea titularului, cu parolă.
"""
import json
import hashlib
import logging
from urllib.parse import quote, urlencode, urlparse, parse_qs
import random
import re
import secrets
import uuid
from html import escape
from datetime import date, datetime
from copy import deepcopy
from itertools import cycle
from django.shortcuts import render, redirect, get_object_or_404
from django.template.loader import render_to_string
from django.urls import reverse
from django.utils import timezone
from django.http import HttpResponse, JsonResponse
from django.db.models import Case, Count, Exists, IntegerField, Max, OuterRef, Q, Subquery, Sum, When
from django.db.models import F
from django.db.models.functions import TruncMonth
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from django.core.mail import send_mail, EmailMessage
from decimal import Decimal
from django.db import transaction
import math
import os
from django.views.decorators.http import require_POST, require_http_methods
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.contrib.auth.views import redirect_to_login
from django.views.decorators.csrf import csrf_protect
from .data import DEMO_DOGS, DEMO_DOG_IMAGE, A2_QUOTE_POOL, HERO_SLIDER_IMAGES
from .pet_age_bands import (
    AGE_LABELS_ORDERED,
    BAND_CHOICES_UI,
    BAND_FILTER_GET_VALUES,
    animal_listing_matches_collab_offer_targets,
    build_age_band_filter_q,
)
from .pt_p2_list import PT_P2_PAGE_SIZE, pt_pets_page_context
from .mail_helpers import email_subject_for_user, send_mail_text_and_html
from .context_processors import get_navbar_unread_counts
from . import inbox_notifications as _inbox
from .models import (
    WishlistItem,
    SiteCartItem,
    SiteCartCheckoutIntent,
    AnimalListing,
    UserAdoption,
    AccountProfile,
    UserProfile,
    UserLegalConsent,
    ContactMessage,
    PetMessage,
    CollabServiceMessage,
    AdoptionRequest,
    AdoptionBonusSelection,
    CollaboratorServiceOffer,
    CollaboratorOfferClaim,
    PromoA2Order,
    ReclamaSlotNote,
    PublicitateOrder,
    PublicitateOrderLine,
    PublicitateOrderCreativeAccess,
    PublicitateLineCreative,
    TransportVeterinaryRequest,
    TransportOperatorProfile,
    TransportDispatchJob,
    TransportDispatchRecipient,
    TransportTripRating,
    UserInboxNotification,
)
from django.contrib.auth import get_user_model
from functools import wraps
from django.contrib import messages
from django.core.signing import TimestampSigner, SignatureExpired, BadSignature

LEGAL_TERMS_VERSION = "1.0"
LEGAL_PRIVACY_VERSION = "1.0"
LEGAL_MARKETING_VERSION = "1.0"


def _user_can_use_mypet(request):
    """
    MyPet + inbox mesaje din navbar: doar PF și ONG/SRL (postează câini spre adopție).
    Colaboratorii (servicii / produse) nu au acces. Staff: da, mai puțin „Vezi ca colaborator”.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        va = request.session.get("view_as_role")
        if va == "collaborator":
            return False
        return True
    try:
        ap = getattr(user, "account_profile", None)
        if not ap:
            return False
        if ap.role == AccountProfile.ROLE_COLLAB:
            return False
        return ap.role in (AccountProfile.ROLE_PF, AccountProfile.ROLE_ORG)
    except Exception:
        return False


def _mypet_access_redirect(request):
    messages.info(
        request,
        "MyPet este pentru persoane fizice și organizații (ONG / firmă) care publică anunțuri de adopție.",
    )
    return redirect("home")


def mypet_pf_org_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _user_can_use_mypet(request):
            return _mypet_access_redirect(request)
        return view_func(request, *args, **kwargs)
    return _wrapped


def mypet_pf_org_required_json(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _user_can_use_mypet(request):
            return JsonResponse(
                {"ok": False, "error": "MyPet este doar pentru conturi PF și ONG/SRL."},
                status=403,
            )
        return view_func(request, *args, **kwargs)
    return _wrapped


def _client_ip(request) -> str:
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip()[:64]
    return (request.META.get("REMOTE_ADDR") or "")[:64]


def _log_legal_consents(
    request,
    user,
    *,
    accept_termeni: bool,
    accept_gdpr: bool,
    email_opt_in: bool,
    source: str,
    previous: dict | None = None,
):
    """
    Audit trail pentru consimțăminte legale.
    Înregistrează doar schimbările față de `previous` (dacă este furnizat).
    """
    previous = previous or {}
    current = {
        UserLegalConsent.CONSENT_TERMS: bool(accept_termeni),
        UserLegalConsent.CONSENT_PRIVACY: bool(accept_gdpr),
        UserLegalConsent.CONSENT_MARKETING: bool(email_opt_in),
    }
    versions = {
        UserLegalConsent.CONSENT_TERMS: LEGAL_TERMS_VERSION,
        UserLegalConsent.CONSENT_PRIVACY: LEGAL_PRIVACY_VERSION,
        UserLegalConsent.CONSENT_MARKETING: LEGAL_MARKETING_VERSION,
    }
    ip = _client_ip(request)
    ua = (request.META.get("HTTP_USER_AGENT") or "")[:500]

    rows = []
    for consent_type, accepted in current.items():
        if consent_type in previous and bool(previous.get(consent_type)) == accepted:
            continue
        rows.append(
            UserLegalConsent(
                user=user,
                consent_type=consent_type,
                accepted=accepted,
                version=versions[consent_type],
                source=source,
                ip_address=ip,
                user_agent=ua,
            )
        )
    if rows:
        UserLegalConsent.objects.bulk_create(rows)


def _user_can_use_magazinul_meu(request):
    """
    Pagina Magazinul meu / My transport: colaboratori (cabinet / servicii / magazin / transport).
    Staff: „Vezi ca colaborator” sau cont real cu rol colaborator (ex. admin + transportator).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    try:
        ap = getattr(user, "account_profile", None)
        real_collab = bool(ap and ap.role == AccountProfile.ROLE_COLLAB)
    except Exception:
        real_collab = False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        if request.session.get("view_as_role") == "collaborator":
            return True
        return real_collab
    return real_collab


def _magazinul_meu_access_redirect(request):
    messages.info(
        request,
        "Magazinul meu este pentru conturi colaborator (cabinet / servicii / magazin).",
    )
    return redirect("home")


def collab_magazin_required(view_func):
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not _user_can_use_magazinul_meu(request):
            return _magazinul_meu_access_redirect(request)
        return view_func(request, *args, **kwargs)
    return _wrapped


def _user_has_published_animals(user) -> bool:
    """True dacă userul are cel puțin un AnimalListing publicat (proprietar)."""
    if not getattr(user, "pk", None):
        return False
    return AnimalListing.objects.filter(owner_id=user.pk, is_published=True).exists()


def _promo_a2_nav_context(user) -> dict:
    """
    Link + etichete pentru ieșirea din fluxul promovare A2:
    - cu animale postate → MyPet
    - fără → Prietenul tău (PT / pets_all)
    """
    if _user_has_published_animals(user):
        return {
            "promo_flow_exit_url": reverse("mypet"),
            "promo_flow_exit_label": "Înapoi la MyPet",
            "promo_flow_done_label": "Mergi la MyPet",
        }
    return {
        "promo_flow_exit_url": reverse("pets_all"),
        "promo_flow_exit_label": "Înapoi la Prietenul tău",
        "promo_flow_done_label": "Mergi la Prietenul tău",
    }


def _promo_a2_flow_redirect(request, pet: AnimalListing):
    """După respingere în fluxul promovare A2: cu anunțuri publicate → MyPet, altfel → PT."""
    if _user_has_published_animals(request.user):
        return redirect("mypet")
    return redirect("pets_all")


HOME_BURTIERA_DEFAULT_TEXT = (
    "#EuAdopt #NuCumpar – EU-Adopt este o inițiativă independentă pentru promovarea adopției "
    "animalelor. Acest proiect nu este afiliat, finanțat sau administrat de Uniunea Europeană."
)
HOME_BURTIERA_DEFAULT_SPEED_SECONDS = 28


def _get_home_burtiera_text() -> str:
    note = ReclamaSlotNote.objects.filter(section="home", slot_code="Burtieră").first()
    txt = (note.text if note else "") or ""
    txt = txt.strip()
    return txt or HOME_BURTIERA_DEFAULT_TEXT


def _get_home_burtiera_speed_seconds() -> int:
    note = ReclamaSlotNote.objects.filter(section="home", slot_code="BurtierăSpeed").first()
    raw = ((note.text if note else "") or "").strip()
    try:
        sec = int(raw)
    except (TypeError, ValueError):
        sec = HOME_BURTIERA_DEFAULT_SPEED_SECONDS
    return max(8, min(120, sec))


def _promo_a2_order_hours(package: str) -> int:
    return 12 if (package or "").strip().lower() == "12h" else 6


def _promo_a2_compute_window(start_date, package: str, quantity: int):
    qty = max(1, int(quantity or 1))
    hours = _promo_a2_order_hours(package)
    starts_at = timezone.make_aware(datetime.combine(start_date, datetime.min.time()))
    ends_at = starts_at + timezone.timedelta(hours=hours * qty)
    return starts_at, ends_at


def _promo_a2_build_summary_payload(order: PromoA2Order) -> dict:
    pet = getattr(order, "pet", None)
    pet_label = (getattr(pet, "name", None) or f"Anunț #{getattr(order, 'pet_id', '-')}")
    pet_url = ""
    if pet and getattr(pet, "is_published", False):
        try:
            path = reverse("pets_single", args=[pet.pk])
            base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
            pet_url = f"{base}{path}" if base else path
        except Exception:
            pet_url = ""
    starts = timezone.localtime(order.starts_at) if order.starts_at else None
    ends = timezone.localtime(order.ends_at) if order.ends_at else None
    return {
        "pet_label": pet_label,
        "pet_url": pet_url,
        "package": order.package or "6h",
        "quantity": int(order.quantity or 1),
        "unit_price": int(order.unit_price or 0),
        "total_price": int(order.total_price or 0),
        "starts_at": starts,
        "ends_at": ends,
        "schedule": order.schedule or "intercalat",
    }


def _promo_a2_send_summary_email(order: PromoA2Order) -> bool:
    to = (order.payer_email or "").strip()
    if not to:
        return False
    p = _promo_a2_build_summary_payload(order)
    starts_txt = p["starts_at"].strftime("%d.%m.%Y %H:%M") if p["starts_at"] else "—"
    ends_txt = p["ends_at"].strftime("%d.%m.%Y %H:%M") if p["ends_at"] else "—"
    uname = None
    try:
        if order.payer_user_id and order.payer_user:
            uname = order.payer_user.username
    except Exception:
        uname = None
    if not uname and to:
        uname = (to.split("@", 1)[0] if "@" in to else None) or "oaspete"
    subj = email_subject_for_user(
        uname,
        f"EU-Adopt: rezumat final promovare A2 – {p['pet_label']}",
    )
    body = (
        f"Bună,\n\n"
        f"S-a încheiat perioada cumpărată pentru promovarea A2.\n\n"
        f"Detalii comandă:\n"
        f"- Anunț: {p['pet_label']}\n"
        f"- Pachet: {p['package']}\n"
        f"- Cantitate: {p['quantity']}\n"
        f"- Programare: {p['schedule']}\n"
        f"- Perioadă afișare: {starts_txt} → {ends_txt}\n"
        f"- Preț unitar: {p['unit_price']} lei\n"
        f"- Total achitat: {p['total_price']} lei\n"
    )
    if p["pet_url"]:
        body += f"- Link anunț: {p['pet_url']}\n"
    body += "\nMulțumim!\n— Aplicația EU-Adopt\n"
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    send_mail(subj, body, from_email, [to], fail_silently=False)
    return True


def _collaborator_tip_partener(request) -> str:
    """
    Valoare din înregistrare colaborator (tip_partener): cabinet | servicii | magazin | transport.
    Cabinet și servicii folosesc același template; magazin are pagină separată (produse).
    Transport: panou dedicat, fără oferte S3/S4/S5.
    Pentru staff cu „Vezi ca colaborator”, tipul vine din sesiune (preview Magazinul meu).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return "servicii"
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        if request.session.get("view_as_role") == "collaborator":
            st = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
            if st in ("cabinet", "servicii", "magazin", "transport"):
                return st
            return "servicii"
    try:
        prof = getattr(user, "profile", None)
        tip = (getattr(prof, "collaborator_type", None) or "").strip().lower()
    except Exception:
        tip = ""
    if tip in ("cabinet", "servicii", "magazin", "transport"):
        return tip
    return "servicii"


def _phone_digits(phone_str):
    """Returnează doar cifrele din număr (pentru comparatie unicitate)."""
    if not phone_str:
        return ""
    return "".join(c for c in str(phone_str) if c.isdigit())


def _phone_normalize_for_compare(digits):
    """Normalizează cifrele pentru comparare: 0753017424 (10 cifre) = 753017424 (9 cifre) = 40753017424 (prefix RO)."""
    if not digits or len(digits) < 9:
        return digits
    # România: 10 cifre începând cu 0 → 40 + 9 cifre
    if len(digits) == 10 and digits[0] == "0":
        return "40" + digits[1:]
    # 9 cifre începând cu 6 sau 7 → același 40 + 9 cifre (ca 0xxxxxxxx)
    if len(digits) == 9 and digits[0] in "67":
        return "40" + digits
    return digits


def _phone_already_used(phone_input):
    """True dacă există deja un UserProfile cu același număr (comparat pe cifre normalizate)."""
    norm = _phone_normalize_for_compare(_phone_digits(phone_input))
    if not norm:
        return False
    for p in UserProfile.objects.exclude(phone="").exclude(phone__isnull=True):
        other = _phone_normalize_for_compare(_phone_digits(p.phone))
        if other and other == norm:
            return True
    return False


def _email_duplicate_blocked(email, *, exclude_user_pk=None):
    """
    True dacă emailul e deja folosit de alt cont (unicitate la nivel de aplicație).
    Dezactivare temporară (doar dev/QA): setează EUADOPT_RELAX_EMAIL_UNIQUE=1 în `.env`.
    """
    if getattr(settings, "EUADOPT_RELAX_EMAIL_UNIQUE", False):
        return False
    em = (email or "").strip()
    if not em:
        return False
    User = get_user_model()
    qs = User.objects.filter(email__iexact=em)
    if exclude_user_pk is not None:
        qs = qs.exclude(pk=exclude_user_pk)
    return qs.exists()


# A2 selection: 12 dogs. New (added in last 24h) first, then fill randomly from PT. Never empty if any available.
A2_SLOT_COUNT = 12
A2_NEW_HOURS = 24
MESSAGE_ARCHIVE_DAYS = 30
MESSAGE_DELETE_DAYS = 180


def _messages_active_since():
    """
    Mesaje active în inbox:
    - arhivate logic după 30 zile (nu apar în notele active)
    - șterse definitiv după 180 zile
    """
    now = timezone.now()
    delete_before = now - timezone.timedelta(days=MESSAGE_DELETE_DAYS)
    try:
        PetMessage.objects.filter(created_at__lt=delete_before).delete()
    except Exception:
        pass
    try:
        CollabServiceMessage.objects.filter(created_at__lt=delete_before).delete()
    except Exception:
        pass
    return now - timezone.timedelta(days=MESSAGE_ARCHIVE_DAYS)


def _adopter_messaging_allowed(pet, user) -> bool:
    """
    Mesaje libere din fișă către owner (hibrid): același criteriu ca pe fișa publică —
    utilizator autentificat, nu proprietarul, poate adopta, anunț publicat, animal nu e deja adoptat.
    """
    if not user or not user.is_authenticated:
        return False
    if pet.owner_id == user.id:
        return False
    if not getattr(pet, "is_published", True):
        return False
    if (pet.adoption_state or "").strip() == AnimalListing.ADOPTION_STATE_ADOPTED:
        return False
    ap = getattr(user, "account_profile", None)
    if ap and not ap.can_adopt_animals:
        return False
    return True


def _adoption_state_label(state: str) -> str:
    mapping = {
        AnimalListing.ADOPTION_STATE_FREE: "Liber",
        AnimalListing.ADOPTION_STATE_OPEN: "Spre adopție",
        AnimalListing.ADOPTION_STATE_IN_PROGRESS: "În curs de adopție",
        AnimalListing.ADOPTION_STATE_ADOPTED: "Adoptat",
    }
    return mapping.get((state or "").strip(), "Liber")


def _sync_animal_adoption_state(animal: AnimalListing) -> str:
    """
    Sincronizează starea animalului după stările cererilor de adopție.
    Prioritate: finalizată > acceptată > în așteptare > liber.
    """
    now = timezone.now()
    changed = False
    for req in AdoptionRequest.objects.filter(animal=animal, status=AdoptionRequest.STATUS_ACCEPTED):
        if req.accepted_expires_at and req.accepted_expires_at < now:
            req.status = AdoptionRequest.STATUS_EXPIRED
            req.save(update_fields=["status", "updated_at"])
            changed = True
    if changed:
        animal.refresh_from_db(fields=["id"])

    if AdoptionRequest.objects.filter(animal=animal, status=AdoptionRequest.STATUS_FINALIZED).exists():
        target = AnimalListing.ADOPTION_STATE_ADOPTED
    elif AdoptionRequest.objects.filter(animal=animal, status=AdoptionRequest.STATUS_ACCEPTED).exists():
        target = AnimalListing.ADOPTION_STATE_IN_PROGRESS
    elif AdoptionRequest.objects.filter(animal=animal, status=AdoptionRequest.STATUS_PENDING).exists():
        target = AnimalListing.ADOPTION_STATE_OPEN
    else:
        target = AnimalListing.ADOPTION_STATE_FREE

    if animal.adoption_state != target:
        animal.adoption_state = target
        animal.save(update_fields=["adoption_state", "updated_at"])
    return target


def _adoption_contact_block(user):
    """Text pentru email: date cont + profil (fără HTML)."""
    lines = []
    name = (f"{user.first_name} {user.last_name}").strip() or user.username
    lines.append(f"Nume: {name}")
    lines.append(f"Email: {user.email or '—'}")
    prof = UserProfile.objects.filter(user=user).first()
    ap = getattr(user, "account_profile", None)
    role_label = ""
    if ap:
        if ap.role == AccountProfile.ROLE_ORG:
            role_label = "ONG / organizație / firmă"
            if prof:
                dn = (prof.company_display_name or prof.company_legal_name or "").strip()
                if dn:
                    lines.append(f"Organizație: {dn}")
                if prof.company_address:
                    lines.append(f"Adresă: {prof.company_address}")
                jc = ", ".join(x for x in (prof.company_judet, prof.company_oras) if x)
                if jc:
                    lines.append(f"Județ / Oraș (firmă): {jc}")
                if prof.company_cui:
                    cui = ("RO " if prof.company_cui_has_ro else "") + prof.company_cui
                    lines.append(f"CUI: {cui}")
        elif ap.role == AccountProfile.ROLE_COLLAB:
            role_label = "Colaborator"
        else:
            role_label = "Persoană fizică"
    if role_label:
        lines.insert(1, f"Tip cont: {role_label}")
    if prof:
        if prof.phone:
            lines.append(f"Telefon: {prof.phone}")
        if ap and ap.role == AccountProfile.ROLE_PF:
            loc = ", ".join(x for x in (prof.judet, prof.oras) if x)
            if loc:
                lines.append(f"Județ / Oraș: {loc}")
    return "\n".join(lines)


def _send_adoption_accept_emails(ar: AdoptionRequest):
    """
    După accept: owner primește date adoptator; adoptator primește date owner
    + rezumat oferte Servicii bifate pentru bonus (fără coduri — acestea la finalizare în MyPet).
    """
    pet = ar.animal
    owner = pet.owner
    adopter = ar.adopter
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    bonus_txt, bonus_html = _adoption_bonus_selection_summary(ar)
    sub_owner = f"EU-Adopt: datele adoptatorului – {pet_label}"
    sub_adopter = f"EU-Adopt: date de contact pentru {pet_label}"
    body_owner = (
        f"Bună ziua,\n\n"
        f"Ai acceptat cererea de adopție pentru „{pet_label}”.\n\n"
        f"Date adoptator (discutați direct):\n"
        f"---\n{_adoption_contact_block(adopter)}\n---\n\n"
        f"Aplicația EU-Adopt\n"
    )
    body_adopter = (
        f"Bună ziua,\n\n"
        f"Cererea ta de adopție pentru „{pet_label}” a fost acceptată.\n\n"
        f"Date organizație / proprietar (discutați direct):\n"
        f"---\n{_adoption_contact_block(owner)}\n---\n\n"
        + (f"{bonus_txt}\n\n" if bonus_txt else "")
        + f"Aplicația EU-Adopt\n"
    )
    html_owner = (
        f"<p>Bună ziua,</p>"
        f"<p>Ai acceptat cererea de adopție pentru <strong>{escape(pet_label)}</strong>.</p>"
        f"<p><strong>Date adoptator</strong> (discutați direct):</p>"
        f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(_adoption_contact_block(adopter))}</pre>"
        f"<p>Aplicația EU-Adopt</p>"
    )
    html_adopter = (
        f"<p>Bună ziua,</p>"
        f"<p>Cererea ta de adopție pentru <strong>{escape(pet_label)}</strong> a fost <strong>acceptată</strong>.</p>"
        f"<p><strong>Date proprietar / organizație</strong> (discutați direct):</p>"
        f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(_adoption_contact_block(owner))}</pre>"
        + (bonus_html or "")
        + "<p>Aplicația EU-Adopt</p>"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        if owner.email:
            send_mail_text_and_html(
                email_subject_for_user(owner.username, sub_owner),
                body_owner,
                from_email,
                [owner.email],
                html_owner,
                mail_kind="adoption_accept_owner",
            )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_accept_email_owner: %s", exc)
    try:
        if adopter.email:
            send_mail_text_and_html(
                email_subject_for_user(adopter.username, sub_adopter),
                body_adopter,
                from_email,
                [adopter.email],
                html_adopter,
                mail_kind="adoption_accept_adopter",
            )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_accept_email_adopter: %s", exc)


def _adoption_pet_public_email_lines(pet: AnimalListing):
    """Rezumat din fișă (date publice din anunț) pentru email către adoptator la cerere nouă."""
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


def _send_adoption_request_adopter_email(ar: AdoptionRequest):
    """Adoptator: confirmare cerere + rezumat animal + link către fișa publică."""
    pet = ar.animal
    adopter = ar.adopter
    if not adopter.email:
        return
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        pet_path = reverse("pets_single", args=[pet.pk])
    except Exception:
        pet_path = f"/pets/{pet.pk}/"
    pet_link = f"{site_base}{pet_path}" if site_base else pet_path

    summary_lines = _adoption_pet_public_email_lines(pet)
    summary_txt = "\n".join(summary_lines)

    sub = f"EU-Adopt: cererea ta de adopție pentru {pet_label}"
    body = (
        f"Bună ziua,\n\n"
        f"Am înregistrat cererea ta de adopție pentru „{pet_label}”.\n"
        f"Proprietarul sau organizația au fost notificați; îți vor răspunde prin EU-Adopt "
        f"(MyPet / email) când se ia o decizie.\n\n"
        f"Date din anunț:\n"
        f"---\n{summary_txt}\n---\n\n"
        f"Pagina animalului (detalii complete): {pet_link}\n\n"
        f"Aplicația EU-Adopt\n"
    )
    items_html = "".join(f"<li>{escape(line)}</li>" for line in summary_lines)
    html_body = (
        f"<p>Bună ziua,</p>"
        f"<p>Am înregistrat cererea ta de adopție pentru <strong>{escape(pet_label)}</strong>.</p>"
        f"<p>Proprietarul sau organizația au fost notificați; îți vor răspunde prin EU-Adopt "
        f"(MyPet / email) când se ia o decizie.</p>"
        f"<p><strong>Date din anunț:</strong></p>"
        f"<ul style=\"margin:0 0 1em 1.1em;padding:0;\">{items_html}</ul>"
        f"<p>Pagina animalului (detalii complete): "
        f"<a href=\"{escape(pet_link)}\">{escape(pet_link)}</a></p>"
        f"<p>Aplicația EU-Adopt</p>"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail_text_and_html(
            email_subject_for_user(adopter.username, sub),
            body,
            from_email,
            [adopter.email],
            html_body,
            mail_kind="adoption_request_adopter",
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_request_email_adopter: %s", exc)


def _send_adoption_request_owner_email(ar: AdoptionRequest):
    """Owner primește notificare pentru cerere nouă + link către MyPet (accept/respinge din email)."""
    pet = ar.animal
    owner = pet.owner
    adopter = ar.adopter
    owner_to = (getattr(owner, "email", None) or "").strip()
    if not owner_to:
        logging.getLogger(__name__).warning(
            "adoption_request_owner_email skipped: owner has no email (user_id=%s username=%s ar_id=%s). "
            "Completează câmpul E-mail în contul Django / admin pentru a primi linkurile Accept/Respinge.",
            owner.pk,
            owner.username,
            ar.pk,
        )
        return
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    adopter_name = (f"{adopter.first_name} {adopter.last_name}").strip() or adopter.username
    mypet_link = ""
    try:
        mypet_link = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/") + reverse("mypet")
    except Exception:
        mypet_link = reverse("mypet")
    signer = TimestampSigner(salt="adoption-owner-email-v1")
    token = signer.sign(f"{ar.pk}:{owner.pk}")
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        decide_path = reverse("adoption_email_owner_action")
        accept_path = f"{decide_path}?{urlencode({'t': token, 'd': 'accept'})}"
        reject_path = f"{decide_path}?{urlencode({'t': token, 'd': 'reject'})}"
    except Exception:
        accept_path = f"/adoption/email/d/?{urlencode({'t': token, 'd': 'accept'})}"
        reject_path = f"/adoption/email/d/?{urlencode({'t': token, 'd': 'reject'})}"
    accept_link = f"{site_base}{accept_path}" if site_base else accept_path
    reject_link = f"{site_base}{reject_path}" if site_base else reject_path

    sub = f"EU-Adopt: cerere nouă de adopție pentru {pet_label}"
    body = (
        f"Bună ziua,\n\n"
        f"Aveți o cerere de adopție pentru „{pet_label}”, de la utilizatorul {adopter_name}.\n\n"
        f"Alegeți una dintre acțiuni:\n"
        f"- Acceptă cererea: {accept_link}\n"
        f"- Respinge cererea: {reject_link}\n\n"
        f"Dacă ați apăsat greșit, deschideți celălalt link (acesta inversează decizia).\n"
        f"Sau gestionați manual din MyPet: {mypet_link}\n\n"
        f"Aplicația EU-Adopt\n"
    )
    html_body = (
        f"<p>Bună ziua,</p>"
        f"<p>Aveți o cerere de adopție pentru <strong>{pet_label}</strong>, de la utilizatorul <strong>{adopter_name}</strong>.</p>"
        f"<p>"
        f"<a href=\"{accept_link}\" style=\"display:inline-block;padding:10px 14px;border-radius:8px;background:#2e7d32;color:#fff;text-decoration:none;font-weight:700;margin-right:8px;\">Acceptă cererea</a>"
        f"<a href=\"{reject_link}\" style=\"display:inline-block;padding:10px 14px;border-radius:8px;background:#fff;color:#b71c1c;border:1px solid #b71c1c;text-decoration:none;font-weight:700;\">Respinge cererea</a>"
        f"</p>"
        f"<p style=\"font-size:13px;color:#555;\">Dacă ați apăsat greșit, deschideți celălalt buton pentru a inversa decizia.</p>"
        f"<p>Gestionare completă în MyPet: <a href=\"{mypet_link}\">{mypet_link}</a></p>"
        f"<p>Aplicația EU-Adopt</p>"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail_text_and_html(
            email_subject_for_user(owner.username, sub),
            body,
            from_email,
            [owner_to],
            html_body,
            mail_kind="adoption_request_owner",
        )
    except Exception as exc:
        logging.getLogger(__name__).exception(
            "adoption_request_email_owner: ar_id=%s owner_id=%s to=%s err=%s",
            ar.pk,
            owner.pk,
            owner_to,
            exc,
        )


def _send_adoption_pending_owner_reminder_email(ar: AdoptionRequest, *, variant: str) -> bool:
    """
    Reminder proprietar: cerere de adopție încă în așteptare (Accept/Respinge).
    variant: '24h' | '72h'. Returnează True dacă emailul a fost trimis cu succes.
    """
    if variant not in ("24h", "72h"):
        raise ValueError(variant)
    pet = ar.animal
    owner = pet.owner
    owner_to = (getattr(owner, "email", None) or "").strip()
    if not owner_to:
        logging.getLogger(__name__).warning(
            "adoption_pending_owner_reminder skipped: owner has no email (ar_id=%s)",
            ar.pk,
        )
        return False
    adopter = ar.adopter
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    adopter_name = (f"{adopter.first_name} {adopter.last_name}").strip() or adopter.username
    mypet_link = ""
    try:
        mypet_link = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/") + reverse("mypet")
    except Exception:
        mypet_link = reverse("mypet")
    signer = TimestampSigner(salt="adoption-owner-email-v1")
    token = signer.sign(f"{ar.pk}:{owner.pk}")
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        decide_path = reverse("adoption_email_owner_action")
        accept_path = f"{decide_path}?{urlencode({'t': token, 'd': 'accept'})}"
        reject_path = f"{decide_path}?{urlencode({'t': token, 'd': 'reject'})}"
    except Exception:
        accept_path = f"/adoption/email/d/?{urlencode({'t': token, 'd': 'accept'})}"
        reject_path = f"/adoption/email/d/?{urlencode({'t': token, 'd': 'reject'})}"
    accept_link = f"{site_base}{accept_path}" if site_base else accept_path
    reject_link = f"{site_base}{reject_path}" if site_base else reject_path

    if variant == "24h":
        sub = f"EU-Adopt: reamintire – aveți o cerere de adopție pentru {pet_label}"
        intro_txt = (
            f"Aveți în continuare o cerere de adopție nerezolvată pentru „{pet_label}”, "
            f"de la utilizatorul {adopter_name}. Vă rugăm să acceptați sau să respingeți cererea în MyPet "
            f"sau din linkurile de mai jos."
        )
        intro_html = (
            f"<p>Aveți în continuare o cerere de adopție nerezolvată pentru <strong>{escape(pet_label)}</strong>, "
            f"de la utilizatorul <strong>{escape(adopter_name)}</strong>. Vă rugăm să acceptați sau să respingeți "
            f"cererea în MyPet sau din linkurile de mai jos.</p>"
        )
        mail_kind = "adoption_pending_owner_reminder_24h"
    else:
        sub = f"EU-Adopt: a doua reamintire – cerere de adopție pentru {pet_label}"
        intro_txt = (
            f"Aveți încă o cerere de adopție nerezolvată pentru „{pet_label}”, "
            f"de la utilizatorul {adopter_name}. Dacă nu răspundeți în 7 zile de la data cererii, "
            f"aceasta poate fi închisă automat (fără acceptare)."
        )
        intro_html = (
            f"<p>Aveți încă o cerere de adopție nerezolvată pentru <strong>{escape(pet_label)}</strong>, "
            f"de la <strong>{escape(adopter_name)}</strong>. Dacă nu răspundeți în 7 zile de la data cererii, "
            f"aceasta poate fi închisă automat.</p>"
        )
        mail_kind = "adoption_pending_owner_reminder_72h"

    body = (
        f"Bună ziua,\n\n"
        f"{intro_txt}\n\n"
        f"- Acceptă cererea: {accept_link}\n"
        f"- Respinge cererea: {reject_link}\n\n"
        f"Sau deschideți MyPet: {mypet_link}\n\n"
        f"Aplicația EU-Adopt\n"
    )
    html_body = (
        f"<p>Bună ziua,</p>"
        f"{intro_html}"
        f"<p>"
        f"<a href=\"{accept_link}\" style=\"display:inline-block;padding:10px 14px;border-radius:8px;background:#2e7d32;color:#fff;text-decoration:none;font-weight:700;margin-right:8px;\">Acceptă cererea</a>"
        f"<a href=\"{reject_link}\" style=\"display:inline-block;padding:10px 14px;border-radius:8px;background:#fff;color:#b71c1c;border:1px solid #b71c1c;text-decoration:none;font-weight:700;\">Respinge cererea</a>"
        f"</p>"
        f"<p>Gestionare în MyPet: <a href=\"{mypet_link}\">{mypet_link}</a></p>"
        f"<p>Aplicația EU-Adopt</p>"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail_text_and_html(
            email_subject_for_user(owner.username, sub),
            body,
            from_email,
            [owner_to],
            html_body,
            mail_kind=mail_kind,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception(
            "adoption_pending_owner_reminder: ar_id=%s variant=%s err=%s",
            ar.pk,
            variant,
            exc,
        )
        return False
    return True


def _send_adoption_reject_adopter_email(ar: AdoptionRequest, *, reason: str = "owner_reject"):
    """
    Adoptator: cerere închisă (respingere explicită, înlocuită de altă cerere acceptată sau expirată fără răspuns).
    reason: owner_reject | superseded | pending_timeout.
    """
    pet = ar.animal
    adopter = ar.adopter
    if not adopter.email:
        return
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        pets_path = reverse("pets_all")
    except Exception:
        pets_path = "/pets/"
    pets_link = f"{site_base}{pets_path}" if site_base else pets_path

    sub = "EU-Adopt: răspuns la cererea ta de adopție"
    if reason == "superseded":
        body = (
            f"Bună ziua,\n\n"
            f"Pentru „{pet_label}”, persoana sau organizația care publică anunțul a acceptat "
            f"o altă cerere de adopție. Cererea ta nu mai este activă în acest moment.\n\n"
            f"Îți mulțumim pentru interes. Îți recomandăm să verifici disponibilitatea altor animale "
            f"din zona ta pe EU-Adopt.\n\n"
            f"Pagina cu anunțuri: {pets_link}\n\n"
            f"Cu stimă,\n"
            f"Echipa EU-Adopt\n"
        )
        html_body = (
            f"<p>Bună ziua,</p>"
            f"<p>Pentru <strong>{escape(pet_label)}</strong>, persoana sau organizația care publică "
            f"anunțul a acceptat o altă cerere de adopție. Cererea ta nu mai este activă în acest moment.</p>"
            f"<p>Îți mulțumim pentru interes. Îți recomandăm să verifici disponibilitatea altor animale "
            f"din zona ta pe EU-Adopt.</p>"
            f"<p>Pagina cu anunțuri: <a href=\"{escape(pets_link)}\">{escape(pets_link)}</a></p>"
            f"<p>Cu stimă,<br/>Echipa EU-Adopt</p>"
        )
    elif reason == "pending_timeout":
        sub = "EU-Adopt: cererea ta de adopție a fost închisă automat (fără răspuns în 7 zile)"
        body = (
            f"Bună ziua,\n\n"
            f"Ne pare rău: pentru „{pet_label}”, persoana sau organizația care publică anunțul nu a "
            f"răspuns la cererea ta de adopție în termenul prevăzut (7 zile). Cererea a fost închisă automat.\n\n"
            f"Îți mulțumim pentru interes. Poți căuta alte animale disponibile pe EU-Adopt.\n\n"
            f"Pagina cu anunțuri: {pets_link}\n\n"
            f"Cu stimă,\n"
            f"Echipa EU-Adopt\n"
        )
        html_body = (
            f"<p>Bună ziua,</p>"
            f"<p>Ne pare rău: pentru <strong>{escape(pet_label)}</strong>, persoana sau organizația care publică "
            f"anunțul nu a răspuns la cererea ta de adopție în termenul prevăzut (7 zile). "
            f"Cererea a fost închisă automat.</p>"
            f"<p>Îți mulțumim pentru interes. Poți căuta alte animale disponibile pe EU-Adopt.</p>"
            f"<p>Pagina cu anunțuri: <a href=\"{escape(pets_link)}\">{escape(pets_link)}</a></p>"
            f"<p>Cu stimă,<br/>Echipa EU-Adopt</p>"
        )
    else:
        body = (
            f"Bună ziua,\n\n"
            f"Îți confirmăm că persoana sau organizația care a publicat anunțul pentru „{pet_label}” "
            f"a respins cererea ta de adopție.\n\n"
            f"Din motive obiective, cererea nu poate fi continuată în acest moment. "
            f"Decizia de a accepta sau respinge o cerere aparține în întregime utilizatorului care "
            f"gestionează animalul (inclusiv adăpost).\n\n"
            f"Îți mulțumim pentru interes. Îți recomandăm să verifici disponibilitatea altor animale "
            f"din zona ta pe EU-Adopt.\n\n"
            f"Pagina cu anunțuri: {pets_link}\n\n"
            f"Cu stimă,\n"
            f"Echipa EU-Adopt\n"
        )
        html_body = (
            f"<p>Bună ziua,</p>"
            f"<p>Îți confirmăm că persoana sau organizația care a publicat anunțul pentru "
            f"<strong>{escape(pet_label)}</strong> a respins cererea ta de adopție.</p>"
            f"<p>Din motive obiective, cererea nu poate fi continuată în acest moment. "
            f"Decizia de a accepta sau respinge o cerere aparține în întregime utilizatorului care "
            f"gestionează animalul (inclusiv adăpost).</p>"
            f"<p>Îți mulțumim pentru interes. Îți recomandăm să verifici disponibilitatea altor animale "
            f"din zona ta pe EU-Adopt.</p>"
            f"<p>Pagina cu anunțuri: <a href=\"{escape(pets_link)}\">{escape(pets_link)}</a></p>"
            f"<p>Cu stimă,<br/>Echipa EU-Adopt</p>"
        )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail(
            email_subject_for_user(adopter.username, sub),
            body,
            from_email,
            [adopter.email],
            fail_silently=False,
            html_message=html_body,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_reject_email_adopter: %s", exc)


SESSION_ADOPTION_BONUS_AR = "adoption_bonus_focus_request_id"
SESSION_ADOPTION_BONUS_CART_UNLOCK_AR = "adoption_bonus_cart_unlock_ar_id"
# După „Salvează alegerile”: afișează nota blocată o singură dată la următoarea vizită GET pe Servicii, apoi se consumă.
SESSION_ADOPTION_BONUS_SHOW_LOCKED_NOTICE_AR = "adoption_bonus_show_locked_notice_ar_id"
SITE_CART_MAX_ITEMS = 80
_ADOPTION_BONUS_CODE_ALPH = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _norm_county_str(s: str) -> str:
    t = (s or "").strip().casefold()
    return t


def _adopter_profile_county_raw(user) -> str:
    prof = UserProfile.objects.filter(user=user).first()
    if not prof:
        return ""
    return (prof.judet or "").strip() or (prof.company_judet or "").strip()


def _adopter_profile_city_raw(user) -> str:
    prof = UserProfile.objects.filter(user=user).first()
    if not prof:
        return ""
    return (prof.oras or "").strip() or (prof.company_oras or "").strip()


def _adopter_has_county_for_transport(user) -> bool:
    """Transport la adopție: afișăm opțiunea dacă userul are județ în profil (zonă cunoscută)."""
    if not getattr(user, "is_authenticated", False):
        return False
    return bool(_adopter_profile_county_raw(user).strip())


def _offer_collab_county_norm(offer: CollaboratorServiceOffer) -> str:
    try:
        pr = offer.collaborator.profile
        raw = (pr.company_judet or "").strip() or (pr.judet or "").strip()
        return _norm_county_str(raw)
    except UserProfile.DoesNotExist:
        return ""


def _resolve_adoption_bonus_request(user, session) -> AdoptionRequest | None:
    fid = session.get(SESSION_ADOPTION_BONUS_AR)
    if fid:
        try:
            pk = int(fid)
        except (TypeError, ValueError):
            pk = 0
        if pk:
            ar = AdoptionRequest.objects.filter(
                pk=pk,
                adopter=user,
                status__in=(
                    AdoptionRequest.STATUS_PENDING,
                    AdoptionRequest.STATUS_ACCEPTED,
                ),
            ).first()
            if ar:
                return ar
    qs = (
        AdoptionRequest.objects.filter(
            adopter=user,
            status__in=(
                AdoptionRequest.STATUS_PENDING,
                AdoptionRequest.STATUS_ACCEPTED,
            ),
        )
        .annotate(
            _prio=Case(
                When(status=AdoptionRequest.STATUS_ACCEPTED, then=0),
                When(status=AdoptionRequest.STATUS_PENDING, then=1),
                default=2,
                output_field=IntegerField(),
            )
        )
        .order_by("_prio", "-created_at")
    )
    return qs.first()


def _servicii_bundle_adoption_bonus(request):
    """Context Servicii: inimioare bonus adopție (județ adoptator + cerere activă)."""
    bundle = {
        "adoption_bonus_request_id": None,
        "adoption_bonus_selection_by_kind": {},
        "adoption_bonus_show_banner": False,
        "adoption_bonus_has_selection": False,
        "adoption_bonus_servicii_locked": False,
        "adoption_bonus_ar_pending": False,
    }
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return bundle
    county_raw = _adopter_profile_county_raw(user)
    if not (county_raw or "").strip():
        return bundle
    ar = _resolve_adoption_bonus_request(user, request.session)
    if not ar:
        return bundle
    bundle["adoption_bonus_request_id"] = ar.pk
    bundle["adoption_bonus_show_banner"] = True
    bundle["adoption_bonus_servicii_locked"] = bool(getattr(ar, "bonus_servicii_locked_at", None))
    bundle["adoption_bonus_ar_pending"] = ar.status == AdoptionRequest.STATUS_PENDING
    for s in AdoptionBonusSelection.objects.filter(adoption_request=ar):
        bundle["adoption_bonus_selection_by_kind"][s.partner_kind] = s.offer_id
    bundle["adoption_bonus_has_selection"] = bool(bundle["adoption_bonus_selection_by_kind"])
    return bundle


def _servicii_tag_offer_bonus(offer, bundle: dict, county_norm: str) -> None:
    sm = bundle.get("adoption_bonus_selection_by_kind") or {}
    rid = bundle.get("adoption_bonus_request_id")
    offer.adoption_bonus_heart_frozen = False
    if not rid:
        offer.adoption_bonus_show_heart = False
    elif bundle.get("adoption_bonus_servicii_locked"):
        # După „Salvează alegerile”: doar ofertele deja alese rămân vizibile (♥ blocat, fără toggle).
        chosen_id = sm.get(offer.partner_kind)
        offer.adoption_bonus_show_heart = chosen_id == offer.pk
        offer.adoption_bonus_heart_frozen = bool(offer.adoption_bonus_show_heart)
        offer.adoption_bonus_selected = offer.adoption_bonus_show_heart
    elif not (county_norm or "").strip():
        # Fără județ în cont: inimioare pe toate ofertele (demo / cont incomplet — evită un canal „fără ♥”).
        offer.adoption_bonus_show_heart = True
    else:
        offer.adoption_bonus_show_heart = _offer_collab_county_norm(offer) == county_norm
    if not getattr(offer, "adoption_bonus_heart_frozen", False):
        offer.adoption_bonus_selected = sm.get(offer.partner_kind) == offer.pk
    offer.site_cart_ref_key = f"servicii_offer:{offer.pk}"


def _safe_site_cart_detail_url(raw: str) -> str:
    p = (raw or "").strip()
    if not p.startswith("/") or p.startswith("//"):
        return ""
    if "\n" in p or "\r" in p:
        return ""
    return p[:500]


def _servicii_show_offer_cart(request, bonus_bundle: dict) -> bool:
    """Coș pe carduri Servicii: ascuns în flux bonus adopție până la „Salvează alegerile” (unlock în sesiune)."""
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    rid = bonus_bundle.get("adoption_bonus_request_id")
    if not rid:
        return True
    if bonus_bundle.get("adoption_bonus_servicii_locked"):
        return True
    unlock = request.session.get(SESSION_ADOPTION_BONUS_CART_UNLOCK_AR)
    try:
        unlock_int = int(unlock)
    except (TypeError, ValueError):
        unlock_int = None
    return unlock_int == int(rid)


def _new_adoption_bonus_redemption_code() -> str:
    while True:
        c = "EUADOPT-" + "".join(secrets.choice(_ADOPTION_BONUS_CODE_ALPH) for _ in range(6))
        if not AdoptionBonusSelection.objects.filter(redemption_code=c).exists():
            return c


def _offer_public_absolute_url(offer: CollaboratorServiceOffer) -> str:
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        path = reverse("public_offer_detail", args=[offer.pk])
    except Exception:
        path = f"/oferte-parteneri/{offer.pk}/"
    return f"{site_base}{path}" if site_base else path


def _adoption_bonus_selection_summary(ar: AdoptionRequest) -> tuple[str, str]:
    """
    Rezumat oferte Servicii bifate pentru bonus (text + HTML), fără coduri de revendicare.
    Codurile se generează și se trimit pe email la finalizarea adopției în MyPet.
    """
    sels = list(
        AdoptionBonusSelection.objects.filter(adoption_request=ar)
        .select_related("offer")
        .order_by("partner_kind", "pk")
    )
    if not sels:
        return "", ""
    lines_txt: list[str] = []
    lines_html: list[str] = []
    for sel in sels:
        off = sel.offer
        kind_label = off.get_partner_kind_display()
        url = _offer_public_absolute_url(off)
        bits: list[str] = []
        ph = (off.price_hint or "").strip()
        if ph:
            bits.append(f"preț indicativ: {ph}")
        if getattr(off, "discount_percent", None):
            bits.append(f"discount {off.discount_percent}%")
        extra = (" (" + ", ".join(bits) + ")") if bits else ""
        lines_txt.append(f"- [{kind_label}] {off.title}{extra}\n  {url}")
        bits_esc = escape(extra) if extra else ""
        lines_html.append(
            f"<li><strong>{escape(kind_label)}</strong> — {escape(off.title)}{bits_esc}<br/>"
            f"<a href=\"{escape(url)}\">{escape(url)}</a></li>"
        )
    head_txt = (
        "Oferte Servicii bifate pentru bonus (rezumat — codurile de revendicare se trimit pe email "
        "după ce adopția este finalizată în MyPet):\n"
    )
    head_html = (
        "<p><strong>Oferte Servicii bifate pentru bonus</strong> (rezumat). "
        "<strong>Codurile de revendicare</strong> pentru parteneri le primești pe email "
        "după <strong>finalizarea adopției</strong> în MyPet.</p>"
    )
    return head_txt + "\n".join(lines_txt), head_html + "<ul style=\"margin:0 0 1em 1.1em;padding:0;\">" + "".join(lines_html) + "</ul>"


def _process_adoption_finalize_bonus(ar: AdoptionRequest):
    """
    După finalizare: coduri + mail adoptator (toate ofertele) + mail per colaborator.
    Idempotent dacă bonus_emails_sent_at e deja setat.
    """
    sels = list(
        AdoptionBonusSelection.objects.filter(
            adoption_request=ar,
            bonus_emails_sent_at__isnull=True,
        ).select_related("offer", "offer__collaborator")
    )
    if not sels:
        return
    pet = ar.animal
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    adopter = ar.adopter
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    now = timezone.now()

    lines_adopter = []
    html_items = []
    for sel in sels:
        code = _new_adoption_bonus_redemption_code()
        sel.redemption_code = code
        sel.bonus_emails_sent_at = now
        sel.save(update_fields=["redemption_code", "bonus_emails_sent_at", "updated_at"])
        off = sel.offer
        url = _offer_public_absolute_url(off)
        kind_label = off.get_partner_kind_display()
        lines_adopter.append(f"- [{kind_label}] {off.title}\n  Cod: {code}\n  Link: {url}\n")
        html_items.append(
            f"<li><strong>{escape(kind_label)}</strong> — {escape(off.title)}<br/>"
            f"Cod: <strong>{escape(code)}</strong><br/>"
            f"<a href=\"{escape(url)}\">{escape(url)}</a></li>"
        )
        collab = off.collaborator
        sub_c = f"EU-Adopt: bonus adopție – {off.title} (cod {code})"
        body_c = (
            f"Bună ziua,\n\n"
            f"Un adoptator a finalizat adopția pentru „{pet_label}” și a ales oferta dumneavoastră "
            f"„{off.title}” (canal: {kind_label}).\n\n"
            f"Cod comun de identificare (același pentru dumneavoastră și adoptator): {code}\n\n"
            f"Date adoptator:\n---\n{_adoption_contact_block(adopter)}\n---\n\n"
            f"Link ofertă: {url}\n\n"
            f"EU-Adopt\n"
        )
        html_c = (
            f"<p>Bună ziua,</p>"
            f"<p>Un adoptator a finalizat adopția pentru <strong>{escape(pet_label)}</strong> și a ales "
            f"oferta <strong>{escape(off.title)}</strong> ({escape(kind_label)}).</p>"
            f"<p>Cod comun: <strong>{escape(code)}</strong></p>"
            f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(_adoption_contact_block(adopter))}</pre>"
            f"<p><a href=\"{escape(url)}\">Deschide oferta</a></p>"
            f"<p>EU-Adopt</p>"
        )
        if collab.email:
            try:
                send_mail(
                    email_subject_for_user(collab.username, sub_c),
                    body_c,
                    from_email,
                    [collab.email],
                    fail_silently=False,
                    html_message=html_c,
                )
            except Exception as exc:
                logging.getLogger(__name__).exception("adoption_bonus_email_collab: %s", exc)

    if not adopter.email:
        return
    sub_a = f"EU-Adopt: oferte partener după adopția lui {pet_label}"
    body_a = (
        f"Bună ziua,\n\n"
        f"Felicitări pentru adopția lui „{pet_label}”! Mai jos găsești ofertele partenerilor pe care le-ai "
        f"selectat în pagina Servicii (cu inimioara), împreună cu codurile de identificare.\n\n"
        f"{''.join(lines_adopter)}\n"
        f"Prezintă codul la partener pentru a beneficia de condițiile afișate în ofertă.\n\n"
        f"EU-Adopt\n"
    )
    html_a = (
        f"<p>Bună ziua,</p>"
        f"<p>Felicitări pentru adopția lui <strong>{escape(pet_label)}</strong>! "
        f"Iată ofertele selectate în Servicii:</p>"
        f"<ul>{''.join(html_items)}</ul>"
        f"<p>Prezintă codul la partener pentru a beneficia de condițiile din ofertă.</p>"
        f"<p>EU-Adopt</p>"
    )
    try:
        send_mail(
            email_subject_for_user(adopter.username, sub_a),
            body_a,
            from_email,
            [adopter.email],
            fail_silently=False,
            html_message=html_a,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_bonus_email_adopter: %s", exc)


def _goodwill_offers_one_per_kind(county_norm: str):
    """Câte o ofertă activă per partner_kind, același județ colaborator."""
    if not county_norm:
        return []
    picked = []
    for kind in (
        CollaboratorServiceOffer.PARTNER_KIND_CABINET,
        CollaboratorServiceOffer.PARTNER_KIND_SERVICII,
        CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN,
    ):
        base = CollaboratorServiceOffer.objects.filter(is_active=True, partner_kind=kind)
        if kind == CollaboratorServiceOffer.PARTNER_KIND_SERVICII:
            base = _servicii_saloane_qs_exclude_transportatori(base)
        candidates = (
            _collab_offer_valid_public_qs(base)
            .select_related("collaborator")
            .order_by("-created_at")[:80]
        )
        for off in candidates:
            if _offer_collab_county_norm(off) == county_norm:
                picked.append(off)
                break
    return picked


def _send_adoption_goodwill_15d_email(ar: AdoptionRequest) -> bool:
    """Mail la +15 zile: 3 sugestii (dacă există), servicii opționale."""
    adopter = ar.adopter
    if not adopter.email:
        return True
    county_norm = _norm_county_str(_adopter_profile_county_raw(adopter))
    offers = _goodwill_offers_one_per_kind(county_norm)
    pet = ar.animal
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    site_base = (getattr(settings, "SITE_BASE_URL", "") or "").rstrip("/")
    try:
        serv_path = reverse("servicii")
    except Exception:
        serv_path = "/servicii/"
    serv_link = f"{site_base}{serv_path}" if site_base else serv_path

    lines = []
    html_lis = []
    for off in offers:
        url = _offer_public_absolute_url(off)
        lines.append(f"- {off.get_partner_kind_display()}: {off.title}\n  {url}\n")
        html_lis.append(
            f"<li><strong>{escape(off.get_partner_kind_display())}</strong> — {escape(off.title)} — "
            f"<a href=\"{escape(url)}\">{escape(url)}</a></li>"
        )
    if not lines:
        lines.append("(În acest moment nu am găsit oferte noi în județul tău pe toate categoriile; vezi pagina Servicii.)\n")
        html_lis.append(
            "<li><em>Poți explora oricând ofertele actualizate din pagina Servicii (link mai jos).</em></li>"
        )

    sub = f"EU-Adopt: idei de servicii după adopția lui {pet_label}"
    body = (
        f"Bună ziua,\n\n"
        f"Îți mulțumim din nou pentru adopția lui „{pet_label}”. "
        f"Îți propunem câteva idei de la partenerii noștri (prețuri speciale sau oferte dedicate comunității).\n\n"
        f"{''.join(lines)}\n"
        f"Serviciile de mai sus sunt opționale. Poți alege alte oferte sau furnizori în funcție de nevoile tale, "
        f"direct din pagina Servicii:\n{serv_link}\n\n"
        f"Cu stimă,\nEchipa EU-Adopt\n"
    )
    html_body = (
        f"<p>Bună ziua,</p>"
        f"<p>Îți mulțumim pentru adopția lui <strong>{escape(pet_label)}</strong>. "
        f"Iată câteva sugestii de la parteneri:</p>"
        f"<ul>{''.join(html_lis)}</ul>"
        f"<p><strong>Serviciile sunt opționale.</strong> Poți alege alte oferte în funcție de nevoile tale din "
        f"<a href=\"{escape(serv_link)}\">pagina Servicii</a>.</p>"
        f"<p>Cu stimă,<br/>Echipa EU-Adopt</p>"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail(
            email_subject_for_user(adopter.username, sub),
            body,
            from_email,
            [adopter.email],
            fail_silently=False,
            html_message=html_body,
        )
        return True
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_goodwill_15d: %s", exc)
        return False


def _apply_owner_decision_for_request(ad_req: AdoptionRequest, decision: str):
    """
    Aplică decizia owner-ului pentru o cerere (accept/reject), inclusiv corecție rapidă.
    Returnează (ok, msg, changed).
    """
    decision = (decision or "").strip().lower()
    if decision not in {"accept", "reject"}:
        return False, "Acțiune invalidă.", False

    superseded_pending_ids = []
    with transaction.atomic():
        locked_qs = AdoptionRequest.objects.select_for_update().filter(animal=ad_req.animal)
        ad_req = locked_qs.filter(pk=ad_req.pk).first()
        if not ad_req:
            return False, "Cererea nu mai există.", False
        if ad_req.status == AdoptionRequest.STATUS_FINALIZED:
            return False, "Cererea este deja finalizată și nu mai poate fi schimbată.", False

        if decision == "accept":
            if ad_req.status == AdoptionRequest.STATUS_ACCEPTED:
                return True, "Cererea era deja acceptată.", False
            if locked_qs.filter(status=AdoptionRequest.STATUS_ACCEPTED).exclude(pk=ad_req.pk).exists():
                return False, "Există deja o altă adopție activă pentru acest animal.", False
            superseded_pending_ids = list(
                locked_qs.filter(status=AdoptionRequest.STATUS_PENDING)
                .exclude(pk=ad_req.pk)
                .values_list("pk", flat=True)
            )
            if superseded_pending_ids:
                AdoptionRequest.objects.filter(
                    pk__in=superseded_pending_ids,
                    animal_id=ad_req.animal_id,
                    status=AdoptionRequest.STATUS_PENDING,
                ).update(status=AdoptionRequest.STATUS_REJECTED)
                AdoptionBonusSelection.objects.filter(adoption_request_id__in=superseded_pending_ids).delete()
            ad_req.status = AdoptionRequest.STATUS_ACCEPTED
            ad_req.accepted_at = timezone.now()
            ad_req.accepted_expires_at = timezone.now() + timezone.timedelta(days=7)
            ad_req.save(update_fields=["status", "accepted_at", "accepted_expires_at", "updated_at"])
            changed = True
        else:
            if ad_req.status == AdoptionRequest.STATUS_REJECTED:
                return True, "Cererea era deja respinsă.", False
            ad_req.status = AdoptionRequest.STATUS_REJECTED
            ad_req.save(update_fields=["status", "updated_at"])
            changed = True

    _sync_animal_adoption_state(ad_req.animal)

    if changed and decision == "accept":
        for oid in superseded_pending_ids:
            other_ar = AdoptionRequest.objects.filter(pk=oid).select_related("animal", "animal__owner", "adopter").first()
            if not other_ar:
                continue
            _send_adoption_reject_adopter_email(other_ar, reason="superseded")
            PetMessage.objects.create(
                animal=other_ar.animal,
                sender=other_ar.animal.owner,
                receiver=other_ar.adopter,
                body=(
                    "Pentru acest animal a fost acceptată o altă cerere de adopție. "
                    "Cererea ta nu mai este activă. Îți mulțumim pentru interes."
                ),
                is_read=False,
            )
            pl_other = (other_ar.animal.name or f"Animal #{other_ar.animal.pk}").strip()
            _inbox.create_inbox_notification(
                other_ar.adopter,
                _inbox.KIND_ADOPTION_SUPERSEDED_ADOPTER,
                "Cererea ta de adopție nu mai este activă",
                f"Pentru „{pl_other}” a fost acceptată o altă cerere.",
                link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={other_ar.animal_id}",
                metadata={"pet_id": other_ar.animal_id},
            )
        _send_adoption_accept_emails(ad_req)
        PetMessage.objects.create(
            animal=ad_req.animal,
            sender=ad_req.animal.owner,
            receiver=ad_req.adopter,
            body=(
                "Am acceptat cererea ta de adopție. Datele de contact au fost trimise pe email; "
                "poți folosi și această conversație pentru detalii suplimentare."
            ),
            is_read=False,
        )
        pl = (ad_req.animal.name or f"Animal #{ad_req.animal.pk}").strip()
        _inbox.create_inbox_notification(
            ad_req.adopter,
            _inbox.KIND_ADOPTION_ACCEPTED_ADOPTER,
            "Cererea ta de adopție a fost acceptată",
            f"Pentru „{pl}”. Verifică emailul și mesajele din cont.",
            link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={ad_req.animal_id}",
            metadata={"pet_id": ad_req.animal_id, "adoption_request_id": ad_req.pk},
        )
        return True, "Cererea a fost acceptată.", True

    if changed and decision == "reject":
        AdoptionBonusSelection.objects.filter(adoption_request_id=ad_req.pk).delete()
        _send_adoption_reject_adopter_email(ad_req)
        PetMessage.objects.create(
            animal=ad_req.animal,
            sender=ad_req.animal.owner,
            receiver=ad_req.adopter,
            body="Cererea de adopție nu a fost acceptată. Îți mulțumim pentru interes.",
            is_read=False,
        )
        plr = (ad_req.animal.name or f"Animal #{ad_req.animal.pk}").strip()
        _inbox.create_inbox_notification(
            ad_req.adopter,
            _inbox.KIND_ADOPTION_REJECTED_ADOPTER,
            "Cererea ta de adopție nu a fost acceptată",
            f"Pentru „{plr}”. Îți mulțumim pentru interes.",
            link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={ad_req.animal_id}",
            metadata={"pet_id": ad_req.animal_id},
        )
        return True, "Cererea a fost respinsă.", True

    return True, "Nicio schimbare necesară.", False


@require_http_methods(["GET"])
def adoption_email_owner_action_view(request, token=None, decision=None):
    """
    Acțiune rapidă din email: accept/reject pentru owner.
    Link semnat, valabil 48h.

    URL recomandat (email): /adoption/email/d/?t=<token>&d=accept|reject
    (tokenul conține ':' — query evită clienți de email care strică path-ul.)

    Compatibilitate: /adoption/email/<token>/<decision>/ (vezi adoption_email_owner_action_path).
    """
    if token is None or decision is None:
        token = (request.GET.get("t") or request.GET.get("token") or "").strip()
        decision = (request.GET.get("d") or request.GET.get("decision") or "").strip()
    if not token or not decision:
        return HttpResponse(
            "<h3>Link incomplet</h3><p>Lipsește tokenul sau decizia. Deschide linkul din email din nou.</p>",
            status=400,
        )

    signer = TimestampSigner(salt="adoption-owner-email-v1")
    try:
        payload = signer.unsign(token, max_age=48 * 3600)
        req_id_s, owner_id_s = payload.split(":", 1)
        req_id = int(req_id_s)
        owner_id = int(owner_id_s)
    except SignatureExpired:
        return HttpResponse("<h3>Link expirat</h3><p>Acest link de decizie a expirat (48h).</p>", status=410)
    except (BadSignature, ValueError):
        return HttpResponse("<h3>Link invalid</h3><p>Acest link nu este valid.</p>", status=400)

    ad_req = get_object_or_404(AdoptionRequest, pk=req_id, animal__owner_id=owner_id)
    ok, msg, _changed = _apply_owner_decision_for_request(ad_req, decision)

    opposite = "reject" if (decision or "").strip().lower() == "accept" else "accept"
    try:
        opposite_path = f"{reverse('adoption_email_owner_action')}?{urlencode({'t': token, 'd': opposite})}"
    except Exception:
        opposite_path = f"/adoption/email/d/?{urlencode({'t': token, 'd': opposite})}"
    try:
        mypet_path = reverse("mypet")
    except Exception:
        mypet_path = "/mypet/"
    opposite_url = request.build_absolute_uri(opposite_path)
    mypet_url = request.build_absolute_uri(mypet_path)

    status_code = 200 if ok else 400
    html = (
        "<html><body style='font-family:Arial,sans-serif;padding:20px;'>"
        f"<h3>{'Acțiune procesată' if ok else 'Acțiune nereușită'}</h3>"
        f"<p>{msg}</p>"
        "<p>Dacă ai apăsat greșit, poți inversa decizia:</p>"
        f"<p><a href='{escape(opposite_url)}' style='display:inline-block;padding:10px 14px;border-radius:8px;background:#f5f5f5;border:1px solid #888;color:#111;text-decoration:none;font-weight:700;'>Inversează decizia</a></p>"
        f"<p><a href='{escape(mypet_url)}'>Deschide MyPet</a></p>"
        "</body></html>"
    )
    return HttpResponse(html, status=status_code)


def _send_adoption_waiting_list_email(ar: AdoptionRequest):
    """Adoptatorul este notificat că intră în lista de așteptare."""
    adopter = ar.adopter
    pet = ar.animal
    if not adopter.email:
        return
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    sub = f"EU-Adopt: listă de așteptare pentru {pet_label}"
    body = (
        f"Bună ziua,\n\n"
        f"Te informăm că pentru „{pet_label}” există deja o adopție în curs, iar cererea ta a fost pusă în lista de așteptare.\n"
        f"Dacă adopția curentă nu se finalizează, vei primi detaliile necesare pentru continuarea procesului.\n\n"
        f"Aplicația EU-Adopt\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail(
            email_subject_for_user(adopter.username, sub),
            body,
            from_email,
            [adopter.email],
            fail_silently=False,
        )
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_waiting_email_adopter: %s", exc)


def select_a2_dogs(available_dogs, limit=A2_SLOT_COUNT):
    """
    From available_dogs (each dict with 'id' and optional 'added_at' datetime):
    - Dogs added in last A2_NEW_HOURS appear first (newest first).
    - Remaining slots filled randomly from the rest.
    - Returns up to `limit` dogs; never empty if available_dogs is non-empty.
    """
    if not available_dogs:
        return []
    now = timezone.now()
    cutoff = now - timezone.timedelta(hours=A2_NEW_HOURS)
    # Ensure we have added_at for comparison (missing => treat as old)
    with_dates = []
    for d in available_dogs:
        d = deepcopy(d)
        if "added_at" not in d:
            d["added_at"] = now - timezone.timedelta(hours=A2_NEW_HOURS + 1)
        with_dates.append(d)
    new = [d for d in with_dates if d["added_at"] >= cutoff]
    new.sort(key=lambda d: d["added_at"], reverse=True)
    other_ids = {d["id"] for d in with_dates if d not in new}
    other = [d for d in with_dates if d["id"] in other_ids]
    chosen = new[:limit]
    chosen_ids = {d["id"] for d in chosen}
    remaining = [d for d in other if d["id"] not in chosen_ids]
    need = limit - len(chosen)
    if need > 0 and remaining:
        fill = random.sample(remaining, min(need, len(remaining)))
        chosen.extend(fill)
    return chosen[:limit]


PT_PUB_SLOT_CODES = ("P4.3", "P5.1", "P5.2", "P5.3")
PT_PUB_NOTE_SECTION = "pt"
# Benzi P1/P3: celule închiriabile P1.1–P1.36, P3.1–P3.36 (între celule EU Adopt).
PT_STRIP_RENT_SLOT_CODES = frozenset([f"P1.{i}" for i in range(1, 37)] + [f"P3.{i}" for i in range(1, 37)])
HOME_SIDEBAR_SLOT_CODES = ("A5.1", "A5.2", "A5.3", "A6.1", "A6.2", "A6.3")
SERVICII_PUB_NOTE_SECTION = "servicii"
SERVICII_STRIP_RENT_SLOT_CODES = frozenset([f"S1.{i}" for i in range(1, 37)] + [f"S7.{i}" for i in range(1, 37)])


def _build_pub_strip_band_sequence(band: str) -> list[dict]:
    """40 celule: EU{band}.1 + 10 pub, …, EU{band}.4 + 6 pub (ex. EUS1.1, S1.1…)."""
    pub_counts = (10, 10, 10, 6)
    seq: list[dict] = []
    pub_n = 0
    for block_i, n_pub in enumerate(pub_counts, start=1):
        seq.append({"kind": "eu", "code": f"EU{band}.{block_i}", "label": f"EU{band}.{block_i}"})
        for _ in range(n_pub):
            pub_n += 1
            seq.append({"kind": "pub", "code": f"{band}.{pub_n}", "label": f"{band}.{pub_n}"})
    return seq


PUB_STRIP_SEQ_P1 = _build_pub_strip_band_sequence("P1")
PUB_STRIP_SEQ_P3 = _build_pub_strip_band_sequence("P3")
PUB_STRIP_SEQ_S1 = _build_pub_strip_band_sequence("S1")
PUB_STRIP_SEQ_S7 = _build_pub_strip_band_sequence("S7")


def _enrich_pub_strip_sequence(section: str, sequence: list[dict]) -> list[dict]:
    """Îmbogățește secvența benzii cu text EU sau creative JSON din ReclamaSlotNote."""
    codes = [c["code"] for c in sequence]
    notes = {}
    try:
        notes = {
            n.slot_code: n
            for n in ReclamaSlotNote.objects.filter(section=section, slot_code__in=codes)
        }
    except Exception:
        notes = {}
    out = []
    for cell in sequence:
        if cell["kind"] == "eu":
            n = notes.get(cell["code"])
            raw = (n.text if n else "") or ""
            out.append({**cell, "eu_text": (raw.strip()[:2000] or "EU Adopt")})
        else:
            out.append({**cell, "creative": _pt_pub_slot_parse_note(notes.get(cell["code"]))})
    return out


def _pt_pub_slot_parse_note(note):
    """
    Creative pentru slot PT din ReclamaSlotNote (section='pt', slot_code=P4.3 / P5.1 / …).
    Câmpul text = JSON: {"img": "…", "link": "…", "alt": "…"}.
    img: URL https sau cale absolută /… sau cale static (ex. images/parteneri/x.png).
    Aceeași sursă alimentează desktop și mobil (un singur DOM pe pt.html).
    """
    from django.templatetags.static import static as django_static

    if note is None:
        return None
    raw = (note.text or "").strip()
    if not raw:
        return None
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        data = {"img": raw, "link": "", "alt": ""}
    if not isinstance(data, dict):
        return None
    img = (data.get("img") or "").strip()
    video = (data.get("video") or "").strip()
    if not img and not video:
        return None
    link = (data.get("link") or "").strip()
    alt = (data.get("alt") or "").strip()
    price = (data.get("price") or "").strip()[:24]
    discount = (data.get("discount") or "").strip()[:8]
    if link:
        try:
            URLValidator()(link)
        except DjangoValidationError:
            link = ""
    def _resolve_media_href(raw_value: str) -> str:
        if not raw_value:
            return ""
        if raw_value.startswith(("http://", "https://")):
            try:
                URLValidator()(raw_value)
            except DjangoValidationError:
                return ""
            return raw_value
        if raw_value.startswith("/"):
            if ".." in raw_value or "\x00" in raw_value:
                return ""
            return raw_value
        if any(c not in "abcdefghijklmnopqrstuvwxyzABCDEFGHIJKLMNOPQRSTUVWXYZ0123456789./_-" for c in raw_value):
            return ""
        return django_static(raw_value)

    img_href = _resolve_media_href(img)
    video_href = _resolve_media_href(video)
    if not img_href and not video_href:
        return None
    return {
        "link": link,
        "img": img_href,
        "video": video_href,
        "alt": alt or "Reclamă",
        "price": price,
        "discount": discount,
    }


def _pt_pub_slot_list_for_template():
    try:
        notes = list(
            ReclamaSlotNote.objects.filter(
                section=PT_PUB_NOTE_SECTION,
                slot_code__in=PT_PUB_SLOT_CODES,
            )
        )
    except Exception:
        notes = []
    by_code = {n.slot_code: n for n in notes}
    return [
        {
            "code": code,
            "creative": _pt_pub_slot_parse_note(by_code.get(code)),
            "is_p52": code == "P5.2",
        }
        for code in PT_PUB_SLOT_CODES
    ]


def _home_sidebar_pub_slots_for_template() -> tuple[list[dict | None], list[dict | None]]:
    """
    HOME A5/A6: mapare note publicitate active pe sloturile laterale.
    Returnează două liste de lungime 3 (stânga A5, dreapta A6) cu dict sau None.
    """
    by_code: dict[str, ReclamaSlotNote] = {}
    try:
        notes = ReclamaSlotNote.objects.filter(section="home", slot_code__in=HOME_SIDEBAR_SLOT_CODES)
        by_code = {n.slot_code: n for n in notes}
    except Exception:
        by_code = {}

    def _entry(slot_code: str) -> dict | None:
        creative = _pt_pub_slot_parse_note(by_code.get(slot_code))
        if not creative:
            return None
        return {
            "name": slot_code,
            "url": (creative.get("link") or "").strip() or "#",
            "image_url": creative.get("img") or "",
            "video_url": creative.get("video") or "",
            "price": (creative.get("price") or "").strip(),
            "discount": (creative.get("discount") or "").strip(),
        }

    left = [_entry("A5.1"), _entry("A5.2"), _entry("A5.3")]
    right = [_entry("A6.1"), _entry("A6.2"), _entry("A6.3")]
    return left, right


@require_http_methods(["GET"])
def pets_p2_more_view(request):
    """JSON: fragment HTML pentru următorul lot P2 (scroll infinit, același filtru GET ca pagina)."""
    try:
        offset = int(request.GET.get("offset", "0") or "0")
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)
    ctx = pt_pets_page_context(request)
    p2_list = ctx.pop("p2_list")
    batch = p2_list[offset : offset + PT_P2_PAGE_SIZE]
    next_off = offset + len(batch)
    has_more = next_off < len(p2_list)
    wishlist_ids = set()
    if request.user.is_authenticated:
        try:
            wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
        except Exception:
            pass
    html = render_to_string(
        "anunturi/includes/pt_p2_grid_chunk.html",
        {"pets": batch, "wishlist_ids": wishlist_ids},
        request=request,
    )
    return JsonResponse({"ok": True, "html": html, "has_more": has_more, "next_offset": next_off})


def home_view(request):
    if request.resolver_match.url_name == "pets_all" and request.GET.get("go"):
        try:
            pk = int(request.GET.get("go"))
            return redirect(reverse("pets_single", args=[pk]))
        except (ValueError, TypeError):
            pass
    if request.resolver_match.url_name == "pets_all":
        pt_ctx = pt_pets_page_context(request)
        p2_list = pt_ctx.pop("p2_list")
        p2_pets = p2_list[:PT_P2_PAGE_SIZE]
        p2_has_more = len(p2_list) > PT_P2_PAGE_SIZE
        p2_next_offset = PT_P2_PAGE_SIZE if p2_has_more else len(p2_list)
        wishlist_ids = set()
        if request.user.is_authenticated:
            try:
                wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
            except Exception:
                pass
        return render(
            request,
            "anunturi/pt.html",
            {
                **pt_ctx,
                "p2_pets": p2_pets,
                "p2_has_more": p2_has_more,
                "p2_next_offset": p2_next_offset,
                "pt_p2_page_size": PT_P2_PAGE_SIZE,
                "wishlist_ids": wishlist_ids,
                "pt_pub_slot_list": _pt_pub_slot_list_for_template(),
                "pt_strip_p1_cells": _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P1),
                "pt_strip_p3_cells": _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P3),
            },
        )

    is_home = request.resolver_match.url_name == "home"

    # Available dogs pentru A2 (HOME) / PT:
    # 1) întâi din DB (AnimalListing, is_published=True), cu added_at = created_at
    # 2) dacă nu există niciun câine în DB, folosim lista demo (DEMO_DOGS)
    available_for_pt = []
    db_pets_for_a2 = list(
        AnimalListing.objects.filter(is_published=True).order_by("-created_at")[:200]
    )
    if db_pets_for_a2:
        for listing in db_pets_for_a2:
            available_for_pt.append({
                "id": listing.pk,
                "nume": listing.name or "—",
                "varsta": listing.age_label or "",
                "descriere": listing.cine_sunt or listing.probleme_medicale or "",
                "imagine": listing.photo_1,
                "imagine_2": listing.photo_2,
                "imagine_3": listing.photo_3,
                # păstrăm imaginea demo ca fallback – A2 folosește {% static pet.imagine_fallback %}
                "imagine_fallback": DEMO_DOG_IMAGE,
                "added_at": listing.created_at or timezone.now(),
            })
    else:
        now = timezone.now()
        for d in DEMO_DOGS:
            row = deepcopy(d)
            if "added_at" not in row:
                row["added_at"] = now - timezone.timedelta(hours=A2_NEW_HOURS + 1)
            available_for_pt.append(row)

    # A2: 12 dogs – new (last 24h) first, then fill randomly from PT
    a2_selected = select_a2_dogs(available_for_pt, limit=A2_SLOT_COUNT)
    a2_pets = []
    for d in a2_selected:
        pet = {
            "pk": d["id"],
            "nume": d["nume"],
            "varsta": d["varsta"],
            "descriere": d["descriere"],
            "imagine": d.get("imagine"),
            "imagine_2": d.get("imagine_2"),
            "imagine_3": d.get("imagine_3"),
            "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
        }
        if is_home:
            pet["quote"] = random.choice(A2_QUOTE_POOL)
        a2_pets.append(pet)

    hero_slider_images = HERO_SLIDER_IMAGES[:5]
    # Notă bun venit: welcome=1 (după activare cont); welcome_demo=1 e legacy
    show_welcome_demo = request.GET.get("welcome_demo") == "1" or request.GET.get("welcome") == "1"
    wishlist_ids = set()
    if request.user.is_authenticated:
        try:
            wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
        except Exception:
            pass
    left_sidebar_partners, right_sidebar_partners = _home_sidebar_pub_slots_for_template()
    return render(request, "anunturi/home_v2.html", {
        "a2_pets": a2_pets,
        "a2_quote_pool": A2_QUOTE_POOL,
        "a2_compact": is_home,
        "left_sidebar_partners": left_sidebar_partners,
        "right_sidebar_partners": right_sidebar_partners,
        "hero_slider_images": hero_slider_images,
        "adopted_animals": 0,
        "active_animals": len(DEMO_DOGS),
        "show_welcome_demo": show_welcome_demo,
        "wishlist_ids": wishlist_ids,
        "home_burtiera_text": _get_home_burtiera_text(),
        "home_burtiera_speed_seconds": _get_home_burtiera_speed_seconds(),
        "home_site_note_show_mypet": _user_can_use_mypet(request),
        "home_site_note_show_ilove": bool(request.user.is_authenticated),
        "home_site_note_show_publicitate": _user_can_use_publicitate(request),
        "home_site_note_show_magazinul_meu": _user_can_use_magazinul_meu(request),
    })


def logout_view(request):
    """Delogare și redirect la Home."""
    from django.contrib.auth import logout as auth_logout
    from django.shortcuts import redirect
    auth_logout(request)
    return redirect("home")


def login_view(request):
    """Pagina de autentificare – acceptă email sau username."""
    from django.contrib.auth import authenticate, login as auth_login
    from django.contrib.auth import get_user_model
    error = None
    login_value = ""
    if request.method == "POST":
        login_value = (request.POST.get("login") or "").strip()
        password = request.POST.get("password") or ""
        if not login_value or not password:
            error = "Completează Email/Utilizator și parola."
        else:
            User = get_user_model()
            username = login_value
            if "@" in login_value:
                user_by_email = User.objects.filter(email__iexact=login_value).first()
                if user_by_email:
                    username = user_by_email.username
            user = authenticate(request, username=username, password=password)
            if user is not None:
                auth_login(request, user)
                next_url = request.GET.get("next") or request.POST.get("next") or "/"
                from django.shortcuts import redirect
                return redirect(next_url)
            error = "Email/Utilizator sau parolă incorectă."
    return render(request, "anunturi/login.html", {
        "error": error,
        "login_value": login_value,
        "password_reset_success": request.GET.get("password_reset") == "1",
    })


def forgot_password_view(request):
    """Trimite link de resetare parolă pe email. Nu dezvăluie dacă emailul există în sistem."""
    from django.core.signing import TimestampSigner
    from django.core.mail import send_mail
    from urllib.parse import quote

    ctx = {"success": False, "error": None, "submitted_email": ""}
    if request.GET.get("expired"):
        ctx["error"] = "Linkul a expirat. Solicită un link nou mai jos."
    elif request.GET.get("invalid"):
        ctx["error"] = "Link invalid sau deja folosit. Solicită un link nou mai jos."
    if request.method == "POST":
        email = (request.POST.get("email") or "").strip().lower()
        if not email:
            ctx["error"] = "Introdu adresa de email."
        else:
            User = get_user_model()
            user = User.objects.filter(email__iexact=email).first()
            if user:
                signer = TimestampSigner()
                token = signer.sign(user.pk)
                reset_url = (
                    request.build_absolute_uri(reverse("reset_password"))
                    + "?token=" + quote(token)
                )
                plain = f"Bună ziua,\n\nLink pentru resetarea parolei:\n{reset_url}\n\nLinkul este valabil 1 oră. Dacă nu ai solicitat resetarea, ignoră acest email."
                html = (
                    f'<p>Bună ziua,</p>'
                    f'<p><a href="{reset_url}" style="color:#1565c0;font-weight:bold;">Resetează parola</a></p>'
                    f'<p>Linkul este valabil 1 oră. Dacă nu ai solicitat resetarea, ignoră acest email.</p>'
                )
                try:
                    send_mail(
                        subject=email_subject_for_user(user.username, "Resetare parolă – EU-Adopt"),
                        message=plain,
                        from_email=None,
                        recipient_list=[user.email],
                        fail_silently=False,
                        html_message=html,
                    )
                except Exception:
                    ctx["error"] = "Nu am putut trimite emailul. Încearcă din nou mai târziu."
                    ctx["submitted_email"] = email
                    return render(request, "anunturi/forgot_password.html", ctx)
            ctx["success"] = True
        ctx["submitted_email"] = email
    return render(request, "anunturi/forgot_password.html", ctx)


def reset_password_view(request):
    """Pagina de setare parolă nouă (link din email). Token valabil 1 oră."""
    from django.core.signing import TimestampSigner
    from django.core.signing import SignatureExpired

    token = (request.GET.get("token") or request.POST.get("token") or "").strip()
    if not token:
        return redirect(reverse("forgot_password") + "?invalid=1")

    signer = TimestampSigner()
    try:
        user_pk = signer.unsign(token, max_age=3600)
    except SignatureExpired:
        return redirect(reverse("forgot_password") + "?expired=1")
    except Exception:
        return redirect(reverse("forgot_password") + "?invalid=1")

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect(reverse("forgot_password") + "?invalid=1")

    error = None
    if request.method == "POST":
        password1 = request.POST.get("password1") or ""
        password2 = request.POST.get("password2") or ""
        if len(password1) < 8:
            error = "Parola trebuie să aibă cel puțin 8 caractere."
        elif password1 != password2:
            error = "Parolele nu coincid."
        else:
            user.set_password(password1)
            user.save()
            return redirect(reverse("login") + "?password_reset=1")

    return render(request, "anunturi/reset_password.html", {"token": token, "error": error})


def signup_choose_type_view(request):
    """Pagina de alegere tip cont (persoană fizică / firmă / ONG / colaborator)."""
    ctx = {}
    if request.GET.get("link_expirat"):
        ctx["link_expirat"] = True
    if request.GET.get("link_invalid"):
        ctx["link_invalid"] = True
    return render(request, "anunturi/signup_choose_type.html", ctx)


def signup_pf_view(request):
    """Formular înregistrare – Persoană fizică. La POST: validează, salvează în sesiune, redirect SMS. La GET: prefill din sesiune dacă user a dat Back din SMS."""
    if request.method != "POST":
        ctx = {}
        if request.GET.get("phone_taken"):
            ctx["signup_errors"] = ["Acest număr de telefon este deja folosit. Te rugăm folosește alt număr."]
        if request.GET.get("email_taken"):
            ctx["signup_errors"] = ["Acest email este deja folosit. Te rugăm folosește alt email."]
        data = _get_signup_pending(request)
        if data and data.get("role") == "pf":
            # Include password1/password2 din sesiune ca parola să rămână vizibilă la erori (ex. phone_taken)
            prefill = dict(data)
            pwd = data.get("password", "")
            prefill["password1"] = pwd
            prefill["password2"] = pwd
            ctx["form_prefill"] = prefill
        return render(request, "anunturi/signup_pf.html", ctx)

    User = get_user_model()
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    phone_country = (request.POST.get("phone_country") or "+40").strip()
    phone = (request.POST.get("phone") or "").strip()
    judet = (request.POST.get("judet") or "").strip()
    oras = (request.POST.get("oras") or "").strip()
    password1 = request.POST.get("password1") or ""
    password2 = request.POST.get("password2") or ""
    accept_termeni = request.POST.get("accept_termeni") == "on"
    accept_gdpr = request.POST.get("accept_gdpr") == "on"
    email_opt_in_wishlist = request.POST.get("email_opt_in_wishlist") == "on"

    errors = []
    if not email:
        errors.append("Email obligatoriu.")
    if _email_duplicate_blocked(email):
        errors.append("Acest email este deja folosit.")
    if not first_name:
        errors.append("Prenumele este obligatoriu.")
    if not last_name:
        errors.append("Numele este obligatoriu.")
    if not phone:
        errors.append("Telefonul este obligatoriu.")
    if not judet:
        errors.append("Județul este obligatoriu.")
    if not oras:
        errors.append("Orașul / localitatea este obligatoriu.")
    full_phone = f"{phone_country} {phone}".strip()
    if _phone_already_used(full_phone):
        errors.append("Acest număr de telefon este deja folosit.")
    if len(password1) < 8:
        errors.append("Parola trebuie să aibă cel puțin 8 caractere.")
    if password1 != password2:
        errors.append("Parolele nu coincid.")
    if not accept_termeni:
        errors.append("Trebuie să accepți termenii și condițiile.")
    if not accept_gdpr:
        errors.append("Trebuie să accepți prelucrarea datelor conform GDPR.")

    if errors:
        prefill = {
            "first_name": first_name, "last_name": last_name, "email": email,
            "phone_country": phone_country, "phone": phone, "judet": judet, "oras": oras,
            "password1": password1, "password2": password2,
        }
        return render(request, "anunturi/signup_pf.html", {"signup_errors": errors, "form_prefill": prefill})

    request.session["signup_pending"] = {
        "role": "pf",
        "first_name": first_name,
        "last_name": last_name,
        "email": email,
        "phone_country": phone_country,
        "phone": phone,
        "judet": judet,
        "oras": oras,
        "password": password1,
        "accept_termeni": accept_termeni,
        "accept_gdpr": accept_gdpr,
        "email_opt_in_wishlist": email_opt_in_wishlist,
    }
    return redirect(reverse("signup_verificare_sms"))


def _get_signup_pending(request):
    """Returnează datele signup din sesiune (signup_pending sau migrare din signup_pf_pending)."""
    data = request.session.get("signup_pending")
    if data:
        return data
    legacy = request.session.get("signup_pf_pending")
    if legacy:
        data = dict(legacy)
        data["role"] = "pf"
        request.session["signup_pending"] = data
        request.session.pop("signup_pf_pending", None)
        return data
    return None


def _redirect_for_role(role, param):
    """URL formular signup după rol (pentru email_taken / phone_taken)."""
    if role == "pf":
        return reverse("signup_pf")
    if role == "org":
        return reverse("signup_organizatie")
    if role == "collaborator":
        return reverse("signup_colaborator")
    return reverse("signup_choose_type")


# Prescurtări județe (2 litere) pentru username la duplicate
_JUDET_CODES = {
    "alba": "AB", "arad": "AR", "arges": "AG", "bacau": "BC", "bihor": "BH",
    "bistrita-nasaud": "BN", "bistrita": "BN", "botosani": "BT", "braila": "BR",
    "buzau": "BZ", "caras-severin": "CS", "cluj": "CJ", "constanta": "CT",
    "covasna": "CV", "dambovita": "DB", "dolj": "DJ", "galati": "GL",
    "giurgiu": "GR", "gorj": "GJ", "harghita": "HR", "hunedoara": "HD",
    "ialomita": "IL", "iasi": "IS", "ilfov": "IF", "maramures": "MM",
    "mehedinti": "MH", "mures": "MS", "neamt": "NT", "olt": "OT",
    "prahova": "PH", "salaj": "SJ", "satu mare": "SM", "sibiu": "SB",
    "suceava": "SV", "teleorman": "TR", "timis": "TM", "tulcea": "TL",
    "valcea": "VL", "vrancea": "VS", "bucuresti": "B",
}


def _judet_to_code(judet):
    """Returnează cod 2 litere pentru județ (ex: Neamț -> NT)."""
    if not (judet and isinstance(judet, str)):
        return "XX"
    key = judet.strip().lower().replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
    key = "".join(c for c in key if c.isalnum() or c in " -")
    key = key.replace(" ", "-").replace("--", "-").strip("-")
    return _JUDET_CODES.get(key, (key[:2] if len(key) >= 2 else key + "X").upper())


def _normalize_username_base(s):
    """Doar litere și cifre, fără spații/diacritice, pentru username."""
    if not s or not isinstance(s, str):
        return ""
    s = s.strip()
    s = s.replace("ă", "a").replace("â", "a").replace("î", "i").replace("ș", "s").replace("ț", "t")
    return "".join(c for c in s if c.isalnum())


def _make_signup_username(data, role):
    """PF: Prenume+Nume. ONG: denumire organizație. Colab: denumire societate (fallback denumire). La duplicate: + _XX (cod județ 2 litere)."""
    if role == "pf":
        prenume = (data.get("first_name") or "").strip()
        nume = (data.get("last_name") or "").strip()
        base = _normalize_username_base(prenume) + _normalize_username_base(nume)
    elif role == "org":
        base = _normalize_username_base(data.get("denumire") or "")
    else:
        base = _normalize_username_base(data.get("denumire_societate") or data.get("denumire") or "")
    if not base:
        base = "User"
    judet_code = _judet_to_code(data.get("judet") or "")
    User = get_user_model()
    username = base
    if User.objects.filter(username=username).exists():
        username = f"{base}_{judet_code}"
    n = 1
    while User.objects.filter(username=username).exists():
        username = f"{base}_{judet_code}{n}"
        n += 1
        if n > 99:
            break
    return username


def signup_verificare_sms_view(request):
    """Pas SMS comun pentru PF, ONG, Colaborator: cod 111111, creare user (inactiv), email cu link, redirect verifică email."""
    data = _get_signup_pending(request)
    if not data:
        if request.GET.get("preview") == "1":
            import time
            return render(
                request,
                "anunturi/signup_pf_sms.html",
                {"email": "", "back_url": reverse("signup_choose_type"), "expires_at": int(time.time()) + 300},
            )
        return redirect(reverse("signup_choose_type"))

    role = data.get("role", "pf")
    email = (data.get("email") or "").strip().lower()

    if request.method != "POST":
        import time
        if "signup_sms_at" not in request.session:
            request.session["signup_sms_at"] = time.time()
        if "signup_sms_resend_count" not in request.session:
            request.session["signup_sms_resend_count"] = 0
        expires_at = int(request.session["signup_sms_at"]) + 300
        back_url = _redirect_for_role(role, "")
        now = int(time.time())
        sms_resend_count = request.session.get("signup_sms_resend_count", 0)
        sms_cooldown_until = request.session.get("signup_sms_cooldown_until") or 0
        sms_in_cooldown = sms_cooldown_until > 0 and now < sms_cooldown_until
        return render(request, "anunturi/signup_pf_sms.html", {
            "email": email, "back_url": back_url, "expires_at": expires_at,
            "sms_resend_count": sms_resend_count, "sms_resend_remaining": max(0, 3 - sms_resend_count),
            "sms_cooldown_until": int(sms_cooldown_until),
            "sms_retrimis": request.GET.get("retrimis"), "sms_cooldown": request.GET.get("cooldown"),
            "sms_in_cooldown": sms_in_cooldown,
        })

    sms_code = (request.POST.get("sms_code") or "").strip()
    if sms_code != "111111":
        import time
        sms_at = request.session.get("signup_sms_at") or time.time()
        expires_at = int(float(sms_at)) + 300
        back_url = _redirect_for_role(role, "")
        now = time.time()
        sms_expired = now > expires_at
        sms_resend_count = request.session.get("signup_sms_resend_count", 0)
        sms_cooldown_until = request.session.get("signup_sms_cooldown_until") or 0
        sms_in_cooldown = sms_cooldown_until > 0 and now < sms_cooldown_until
        if sms_expired:
            sms_error = "Codul a expirat. Poți solicita un cod nou mai jos (max 3 încercări)."
        else:
            sms_error = "Cod invalid. Folosește 111111 pentru verificare."
        return render(
            request,
            "anunturi/signup_pf_sms.html",
            {
                "email": email, "sms_error": sms_error, "back_url": back_url, "expires_at": expires_at,
                "sms_expired": sms_expired, "sms_resend_count": sms_resend_count, "sms_resend_remaining": max(0, 3 - sms_resend_count),
                "sms_cooldown_until": int(sms_cooldown_until),
                "sms_in_cooldown": sms_in_cooldown, "sms_retrimis": None, "sms_cooldown": None,
            },
        )

    if role == "pf":
        full_phone = f"{data.get('phone_country', '')} {data.get('phone', '')}".strip()
    else:
        full_phone = (data.get("telefon") or "").strip()

    if _phone_already_used(full_phone):
        # Nu ștergem signup_pending – ca la redirect pe formular datele (inclusiv parola) să rămână
        return redirect(_redirect_for_role(role, "phone") + "?phone_taken=1")

    User = get_user_model()
    if _email_duplicate_blocked(email):
        # Nu ștergem signup_pending – ca la redirect pe formular datele să rămână
        return redirect(_redirect_for_role(role, "email") + "?email_taken=1")

    username = _make_signup_username(data, role)

    if role == "pf":
        user = User.objects.create_user(
            username=username,
            email=email,
            password=data["password"],
            first_name=data.get("first_name", ""),
            last_name=data.get("last_name", ""),
            is_active=False,
        )
        acc, _ = AccountProfile.objects.get_or_create(user=user, defaults={"role": AccountProfile.ROLE_PF})
        acc.role = AccountProfile.ROLE_PF
        acc.save()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        profile.phone = full_phone
        profile.judet = data.get("judet", "")
        profile.oras = data.get("oras", "")
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in_wishlist", False)
        profile.save()
        _log_legal_consents(
            request,
            user,
            accept_termeni=profile.accept_termeni,
            accept_gdpr=profile.accept_gdpr,
            email_opt_in=profile.email_opt_in_wishlist,
            source="signup_pf_sms",
        )
    elif role == "org":
        user = User.objects.create_user(
            username=username,
            email=email,
            password=data["password"],
            first_name=data.get("pers_contact", ""),
            last_name=data.get("denumire", ""),
            is_active=False,
        )
        acc, _ = AccountProfile.objects.get_or_create(user=user, defaults={"role": AccountProfile.ROLE_ORG})
        acc.role = AccountProfile.ROLE_ORG
        acc.is_public_shelter = data.get("is_public_shelter", False)
        acc.save()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        profile.phone = full_phone
        profile.judet = data.get("judet", "")
        profile.oras = data.get("oras", "")
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in", False)
        # Păstrăm și datele de entitate juridică pentru afișarea corectă în fișa contului ONG/SRL.
        profile.company_display_name = data.get("denumire", "")
        profile.company_legal_name = data.get("denumire_societate", "")
        profile.company_cui = data.get("cui", "")
        profile.company_cui_has_ro = (data.get("cui_cu_ro") == "da")
        profile.company_judet = data.get("judet", "")
        profile.company_oras = data.get("oras", "")
        profile.company_address = (data.get("adresa_firma") or "").strip()
        profile.collaborator_type = ""
        profile.save()
        _log_legal_consents(
            request,
            user,
            accept_termeni=profile.accept_termeni,
            accept_gdpr=profile.accept_gdpr,
            email_opt_in=profile.email_opt_in_wishlist,
            source="signup_org_sms",
        )
    else:
        user = User.objects.create_user(
            username=username,
            email=email,
            password=data["password"],
            first_name=data.get("pers_contact", ""),
            last_name=data.get("denumire", ""),
            is_active=False,
        )
        acc, _ = AccountProfile.objects.get_or_create(user=user, defaults={"role": AccountProfile.ROLE_COLLAB})
        acc.role = AccountProfile.ROLE_COLLAB
        acc.save()
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        profile.phone = full_phone
        profile.judet = data.get("judet", "")
        profile.oras = data.get("oras", "")
        # Date firmă / colaborator salvate în profil pentru contul Colaborator
        profile.company_display_name = data.get("denumire", "")
        profile.company_legal_name = data.get("denumire_societate", "")
        profile.company_cui = data.get("cui", "")
        profile.company_cui_has_ro = (data.get("cui_cu_ro") == "da")
        profile.company_address = data.get("adresa_firma", "")
        profile.company_judet = data.get("judet", "")
        profile.company_oras = data.get("oras", "")
        profile.collaborator_type = data.get("tip_partener", "")
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in", False)
        profile.save()
        tip_col = (data.get("tip_partener") or "").strip().lower()
        if tip_col == "transport":
            TransportOperatorProfile.objects.update_or_create(
                user=user,
                defaults={
                    "transport_national": bool(data.get("transport_national")),
                    "transport_international": bool(data.get("transport_international")),
                    "max_caini": max(1, min(99, int(data.get("max_caini") or 1))),
                    "max_pisici": max(1, min(99, int(data.get("max_pisici") or 1))),
                    "approval_status": TransportOperatorProfile.APPROVAL_PENDING,
                },
            )
        _log_legal_consents(
            request,
            user,
            accept_termeni=profile.accept_termeni,
            accept_gdpr=profile.accept_gdpr,
            email_opt_in=profile.email_opt_in_wishlist,
            source="signup_collaborator_sms",
        )

    from django.core.signing import TimestampSigner
    from django.core.mail import send_mail
    from django.core.cache import cache
    from urllib.parse import quote
    import uuid

    signer = TimestampSigner()
    token = signer.sign(user.pk)
    waiting_id = str(uuid.uuid4())
    request.session["signup_waiting_id"] = waiting_id
    cache.set("signup_waiting_" + waiting_id, "pending", timeout=600)
    verify_url = (
        request.build_absolute_uri(reverse("signup_verify_email"))
        + "?token=" + quote(token)
        + "&waiting_id=" + quote(waiting_id)
    )
    plain_msg = f"Bună ziua,\n\nApasă pe link pentru a-ți activa contul:\n{verify_url}\n\nDacă nu ai creat cont, poți ignora acest email."
    html_msg = (
        f'<p>Bună ziua,</p>'
        f'<p>Apasă pe link pentru a-ți activa contul:<br/>'
        f'<a href="{verify_url}" style="color:#1565c0;font-weight:bold;">Activează contul</a></p>'
        f'<p>Dacă linkul nu merge, copiază în browser:</p><p style="word-break:break-all;">{verify_url}</p>'
        f'<p>Dacă nu ai creat cont, poți ignora acest email.</p>'
    )
    try:
        send_mail(
            subject=email_subject_for_user(user.username, "Verificare email – EU-Adopt"),
            message=plain_msg,
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
            html_message=html_msg,
        )
    except Exception:
        pass

    import time
    request.session["signup_link_created_at"] = time.time()
    request.session["signup_waiting_user_pk"] = user.pk
    request.session["signup_email_resend_count"] = 0
    request.session.pop("signup_pending", None)
    request.session.pop("signup_pf_pending", None)
    # Mereu redirect la „Verifică email” – nu la home; logarea se face doar după click pe link din email
    check_email_url = reverse("signup_pf_check_email") + f"?email={quote(email)}"
    return redirect(check_email_url)


def signup_retrimite_sms_view(request):
    """Retrimite cod SMS: resetează timerul 5 min. Max 3 încercări, apoi cooldown 45 min."""
    import time
    data = _get_signup_pending(request)
    if not data:
        return redirect(reverse("signup_choose_type"))
    if request.method != "POST":
        return redirect(reverse("signup_verificare_sms"))
    now = time.time()
    cooldown_until = request.session.get("signup_sms_cooldown_until") or 0
    if now < cooldown_until:
        return redirect(reverse("signup_verificare_sms") + "?cooldown=1")
    resend_count = request.session.get("signup_sms_resend_count", 0)
    if resend_count >= 3:
        request.session["signup_sms_cooldown_until"] = now + 45 * 60
        return redirect(reverse("signup_verificare_sms") + "?cooldown=1")
    request.session["signup_sms_resend_count"] = resend_count + 1
    request.session["signup_sms_at"] = now
    if request.session["signup_sms_resend_count"] >= 3:
        request.session["signup_sms_cooldown_until"] = now + 45 * 60
    return redirect(reverse("signup_verificare_sms") + "?retrimis=1")


def signup_pf_sms_view(request):
    """Redirect către pasul comun de verificare SMS (compatibilitate link vechi)."""
    return signup_verificare_sms_view(request)


def signup_pf_check_email_view(request):
    """Pagina 'Verifică email-ul – am trimis un link la ...'. Dacă există waiting_id, JS face polling ca la activare din alt device să logheze aici."""
    import time
    email = request.GET.get("email", "")
    waiting_id = request.session.get("signup_waiting_id", "")
    created = request.session.get("signup_link_created_at") or time.time()
    expires_at = int(created) + 300
    email_resend_count = request.session.get("signup_email_resend_count", 0)
    email_cooldown_until = request.session.get("signup_email_cooldown_until") or 0
    now_ts = int(time.time())
    email_in_cooldown = email_cooldown_until > 0 and now_ts < email_cooldown_until
    return render(
        request,
        "anunturi/signup_pf_check_email.html",
        {
            "email": email, "waiting_id": waiting_id, "back_url": reverse("signup_choose_type"), "expires_at": expires_at,
            "email_resend_count": email_resend_count, "email_resend_remaining": max(0, 3 - email_resend_count),
            "email_cooldown_until": int(email_cooldown_until),
            "email_retrimis": request.GET.get("retrimis"), "email_cooldown": request.GET.get("cooldown"),
            "email_in_cooldown": email_in_cooldown,
        },
    )


def signup_retrimite_email_view(request):
    """Retrimite link activare pe email. Max 3 încercări, apoi cooldown 45 min."""
    import time
    from django.core.signing import TimestampSigner
    from django.core.mail import send_mail
    from urllib.parse import quote
    if request.method != "POST":
        return redirect(reverse("signup_choose_type"))
    user_pk = request.session.get("signup_waiting_user_pk")
    if not user_pk:
        return redirect(reverse("signup_choose_type"))
    now = time.time()
    cooldown_until = request.session.get("signup_email_cooldown_until") or 0
    if now < cooldown_until:
        email = get_user_model().objects.filter(pk=user_pk).values_list("email", flat=True).first() or ""
        return redirect(reverse("signup_pf_check_email") + f"?email={quote(email)}&cooldown=1")
    resend_count = request.session.get("signup_email_resend_count", 0)
    if resend_count >= 3:
        request.session["signup_email_cooldown_until"] = now + 45 * 60
        email = get_user_model().objects.filter(pk=user_pk).values_list("email", flat=True).first() or ""
        return redirect(reverse("signup_pf_check_email") + f"?email={quote(email)}&cooldown=1")
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk, is_active=False)
    except User.DoesNotExist:
        request.session.pop("signup_waiting_user_pk", None)
        return redirect(reverse("signup_choose_type"))
    signer = TimestampSigner()
    token = signer.sign(user.pk)
    waiting_id = request.session.get("signup_waiting_id", "")
    verify_url = (
        request.build_absolute_uri(reverse("signup_verify_email"))
        + "?token=" + quote(token)
        + ("&waiting_id=" + quote(waiting_id) if waiting_id else "")
    )
    plain_msg = f"Bună ziua,\n\nApasă pe link pentru a-ți activa contul:\n{verify_url}\n\nDacă nu ai creat cont, poți ignora acest email."
    html_msg = (
        f'<p>Bună ziua,</p>'
        f'<p>Apasă pe link pentru a-ți activa contul:<br/>'
        f'<a href="{verify_url}" style="color:#1565c0;font-weight:bold;">Activează contul</a></p>'
        f'<p>Dacă linkul nu merge, copiază în browser:</p><p style="word-break:break-all;">{verify_url}</p>'
        f'<p>Dacă nu ai creat cont, poți ignora acest email.</p>'
    )
    try:
        send_mail(
            subject=email_subject_for_user(user.username, "Verificare email – EU-Adopt (retrimis)"),
            message=plain_msg,
            from_email=None,
            recipient_list=[user.email],
            fail_silently=False,
            html_message=html_msg,
        )
    except Exception:
        pass
    request.session["signup_link_created_at"] = now
    request.session["signup_email_resend_count"] = resend_count + 1
    if request.session["signup_email_resend_count"] >= 3:
        request.session["signup_email_cooldown_until"] = now + 45 * 60
    return redirect(reverse("signup_pf_check_email") + f"?email={quote(user.email)}&retrimis=1")


def signup_verify_email_view(request):
    """Link din email: verifică token, activează user, login pe acest device; dacă e waiting_id, pune one_time_token pentru tab-ul de pe laptop."""
    from django.core.signing import TimestampSigner
    from django.core.signing import SignatureExpired
    from django.contrib.auth import login as auth_login
    from django.core.cache import cache
    import uuid

    token = (request.GET.get("token") or "").strip()
    if not token:
        return redirect(reverse("signup_choose_type") + "?link_invalid=1")
    signer = TimestampSigner()
    try:
        user_pk = signer.unsign(token, max_age=300)
    except SignatureExpired:
        return redirect(reverse("signup_choose_type") + "?link_expirat=1")
    except Exception:
        return redirect(reverse("signup_choose_type") + "?link_invalid=1")

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect(reverse("signup_choose_type") + "?link_invalid=1")

    user.is_active = True
    user.save()
    auth_login(request, user)
    # Curățare sesiune după activare – un singur set de chei signup_*
    for key in ("signup_waiting_id", "signup_waiting_user_pk", "signup_email_resend_count", "signup_email_cooldown_until",
                "signup_sms_resend_count", "signup_sms_cooldown_until"):
        request.session.pop(key, None)

    waiting_id = (request.GET.get("waiting_id") or "").strip()
    if waiting_id:
        one_time_token = str(uuid.uuid4())
        cache.set("signup_waiting_" + waiting_id, one_time_token, timeout=300)
        cache.set("signup_onetime_" + one_time_token, user.pk, timeout=300)

    return render(request, "anunturi/signup_activated.html")


def signup_check_activation_status_view(request):
    """Polling de pe pagina 'Verifică email': dacă userul a apăsat linkul (ex. de pe telefon), returnăm one_time_token ca tab-ul să facă complete-login."""
    from django.core.cache import cache
    from django.http import JsonResponse

    waiting_id = (request.GET.get("waiting_id") or "").strip()
    if not waiting_id:
        return JsonResponse({"activated": False})
    val = cache.get("signup_waiting_" + waiting_id)
    if val is None or val == "pending":
        return JsonResponse({"activated": False})
    return JsonResponse({"activated": True, "one_time_token": val})


def signup_complete_login_view(request):
    """După activare din alt device: loghează cu one_time_token și redirect home."""
    from django.core.cache import cache
    from django.contrib.auth import login as auth_login

    token = (request.GET.get("token") or "").strip()
    if not token:
        return redirect(reverse("home"))
    user_pk = cache.get("signup_onetime_" + token)
    if not user_pk:
        return redirect(reverse("home"))
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect(reverse("home"))
    cache.delete("signup_onetime_" + token)
    for key in ("signup_waiting_id", "signup_waiting_user_pk", "signup_email_resend_count", "signup_email_cooldown_until",
                "signup_sms_resend_count", "signup_sms_cooldown_until"):
        request.session.pop(key, None)
    auth_login(request, user)
    return redirect(reverse("home") + "?welcome=1")


def _no_cache_response(response):
    """Evită cache-ul paginii ca la refresh mesajele de eroare să dispară."""
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def _signup_maps_ctx(request):
    """Cheie Maps + origin pentru autocomplete / modal (ca la Transport)."""
    return {
        "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "",
        "maps_page_origin": request.build_absolute_uri("/").rstrip("/"),
    }


def signup_organizatie_view(request):
    """Formular înregistrare – Adăpost / ONG / Firmă. La POST: validează, salvează în sesiune, redirect SMS. La GET: prefill din sesiune dacă user a dat Back din SMS."""
    if request.method != "POST":
        ctx = _signup_maps_ctx(request)
        field_errors_get = {}
        if request.GET.get("phone_taken"):
            field_errors_get["telefon"] = "Acest număr de telefon este deja folosit. Te rugăm folosește alt număr."
        if request.GET.get("email_taken"):
            field_errors_get["email"] = "Acest email este deja folosit. Te rugăm folosește alt email."
        if field_errors_get:
            ctx["field_errors"] = field_errors_get
        data = _get_signup_pending(request)
        if data and data.get("role") == "org":
            if "cui_cu_ro" not in data and data.get("cui") and (data.get("cui") or "").upper().startswith("RO"):
                data = dict(data)
                data["cui_cu_ro"] = "da"
            elif "cui_cu_ro" not in data:
                data = dict(data)
                data["cui_cu_ro"] = "nu"
            ctx["form_prefill"] = data
        return _no_cache_response(render(request, "anunturi/signup_organizatie.html", ctx))

    User = get_user_model()
    denumire = (request.POST.get("denumire") or "").strip()
    denumire_societate = (request.POST.get("denumire_societate") or "").strip()
    cui = (request.POST.get("cui") or "").strip()
    cui_cu_ro = (request.POST.get("cui_cu_ro") or "nu").strip().lower()
    if cui_cu_ro == "da" and cui and not cui.upper().startswith("RO"):
        cui = "RO" + cui
    pers_contact = (request.POST.get("pers_contact") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    telefon = (request.POST.get("telefon") or "").strip()
    judet = (request.POST.get("judet") or "").strip()
    oras = (request.POST.get("oras") or "").strip()
    adresa_firma = (request.POST.get("adresa_firma") or "").strip()
    parola1 = request.POST.get("parola1") or ""
    parola2 = request.POST.get("parola2") or ""
    accept_termeni = request.POST.get("accept_termeni_org") == "on"
    accept_gdpr = request.POST.get("accept_gdpr_org") == "on"
    email_opt_in = request.POST.get("email_opt_in_org") == "on"
    is_public_shelter_val = (request.POST.get("is_public_shelter") or "").strip()
    is_public_shelter = is_public_shelter_val == "yes"

    field_errors = {}
    if is_public_shelter_val not in ("yes", "no"):
        field_errors["is_public_shelter"] = "Trebuie să alegi una dintre variante: Sunt adăpost public / Nu sunt adăpost public."
    if not email:
        field_errors["email"] = "Email obligatoriu."
    elif _email_duplicate_blocked(email):
        field_errors["email"] = "Acest email este deja folosit."
    if not denumire:
        field_errors["denumire"] = "Denumirea organizației este obligatorie."
    if not denumire_societate:
        field_errors["denumire_societate"] = "Denumirea societății este obligatorie."
    if not pers_contact:
        field_errors["pers_contact"] = "Persoana de contact este obligatorie."
    if not telefon:
        field_errors["telefon"] = "Telefonul este obligatoriu."
    elif _phone_already_used(telefon):
        field_errors["telefon"] = "Acest număr de telefon este deja folosit."
    if not judet:
        field_errors["judet"] = "Județul este obligatoriu."
    if not oras:
        field_errors["oras"] = "Orașul / localitatea este obligatorie."
    if not adresa_firma:
        field_errors["adresa_firma"] = "Adresa sediului este obligatorie."
    if len(parola1) < 8:
        field_errors["parola"] = "Parola trebuie să aibă cel puțin 8 caractere."
    elif parola1 != parola2:
        field_errors["parola"] = "Parolele nu coincid."
    if not accept_termeni:
        field_errors["accept_termeni"] = "Trebuie să accepți termenii și condițiile."
    if not accept_gdpr:
        field_errors["accept_gdpr"] = "Trebuie să accepți prelucrarea datelor conform GDPR."

    if field_errors:
        prefill = {
            "denumire": denumire,
            "denumire_societate": denumire_societate,
            "cui": cui,
            "cui_cu_ro": cui_cu_ro if cui_cu_ro in ("da", "nu") else "nu",
            "pers_contact": pers_contact,
            "email": email,
            "telefon": telefon,
            "judet": judet,
            "oras": oras,
            "adresa_firma": adresa_firma,
            "accept_termeni": accept_termeni,
            "accept_gdpr": accept_gdpr,
            "email_opt_in": email_opt_in,
            "is_public_shelter": is_public_shelter if is_public_shelter_val in ("yes", "no") else None,
            "parola1": parola1, "parola2": parola2,
        }
        ctx = {"field_errors": field_errors, "form_prefill": prefill}
        ctx.update(_signup_maps_ctx(request))
        return _no_cache_response(render(request, "anunturi/signup_organizatie.html", ctx))

    request.session["signup_pending"] = {
        "role": "org",
        "denumire": denumire,
        "denumire_societate": denumire_societate,
        "cui": cui,
        "cui_cu_ro": cui_cu_ro if cui_cu_ro in ("da", "nu") else "nu",
        "pers_contact": pers_contact,
        "email": email,
        "telefon": telefon.strip(),
        "judet": judet,
        "oras": oras,
        "adresa_firma": adresa_firma,
        "password": parola1,
        "accept_termeni": accept_termeni,
        "accept_gdpr": accept_gdpr,
        "email_opt_in": email_opt_in,
        "is_public_shelter": is_public_shelter,
    }
    return redirect(reverse("signup_verificare_sms"))


def signup_colaborator_view(request):
    """Formular înregistrare – Cabinet / Magazin / Servicii. La POST: validează, salvează în sesiune, redirect SMS. La GET: prefill din sesiune dacă user a dat Back din SMS."""
    if request.method != "POST":
        ctx = _signup_maps_ctx(request)
        errs = []
        if request.GET.get("phone_taken"):
            errs.append("Acest număr de telefon este deja folosit. Te rugăm folosește alt număr.")
        if request.GET.get("email_taken"):
            errs.append("Acest email este deja folosit. Te rugăm folosește alt email.")
        if errs:
            ctx["signup_errors"] = errs
        data = _get_signup_pending(request)
        if data and data.get("role") == "collaborator":
            if "cui_cu_ro" not in data:
                data = dict(data)
                data["cui_cu_ro"] = "da" if (data.get("cui") or "").upper().startswith("RO") else "nu"
            ctx["form_prefill"] = data
        elif (request.GET.get("tip") or "").strip().lower() == "transport":
            ctx["form_prefill"] = {"tip_partener": "transport"}
        return render(request, "anunturi/signup_colaborator.html", ctx)

    User = get_user_model()
    denumire = (request.POST.get("denumire") or "").strip()
    denumire_societate = (request.POST.get("denumire_societate") or "").strip()
    cui = (request.POST.get("cui") or "").strip()
    cui_cu_ro = (request.POST.get("cui_cu_ro") or "nu").strip().lower()
    if cui_cu_ro == "da" and cui and not cui.upper().startswith("RO"):
        cui = "RO" + cui
    pers_contact = (request.POST.get("pers_contact") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    telefon = (request.POST.get("telefon") or "").strip()
    judet = (request.POST.get("judet") or "").strip()
    oras = (request.POST.get("oras") or "").strip()
    adresa_firma = (request.POST.get("adresa_firma") or "").strip()
    tip_partener = (request.POST.get("tip_partener") or "").strip()
    transport_national = request.POST.get("transport_national") == "on"
    transport_international = request.POST.get("transport_international") == "on"
    try:
        max_caini = max(1, min(99, int((request.POST.get("max_caini") or "1").strip() or "1")))
    except ValueError:
        max_caini = 1
    try:
        max_pisici = max(1, min(99, int((request.POST.get("max_pisici") or "1").strip() or "1")))
    except ValueError:
        max_pisici = 1
    parola1 = request.POST.get("parola1") or ""
    parola2 = request.POST.get("parola2") or ""
    accept_termeni = request.POST.get("accept_termeni_col") == "on"
    accept_gdpr = request.POST.get("accept_gdpr_col") == "on"
    email_opt_in = request.POST.get("email_opt_in_col") == "on"

    errors = []
    if tip_partener not in ("cabinet", "servicii", "magazin", "transport"):
        errors.append("Trebuie să alegi tipul de partener: Cabinet, Servicii, Magazin sau Transportator.")
    if tip_partener == "transport":
        if not transport_national and not transport_international:
            errors.append("Bifează cel puțin una: TRANSPORT NAȚIONAL sau TRANSPORT INTERNATIONAL.")
    if not email:
        errors.append("Email obligatoriu.")
    if _email_duplicate_blocked(email):
        errors.append("Acest email este deja folosit.")
    if not denumire:
        errors.append("Denumirea este obligatorie.")
    if not denumire_societate:
        errors.append("Denumirea societății este obligatorie.")
    if not pers_contact:
        errors.append("Persoana de contact este obligatorie.")
    if not telefon:
        errors.append("Telefonul este obligatoriu.")
    if _phone_already_used(telefon):
        errors.append("Acest număr de telefon este deja folosit.")
    if not judet:
        errors.append("Județul este obligatoriu.")
    if not oras:
        errors.append("Orașul / localitatea este obligatorie.")
    if not adresa_firma:
        errors.append("Adresa sediului este obligatorie.")
    if len(parola1) < 8:
        errors.append("Parola trebuie să aibă cel puțin 8 caractere.")
    if parola1 != parola2:
        errors.append("Parolele nu coincid.")
    if not accept_termeni:
        errors.append("Trebuie să accepți termenii și condițiile.")
    if not accept_gdpr:
        errors.append("Trebuie să accepți prelucrarea datelor conform GDPR.")

    if errors:
        prefill = {
            "denumire": denumire,
            "denumire_societate": denumire_societate,
            "cui": cui,
            "cui_cu_ro": cui_cu_ro if cui_cu_ro in ("da", "nu") else "nu",
            "pers_contact": pers_contact,
            "judet": judet,
            "oras": oras,
            "adresa_firma": adresa_firma,
            "email": email,
            "telefon": telefon,
            "tip_partener": tip_partener if tip_partener in ("cabinet", "servicii", "magazin", "transport") else "",
            "transport_national": transport_national,
            "transport_international": transport_international,
            "max_caini": max_caini,
            "max_pisici": max_pisici,
            "accept_termeni": accept_termeni,
            "accept_gdpr": accept_gdpr,
            "email_opt_in": email_opt_in,
            "parola1": parola1, "parola2": parola2,
        }
        ctx = {"signup_errors": errors, "form_prefill": prefill}
        ctx.update(_signup_maps_ctx(request))
        return render(request, "anunturi/signup_colaborator.html", ctx)

    pending = {
        "role": "collaborator",
        "tip_partener": tip_partener,
        "denumire": denumire,
        "denumire_societate": denumire_societate,
        "cui": cui,
        "cui_cu_ro": cui_cu_ro if cui_cu_ro in ("da", "nu") else "nu",
        "pers_contact": pers_contact,
        "email": email,
        "telefon": telefon.strip(),
        "judet": judet,
        "oras": oras,
        "adresa_firma": adresa_firma,
        "password": parola1,
        "accept_termeni": accept_termeni,
        "accept_gdpr": accept_gdpr,
        "email_opt_in": email_opt_in,
    }
    if tip_partener == "transport":
        pending["transport_national"] = transport_national
        pending["transport_international"] = transport_international
        pending["max_caini"] = max_caini
        pending["max_pisici"] = max_pisici
    request.session["signup_pending"] = pending
    return redirect(reverse("signup_verificare_sms"))


def _attach_public_offer_stock(offer):
    """
    Locuri rămase din total (quantity_available − cereri), pentru afișare publică.
    Atașează: show_stock_public, quantity_total_public, remaining_slots_public.
    """
    qa = offer.quantity_available
    if qa is None:
        offer.show_stock_public = False
        offer.quantity_total_public = None
        offer.remaining_slots_public = None
        return
    claims = int(getattr(offer, "claims_count", 0) or 0)
    total = int(qa)
    offer.show_stock_public = True
    offer.quantity_total_public = total
    offer.remaining_slots_public = max(0, total - claims)


def _servicii_saloane_qs_exclude_transportatori(base_qs):
    """
    Grila Saloane (partner_kind=servicii): fără transportatori.
    Transportatorii folosesc doar fluxul /transport/ (formular + dispatch).
    """
    return base_qs.exclude(
        Q(collaborator__profile__collaborator_type__iexact="transport")
    ).exclude(
        Exists(
            TransportOperatorProfile.objects.filter(user_id=OuterRef("collaborator_id"))
        )
    )


def _servicii_offers_for_kind(partner_kind: str, max_n: int = 24):
    """Oferte publice pentru S3/S5/S4 după partner_kind (snapshot la creare), nu după bifa curentă din profil."""
    try:
        base = CollaboratorServiceOffer.objects.filter(is_active=True, partner_kind=partner_kind)
        if partner_kind == CollaboratorServiceOffer.PARTNER_KIND_SERVICII:
            base = _servicii_saloane_qs_exclude_transportatori(base)
        offers = list(
            _collab_offer_valid_public_qs(base)
            .select_related("collaborator")
            .annotate(claims_count=Count("claims", distinct=True))
            .order_by("-created_at")[:max_n]
        )
        for o in offers:
            _attach_public_offer_stock(o)
        pad = max(0, max_n - len(offers))
        return offers, [None] * pad
    except Exception:
        return [], [None] * max_n


def termeni_view(request):
    """Hub principal documente legale."""
    return render(request, "anunturi/termeni.html", {})


def termeni_read_view(request):
    """Pagina completă Termeni și Condiții (mod citire)."""
    return render(request, "anunturi/termeni_read.html", {})


def politica_confidentialitate_view(request):
    """Politica de confidențialitate (GDPR)."""
    return render(request, "anunturi/politica_confidentialitate.html", {})


def politici_altele_view(request):
    """Hub politici complementare (cookie-uri, publicitate, moderare)."""
    return render(request, "anunturi/politici_altele.html", {})


def politica_cookie_view(request):
    """Politica de cookie-uri."""
    return render(request, "anunturi/politica_cookie.html", {})


def politica_servicii_platite_view(request):
    """Politica serviciilor plătite / publicitate."""
    return render(request, "anunturi/politica_servicii_platite.html", {})


def politica_moderare_view(request):
    """Politica de moderare, raportare și conținut interzis."""
    return render(request, "anunturi/politica_moderare.html", {})


def contact_view(request):
    """Pagina Contact dedicată."""
    form_prefill = {
        "full_name": "",
        "email": "",
        "phone": "",
        "topic": ContactMessage.TOPIC_GENERAL,
        "subject": "",
        "message": "",
        "attachment_name": "",
        "accept_privacy": False,
    }
    form_errors = []
    form_success = False

    if request.method == "GET" and request.GET.get("sent") == "1":
        form_success = True

    if request.method == "POST":
        attachment = request.FILES.get("attachment")
        form_prefill = {
            "full_name": (request.POST.get("full_name") or "").strip(),
            "email": (request.POST.get("email") or "").strip().lower(),
            "phone": (request.POST.get("phone") or "").strip(),
            "topic": (request.POST.get("topic") or ContactMessage.TOPIC_GENERAL).strip(),
            "subject": (request.POST.get("subject") or "").strip(),
            "message": (request.POST.get("message") or "").strip(),
            "attachment_name": (attachment.name if attachment else ""),
            "accept_privacy": request.POST.get("accept_privacy") == "on",
        }
        honey = (request.POST.get("website") or "").strip()
        if honey:
            return redirect("contact")

        if not form_prefill["full_name"]:
            form_errors.append("Numele este obligatoriu.")
        if not form_prefill["email"]:
            form_errors.append("E-mailul este obligatoriu.")
        if form_prefill["topic"] not in dict(ContactMessage.TOPIC_CHOICES):
            form_errors.append("Selectează un tip de solicitare valid.")
        if not form_prefill["subject"]:
            form_errors.append("Subiectul este obligatoriu.")
        if not form_prefill["message"]:
            form_errors.append("Mesajul este obligatoriu.")
        if len(form_prefill["message"]) > 3000:
            form_errors.append("Mesajul este prea lung (maxim 3000 caractere).")
        if attachment and attachment.size > 8 * 1024 * 1024:
            form_errors.append("Fișierul atașat depășește limita de 8MB.")
        if not form_prefill["accept_privacy"]:
            form_errors.append("Trebuie să accepți politica de confidențialitate pentru a trimite mesajul.")

        if not form_errors:
            entry = ContactMessage.objects.create(
                user=request.user if request.user.is_authenticated else None,
                full_name=form_prefill["full_name"],
                email=form_prefill["email"],
                phone=form_prefill["phone"],
                topic=form_prefill["topic"],
                subject=form_prefill["subject"],
                message=form_prefill["message"],
                attachment=attachment,
                accepted_privacy=form_prefill["accept_privacy"],
                ip_address=_client_ip(request),
                user_agent=(request.META.get("HTTP_USER_AGENT") or "")[:500],
            )
            topic_label = dict(ContactMessage.TOPIC_CHOICES).get(entry.topic, entry.topic)
            msg_lines = [
                "Mesaj nou din pagina Contact (EU-ADOPT)",
                "",
                f"Nume: {entry.full_name}",
                f"E-mail: {entry.email}",
                f"Telefon: {entry.phone or '-'}",
                f"Tip solicitare: {topic_label}",
                f"Subiect: {entry.subject}",
                f"IP: {entry.ip_address or '-'}",
                f"Atașament: {entry.attachment.name if entry.attachment else '-'}",
                "",
                "Mesaj:",
                entry.message,
            ]
            to_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or "euadopt@gmail.com"
            from_email = to_email
            try:
                mail = EmailMessage(
                    subject=f"[Contact EU-ADOPT] {entry.subject}",
                    body="\n".join(msg_lines),
                    from_email=from_email,
                    to=[to_email],
                )
                if entry.attachment:
                    try:
                        mail.attach_file(entry.attachment.path)
                    except Exception:
                        # Păstrăm trimiterea mesajului chiar dacă atașarea eșuează.
                        pass
                mail.send(fail_silently=False)
            except Exception:
                pass

            form_success = True
            # PRG: după trimitere facem redirect ca mesajul/datele să nu rămână la refresh/reintrare.
            return redirect(f"{reverse('contact')}?sent=1")

    return render(
        request,
        "anunturi/contact.html",
        {
            "form_prefill": form_prefill,
            "form_errors": form_errors,
            "form_success": form_success,
            "contact_topic_choices": ContactMessage.TOPIC_CHOICES,
        },
    )


def servicii_view(request):
    """Pagina Servicii – S1/S7 benzi publicitare (celule EU + închiriabile)."""
    max_slot = 24
    vet_offers, vet_offer_empty_slots = _servicii_offers_for_kind(
        CollaboratorServiceOffer.PARTNER_KIND_CABINET, max_slot
    )
    groom_offers, groom_offer_empty_slots = _servicii_offers_for_kind(
        CollaboratorServiceOffer.PARTNER_KIND_SERVICII, max_slot
    )
    shop_offers, shop_offer_empty_slots = _servicii_offers_for_kind(
        CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN, max_slot
    )
    bonus_bundle = _servicii_bundle_adoption_bonus(request)
    county_norm = _norm_county_str(_adopter_profile_county_raw(request.user)) if request.user.is_authenticated else ""
    prefill_county = ""
    prefill_city = ""
    if request.user.is_authenticated and bonus_bundle.get("adoption_bonus_show_banner"):
        # În fluxul venit din adopție, pornim implicit pe zona adoptatorului.
        prefill_county = _adopter_profile_county_raw(request.user)
        prefill_city = _adopter_profile_city_raw(request.user)
    for lst in (vet_offers, groom_offers, shop_offers):
        for off in lst:
            if off is not None:
                _servicii_tag_offer_bonus(off, bonus_bundle, county_norm)
    eligible_bonus_kinds = 0
    if bonus_bundle.get("adoption_bonus_request_id"):
        kinds_elig = set()
        for _lst in (vet_offers, groom_offers, shop_offers):
            for _off in _lst:
                if _off is not None and getattr(_off, "adoption_bonus_show_heart", False):
                    kinds_elig.add(_off.partner_kind)
        eligible_bonus_kinds = len(kinds_elig)
    show_locked_notice_once = False
    rid = bonus_bundle.get("adoption_bonus_request_id")
    if bonus_bundle.get("adoption_bonus_servicii_locked") and rid:
        try:
            pending = int(request.session.get(SESSION_ADOPTION_BONUS_SHOW_LOCKED_NOTICE_AR) or 0)
        except (TypeError, ValueError):
            pending = 0
        if pending == int(rid):
            show_locked_notice_once = True
            request.session.pop(SESSION_ADOPTION_BONUS_SHOW_LOCKED_NOTICE_AR, None)
            request.session.modified = True
    return render(
        request,
        "anunturi/servicii.html",
        {
            "servicii_strip_s1_cells": _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S1),
            "servicii_strip_s7_cells": _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S7),
            "vet_offers": vet_offers,
            "vet_offer_empty_slots": vet_offer_empty_slots,
            "groom_offers": groom_offers,
            "groom_offer_empty_slots": groom_offer_empty_slots,
            "shop_offers": shop_offers,
            "shop_offer_empty_slots": shop_offer_empty_slots,
            "servicii_prefill_county": prefill_county,
            "servicii_prefill_city": prefill_city,
            "adoption_bonus_request_id": bonus_bundle.get("adoption_bonus_request_id"),
            "adoption_bonus_show_banner": bonus_bundle.get("adoption_bonus_show_banner"),
            "adoption_bonus_has_selection": bonus_bundle.get("adoption_bonus_has_selection"),
            "adoption_bonus_eligible_kind_count": eligible_bonus_kinds,
            "adoption_bonus_toggle_url": reverse("adoption_bonus_offer_toggle"),
            "adoption_bonus_shop_url": reverse("shop"),
            "can_request_public_collab_offer": _user_can_request_public_collab_offer(
                request.user
            ),
            "servicii_show_offer_cart": _servicii_show_offer_cart(request, bonus_bundle),
            "adoption_bonus_cart_unlock_url": reverse("adoption_bonus_cart_unlock")
            if bonus_bundle.get("adoption_bonus_request_id")
            else "",
            "adoption_bonus_servicii_locked": bonus_bundle.get("adoption_bonus_servicii_locked"),
            "adoption_bonus_ar_pending": bonus_bundle.get("adoption_bonus_ar_pending"),
            "adoption_bonus_show_locked_notice_once": show_locked_notice_once,
        },
    )


def transport_view(request):
    """Pagina Transport – wrapper TW, layout ca PW/SW."""
    ctx = {
        "google_maps_api_key": getattr(settings, "GOOGLE_MAPS_API_KEY", "") or "",
        "maps_page_origin": request.build_absolute_uri("/").rstrip("/"),
        "from_adoption_pet_pk": None,
        "continue_adoption_url": "",
        "prefill_judet": "",
        "prefill_oras": "",
    }
    if request.user.is_authenticated:
        ctx["prefill_judet"] = _adopter_profile_county_raw(request.user)
        ctx["prefill_oras"] = _adopter_profile_city_raw(request.user)
    if request.GET.get("from_adoption") == "1":
        raw = (request.GET.get("pet") or "").strip()
        if raw.isdigit():
            pk = int(raw)
            if AnimalListing.objects.filter(pk=pk, is_published=True).exists():
                ctx["from_adoption_pet_pk"] = pk
                ctx["continue_adoption_url"] = reverse("pets_single", args=[pk]) + "?after_transport=1"
    return render(request, "anunturi/transport.html", ctx)


def _safe_local_redirect_path(path_val: str) -> str | None:
    """Permite doar path-uri relative pe același site (open redirect safe)."""
    p = (path_val or "").strip()
    if not p.startswith("/") or p.startswith("//"):
        return None
    if "\n" in p or "\r" in p:
        return None
    return p


@require_POST
@csrf_protect
def transport_submit_view(request):
    """Salvează cererea de transport veterinar din formularul paginii /transport/."""
    judet = (request.POST.get("judet") or "").strip()
    oras = (request.POST.get("oras") or "").strip()
    plecare = (request.POST.get("plecare") or "").strip()
    sosire = (request.POST.get("sosire") or "").strip()
    if not judet or not oras or not plecare or not sosire:
        messages.error(
            request,
            "Completează județul, localitatea și punctele de plecare / sosire.",
        )
        return redirect("transport")

    try:
        nr = int(request.POST.get("nr_caini") or "1")
        nr = max(1, min(99, nr))
    except (TypeError, ValueError):
        nr = 1

    related = None
    rp = (request.POST.get("related_pet_id") or "").strip()
    if rp.isdigit():
        related = AnimalListing.objects.filter(pk=int(rp), is_published=True).first()

    rs = (request.POST.get("route_scope") or TransportVeterinaryRequest.ROUTE_NATIONAL).strip()
    if rs not in (TransportVeterinaryRequest.ROUTE_NATIONAL, TransportVeterinaryRequest.ROUTE_INTERNATIONAL):
        rs = TransportVeterinaryRequest.ROUTE_NATIONAL
    uw = (request.POST.get("urgency_window") or TransportVeterinaryRequest.URGENCY_FLEX).strip()
    if uw not in (
        TransportVeterinaryRequest.URGENCY_FLEX,
        TransportVeterinaryRequest.URGENCY_TODAY,
        TransportVeterinaryRequest.URGENCY_24H,
    ):
        uw = TransportVeterinaryRequest.URGENCY_FLEX

    tvr = TransportVeterinaryRequest.objects.create(
        user=request.user if request.user.is_authenticated else None,
        judet=judet[:120],
        oras=oras[:120],
        plecare=plecare[:500],
        sosire=sosire[:500],
        plecare_lat=(request.POST.get("plecare_lat") or "")[:32],
        plecare_lng=(request.POST.get("plecare_lng") or "")[:32],
        sosire_lat=(request.POST.get("sosire_lat") or "")[:32],
        sosire_lng=(request.POST.get("sosire_lng") or "")[:32],
        data_raw=(request.POST.get("data") or "")[:40],
        ora_raw=(request.POST.get("ora") or "")[:20],
        nr_caini=nr,
        related_animal=related,
        route_scope=rs,
        urgency_window=uw,
    )
    if request.user.is_authenticated:
        from .transport_dispatch import create_dispatch_for_tvr

        create_dispatch_for_tvr(request, tvr)
    messages.success(request, "Cererea de transport a fost înregistrată.")

    next_path = _safe_local_redirect_path(request.POST.get("next") or "")
    if next_path:
        return redirect(next_path)
    return redirect("transport")


def transport_dispatch_accept_view(request):
    """Link din email: transportator acceptă cererea."""
    from urllib.parse import urlencode

    from .transport_dispatch import accept_job, maybe_expire_job, parse_token

    token = (request.GET.get("t") or "").strip()
    parsed = parse_token(token)
    if not parsed or parsed[0] != "accept":
        messages.error(request, "Link invalid sau expirat.")
        return redirect("home")
    _, job_id, uid = parsed
    if not request.user.is_authenticated:
        return redirect(reverse("login") + "?" + urlencode({"next": request.get_full_path()}))
    if request.user.pk != uid:
        messages.error(request, "Acest link este pentru alt cont de transportator.")
        return redirect("home")
    job = TransportDispatchJob.objects.filter(pk=job_id).first()
    if job:
        maybe_expire_job(job)
    ok, msg = accept_job(request, job_id, uid)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport_operator_panel")


def transport_dispatch_decline_view(request):
    from urllib.parse import urlencode

    from .transport_dispatch import decline_job, maybe_expire_job, parse_token

    token = (request.GET.get("t") or "").strip()
    parsed = parse_token(token)
    if not parsed or parsed[0] != "decline":
        messages.error(request, "Link invalid sau expirat.")
        return redirect("home")
    _, job_id, uid = parsed
    if not request.user.is_authenticated:
        return redirect(reverse("login") + "?" + urlencode({"next": request.get_full_path()}))
    if request.user.pk != uid:
        messages.error(request, "Acest link este pentru alt cont.")
        return redirect("home")
    job = TransportDispatchJob.objects.filter(pk=job_id).first()
    if job:
        maybe_expire_job(job)
    ok, msg = decline_job(request, job_id, uid)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport_operator_panel")


@login_required
def transport_dispatch_cancel_user_view(request):
    from .transport_dispatch import cancel_job_by_user, parse_token

    token = (request.GET.get("t") or "").strip()
    parsed = parse_token(token)
    if not parsed or parsed[0] != "cancel_user":
        messages.error(request, "Link invalid sau expirat.")
        return redirect("home")
    _, job_id, uid = parsed
    if request.user.pk != uid:
        messages.error(request, "Acest link este pentru contul care a trimis cererea.")
        return redirect("home")
    ok, msg = cancel_job_by_user(request, job_id, uid)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport")


@login_required
@require_POST
def transport_op_release_job_view(request):
    """Transportator renunță după ce a acceptat — re-ofertă."""
    from .transport_dispatch import cancel_assignment_by_transporter

    try:
        job_id = int((request.POST.get("job_id") or "").strip() or "0")
    except ValueError:
        job_id = 0
    if not job_id:
        messages.error(request, "Lipsește cererea.")
        return redirect("transport_operator_panel")
    ok, msg = cancel_assignment_by_transporter(request, job_id, request.user.pk)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport_operator_panel")


def _transport_operator_panel_gate(request):
    """Returnează None dacă userul e colaborator transport; altfel redirect ca la panoul My transport."""
    ap = getattr(request.user, "account_profile", None)
    prof = getattr(request.user, "profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return redirect("home")
    if (getattr(prof, "collaborator_type", None) or "").strip().lower() != "transport":
        return redirect("collab_offers_control")
    return None


@login_required
@require_POST
@collab_magazin_required
def transport_op_accept_pending_view(request):
    """Acceptă oferta din panou (alternativă la linkul din email)."""
    from .transport_dispatch import accept_job, maybe_expire_job

    gate = _transport_operator_panel_gate(request)
    if gate is not None:
        return gate
    try:
        job_id = int((request.POST.get("job_id") or "").strip() or "0")
    except ValueError:
        job_id = 0
    if not job_id:
        messages.error(request, "Lipsește cererea.")
        return redirect("transport_operator_panel")
    job = TransportDispatchJob.objects.filter(pk=job_id).first()
    if job:
        maybe_expire_job(job)
    ok, msg = accept_job(request, job_id, request.user.pk)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport_operator_panel")


@login_required
@require_POST
@collab_magazin_required
def transport_op_decline_pending_view(request):
    """Refuză oferta din panou (alternativă la linkul din email)."""
    from .transport_dispatch import decline_job, maybe_expire_job

    gate = _transport_operator_panel_gate(request)
    if gate is not None:
        return gate
    try:
        job_id = int((request.POST.get("job_id") or "").strip() or "0")
    except ValueError:
        job_id = 0
    if not job_id:
        messages.error(request, "Lipsește cererea.")
        return redirect("transport_operator_panel")
    job = TransportDispatchJob.objects.filter(pk=job_id).first()
    if job:
        maybe_expire_job(job)
    ok, msg = decline_job(request, job_id, request.user.pk)
    if ok:
        messages.success(request, msg)
    else:
        messages.error(request, msg)
    return redirect("transport_operator_panel")


@login_required
@require_http_methods(["GET", "POST"])
def transport_dispatch_rate_view(request, job_id: int):
    """Formular evaluare după cursă (utilizator → transportator sau invers)."""
    from .transport_dispatch import submit_rating

    job = get_object_or_404(
        TransportDispatchJob.objects.select_related("tvr", "assigned_transporter", "tvr__user"),
        pk=job_id,
    )
    if job.status not in (
        TransportDispatchJob.STATUS_ASSIGNED,
        TransportDispatchJob.STATUS_COMPLETED,
    ):
        messages.error(
            request,
            "Evaluarea este disponibilă după ce un transportator a acceptat cererea și cursa s-a derulat.",
        )
        return redirect("transport")

    tvr = job.tvr
    op = job.assigned_transporter
    if not tvr.user_id or not op:
        messages.error(request, "Cerere incompletă.")
        return redirect("transport")

    is_client = request.user.pk == tvr.user_id
    is_op = request.user.pk == op.pk
    if not is_client and not is_op:
        messages.error(request, "Nu poți evalua această cerere.")
        return redirect("home")

    if is_client:
        direction = TransportTripRating.DIR_USER_TO_OP
        to_user = op
        role_title = "Evaluează transportatorul"
        hint = "Nota ta (medie) contribuie la reputația publică a transportatorului."
    else:
        direction = TransportTripRating.DIR_OP_TO_USER
        to_user = tvr.user
        role_title = "Evaluează clientul"
        hint = "Evaluarea este vizibilă doar ție, clientului și echipei admin (nu publică pe site)."

    existing = TransportTripRating.objects.filter(
        job=job, from_user=request.user, direction=direction
    ).first()

    if request.method == "POST":
        if existing:
            messages.info(request, "Ai trimis deja această evaluare.")
            return redirect(reverse("transport_dispatch_rate", kwargs={"job_id": job.pk}))
        try:
            stars = int((request.POST.get("stars") or "0").strip())
        except ValueError:
            stars = 0
        if stars < 1 or stars > 5:
            messages.error(request, "Alege între 1 și 5 stele.")
            return redirect(reverse("transport_dispatch_rate", kwargs={"job_id": job.pk}))
        comment = (request.POST.get("comment") or "").strip()
        submit_rating(job, request.user, to_user, direction, stars, comment)
        messages.success(request, "Mulțumim pentru evaluare.")
        return redirect(reverse("transport_dispatch_rate", kwargs={"job_id": job.pk}))

    return render(
        request,
        "anunturi/transport_dispatch_rate.html",
        {
            "job": job,
            "tvr": tvr,
            "to_user": to_user,
            "role_title": role_title,
            "hint": hint,
            "existing": existing,
            "direction": direction,
        },
    )


def custi_view(request):
    """Pagina cuștilor / harta cuștilor autocarului."""
    return render(request, "anunturi/custi.html", {})


def shop_view(request):
    """Pagina Shop (placeholder)."""
    return render(request, "anunturi/shop.html", {})


def shop_comanda_personalizate_view(request):
    """Pagina simplă de comandă produse personalizate (tricouri, șepci, zgărzi gravate etc.)."""
    return render(request, "anunturi/shop_comanda_personalizate.html", {})


# Plafon listă demo magazin foto – același ordin ca lista P2 din DB în pt_p2_list ([:200]).
SMF_FOTO_LIST_MAX = 200


def _shop_magazin_foto_slots_full():
    """Lista completă de sloturi demo (înlocuiești cu query model când există date reale)."""
    demo_names = [
        "Rex",
        "Bella",
        "Maximilian",
        "Luna",
        "Rocky",
        "Milo",
        "Daisy",
        "Charlie",
        "Coco",
        "Zara",
        "Thor",
        "Nala",
        "Oscar",
        "Maya",
        "Tedi",
        "Bruno",
        "Loki",
        "Numele foarte lung pentru test pe un singur rând",
        "Grivei",
        "Pufi",
    ]
    n = len(demo_names)
    out = []
    for i in range(SMF_FOTO_LIST_MAX):
        out.append(
            {
                "nume": demo_names[i % n],
                "pret_lei": 5 + (i % 4),
                "achizitii": 3 + (i * 11) % 140,
            }
        )
    return out


def shop_magazin_foto_view(request):
    """Magazin foto: același lot inițial ca P2 (PT_P2_PAGE_SIZE), restul prin shop_magazin_foto_more."""
    full = _shop_magazin_foto_slots_full()
    foto_slots = []
    for i in range(min(PT_P2_PAGE_SIZE, len(full))):
        row = dict(full[i])
        row["slot_idx"] = i
        row["ref_key"] = f"shop_foto:{i}"
        foto_slots.append(row)
    foto_has_more = len(full) > PT_P2_PAGE_SIZE
    foto_next_offset = PT_P2_PAGE_SIZE if foto_has_more else len(full)
    return render(
        request,
        "anunturi/shop_magazin_foto.html",
        {
            "foto_slots": foto_slots,
            "foto_has_more": foto_has_more,
            "foto_next_offset": foto_next_offset,
        },
    )


@require_http_methods(["GET"])
def shop_magazin_foto_more_view(request):
    """JSON: fragment HTML pentru următorul lot magazin foto (aceeași mărime lot ca P2)."""
    try:
        offset = int(request.GET.get("offset", "0") or "0")
    except (TypeError, ValueError):
        offset = 0
    offset = max(0, offset)
    full = _shop_magazin_foto_slots_full()
    batch_raw = full[offset : offset + PT_P2_PAGE_SIZE]
    batch = []
    for j, row in enumerate(batch_raw):
        r = dict(row)
        idx = offset + j
        r["slot_idx"] = idx
        r["ref_key"] = f"shop_foto:{idx}"
        batch.append(r)
    next_off = offset + len(batch)
    has_more = next_off < len(full)
    html = render_to_string(
        "anunturi/includes/smf_grid_chunk.html",
        {"slots": batch},
        request=request,
    )
    return JsonResponse({"ok": True, "html": html, "has_more": has_more, "next_offset": next_off})


def dog_profile_view(request, pk):
    """
    Fișa câinelui (PT) – afișează datele reale din AnimalListing.

    Layoutul din `pets-single.html` folosește un obiect `pet` cu câmpuri istorice
    (imagine, imagine_2, imagine_3, descriere etc.). Pentru lista MyPet / PT
    mapăm câmpurile din AnimalListing pe aceste nume, fără să schimbăm șablonul.
    """
    from django.shortcuts import get_object_or_404

    listing = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    _sync_animal_adoption_state(listing)

    # Mapare minimă către câmpurile folosite în șablonul existent
    pet = {
        "pk": listing.pk,
        "nume": listing.name or "—",
        "descriere": listing.cine_sunt or listing.probleme_medicale or "",
        "imagine": listing.photo_1,
        "imagine_2": listing.photo_2,
        "imagine_3": listing.photo_3,
        "video": listing.video,
        "imagine_fallback": DEMO_DOG_IMAGE,
        "judet": listing.county,
        "oras": listing.city,
        "sex": listing.sex,
        "species": listing.species,
        "size": listing.size,
        "age_label": listing.age_label,
        "color": listing.color,
        "sterilizat": listing.sterilizat,
        "carnet_sanatate": listing.carnet_sanatate,
        "cip": listing.cip,
        "vaccin": listing.vaccinat,
        "probleme_medicale": listing.probleme_medicale,
        "greutate_aprox": listing.greutate_aprox,
        "cine_sunt": listing.cine_sunt,
        "detalii_animal": listing.detalii_animal or "",
        # Trăsături potrivire adoptator (bife) – afișate în pets-single.html
        "trait_jucaus": listing.trait_jucaus,
        "trait_iubitor": listing.trait_iubitor,
        "trait_protector": listing.trait_protector,
        "trait_energic": listing.trait_energic,
        "trait_linistit": listing.trait_linistit,
        "trait_bun_copii": listing.trait_bun_copii,
        "trait_bun_caini": listing.trait_bun_caini,
        "trait_bun_pisici": listing.trait_bun_pisici,
        "trait_obisnuit_casa": listing.trait_obisnuit_casa,
        "trait_obisnuit_lesa": listing.trait_obisnuit_lesa,
        "trait_nu_latla": listing.trait_nu_latla,
        "trait_apartament": listing.trait_apartament,
        "trait_se_adapteaza": listing.trait_se_adapteaza,
        "trait_tolereaza_singur": listing.trait_tolereaza_singur,
        "trait_necesita_experienta": listing.trait_necesita_experienta,
        "adoption_state": listing.adoption_state,
        "adoption_state_label": _adoption_state_label(listing.adoption_state),
    }

    adoption_request_status = None
    if request.user.is_authenticated and request.user.pk != listing.owner_id:
        last_ar = (
            AdoptionRequest.objects.filter(animal=listing, adopter=request.user)
            .order_by("-created_at")
            .first()
        )
        if last_ar and last_ar.status in (
            AdoptionRequest.STATUS_PENDING,
            AdoptionRequest.STATUS_ACCEPTED,
            AdoptionRequest.STATUS_FINALIZED,
        ):
            adoption_request_status = last_ar.status

    # Promovare plătită: orice utilizator autentificat (sponsor), nu doar proprietarul.
    promote_allowed = bool(
        request.user.is_authenticated
        and listing.is_published
        and (listing.species or "").strip().lower() in ("dog", "cat")
    )

    viewer_can_adopt = False
    if request.user.is_authenticated and request.user.pk != listing.owner_id:
        ap = getattr(request.user, "account_profile", None)
        if ap:
            viewer_can_adopt = bool(ap.can_adopt_animals)
        else:
            # Fallback defensiv pentru conturi vechi fără profil rol.
            viewer_can_adopt = True

    after_transport = (request.GET.get("after_transport") == "1")
    has_county = _adopter_has_county_for_transport(request.user) if request.user.is_authenticated else False

    can_send_pet_message = bool(
        request.user.is_authenticated
        and request.user.pk != listing.owner_id
        and viewer_can_adopt
        and listing.adoption_state != AnimalListing.ADOPTION_STATE_ADOPTED
    )
    # Buton „VREAU SĂ ADOPT”: separat de mesaje — vizibil și neautentificaților (login la click), ascuns doar owner / adoptat.
    show_pet_adopt_corner = bool(
        listing.adoption_state != AnimalListing.ADOPTION_STATE_ADOPTED
        and (
            not request.user.is_authenticated
            or request.user.pk != listing.owner_id
        )
    )
    ctx = {
        "pet": pet,
        "can_send_pet_message": can_send_pet_message,
        "show_pet_adopt_corner": show_pet_adopt_corner,
        "pet_owner_id": listing.owner_id,
        "adoption_request_status": adoption_request_status,
        # Hibrid: mesaje înainte de accept — același prag ca can_send_pet_message (șabloane vechi).
        "adopter_messaging_unlocked": can_send_pet_message,
        "promote_allowed": promote_allowed,
        "adoption_after_transport": bool(after_transport),
        "adoption_transport_option_available": bool(has_county and not after_transport),
    }
    return render(request, "anunturi/pets-single.html", ctx)


@login_required
def promo_a2_order_view(request, pk):
    """
    Notă comandă promovare A2 (v1).
    Poate plăti orice cont autentificat (sponsor); anunțul trebuie publicat, câine sau pisică.
    """
    pet = get_object_or_404(AnimalListing, pk=pk)
    if not pet.is_published:
        messages.info(
            request,
            "Anunțul trebuie să fie publicat înainte de promovare.",
        )
        return _promo_a2_flow_redirect(request, pet)

    species_ok = (pet.species or "").strip().lower() in ("dog", "cat")
    if not species_ok:
        messages.info(
            request,
            "Promovarea A2 este disponibilă doar pentru anunțuri câine sau pisică, publicate.",
        )
        return _promo_a2_flow_redirect(request, pet)

    price_map = {"6h": 10, "12h": 15}
    order_submitted = False
    start_date = timezone.localdate().isoformat()
    package = "6h"
    quantity = 1
    unit_price = price_map[package]
    total_price = unit_price * quantity
    if request.method == "POST":
        package = (request.POST.get("package") or "6h").strip()
        schedule = "intercalat"
        payment_method = "card"
        start_date_raw = (request.POST.get("start_date") or "").strip()
        quantity_raw = (request.POST.get("quantity") or "1").strip()
        if package not in ("6h", "12h"):
            package = "6h"
        try:
            quantity = int(quantity_raw)
        except ValueError:
            quantity = 1
        if quantity < 1:
            quantity = 1
        if quantity > 30:
            quantity = 30
        unit_price = price_map[package]
        total_price = unit_price * quantity
        try:
            selected_start_date = date.fromisoformat(start_date_raw)
            if selected_start_date < timezone.localdate():
                raise ValueError("date in the past")
            start_date = selected_start_date.isoformat()
        except ValueError:
            messages.error(request, "Selectează o dată de start validă (astăzi sau o dată viitoare).")
            return render(
                request,
                "anunturi/promo_a2_order.html",
                {
                    "pet": pet,
                    "order_submitted": order_submitted,
                    "package": package,
                    "schedule": schedule,
                    "payment_method": payment_method,
                    "start_date": start_date,
                    "quantity": quantity,
                    "unit_price": unit_price,
                    "total_price": total_price,
                    "today_iso": timezone.localdate().isoformat(),
                },
            )
        starts_at, ends_at = _promo_a2_compute_window(selected_start_date, package, quantity)
        payer_name = (request.user.get_full_name() or request.user.username or "").strip()
        order = PromoA2Order.objects.create(
            pet=pet,
            payer_user=request.user,
            payer_email=(request.user.email or "").strip(),
            payer_name_snapshot=payer_name,
            package=package,
            quantity=quantity,
            unit_price=unit_price,
            total_price=total_price,
            payment_method=payment_method,
            schedule=schedule,
            slot_code="A2",
            start_date=selected_start_date,
            starts_at=starts_at,
            ends_at=ends_at,
            status=PromoA2Order.STATUS_CHECKOUT_PENDING,
            payment_provider="demo",
        )

        # v1: pregătim datele pentru checkout demo securizat
        request.session["promo_a2_checkout"] = {
            "order_id": order.pk,
            "pet_id": pet.pk,
            "package": package,
            "schedule": schedule,
            "payment_method": payment_method,
            "start_date": start_date,
            "quantity": quantity,
            "unit_price": unit_price,
            "total_price": total_price,
        }
        return redirect("promo_a2_checkout_demo", pk=pet.pk)

    ctx_order = {
        "pet": pet,
        "order_submitted": order_submitted,
        "package": "6h",
        "schedule": "intercalat",
        "payment_method": "card",
        "start_date": start_date,
        "quantity": quantity,
        "unit_price": unit_price,
        "total_price": total_price,
        "today_iso": timezone.localdate().isoformat(),
    }
    ctx_order.update(_promo_a2_nav_context(request.user))
    return render(request, "anunturi/promo_a2_order.html", ctx_order)


@login_required
def promo_a2_checkout_demo_view(request, pk):
    pet = get_object_or_404(AnimalListing, pk=pk)
    if not pet.is_published or (pet.species or "").strip().lower() not in ("dog", "cat"):
        messages.info(
            request,
            "Promovarea nu este disponibilă pentru acest anunț.",
        )
        return _promo_a2_flow_redirect(request, pet)
    checkout = request.session.get("promo_a2_checkout") or {}
    if checkout.get("pet_id") != pet.pk:
        messages.info(request, "Completează mai întâi nota de comandă pentru a continua către plata demo.")
        return redirect("promo_a2_order", pk=pet.pk)
    order = None
    order_id = checkout.get("order_id")
    if order_id:
        order = PromoA2Order.objects.filter(pk=order_id, payer_user=request.user, pet=pet).first()
    if order is None:
        messages.info(request, "Nu există o comandă promo validă pentru această sesiune.")
        return redirect("promo_a2_order", pk=pet.pk)
    ctx_checkout = {
        "pet": pet,
        "package": checkout.get("package", "6h"),
        "quantity": checkout.get("quantity", 1),
        "unit_price": checkout.get("unit_price", 10),
        "total_price": checkout.get("total_price", 10),
        "start_date": checkout.get("start_date", ""),
        "schedule": checkout.get("schedule", "intercalat"),
        "payment_method": checkout.get("payment_method", "card"),
        "promo_order_id": order.pk,
    }
    ctx_checkout.update(_promo_a2_nav_context(request.user))
    return render(request, "anunturi/promo_a2_checkout_demo.html", ctx_checkout)


@login_required
def promo_a2_checkout_demo_success_view(request, pk):
    pet = get_object_or_404(AnimalListing, pk=pk)
    if not pet.is_published or (pet.species or "").strip().lower() not in ("dog", "cat"):
        messages.info(
            request,
            "Promovarea nu este disponibilă pentru acest anunț.",
        )
        return _promo_a2_flow_redirect(request, pet)
    checkout = request.session.get("promo_a2_checkout") or {}
    if checkout.get("pet_id") != pet.pk:
        messages.info(request, "Nu există o sesiune activă de plată demo pentru acest anunț.")
        return redirect("promo_a2_order", pk=pet.pk)
    order = None
    order_id = checkout.get("order_id")
    if order_id:
        order = PromoA2Order.objects.filter(pk=order_id, payer_user=request.user, pet=pet).first()
    if order is None:
        messages.info(request, "Comanda promo nu a fost găsită.")
        return redirect("promo_a2_order", pk=pet.pk)
    if order.status != PromoA2Order.STATUS_PAID:
        order.status = PromoA2Order.STATUS_PAID
        order.payment_ref = f"DEMO-{order.pk}"
        order.save(update_fields=["status", "payment_ref", "updated_at"])
        pet_label_po = (pet.name or f"Animal #{pet.pk}").strip()
        _inbox.create_inbox_notification(
            request.user,
            _inbox.KIND_PROMO_A2_PAID,
            "Plată reușită — promovare anunț",
            f"Comandă #{order.pk} pentru „{pet_label_po}” (demo).",
            link_url=reverse("mypet"),
            metadata={"promo_order_id": order.pk, "pet_id": pet.pk},
        )

    ctx = {
        "pet": pet,
        "package": checkout.get("package", "6h"),
        "quantity": checkout.get("quantity", 1),
        "unit_price": checkout.get("unit_price", 10),
        "total_price": checkout.get("total_price", 10),
        "start_date": checkout.get("start_date", ""),
        "promo_order_id": order.pk,
    }
    ctx.update(_promo_a2_nav_context(request.user))
    request.session.pop("promo_a2_checkout", None)
    return render(request, "anunturi/promo_a2_checkout_demo_success.html", ctx)


def account_view(request):
    """Pagina cont utilizator: date completate la înscriere + rol."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('account')}")

    user = request.user
    account_profile = getattr(user, "account_profile", None)
    # Întotdeauna citim profilul din DB (nu din cache) ca poza salvată să apară la revenire
    user_profile = UserProfile.objects.filter(user=user).first()
    if account_profile and account_profile.role == AccountProfile.ROLE_PF and user_profile is None:
        user_profile = UserProfile.objects.create(user=user)
    ctx = {
        "account_profile": account_profile,
        "user_profile": user_profile,
    }
    if user_profile and (user_profile.collaborator_type or "").strip().lower() == "transport":
        ctx["transport_operator_profile"] = TransportOperatorProfile.objects.filter(user=user).first()
    # Linkuri evaluare transport (client): joburi asignate fără notă user→transportator
    if request.user.is_authenticated:
        pending_tr = []
        for dj in (
            TransportDispatchJob.objects.filter(
                tvr__user=user,
                status__in=(
                    TransportDispatchJob.STATUS_ASSIGNED,
                    TransportDispatchJob.STATUS_COMPLETED,
                ),
            )
            .select_related("tvr", "assigned_transporter")
            .order_by("-assigned_at")[:12]
        ):
            if not TransportTripRating.objects.filter(
                job=dj,
                from_user=user,
                direction=TransportTripRating.DIR_USER_TO_OP,
            ).exists():
                pending_tr.append(dj)
        if pending_tr:
            ctx["transport_pending_rating_jobs"] = pending_tr
    if _user_can_use_publicitate(request):
        pub_rows = []
        for o in (
            PublicitateOrder.objects.filter(user=request.user, status=PublicitateOrder.STATUS_PAID)
            .order_by("-pk")[:24]
        ):
            if not PublicitateOrderCreativeAccess.objects.filter(order=o).exists():
                continue
            pending = PublicitateLineCreative.objects.filter(
                line__order=o,
                status=PublicitateLineCreative.STATUS_PENDING,
            ).exists()
            pub_rows.append(
                {
                    "order": o,
                    "materials_url": reverse("publicitate_creative_order", kwargs={"order_id": o.pk}),
                    "pending": pending,
                }
            )
        if pub_rows:
            ctx["pub_paid_creative_orders"] = pub_rows
    # Statistici + form_prefill pentru PF/ONG/Colaborator (caseta modificare profil în pagină)
    if account_profile and account_profile.role in (AccountProfile.ROLE_PF, AccountProfile.ROLE_ORG, AccountProfile.ROLE_COLLAB):
        ctx["animale_in_grija"] = AnimalListing.objects.filter(owner=user).count()
        ctx["adoptii_finalizate"] = UserAdoption.objects.filter(user=user, status="completed").count()
        if "edit_errors" in request.session:
            ctx["edit_errors"] = request.session.pop("edit_errors", [])
            ctx["form_prefill"] = request.session.pop("edit_prefill", {})
            # dacă avem și prefill pentru firmă, îl populăm de asemenea
            ctx["form_prefill_firma"] = request.session.pop("edit_prefill_firma", None)
        else:
            phone_country, phone = _parse_phone_for_edit(user_profile.phone if user_profile else "")
            ctx["form_prefill"] = {
                "first_name": user.first_name or "",
                "last_name": user.last_name or "",
                "email": user.email or "",
                "phone_country": phone_country,
                "phone": phone,
                "judet": user_profile.judet if user_profile else "",
                "oras": user_profile.oras if user_profile else "",
                "accept_termeni": user_profile.accept_termeni if user_profile else False,
                "accept_gdpr": user_profile.accept_gdpr if user_profile else False,
                "email_opt_in_wishlist": user_profile.email_opt_in_wishlist if user_profile else False,
            }
    ctx["account_updated"] = request.GET.get("updated") == "1"
    ctx["username_updated"] = request.GET.get("username_updated") == "1"
    # Mesaj/sugestii după încercare schimbare username (PF)
    if account_profile and account_profile.role == AccountProfile.ROLE_PF:
        if "username_error" in request.session:
            ctx["username_error"] = request.session.pop("username_error", "")
            ctx["username_suggestions"] = request.session.pop("username_suggestions", [])
            ctx["username_tried"] = request.session.pop("username_tried", "")
            ctx["show_username_edit"] = True
    response = render(request, "anunturi/account.html", ctx)
    # Fără cache – ca la revenire pe pagină să se vadă poza salvată, nu versiunea veche
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    response["Expires"] = "0"
    return response


def _unified_inbox_owner_pet_message_rows(user, limit=20):
    """Rânduri rezumat: mesaje MyPet ca proprietar, grupate pe animal."""
    active_since = _messages_active_since()
    pet_ids = list(AnimalListing.objects.filter(owner=user).values_list("pk", flat=True))
    if not pet_ids:
        return []
    agg = (
        PetMessage.objects.filter(animal_id__in=pet_ids, created_at__gte=active_since)
        .filter(Q(sender=user) | Q(receiver=user))
        .values("animal_id")
        .annotate(
            last_at=Max("created_at"),
            unread=Count("id", filter=Q(receiver=user, is_read=False)),
        )
        .order_by("-last_at")[:limit]
    )
    animal_ids = [int(x["animal_id"]) for x in agg]
    pets = {p.pk: p for p in AnimalListing.objects.filter(pk__in=animal_ids)}
    out = []
    for row in agg:
        aid = int(row["animal_id"])
        pet = pets.get(aid)
        if not pet:
            continue
        last_msg = (
            PetMessage.objects.filter(animal_id=aid, created_at__gte=active_since)
            .filter(Q(sender=user) | Q(receiver=user))
            .order_by("-created_at")
            .first()
        )
        body = (last_msg.body or "") if last_msg else ""
        preview = (body[:100] + "…") if len(body) > 100 else body
        out.append(
            {
                "animal_id": aid,
                "name": pet.name or f"Pet #{aid}",
                "unread": int(row.get("unread") or 0),
                "preview": preview,
                "open_url": reverse("mypet") + f"?open_messages=1&open_pet_messages={aid}",
            }
        )
    aids = [int(r["animal_id"]) for r in out]
    if aids:
        ur = {
            int(x["animal_id"]): x["t"]
            for x in PetMessage.objects.filter(
                animal_id__in=aids,
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            )
            .values("animal_id")
            .annotate(t=Max("created_at"))
        }
        ia = {
            int(x["animal_id"]): x["t"]
            for x in PetMessage.objects.filter(
                animal_id__in=aids,
                receiver=user,
                created_at__gte=active_since,
            )
            .values("animal_id")
            .annotate(t=Max("created_at"))
        }

        def _owner_row_ts(r):
            aid = int(r["animal_id"])
            u = int(r.get("unread") or 0)
            if u > 0:
                return ur.get(aid) or ia.get(aid)
            return ia.get(aid)

        def _owner_sort_key(r):
            t = _owner_row_ts(r)
            return (0 if int(r.get("unread") or 0) > 0 else 1, -(t.timestamp() if t else 0))

        out.sort(key=_owner_sort_key)
    return out


def _unified_inbox_adopter_pet_message_rows(user, limit=20):
    """Rânduri rezumat: mesaje ca adoptator, grupate pe animal."""
    active_since = _messages_active_since()
    base = (
        PetMessage.objects.filter(Q(sender=user) | Q(receiver=user), created_at__gte=active_since)
        .exclude(animal__owner=user)
    )
    agg = (
        base.values("animal_id")
        .annotate(
            last_at=Max("created_at"),
            unread=Count("id", filter=Q(receiver=user, is_read=False)),
        )
        .order_by("-last_at")[:limit]
    )
    animal_ids = [int(x["animal_id"]) for x in agg]
    pets = {p.pk: p for p in AnimalListing.objects.filter(pk__in=animal_ids).select_related("owner")}
    out = []
    for row in agg:
        aid = int(row["animal_id"])
        pet = pets.get(aid)
        if not pet:
            continue
        owner = pet.owner
        last_msg = (
            PetMessage.objects.filter(animal_id=aid, created_at__gte=active_since)
            .filter(Q(sender=user, receiver=owner) | Q(sender=owner, receiver=user))
            .order_by("-created_at")
            .first()
        )
        body = (last_msg.body or "") if last_msg else ""
        preview = (body[:100] + "…") if len(body) > 100 else body
        owner_name = (f"{owner.first_name} {owner.last_name}").strip() if owner else ""
        owner_name = owner_name or (owner.username if owner else "Proprietar")
        out.append(
            {
                "animal_id": aid,
                "name": pet.name or f"Pet #{aid}",
                "subtitle": owner_name,
                "unread": int(row.get("unread") or 0),
                "preview": preview,
                "open_url": reverse("mypet") + f"?open_messages=1&open_adopter_animal={aid}",
            }
        )
    if out:
        ur_map = {}
        ia_map = {}
        for r in out:
            aid = int(r["animal_id"])
            pet = pets.get(aid)
            if not pet or not pet.owner_id:
                continue
            oid = pet.owner_id
            lu = (
                PetMessage.objects.filter(
                    animal_id=aid,
                    sender_id=oid,
                    receiver=user,
                    is_read=False,
                    created_at__gte=active_since,
                )
                .aggregate(t=Max("created_at"))
                .get("t")
            )
            la = (
                PetMessage.objects.filter(
                    animal_id=aid,
                    sender_id=oid,
                    receiver=user,
                    created_at__gte=active_since,
                )
                .aggregate(t=Max("created_at"))
                .get("t")
            )
            ur_map[aid] = lu
            ia_map[aid] = la

        def _adopter_row_ts(row):
            aid = int(row["animal_id"])
            u = int(row.get("unread") or 0)
            if u > 0:
                return ur_map.get(aid) or ia_map.get(aid)
            return ia_map.get(aid)

        def _adopter_sort_key(r):
            t = _adopter_row_ts(r)
            return (0 if int(r.get("unread") or 0) > 0 else 1, -(t.timestamp() if t else 0))

        out.sort(key=_adopter_sort_key)
    return out


def _unified_inbox_collab_client_rows(user, limit=20):
    """Rânduri rezumat: thread-uri mesaje Servicii (client ↔ colaborator)."""
    active_since = _messages_active_since()
    base = CollabServiceMessage.objects.filter(Q(sender=user) | Q(receiver=user)).exclude(
        collaborator=user
    )
    base = base.filter(created_at__gte=active_since)
    threads_map = {}
    for m in base.order_by("-created_at"):
        key = (m.collaborator_id, m.context_type, m.context_ref or "")
        if key not in threads_map:
            threads_map[key] = m
    UserModel = get_user_model()
    out = []
    for (collab_id, ct, cref), last in threads_map.items():
        collab_u = UserModel.objects.filter(pk=collab_id).first()
        cname = ""
        if collab_u:
            cname = (f"{collab_u.first_name} {collab_u.last_name}").strip() or collab_u.username
        unread = (
            CollabServiceMessage.objects.filter(
                collaborator_id=collab_id,
                context_type=ct,
                context_ref=cref,
                sender_id=collab_id,
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            ).count()
        )
        last_unread_in = (
            CollabServiceMessage.objects.filter(
                collaborator_id=collab_id,
                context_type=ct,
                context_ref=cref,
                sender_id=collab_id,
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            )
            .aggregate(t=Max("created_at"))
            .get("t")
        )
        last_in_any = (
            CollabServiceMessage.objects.filter(
                collaborator_id=collab_id,
                context_type=ct,
                context_ref=cref,
                sender_id=collab_id,
                receiver=user,
                created_at__gte=active_since,
            )
            .aggregate(t=Max("created_at"))
            .get("t")
        )
        preview = last.body or ""
        if len(preview) > 80:
            preview = preview[:80] + "…"
        sort_ts = last_unread_in if unread > 0 else (last_in_any or last.created_at)
        out.append(
            {
                "collaborator_id": collab_id,
                "collaborator_name": cname or f"Colaborator {collab_id}",
                "context_type": ct,
                "context_ref": cref or "",
                "context_label": _collab_context_label(ct),
                "unread": unread,
                "preview": preview,
                "last_at": last.created_at,
                "_sort_ts": sort_ts,
            }
        )
    out.sort(
        key=lambda x: (
            0 if x["unread"] > 0 else 1,
            -((x["_sort_ts"].timestamp() if x.get("_sort_ts") else 0)),
        )
    )
    for x in out:
        x.pop("_sort_ts", None)
    return out[:limit]


@login_required
def adoption_bonus_offers_portal_view(request):
    """Portal adoptator: oferte bonus alese la adopție, coduri, link ofertă, date contact partener."""
    user = request.user
    selections = list(
        AdoptionBonusSelection.objects.filter(adoption_request__adopter=user)
        .select_related("offer", "offer__collaborator", "adoption_request", "adoption_request__animal")
        .order_by("-adoption_request__finalized_at", "-adoption_request__accepted_at", "-created_at")
    )
    status_lbl = dict(AdoptionRequest.STATUS_CHOICES)
    kind_lbl = dict(CollaboratorServiceOffer.PARTNER_KIND_CHOICES)
    rows = []
    for sel in selections:
        ar = sel.adoption_request
        pet = ar.animal
        off = sel.offer
        collab = off.collaborator
        code = (sel.redemption_code or "").strip()
        rows.append(
            {
                "selection": sel,
                "request": ar,
                "pet": pet,
                "offer": off,
                "collaborator": collab,
                "partner_kind_display": kind_lbl.get(sel.partner_kind, sel.partner_kind),
                "code_display": code if code else "— (după finalizare adopție)",
                "status_display": status_lbl.get(ar.status, ar.status),
                "contact_lines": _adoption_contact_block(collab).splitlines(),
            }
        )
    response = render(
        request,
        "anunturi/adoption_bonus_portal.html",
        {
            "bonus_rows": rows,
            "bonus_empty": not rows,
            "has_adoption_activity": AdoptionRequest.objects.filter(adopter=user).exists(),
        },
    )
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    return response


@login_required
def unified_inbox_view(request):
    """Inbox mesaje: trei canale + listă notificări sistem (UserInboxNotification), ușor de citit fără admin."""
    user = request.user
    ap = getattr(user, "account_profile", None)
    role = getattr(ap, "role", None) if ap else None
    prof = getattr(user, "profile", None)
    collab_tip = (getattr(prof, "collaborator_type", None) or "").strip().lower()
    hide_inbox_channel_cards = (request.GET.get("from_transport") == "1") or (
        role == AccountProfile.ROLE_COLLAB and collab_tip == "transport"
    )
    mypet_ok = _user_can_use_mypet(request)
    active_since = _messages_active_since()
    inbox_owner_pet_unread = (
        PetMessage.objects.filter(
            receiver=user,
            is_read=False,
            created_at__gte=active_since,
            animal__owner=user,
        ).count()
    )
    inbox_adopter_pet_unread = (
        PetMessage.objects.filter(receiver=user, is_read=False, created_at__gte=active_since)
        .exclude(animal__owner=user)
        .count()
    )
    owner_rows = _unified_inbox_owner_pet_message_rows(user) if mypet_ok else []
    adopter_rows = _unified_inbox_adopter_pet_message_rows(user) if mypet_ok else []
    collab_rows = _unified_inbox_collab_client_rows(user)
    has_adoption_activity = AdoptionRequest.objects.filter(adopter=user).exists()
    inbox_system_notifications = list(
        UserInboxNotification.objects.filter(user=user, created_at__gte=active_since).order_by("-created_at")[:50]
    )
    ctx = {
        "inbox_owner_pet_unread": inbox_owner_pet_unread,
        "inbox_adopter_pet_unread": inbox_adopter_pet_unread,
        "inbox_owner_thread_rows": owner_rows,
        "inbox_adopter_thread_rows": adopter_rows,
        "inbox_collab_thread_rows": collab_rows,
        "inbox_system_notifications": inbox_system_notifications,
        "quick_mypet_messages_url": (reverse("mypet") + "?open_messages=1") if mypet_ok else "",
        "quick_adopter_url": ((reverse("mypet") + "?open_messages=1") if mypet_ok else ""),
        "quick_adoption_bonus_url": reverse("adoption_bonus_portal") if has_adoption_activity else "",
        "quick_collab_business_url": (
            (reverse("collab_offers_control") + "?open_messages=1")
            if role == AccountProfile.ROLE_COLLAB
            else ""
        ),
        "mypet_ok": mypet_ok,
        "hide_inbox_channel_cards": hide_inbox_channel_cards,
    }
    return render(request, "anunturi/unified_inbox.html", ctx)


@login_required
@require_POST
@csrf_protect
def unified_inbox_mark_read_view(request):
    raw = (request.POST.get("notification_id") or "").strip()
    if raw == "all":
        UserInboxNotification.objects.filter(user=request.user, is_read=False).update(is_read=True)
    elif raw.isdigit():
        UserInboxNotification.objects.filter(pk=int(raw), user=request.user).update(is_read=True)
    next_url = request.POST.get("next") or ""
    safe = _safe_local_redirect_path(next_url)
    return redirect(safe or reverse("unified_inbox"))


@login_required
def admin_analysis_home_view(request):
    """Pagina centrală Analiză (doar pentru admin/staff)."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    view_as_role = request.session.get("view_as_role") or None
    view_as_collab_tip = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
    if view_as_collab_tip not in ("cabinet", "servicii", "magazin", "transport"):
        view_as_collab_tip = "servicii"
    return render(
        request,
        "anunturi/admin_analysis_home.html",
        {
            "view_as_role": view_as_role,
            "view_as_collab_tip": view_as_collab_tip,
        },
    )


def admin_analysis_set_view_as_view(request):
    """Setează „Vezi ca” (doar staff). Opțional `tip` pentru colaborator: cabinet|servicii|magazin."""
    if not (request.user.is_authenticated and (request.user.is_superuser or request.user.is_staff)):
        return redirect(reverse("home"))
    role = (request.GET.get("role") or "").strip()
    tip = (request.GET.get("tip") or "").strip().lower()
    if role in ("pf", "org", "collaborator"):
        request.session["view_as_role"] = role
        if role == "collaborator":
            if tip in ("cabinet", "servicii", "magazin", "transport"):
                request.session["view_as_collab_tip"] = tip
            elif not request.session.get("view_as_collab_tip"):
                request.session["view_as_collab_tip"] = "servicii"
        else:
            request.session.pop("view_as_collab_tip", None)
    else:
        request.session.pop("view_as_role", None)
        request.session.pop("view_as_collab_tip", None)
    return redirect(reverse("admin_analysis_home"))


@login_required
def admin_analysis_dogs_view(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    return render(request, "anunturi/admin_analysis_dogs.html", {})


@login_required
def admin_analysis_requests_view(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    return render(request, "anunturi/admin_analysis_requests.html", {})


@login_required
def admin_analysis_users_view(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    return render(request, "anunturi/admin_analysis_users.html", {})


@login_required
def admin_analysis_alerts_view(request):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    return render(request, "anunturi/admin_analysis_alerts.html", {})


# Reclama: hărți sloturi per „pagină” (nu navigăm către site-ul public, ci între sub-rute /reclama/...).
RECLAMA_WIRE_TEMPLATES = {
    "home": "anunturi/reclama/wires/home.html",
    "pt": "anunturi/reclama/wires/pt.html",
    "servicii": "anunturi/reclama/wires/servicii.html",
    "transport": "anunturi/reclama/wires/transport.html",
    "shop": "anunturi/reclama/wires/shop.html",
    "mypet": "anunturi/reclama/wires/mypet.html",
    "magazinul_meu": "anunturi/reclama/wires/generic.html",
    "i_love": "anunturi/reclama/wires/i_love.html",
    "termeni": "anunturi/reclama/wires/generic.html",
    "contact": "anunturi/reclama/wires/generic.html",
    "mesaje": "anunturi/reclama/wires/generic.html",
}

# (secțiune, titlu browser, etichetă Caseta 2)
RECLAMA_META = {
    "home": ("Acasă", "Caseta 2 – schemă HOME"),
    "pt": ("Prietenul tău", "Caseta 2 – schemă Prietenul tău (PW)"),
    "servicii": ("Servicii", "Caseta 2 – schemă Servicii (SW)"),
    "transport": ("Transport", "Caseta 2 – schemă Transport (TW)"),
    "shop": ("Shop", "Caseta 2 – schemă Shop (SHW)"),
    "mypet": ("MyPet", "Caseta 2 – schemă MyPet (sloturi)"),
    "magazinul_meu": ("Magazinul meu", "Caseta 2 – schemă Magazinul meu (sloturi)"),
    "i_love": ("I Love", "Caseta 2 – schemă I Love (sloturi)"),
    "termeni": ("Termeni", "Caseta 2 – schemă Termeni (sloturi)"),
    "contact": ("Contact", "Caseta 2 – schemă Contact (sloturi)"),
    "mesaje": ("Mesaje", "Caseta 2 – schemă Mesaje (sloturi)"),
}


@login_required
def reclama_staff_view(request, reclama_section="home"):
    """Pagină Reclama (doar staff). Non-staff → Acasă. Sub-rute: hărți sloturi per zonă, nu paginile publice."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    section = (reclama_section or "home").strip().lower()
    if section not in RECLAMA_WIRE_TEMPLATES:
        return redirect(reverse("reclama_staff"))

    if request.method == "POST" and section == "home":
        action = (request.POST.get("action") or "").strip().lower()
        slot_code = (request.POST.get("slot") or "").strip()
        if action == "save_burtiera_note" and slot_code == "Burtieră":
            text = (request.POST.get("burtiera_note") or "").strip()
            speed_raw = (request.POST.get("burtiera_speed_seconds") or "").strip()
            try:
                speed_val = int(speed_raw)
            except (TypeError, ValueError):
                speed_val = HOME_BURTIERA_DEFAULT_SPEED_SECONDS
            speed_val = max(8, min(120, speed_val))
            note, _created = ReclamaSlotNote.objects.get_or_create(
                section="home",
                slot_code="Burtieră",
                defaults={"text": text, "updated_by": request.user},
            )
            if not _created:
                note.text = text
                note.updated_by = request.user
                note.save(update_fields=["text", "updated_by", "updated_at"])
            speed_note, speed_created = ReclamaSlotNote.objects.get_or_create(
                section="home",
                slot_code="BurtierăSpeed",
                defaults={"text": str(speed_val), "updated_by": request.user},
            )
            if not speed_created:
                speed_note.text = str(speed_val)
                speed_note.updated_by = request.user
                speed_note.save(update_fields=["text", "updated_by", "updated_at"])
            messages.success(request, "Textul pentru burtieră a fost salvat.")
            return redirect(f"{reverse('reclama_staff')}?slot=Burtieră")
    meta = RECLAMA_META.get(section, ("Reclama", "Caseta 2"))
    wire_template = RECLAMA_WIRE_TEMPLATES[section]
    now = timezone.now()
    active_orders = list(
        PromoA2Order.objects.filter(
            status=PromoA2Order.STATUS_PAID,
            starts_at__isnull=False,
            ends_at__isnull=False,
            starts_at__lte=now,
            ends_at__gt=now,
        )
        .select_related("pet", "payer_user")
        .order_by("ends_at", "-created_at")[:80]
    )
    expiring_soon = 0
    for o in active_orders:
        try:
            rem = int((o.ends_at - now).total_seconds())
        except Exception:
            rem = 0
        o.remaining_seconds = max(0, rem)
        if rem <= 3600:
            expiring_soon += 1
    paid_today = PromoA2Order.objects.filter(
        status=PromoA2Order.STATUS_PAID,
        updated_at__date=timezone.localdate(),
    ).count()

    slot_allowed = {
        "A2.1", "A2.2", "A2.3", "A2.4", "A2.5", "A2.6",
        "A2.7", "A2.8", "A2.9", "A2.10", "A2.11", "A2.12",
        "A5.1", "A5.2", "A5.3", "A6.1", "A6.2", "A6.3", "Burtieră",
    }
    selected_slot = (request.GET.get("slot") or "").strip()
    raw_months = request.GET.getlist("months")
    selected_months = []
    for m in raw_months:
        try:
            v = int((m or "").strip())
        except (TypeError, ValueError):
            continue
        if 1 <= v <= 12 and v not in selected_months:
            selected_months.append(v)
    if not selected_months:
        selected_months = list(range(1, 13))
    if selected_slot not in slot_allowed:
        selected_slot = ""
    if selected_slot in {"A1", "A3"}:
        selected_slot = ""

    history_rows = []
    history_total_orders = 0
    history_total_revenue = 0
    burtiera_note_text = ""
    if section == "home" and selected_slot:
        if selected_slot == "Burtieră":
            # În editorul C3 afișăm textul curent efectiv din burtieră (fie notă salvată, fie default).
            burtiera_note_text = _get_home_burtiera_text()
        else:
            current_year = timezone.localdate().year
            month_qs = (
                PromoA2Order.objects.filter(
                    status=PromoA2Order.STATUS_PAID,
                    slot_code=selected_slot,
                    starts_at__year=current_year,
                    starts_at__month__in=selected_months,
                )
                .annotate(month=TruncMonth("starts_at"))
                .values("month")
                .annotate(total_orders=Count("id"), total_revenue=Sum("total_price"))
                .order_by("month")
            )
            history_rows = list(month_qs)
            for r in history_rows:
                history_total_orders += int(r.get("total_orders") or 0)
                history_total_revenue += int(r.get("total_revenue") or 0)
    ctx = {
        "reclama_section": section,
        "reclama_page_title": meta[0],
        "reclama_caseta2_label": meta[1],
        "reclama_wire_template": wire_template,
        "promo_active_orders": active_orders,
        "promo_active_total": len(active_orders),
        "promo_expiring_soon": expiring_soon,
        "promo_paid_today": paid_today,
        "reclama_selected_slot": selected_slot,
        "reclama_selected_months": selected_months,
        "reclama_month_options": list(range(1, 13)),
        "reclama_slot_history_rows": history_rows,
        "reclama_slot_history_total_orders": history_total_orders,
        "reclama_slot_history_total_revenue": history_total_revenue,
        "reclama_burtiera_note_text": burtiera_note_text,
        "reclama_burtiera_display_text": _get_home_burtiera_text(),
        "reclama_burtiera_speed_seconds": _get_home_burtiera_speed_seconds(),
        "pub_site_contact_email": (
            (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or "euadopt@gmail.com"
        ),
    }
    if section == "pt":
        ctx["pub_strip_p1_cells"] = _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P1)
        ctx["pub_strip_p3_cells"] = _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P3)
    elif section == "servicii":
        ctx["pub_strip_s1_cells"] = _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S1)
        ctx["pub_strip_s7_cells"] = _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S7)
    return render(request, "anunturi/reclama_staff.html", ctx)


@login_required
@require_POST
def reclama_promo_export_summary_now_view(request, order_id: int):
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect("home")
    order = get_object_or_404(PromoA2Order.objects.select_related("pet"), pk=order_id)
    try:
        sent = _promo_a2_send_summary_email(order)
    except Exception:
        logging.getLogger(__name__).exception("promo_a2_manual_summary_email_fail order=%s", order.pk)
        sent = False
    if sent:
        order.summary_manual_sent_at = timezone.now()
        order.save(update_fields=["summary_manual_sent_at", "updated_at"])
        messages.success(request, f"Rezumatul a fost trimis către {order.payer_email}.")
    else:
        messages.error(request, "Nu am putut trimite rezumatul (email plătitor lipsă).")
    return redirect("reclama_staff")


def _username_suggestions(tried, user_pk):
    """Sugestii de username când cel introdus există deja. Returnează doar variante libere."""
    User = get_user_model()
    base = _normalize_username_base(tried) or "User"
    candidates = [
        f"{base}123",
        f"{base}12",
        f"{base}1",
        f"{base}456",
        "User123",
        "User12",
        "User1",
        f"{tried.strip()}_1",
        f"{tried.strip()}_2",
    ]
    out = []
    for u in candidates:
        if not u or len(u) < 3:
            continue
        if not User.objects.filter(username__iexact=u).exclude(pk=user_pk).exists():
            out.append(u)
        if len(out) >= 5:
            break
    if not out:
        n = 1
        while len(out) < 5 and n < 100:
            c = f"{base}{n}"
            if not User.objects.filter(username__iexact=c).exclude(pk=user_pk).exists():
                out.append(c)
            n += 1
    return out[:5]


@login_required
def account_edit_username_view(request):
    """Schimbare username: POST cu noul username. Verifică unicitate; la duplicat pune în session eroare + sugestii."""
    User = get_user_model()
    user = request.user
    new_username = (request.POST.get("username") or "").strip()
    if not new_username:
        request.session["username_error"] = "Introdu un nume de utilizator."
        request.session["username_tried"] = ""
        request.session["username_suggestions"] = []
        return redirect(reverse("account"))
    if len(new_username) < 3:
        request.session["username_error"] = "Numele de utilizator trebuie să aibă cel puțin 3 caractere."
        request.session["username_tried"] = new_username
        request.session["username_suggestions"] = _username_suggestions(new_username, user.pk)
        return redirect(reverse("account"))
    if not all(c.isalnum() or c in "._" for c in new_username):
        request.session["username_error"] = "Folosește doar litere, cifre, punct și liniuță jos."
        request.session["username_tried"] = new_username
        request.session["username_suggestions"] = _username_suggestions(new_username, user.pk)
        return redirect(reverse("account"))
    if User.objects.filter(username__iexact=new_username).exclude(pk=user.pk).exists():
        request.session["username_error"] = "User existent. Alege altul sau încearcă una dintre sugestiile de mai jos."
        request.session["username_tried"] = new_username
        request.session["username_suggestions"] = _username_suggestions(new_username, user.pk)
        return redirect(reverse("account"))
    user.username = new_username
    user.save(update_fields=["username"])
    return redirect(reverse("account") + "?username_updated=1")


@login_required
@require_POST
def account_upload_avatar_view(request):
    """
    Upload/crop poză profil pentru PF/ONG/Colaborator. Salvare permanentă:
    - fișier pe disc în MEDIA_ROOT/profiles/<user_id>/ (scale la sute/mii de useri),
    - referință în UserProfile.poza_1 (baza de date).
    La refresh sau pe orice pagină, poza se încarcă din media (navbar, pagină cont).
    """
    user = request.user
    account_profile = getattr(user, "account_profile", None)
    # Permitem upload avatar pentru PF, ONG și Colaborator (aceeași logică).
    if not account_profile or account_profile.role not in (
        AccountProfile.ROLE_PF,
        AccountProfile.ROLE_ORG,
        AccountProfile.ROLE_COLLAB,
    ):
        return JsonResponse({"ok": False, "error": "Nu este permis."}, status=403)
    file_obj = request.FILES.get("avatar")
    if not file_obj:
        return JsonResponse({"ok": False, "error": "Nu s-a trimis niciun fișier."}, status=400)
    profiles_dir = os.path.join(settings.MEDIA_ROOT, "profiles")
    if not os.path.isdir(profiles_dir):
        try:
            os.makedirs(profiles_dir, exist_ok=True)
        except Exception as e_dir:
            # dacă nu putem crea, lăsăm să dea eroare la save() mai jos
            pass
    try:
        raw = file_obj.read()
        if not raw:
            return JsonResponse({"ok": False, "error": "Fișierul este gol."}, status=400)
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        safe_name = "avatar_%s_%s.jpg" % (user.id, timezone.now().strftime("%Y%m%d%H%M%S"))
        content = ContentFile(raw)
        profile.poza_1.save(safe_name, content, save=True)
        profile.refresh_from_db()
        if not profile.poza_1.name:
            return JsonResponse({"ok": False, "error": "Poza nu s-a salvat în baza de date."}, status=500)
    except Exception as e:
        return JsonResponse({"ok": False, "error": "Eroare la salvare: " + str(e)}, status=500)
    url = ""
    try:
        rel_url = profile.poza_1.url
        if rel_url:
            url = rel_url if rel_url.startswith("/") else "/" + rel_url.lstrip("/")
    except Exception:
        pass
    if not url:
        return JsonResponse({"ok": False, "error": "Poza s-a salvat dar URL-ul lipsește."}, status=500)
    return JsonResponse({"ok": True, "url": url})


def _parse_phone_for_edit(phone_str):
    """Din profile.phone (ex: '+40 753017411' sau '0753017411') returnează (phone_country, phone)."""
    if not phone_str or not isinstance(phone_str, str):
        return "+40", ""
    s = phone_str.strip()
    if not s:
        return "+40", ""
    parts = s.split(None, 1)
    if len(parts) == 2 and parts[0].startswith("+"):
        return parts[0], parts[1]
    if s.startswith("0"):
        return "+40", s
    return "+40", s


@login_required
def account_edit_view(request):
    """Editează profil PF/ONG/Colaborator.

    Două tipuri de formulare:
    - form_type != 'firma' (implicit): date persoană (PF + colaborator) – ca la înscriere, fără parolă. Dacă telefon/email se schimbă → SMS apoi email.
    - form_type == 'firma' (ONG/Colaborator): date firmă (denumire, CUI, adresă, tip adăpost/tip colaborator)
      – se salvează direct în UserProfile/AccountProfile, fără SMS/email.
    """
    User = get_user_model()
    user = request.user
    account_profile = getattr(user, "account_profile", None)
    user_profile = getattr(user, "profile", None)
    if not account_profile or account_profile.role not in (
        AccountProfile.ROLE_PF,
        AccountProfile.ROLE_ORG,
        AccountProfile.ROLE_COLLAB,
    ):
        return redirect(reverse("account"))

    if request.method != "POST":
        return redirect(reverse("account"))

    form_type = (request.POST.get("form_type") or "").strip()

    # Formular „DATE FIRMĂ” – ONG + colaborator
    if form_type == "firma" and account_profile.role in (AccountProfile.ROLE_COLLAB, AccountProfile.ROLE_ORG):
        company_display_name = (request.POST.get("company_display_name") or "").strip()
        company_legal_name = (request.POST.get("company_legal_name") or "").strip()
        company_cui = (request.POST.get("company_cui") or "").strip()
        company_cui_has_ro = (request.POST.get("company_cui_has_ro") or "") == "da"
        company_judet = (request.POST.get("company_judet") or "").strip()
        company_oras = (request.POST.get("company_oras") or "").strip()
        company_address = (request.POST.get("company_address") or "").strip()
        collaborator_type = (request.POST.get("collaborator_type") or "").strip()
        is_public_shelter_val = (request.POST.get("is_public_shelter") or request.POST.get("is_public_shelter_org") or "").strip()

        errors = []
        if not company_display_name:
            errors.append("Denumirea afișată a firmei este obligatorie.")
        if not company_legal_name:
            errors.append("Denumirea societății este obligatorie.")
        if not company_cui:
            errors.append("CUI/CIF este obligatoriu.")
        if not company_judet:
            errors.append("Județul firmei este obligatoriu.")
        if not company_oras:
            errors.append("Orașul/localitatea firmei este obligatorie.")
        if account_profile.role == AccountProfile.ROLE_COLLAB:
            if collaborator_type not in ("cabinet", "servicii", "magazin", "transport"):
                errors.append("Tipul de colaborator trebuie să fie Cabinet, Servicii, Magazin sau Transportator.")
        elif account_profile.role == AccountProfile.ROLE_ORG:
            if is_public_shelter_val not in ("yes", "no"):
                errors.append("Alege tipul de adăpost: Sunt adăpost public / Nu sunt adăpost public.")

        if errors:
            request.session["edit_errors"] = errors
            # prefill pentru firmă
            request.session["edit_prefill_firma"] = {
                "company_display_name": company_display_name,
                "company_legal_name": company_legal_name,
                "company_cui": company_cui,
                "company_cui_has_ro": "da" if company_cui_has_ro else "nu",
                "company_judet": company_judet,
                "company_oras": company_oras,
                "company_address": company_address,
                "collaborator_type": collaborator_type if account_profile.role == AccountProfile.ROLE_COLLAB else "",
                "is_public_shelter": is_public_shelter_val if is_public_shelter_val in ("yes", "no") else "",
            }
            return redirect(reverse("account"))

        if user_profile is None:
            user_profile = UserProfile.objects.create(user=user)
        user_profile.company_display_name = company_display_name
        user_profile.company_legal_name = company_legal_name
        user_profile.company_cui = company_cui
        user_profile.company_cui_has_ro = company_cui_has_ro
        user_profile.company_judet = company_judet
        user_profile.company_oras = company_oras
        user_profile.company_address = company_address
        user_profile.collaborator_type = collaborator_type if account_profile.role == AccountProfile.ROLE_COLLAB else ""
        user_profile.save()
        if account_profile.role == AccountProfile.ROLE_ORG:
            account_profile.is_public_shelter = is_public_shelter_val == "yes"
            account_profile.save(update_fields=["is_public_shelter"])
        request.session["account_updated"] = True
        if account_profile.role == AccountProfile.ROLE_COLLAB:
            if collaborator_type == "transport":
                return redirect(reverse("transport_operator_panel") + "?tip_updated=1")
            return redirect(reverse("collab_offers_control") + "?tip_updated=1")
        return redirect(reverse("account") + "?updated=1")

    # Formular principal (PF + colaborator) – date persoană
    first_name = (request.POST.get("first_name") or "").strip()
    last_name = (request.POST.get("last_name") or "").strip()
    email = (request.POST.get("email") or "").strip().lower()
    phone_country = (request.POST.get("phone_country") or "+40").strip()
    phone = (request.POST.get("phone") or "").strip()
    judet = (request.POST.get("judet") or "").strip()
    oras = (request.POST.get("oras") or "").strip()
    accept_termeni = request.POST.get("accept_termeni") == "on"
    accept_gdpr = request.POST.get("accept_gdpr") == "on"
    email_opt_in_wishlist = request.POST.get("email_opt_in_wishlist") == "on"

    errors = []
    if not email:
        errors.append("Email obligatoriu.")
    if _email_duplicate_blocked(email, exclude_user_pk=user.pk):
        errors.append("Acest email este deja folosit.")
    if not first_name:
        errors.append("Prenumele este obligatoriu.")
    if not last_name:
        errors.append("Numele este obligatoriu.")
    if not phone:
        errors.append("Telefonul este obligatoriu.")
    if not judet:
        errors.append("Județul este obligatoriu.")
    if not oras:
        errors.append("Orașul / localitatea este obligatoriu.")
    full_phone = f"{phone_country} {phone}".strip()
    current_phone = (user_profile.phone or "").strip() if user_profile else ""
    phone_changed = full_phone != current_phone
    if phone_changed:
        norm_new = _phone_normalize_for_compare(_phone_digits(full_phone))
        for p in UserProfile.objects.exclude(user=user).exclude(phone="").exclude(phone__isnull=True):
            if _phone_normalize_for_compare(_phone_digits(p.phone)) == norm_new:
                errors.append("Acest număr de telefon este deja folosit.")
                break
    if not accept_termeni:
        errors.append("Trebuie să accepți termenii și condițiile.")
    if not accept_gdpr:
        errors.append("Trebuie să accepți prelucrarea datelor conform GDPR.")

    email_changed = email != (user.email or "")

    if errors:
        prefill = {
            "first_name": first_name, "last_name": last_name, "email": email,
            "phone_country": phone_country, "phone": phone, "judet": judet, "oras": oras,
            "accept_termeni": accept_termeni, "accept_gdpr": accept_gdpr, "email_opt_in_wishlist": email_opt_in_wishlist,
        }
        request.session["edit_errors"] = errors
        request.session["edit_prefill"] = prefill
        return redirect(reverse("account"))

    if not phone_changed and not email_changed:
        prev_consents = {
            UserLegalConsent.CONSENT_TERMS: bool(user_profile.accept_termeni) if user_profile else False,
            UserLegalConsent.CONSENT_PRIVACY: bool(user_profile.accept_gdpr) if user_profile else False,
            UserLegalConsent.CONSENT_MARKETING: bool(user_profile.email_opt_in_wishlist) if user_profile else False,
        }
        user.first_name = first_name
        user.last_name = last_name
        user.save(update_fields=["first_name", "last_name"])
        if user_profile is None:
            user_profile = UserProfile.objects.create(user=user)
        user_profile.phone = full_phone
        user_profile.judet = judet
        user_profile.oras = oras
        user_profile.accept_termeni = accept_termeni
        user_profile.accept_gdpr = accept_gdpr
        user_profile.email_opt_in_wishlist = email_opt_in_wishlist
        user_profile.save()
        _log_legal_consents(
            request,
            user,
            accept_termeni=user_profile.accept_termeni,
            accept_gdpr=user_profile.accept_gdpr,
            email_opt_in=user_profile.email_opt_in_wishlist,
            source="account_edit_direct",
            previous=prev_consents,
        )
        return redirect(reverse("account") + "?updated=1")

    edit_pending = {
        "user_pk": user.pk,
        "first_name": first_name, "last_name": last_name, "email": email,
        "phone_country": phone_country, "phone": phone, "judet": judet, "oras": oras,
        "accept_termeni": accept_termeni, "accept_gdpr": accept_gdpr, "email_opt_in_wishlist": email_opt_in_wishlist,
        "phone_changed": phone_changed, "email_changed": email_changed,
    }
    request.session["edit_pending"] = edit_pending

    if phone_changed:
        import time
        request.session["edit_sms_at"] = time.time()
        return redirect(reverse("edit_verificare_sms"))
    else:
        from django.core.signing import TimestampSigner
        from django.core.mail import send_mail
        from urllib.parse import quote
        signer = TimestampSigner()
        token = signer.sign(f"{user.pk}:{email}")
        verify_url = request.build_absolute_uri(reverse("edit_verify_email")) + "?token=" + quote(token)
        plain = f"Bună ziua,\n\nConfirmă noul email pentru contul EU-Adopt:\n{verify_url}\n\nLinkul este valabil 1 oră."
        html = f'<p>Bună ziua,</p><p><a href="{verify_url}" style="color:#1565c0;font-weight:bold;">Confirmă emailul</a></p><p>Linkul este valabil 1 oră.</p>'
        try:
            send_mail(
                subject=email_subject_for_user(user.username, "Confirmă noul email – EU-Adopt"),
                message=plain,
                from_email=None,
                recipient_list=[email],
                fail_silently=False,
                html_message=html,
            )
        except Exception:
            pass
        return redirect(reverse("edit_check_email") + f"?email={quote(email)}")


@login_required
def edit_verificare_sms_view(request):
    """Verificare SMS pentru modificare profil: cod 111111, apoi actualizare date; dacă email schimbat, trimite link."""
    data = request.session.get("edit_pending")
    if not data or data.get("user_pk") != request.user.pk:
        return redirect(reverse("account"))

    if request.method != "POST":
        import time
        if "edit_sms_at" not in request.session:
            request.session["edit_sms_at"] = time.time()
        expires_at = int(request.session["edit_sms_at"]) + 300
        return render(request, "anunturi/edit_verify_sms.html", {
            "email": data.get("email", ""),
            "back_url": reverse("account_edit"),
            "expires_at": expires_at,
        })

    sms_code = (request.POST.get("sms_code") or "").strip()
    if sms_code != "111111":
        import time
        expires_at = int(request.session.get("edit_sms_at", time.time())) + 300
        return render(request, "anunturi/edit_verify_sms.html", {
            "email": data.get("email", ""),
            "sms_error": "Cod invalid. Folosește 111111 pentru verificare.",
            "back_url": reverse("account_edit"),
            "expires_at": expires_at,
        })

    User = get_user_model()
    user = User.objects.get(pk=data["user_pk"])
    profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
    prev_consents = {
        UserLegalConsent.CONSENT_TERMS: bool(profile.accept_termeni),
        UserLegalConsent.CONSENT_PRIVACY: bool(profile.accept_gdpr),
        UserLegalConsent.CONSENT_MARKETING: bool(profile.email_opt_in_wishlist),
    }
    full_phone = f"{data.get('phone_country', '')} {data.get('phone', '')}".strip()
    user.first_name = data.get("first_name", "")
    user.last_name = data.get("last_name", "")
    user.save(update_fields=["first_name", "last_name"])
    profile.phone = full_phone
    profile.judet = data.get("judet", "")
    profile.oras = data.get("oras", "")
    profile.accept_termeni = data.get("accept_termeni", False)
    profile.accept_gdpr = data.get("accept_gdpr", False)
    profile.email_opt_in_wishlist = data.get("email_opt_in_wishlist", False)
    profile.save()
    _log_legal_consents(
        request,
        user,
        accept_termeni=profile.accept_termeni,
        accept_gdpr=profile.accept_gdpr,
        email_opt_in=profile.email_opt_in_wishlist,
        source="account_edit_sms",
        previous=prev_consents,
    )

    if data.get("email_changed"):
        from django.core.signing import TimestampSigner
        from django.core.mail import send_mail
        from urllib.parse import quote
        signer = TimestampSigner()
        token = signer.sign(f"{user.pk}:{data['email']}")
        verify_url = request.build_absolute_uri(reverse("edit_verify_email")) + "?token=" + quote(token)
        plain = f"Bună ziua,\n\nConfirmă noul email pentru contul EU-Adopt:\n{verify_url}\n\nLinkul este valabil 1 oră."
        html = f'<p>Bună ziua,</p><p><a href="{verify_url}" style="color:#1565c0;font-weight:bold;">Confirmă emailul</a></p><p>Linkul este valabil 1 oră.</p>'
        try:
            send_mail(
                subject=email_subject_for_user(user.username, "Confirmă noul email – EU-Adopt"),
                message=plain,
                from_email=None,
                recipient_list=[data["email"]],
                fail_silently=False,
                html_message=html,
            )
        except Exception:
            pass
        request.session.pop("edit_pending", None)
        request.session.pop("edit_sms_at", None)
        return redirect(reverse("edit_check_email") + f"?email={quote(data['email'])}")
    request.session.pop("edit_pending", None)
    request.session.pop("edit_sms_at", None)
    return redirect(reverse("account") + "?updated=1")


def edit_check_email_view(request):
    """Pagina 'Am trimis link la noul email' după verificare SMS la edit profil."""
    if not request.user.is_authenticated:
        return redirect(reverse("account"))
    email = request.GET.get("email", "")
    return render(request, "anunturi/edit_check_email.html", {"email": email, "back_url": reverse("account")})


def edit_verify_email_view(request):
    """Link din email: confirmă noul email și actualizează userul (+ restul din edit_pending dacă există)."""
    from django.core.signing import TimestampSigner
    from django.core.signing import SignatureExpired

    token = (request.GET.get("token") or "").strip()
    if not token:
        return redirect(reverse("account") + "?edit_email_invalid=1")
    signer = TimestampSigner()
    try:
        payload = signer.unsign(token, max_age=3600)
    except SignatureExpired:
        return redirect(reverse("account") + "?edit_email_expired=1")
    except Exception:
        return redirect(reverse("account") + "?edit_email_invalid=1")
    parts = payload.split(":", 1)
    if len(parts) != 2:
        return redirect(reverse("account") + "?edit_email_invalid=1")
    user_pk, new_email = parts[0], parts[1]
    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect(reverse("account") + "?edit_email_invalid=1")

    data = request.session.get("edit_pending")
    if data and str(data.get("user_pk")) == str(user.pk):
        user.first_name = data.get("first_name", "")
        user.last_name = data.get("last_name", "")
        user.email = new_email
        user.save(update_fields=["first_name", "last_name", "email"])
        profile, _ = UserProfile.objects.get_or_create(user=user, defaults={})
        prev_consents = {
            UserLegalConsent.CONSENT_TERMS: bool(profile.accept_termeni),
            UserLegalConsent.CONSENT_PRIVACY: bool(profile.accept_gdpr),
            UserLegalConsent.CONSENT_MARKETING: bool(profile.email_opt_in_wishlist),
        }
        full_phone = f"{data.get('phone_country', '')} {data.get('phone', '')}".strip()
        profile.phone = full_phone
        profile.judet = data.get("judet", "")
        profile.oras = data.get("oras", "")
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in_wishlist", False)
        profile.save()
        _log_legal_consents(
            request,
            user,
            accept_termeni=profile.accept_termeni,
            accept_gdpr=profile.accept_gdpr,
            email_opt_in=profile.email_opt_in_wishlist,
            source="account_edit_email_verify",
            previous=prev_consents,
        )
    else:
        user.email = new_email
        user.save(update_fields=["email"])
    request.session.pop("edit_pending", None)
    return redirect(reverse("account") + "?updated=1")


def _build_mypet_as_adopter_rows(user, active_since):
    """Cereri AdoptionRequest unde userul e adoptator (animale care nu îi aparțin)."""
    mypet_as_adopter_rows = []
    try:
        qs_ad = list(
            AdoptionRequest.objects.filter(adopter=user)
            .exclude(animal__owner_id=user.id)
            .filter(
                status__in=[
                    AdoptionRequest.STATUS_PENDING,
                    AdoptionRequest.STATUS_ACCEPTED,
                    AdoptionRequest.STATUS_FINALIZED,
                    AdoptionRequest.STATUS_EXPIRED,
                ]
            )
            .select_related("animal", "animal__owner")
            .order_by("-updated_at")[:40]
        )
        if not qs_ad:
            return []
        status_lbl_ar = dict(AdoptionRequest.STATUS_CHOICES)
        aids_ad = [int(ar.animal_id) for ar in qs_ad if ar.animal_id]
        pets_ad = {
            p.pk: p
            for p in AnimalListing.objects.filter(pk__in=aids_ad).select_related("owner")
        }
        unread_ad = {}
        for row in PetMessage.objects.filter(
            animal_id__in=aids_ad,
            receiver=user,
            is_read=False,
            created_at__gte=active_since,
        ).values("animal_id", "sender_id"):
            aid = int(row["animal_id"])
            pet_o = pets_ad.get(aid)
            if not pet_o or not pet_o.owner_id or int(row["sender_id"]) != int(pet_o.owner_id):
                continue
            unread_ad[aid] = unread_ad.get(aid, 0) + 1
        for ar in qs_ad:
            pet = getattr(ar, "animal", None) or pets_ad.get(int(ar.animal_id))
            if not pet:
                continue
            own = pet.owner
            ol = (f"{own.first_name} {own.last_name}").strip() if own else ""
            ol = ol or (own.username if own else "Proprietar")
            sp = (pet.species or "").strip().lower()
            if sp not in ("dog", "cat"):
                sp = "other"
            try:
                pet_url = (
                    reverse("pets_single", args=[pet.pk]) if getattr(pet, "is_published", False) else ""
                )
            except Exception:
                pet_url = ""
            try:
                photo_url = pet.photo_1.url if getattr(pet, "photo_1", None) else ""
            except Exception:
                photo_url = ""
            mypet_as_adopter_rows.append(
                {
                    "request": ar,
                    "animal": pet,
                    "owner_label": ol,
                    "status_label": status_lbl_ar.get(ar.status, ar.status),
                    "species_key": sp,
                    "pet_url": pet_url,
                    "photo_url": photo_url,
                    "messages_open_url": reverse("mypet")
                    + f"?open_messages=1&open_adopter_animal={pet.pk}",
                    "unread_from_owner": int(unread_ad.get(int(pet.pk), 0)),
                }
            )
    except Exception:
        return []
    return mypet_as_adopter_rows


@login_required
@mypet_pf_org_required
def mypet_view(request):
    """
    Pagina MyPet – listă animale ale userului (un rând per câine).
    Acces: doar PF și ONG/SRL (`AccountProfile`). Colaboratorii nu postează câini spre adopție.
    """
    user = request.user
    pets = list(
        AnimalListing.objects.filter(owner=user)
        .order_by("-id")[:50]
    )
    arc_q = (request.GET.get("arc") or "").strip().lower()
    mypet_initial_arc = "adopted" if arc_q == "adopted" else "active"
    mypet_count = len([p for p in pets if p is not None])
    user_has_owned_pets = mypet_count > 0
    adopted_count = 0
    if mypet_count:
        pet_ids_all = list(AnimalListing.objects.filter(owner=user).values_list("pk", flat=True))
        if pet_ids_all:
            adopted_count = UserAdoption.objects.filter(status="completed", animal_id__in=pet_ids_all).count()
    total_count = int(mypet_count) + int(adopted_count)
    # Wishlist counts (I love): câte inimioare are fiecare câine
    pet_ids = [p.pk for p in pets if p is not None]
    wish_map = {}
    if pet_ids:
        for row in (
            WishlistItem.objects
            .filter(animal_id__in=pet_ids)
            .values("animal_id")
            .annotate(c=Count("id"))
        ):
            wish_map[int(row["animal_id"])] = int(row["c"])
    for p in pets:
        if p is None:
            continue
        p.wish_count = wish_map.get(p.pk, 0)
        # Fișă completă (procent vizibilitate): 1/2/3 poze + video + 3 bife cheie
        points = 0
        missing = []
        trait_fields = [
            "trait_jucaus",
            "trait_iubitor",
            "trait_protector",
            "trait_energic",
            "trait_linistit",
            "trait_bun_copii",
            "trait_bun_caini",
            "trait_bun_pisici",
            "trait_obisnuit_casa",
            "trait_obisnuit_lesa",
            "trait_nu_latla",
            "trait_apartament",
            "trait_se_adapteaza",
            "trait_tolereaza_singur",
            "trait_necesita_experienta",
        ]
        selected_traits = 0

        poze_ok = False
        video_ok = False
        # Poze: prima contează mai mult (copertă)
        if getattr(p, "photo_1", None):
            points += 2
        photo_1_ok = bool(getattr(p, "photo_1", None))
        if getattr(p, "photo_2", None):
            points += 1
        photo_2_ok = bool(getattr(p, "photo_2", None))
        if getattr(p, "photo_3", None):
            points += 1
        photo_3_ok = bool(getattr(p, "photo_3", None))

        poze_ok = photo_1_ok and photo_2_ok and photo_3_ok
        if not poze_ok:
            missing.append("Poze")
        # Video
        video_ok = bool(getattr(p, "video", None))
        if video_ok:
            points += 2
        else:
            missing.append("Video")

        for field in trait_fields:
            if bool(getattr(p, field, False)):
                selected_traits += 1

        # Nu avem bife obligatorii: considerăm OK dacă sunt >= 3 bife selectate.
        calitati_ok = selected_traits >= 3
        if not calitati_ok:
            missing.append("Calități")

        # Punctaj maxim pentru bife: primele 3 bife selectate => 3 puncte.
        points += min(selected_traits, 3)

        total_points = 9  # (Poza 1-3) 4 + Video 2 + Calități 3
        try:
            p.fisa_percent = int(round((points / float(total_points)) * 100))
        except Exception:
            p.fisa_percent = 0
        p.fisa_missing = missing

    # Mesaje noi pe fiecare pet (pentru owner-ul autentificat)
    active_since = _messages_active_since()
    unread_by_pet = {}
    if pet_ids:
        for row in (
            PetMessage.objects
            .filter(animal_id__in=pet_ids, receiver=user, is_read=False, created_at__gte=active_since)
            .values("animal_id")
            .annotate(c=Count("id"))
        ):
            unread_by_pet[int(row["animal_id"])] = int(row["c"])
    for p in pets:
        if p is None:
            continue
        p.unread_messages = unread_by_pet.get(p.pk, 0)
    # Mesaje necitite ca adoptator (pe animale care nu îți aparțin) — pentru ?open_messages=1.
    adopter_pet_message_unread = 0
    try:
        adopter_pet_message_unread = (
            PetMessage.objects.filter(
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            )
            .exclude(animal__owner_id=user.id)
            .count()
        )
    except Exception:
        adopter_pet_message_unread = 0
    # Adopție: coloana „În curs” + buton finalizare (cerere acceptată)
    pending_counts = {}
    if pet_ids:
        for row in (
            AdoptionRequest.objects.filter(
                animal_id__in=pet_ids,
                status=AdoptionRequest.STATUS_PENDING,
            )
            .values("animal_id")
            .annotate(c=Count("id"))
        ):
            pending_counts[int(row["animal_id"])] = int(row["c"])
    accepted_map = {}
    now = timezone.now()
    if pet_ids:
        for ar in AdoptionRequest.objects.filter(
            animal_id__in=pet_ids,
            status=AdoptionRequest.STATUS_ACCEPTED,
        ).filter(
            Q(accepted_expires_at__isnull=True) | Q(accepted_expires_at__gte=now)
        ).order_by("-accepted_at", "-pk"):
            aid = int(ar.animal_id)
            if aid not in accepted_map:
                accepted_map[aid] = ar.pk

    pending_first = {}
    if pet_ids:
        for ar in AdoptionRequest.objects.filter(
            animal_id__in=pet_ids,
            status=AdoptionRequest.STATUS_PENDING,
        ).order_by("created_at"):
            aid = int(ar.animal_id)
            if aid not in pending_first:
                pending_first[aid] = ar

    manage_by_animal = {}
    if pet_ids:
        for ar in AdoptionRequest.objects.filter(
            animal_id__in=pet_ids,
            status__in=[AdoptionRequest.STATUS_ACCEPTED, AdoptionRequest.STATUS_EXPIRED],
        ).order_by("-accepted_at", "-pk"):
            aid = int(ar.animal_id)
            if aid not in manage_by_animal:
                manage_by_animal[aid] = ar

    for p in pets:
        if p is None:
            continue
        _sync_animal_adoption_state(p)
        parts = []
        npc = pending_counts.get(p.pk, 0)
        if npc:
            parts.append(f"Așteptare ({npc})")
        if p.pk in accepted_map:
            parts.append("Adopție acceptată")
        p.adoption_row_label = " · ".join(parts) if parts else _adoption_state_label(getattr(p, "adoption_state", ""))
        # Versiune compactă pentru tabel (tooltip-ul păstrează textul complet).
        p.adoption_row_compact = "•"
        if parts:
            if npc and p.pk in accepted_map:
                p.adoption_row_compact = "A+"
            elif p.pk in accepted_map:
                p.adoption_row_compact = "ACC"
            elif npc:
                p.adoption_row_compact = "AST"
        else:
            st = getattr(p, "adoption_state", "")
            if st == AnimalListing.ADOPTION_STATE_FREE:
                p.adoption_row_compact = "L"
            elif st == AnimalListing.ADOPTION_STATE_OPEN:
                p.adoption_row_compact = "SA"
            elif st == AnimalListing.ADOPTION_STATE_IN_PROGRESS:
                p.adoption_row_compact = "CA"
            elif st == AnimalListing.ADOPTION_STATE_ADOPTED:
                p.adoption_row_compact = "AD"
        p.adoption_finalize_id = accepted_map.get(p.pk)

        manage_ar = manage_by_animal.get(p.pk)
        pend_ar = pending_first.get(p.pk)
        p.adoption_pending_req_id = None
        p.adoption_manage_req_id = None
        p.adoption_can_extend = False
        p.adoption_can_next = False
        p.adoption_manage_is_expired = False
        if manage_ar:
            ext = int(getattr(manage_ar, "extension_count", 0) or 0)
            has_waitlist = npc > 0
            can_extend = manage_ar.status in (
                AdoptionRequest.STATUS_ACCEPTED,
                AdoptionRequest.STATUS_EXPIRED,
            ) and ext < 2
            # „Următorul adoptator” are sens doar dacă există cereri în așteptare.
            can_next = manage_ar.status in (
                AdoptionRequest.STATUS_ACCEPTED,
                AdoptionRequest.STATUS_EXPIRED,
            ) and has_waitlist
            exp = getattr(manage_ar, "accepted_expires_at", None)
            p.adoption_manage_is_expired = bool(exp and exp < now) or manage_ar.status == AdoptionRequest.STATUS_EXPIRED
            # Expirat + zero în coadă: nu mai afișăm ⚙ (nu există „următorul”; prelungirea după expirare fără coadă nu e oferită).
            show_manage = (can_extend or can_next) and not (
                manage_ar.status == AdoptionRequest.STATUS_EXPIRED and not has_waitlist
            )
            if show_manage:
                p.adoption_manage_req_id = manage_ar.pk
                p.adoption_can_extend = can_extend
                p.adoption_can_next = can_next
        elif pend_ar:
            p.adoption_pending_req_id = pend_ar.pk
    # Minim 20 rânduri pentru a vedea scroll-ul
    while len(pets) < 20:
        pets.append(None)
    # Contorul din navbar folosește valorile globale din context processor (DEMO_DOGS),
    # nu mai suprascriem aici active_animals/adopted_animals.
    return render(request, "anunturi/mypet.html", {
        "pets": pets,
        "mypet_count": mypet_count,
        "adopted_count": adopted_count,
        "total_count": total_count,
        "user_has_owned_pets": user_has_owned_pets,
        "adopter_pet_message_unread": adopter_pet_message_unread,
        "mypet_initial_arc": mypet_initial_arc,
    })


@login_required
@mypet_pf_org_required
def mypet_adopter_adoptions_view(request):
    """Grilă carduri: adopții în care userul e adoptator (animale de la alții)."""
    active_since = _messages_active_since()
    rows = _build_mypet_as_adopter_rows(request.user, active_since)
    return render(
        request,
        "anunturi/mypet_adopter_adoptions.html",
        {
            "mypet_as_adopter_rows": rows,
            "mypet_home_url": reverse("mypet"),
        },
    )


@login_required
@collab_magazin_required
def magazinul_meu_view(request):
    """
    Ruta /magazinul-meu/ redirecționează către pagina de control oferte (prima pagină colaborator).
    Transportatorii → panou transport. Păstrăm URL-ul pentru compatibilitate.
    """
    try:
        prof = getattr(request.user, "profile", None)
        if prof and (prof.collaborator_type or "").strip().lower() == "transport":
            target = reverse("transport_operator_panel")
            if request.GET:
                target += "?" + request.GET.urlencode()
            return redirect(target)
    except Exception:
        pass
    target = reverse("collab_offers_control")
    if request.GET:
        target += "?" + request.GET.urlencode()
    return redirect(target)


def _mypet_form_trait_labels_ctx(ctx: dict) -> dict:
    """Include mapări etichete trăsături (dog/cat) pentru template + json_script."""
    from home.pet_traits import TRAITS_LABELS_BY_SPECIES

    out = dict(ctx)
    out["trait_labels_by_species"] = TRAITS_LABELS_BY_SPECIES
    return out


@login_required
@mypet_pf_org_required
def mypet_add_view(request):
    """
    Formular simplu pentru a adăuga un pet nou.
    În pasul următor vom rafina câmpurile și layout-ul fișei.
    """
    user = request.user
    profile = getattr(user, "profile", None)
    account_profile = getattr(user, "account_profile", None)
    default_city = getattr(profile, "oras", "") if profile else ""
    default_county = getattr(profile, "judet", "") if profile else ""
    is_public_shelter = bool(
        account_profile
        and account_profile.role == AccountProfile.ROLE_ORG
        and getattr(account_profile, "is_public_shelter", False)
    )
    default_med = "da" if is_public_shelter else ""

    age_choices = list(AGE_LABELS_ORDERED)

    # GET ?species=dog|cat|other — fără asta, /mypet/add/ pornea mereu pe câine.
    add_species_q = (request.GET.get("species") or "").strip().lower()
    if add_species_q not in ("dog", "cat", "other"):
        add_species_q = "dog"

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        species_mode = (request.POST.get("species_mode") or "").strip().lower()
        species_custom = (request.POST.get("species_custom") or "").strip()
        if species_mode in ("dog", "cat"):
            species = species_mode
        else:
            species_mode = "other"
            species = species_custom
        size = (request.POST.get("size") or "").strip()
        age_label = (request.POST.get("age_label") or "").strip()
        city = (request.POST.get("city") or "").strip()
        county = (request.POST.get("county") or "").strip()
        color = (request.POST.get("color") or "").strip()
        sterilizat = (request.POST.get("sterilizat") or "").strip()
        vaccinat = (request.POST.get("vaccinat") or "").strip()
        carnet_sanatate = (request.POST.get("carnet_sanatate") or "").strip()
        cip = (request.POST.get("cip") or "").strip()
        sex = (request.POST.get("sex") or "").strip()
        greutate_aprox = (request.POST.get("greutate_aprox") or "").strip()
        probleme_medicale = (request.POST.get("probleme_medicale") or "").strip()
        cine_sunt = (request.POST.get("cine_sunt") or "").strip()
        detalii_animal = (
            (request.POST.get("detalii_animal") or "").strip()
            if species_mode == "other"
            else ""
        )
        # Trăsături (checkboxes): doar câine/pisică; la «Altele» nu se salvează
        def trait(name):
            if species_mode == "other":
                return False
            return name in request.POST

        error = None
        # Toate câmpurile sunt obligatorii (în afară de bifele de potrivire adoptator)
        required = [
            ("name", name, "Te rugăm să completezi numele animalului."),
            ("species", species, "Te rugăm să alegi specia."),
            ("age_label", age_label, "Te rugăm să alegi vârsta estimată."),
            ("size", size, "Te rugăm să alegi talia."),
            ("color", color, "Te rugăm să alegi culoarea."),
            ("sterilizat", sterilizat, "Te rugăm să alegi dacă este sterilizat."),
            ("vaccinat", vaccinat, "Te rugăm să alegi dacă este vaccinat."),
            ("carnet_sanatate", carnet_sanatate, "Te rugăm să alegi dacă are carnet de sănătate."),
            ("cip", cip, "Te rugăm să alegi dacă are CIP."),
            ("sex", sex, "Te rugăm să alegi sexul."),
            ("greutate_aprox", greutate_aprox, "Te rugăm să completezi greutatea (aprox.)."),
            ("county", county, "Te rugăm să completezi județul."),
            ("city", city, "Te rugăm să completezi orașul/localitatea."),
            ("probleme_medicale", probleme_medicale, "Te rugăm să completezi problemele medicale (scrie „Nu” dacă nu sunt)."),
            ("cine_sunt", cine_sunt, "Te rugăm să completezi „Cine sunt și de unde sunt”."),
        ]
        for _key, val, msg in required:
            if not val:
                error = msg
                break
        if not error and species_mode == "other" and not species_custom:
            error = "Te rugăm să completezi specia pentru categoria «Altele» (ex: hamster)."
        if not error:
            try:
                listing = AnimalListing.objects.create(
                    owner=user,
                    name=name,
                    species=species,
                    size=size,
                    age_label=age_label,
                    city=city,
                    county=county,
                    color=color,
                    sterilizat=sterilizat,
                    vaccinat=vaccinat,
                    carnet_sanatate=carnet_sanatate,
                    cip=cip,
                    sex=sex,
                    greutate_aprox=greutate_aprox,
                    probleme_medicale=probleme_medicale,
                    cine_sunt=cine_sunt,
                    detalii_animal=detalii_animal,
                    photo_1=request.FILES.get("photo_1"),
                    photo_2=request.FILES.get("photo_2"),
                    photo_3=request.FILES.get("photo_3"),
                    video=request.FILES.get("video"),
                    trait_jucaus=trait("trait_jucaus"),
                    trait_iubitor=trait("trait_iubitor"),
                    trait_protector=trait("trait_protector"),
                    trait_energic=trait("trait_energic"),
                    trait_linistit=trait("trait_linistit"),
                    trait_bun_copii=trait("trait_bun_copii"),
                    trait_bun_caini=trait("trait_bun_caini"),
                    trait_bun_pisici=trait("trait_bun_pisici"),
                    trait_obisnuit_casa=trait("trait_obisnuit_casa"),
                    trait_obisnuit_lesa=trait("trait_obisnuit_lesa"),
                    trait_nu_latla=trait("trait_nu_latla"),
                    trait_apartament=trait("trait_apartament"),
                    trait_se_adapteaza=trait("trait_se_adapteaza"),
                    trait_tolereaza_singur=trait("trait_tolereaza_singur"),
                    trait_necesita_experienta=trait("trait_necesita_experienta"),
                    is_published=True,
                )
                # După salvarea fișei noi, ducem userul în lista MyPet
                return redirect("mypet")
            except Exception as exc:
                error = str(exc)
        ctx = {
            "error": error,
            "name": name,
            "species": species,
            "species_mode": species_mode,
            "species_custom": species_custom,
            "size": size,
            "age_label": age_label,
            "city": city or default_city,
            "county": county or default_county,
            "color": color,
            "sterilizat": sterilizat or default_med,
            "vaccinat": vaccinat or default_med,
            "carnet_sanatate": carnet_sanatate or default_med,
            "cip": cip or default_med,
            "sex": sex,
            "greutate_aprox": greutate_aprox,
            "probleme_medicale": probleme_medicale,
            "cine_sunt": cine_sunt,
            "detalii_animal": detalii_animal,
            "age_choices": age_choices,
            "has_photo_1": False,
            "has_photo_2": False,
            "has_photo_3": False,
            "listing": None,
            "trait_jucaus": trait("trait_jucaus"),
            "trait_iubitor": trait("trait_iubitor"),
            "trait_protector": trait("trait_protector"),
            "trait_energic": trait("trait_energic"),
            "trait_linistit": trait("trait_linistit"),
            "trait_bun_copii": trait("trait_bun_copii"),
            "trait_bun_caini": trait("trait_bun_caini"),
            "trait_bun_pisici": trait("trait_bun_pisici"),
            "trait_obisnuit_casa": trait("trait_obisnuit_casa"),
            "trait_obisnuit_lesa": trait("trait_obisnuit_lesa"),
            "trait_nu_latla": trait("trait_nu_latla"),
            "trait_apartament": trait("trait_apartament"),
            "trait_se_adapteaza": trait("trait_se_adapteaza"),
            "trait_tolereaza_singur": trait("trait_tolereaza_singur"),
            "trait_necesita_experienta": trait("trait_necesita_experienta"),
            "traits_empty": not any(trait(n) for n in (
                "trait_jucaus","trait_iubitor","trait_protector","trait_energic","trait_linistit",
                "trait_bun_copii","trait_bun_caini","trait_bun_pisici","trait_obisnuit_casa","trait_obisnuit_lesa",
                "trait_nu_latla","trait_apartament","trait_se_adapteaza","trait_tolereaza_singur","trait_necesita_experienta"
            )),
        }
        return render(request, "anunturi/mypet_add.html", _mypet_form_trait_labels_ctx(ctx))

    ctx = {
        "error": None,
        "name": "",
        "species": "dog"
        if add_species_q == "dog"
        else ("cat" if add_species_q == "cat" else ""),
        "species_mode": add_species_q,
        "species_custom": "",
        "size": "",
        "age_label": "",
        "city": default_city,
        "county": default_county,
        "color": "",
        "sterilizat": default_med,
        "vaccinat": default_med,
        "carnet_sanatate": default_med,
        "cip": default_med,
        "sex": "",
        "greutate_aprox": "",
        "probleme_medicale": "",
        "cine_sunt": "",
        "detalii_animal": "",
        "age_choices": age_choices,
        "has_photo_1": False,
        "has_photo_2": False,
        "has_photo_3": False,
        "listing": None,
        "trait_jucaus": False,
        "trait_iubitor": False,
        "trait_protector": False,
        "trait_energic": False,
        "trait_linistit": False,
        "trait_bun_copii": False,
        "trait_bun_caini": False,
        "trait_bun_pisici": False,
        "trait_obisnuit_casa": False,
        "trait_obisnuit_lesa": False,
        "trait_nu_latla": False,
        "trait_apartament": False,
        "trait_se_adapteaza": False,
        "trait_tolereaza_singur": False,
        "trait_necesita_experienta": False,
        "traits_empty": True,
    }
    return render(request, "anunturi/mypet_add.html", _mypet_form_trait_labels_ctx(ctx))


@login_required
@mypet_pf_org_required
def mypet_edit_view(request, pk):
    """Editare fișă pet existent."""
    user = request.user
    listing = AnimalListing.objects.filter(owner=user, pk=pk).first()
    if not listing:
        return redirect("mypet")

    profile = getattr(user, "profile", None)
    account_profile = getattr(user, "account_profile", None)
    default_city = getattr(profile, "oras", "") if profile else ""
    default_county = getattr(profile, "judet", "") if profile else ""
    is_public_shelter = bool(
        account_profile
        and account_profile.role == AccountProfile.ROLE_ORG
        and getattr(account_profile, "is_public_shelter", False)
    )
    default_med = "da" if is_public_shelter else ""

    age_choices = list(AGE_LABELS_ORDERED)

    if request.method == "POST":
        form_action = (request.POST.get("form_action") or "save").strip().lower()
        edit_mode = (request.POST.get("edit_mode") or "").strip().lower()
        if form_action == "delete":
            listing.delete()
            return redirect("mypet")
        if edit_mode != "edit":
            messages.info(request, "Fișa este blocată. Apasă mai întâi pe „Modifică fișa”.")
            return redirect("mypet_edit", pk=listing.pk)

        name = (request.POST.get("name") or "").strip()
        species_mode = (request.POST.get("species_mode") or "").strip().lower()
        species_custom = (request.POST.get("species_custom") or "").strip()
        if species_mode in ("dog", "cat"):
            species = species_mode
        else:
            species_mode = "other"
            species = species_custom
        size = (request.POST.get("size") or "").strip()
        age_label = (request.POST.get("age_label") or "").strip()
        city = (request.POST.get("city") or "").strip()
        county = (request.POST.get("county") or "").strip()
        color = (request.POST.get("color") or "").strip()
        sterilizat = (request.POST.get("sterilizat") or "").strip()
        vaccinat = (request.POST.get("vaccinat") or "").strip()
        carnet_sanatate = (request.POST.get("carnet_sanatate") or "").strip()
        cip = (request.POST.get("cip") or "").strip()
        sex = (request.POST.get("sex") or "").strip()
        greutate_aprox = (request.POST.get("greutate_aprox") or "").strip()
        probleme_medicale = (request.POST.get("probleme_medicale") or "").strip()
        cine_sunt = (request.POST.get("cine_sunt") or "").strip()
        detalii_animal = (
            (request.POST.get("detalii_animal") or "").strip()
            if species_mode == "other"
            else ""
        )

        def trait(name):
            if species_mode == "other":
                return False
            return name in request.POST

        error = None
        required = [
            ("name", name, "Te rugăm să completezi numele animalului."),
            ("species", species, "Te rugăm să alegi specia."),
            ("age_label", age_label, "Te rugăm să alegi vârsta estimată."),
            ("size", size, "Te rugăm să alegi talia."),
            ("color", color, "Te rugăm să alegi culoarea."),
            ("sterilizat", sterilizat, "Te rugăm să alegi dacă este sterilizat."),
            ("vaccinat", vaccinat, "Te rugăm să alegi dacă este vaccinat."),
            ("carnet_sanatate", carnet_sanatate, "Te rugăm să alegi dacă are carnet de sănătate."),
            ("cip", cip, "Te rugăm să alegi dacă are CIP."),
            ("sex", sex, "Te rugăm să alegi sexul."),
            ("greutate_aprox", greutate_aprox, "Te rugăm să completezi greutatea (aprox.)."),
            ("county", county, "Te rugăm să completezi județul."),
            ("city", city, "Te rugăm să completezi orașul/localitatea."),
            ("probleme_medicale", probleme_medicale, "Te rugăm să completezi problemele medicale (scrie „Nu” dacă nu sunt)."),
            ("cine_sunt", cine_sunt, "Te rugăm să completezi „Cine sunt și de unde sunt”."),
        ]
        for _key, val, msg in required:
            if not val:
                error = msg
                break
        if not error and species_mode == "other" and not species_custom:
            error = "Te rugăm să completezi specia pentru categoria «Altele» (ex: hamster)."
        if not error:
            try:
                listing.name = name
                listing.species = species
                listing.size = size
                listing.age_label = age_label
                listing.city = city
                listing.county = county
                listing.color = color
                listing.sterilizat = sterilizat
                listing.vaccinat = vaccinat
                listing.carnet_sanatate = carnet_sanatate
                listing.cip = cip
                listing.sex = sex
                listing.greutate_aprox = greutate_aprox
                listing.probleme_medicale = probleme_medicale
                listing.cine_sunt = cine_sunt
                listing.detalii_animal = detalii_animal
                if request.FILES.get("photo_1"):
                    listing.photo_1 = request.FILES.get("photo_1")
                if request.FILES.get("photo_2"):
                    listing.photo_2 = request.FILES.get("photo_2")
                if request.FILES.get("photo_3"):
                    listing.photo_3 = request.FILES.get("photo_3")
                if request.FILES.get("video"):
                    listing.video = request.FILES.get("video")
                listing.trait_jucaus = trait("trait_jucaus")
                listing.trait_iubitor = trait("trait_iubitor")
                listing.trait_protector = trait("trait_protector")
                listing.trait_energic = trait("trait_energic")
                listing.trait_linistit = trait("trait_linistit")
                listing.trait_bun_copii = trait("trait_bun_copii")
                listing.trait_bun_caini = trait("trait_bun_caini")
                listing.trait_bun_pisici = trait("trait_bun_pisici")
                listing.trait_obisnuit_casa = trait("trait_obisnuit_casa")
                listing.trait_obisnuit_lesa = trait("trait_obisnuit_lesa")
                listing.trait_nu_latla = trait("trait_nu_latla")
                listing.trait_apartament = trait("trait_apartament")
                listing.trait_se_adapteaza = trait("trait_se_adapteaza")
                listing.trait_tolereaza_singur = trait("trait_tolereaza_singur")
                listing.trait_necesita_experienta = trait("trait_necesita_experienta")
                listing.save()
                return redirect("mypet")
            except Exception as exc:
                error = str(exc)

        ctx = {
            "listing": listing,
            "form_locked": False,
            "error": error,
            "name": name,
            "species": species,
            "species_mode": species_mode,
            "species_custom": species_custom,
            "size": size,
            "age_label": age_label,
            "city": city or default_city,
            "county": county or default_county,
            "color": color,
            "sterilizat": sterilizat or default_med,
            "vaccinat": vaccinat or default_med,
            "carnet_sanatate": carnet_sanatate or default_med,
            "cip": cip or default_med,
            "sex": sex,
            "greutate_aprox": greutate_aprox,
            "probleme_medicale": probleme_medicale,
            "cine_sunt": cine_sunt,
            "detalii_animal": detalii_animal,
            "age_choices": age_choices,
            "has_photo_1": bool(listing.photo_1),
            "has_photo_2": bool(listing.photo_2),
            "has_photo_3": bool(listing.photo_3),
            "trait_jucaus": listing.trait_jucaus,
            "trait_iubitor": listing.trait_iubitor,
            "trait_protector": listing.trait_protector,
            "trait_energic": listing.trait_energic,
            "trait_linistit": listing.trait_linistit,
            "trait_bun_copii": listing.trait_bun_copii,
            "trait_bun_caini": listing.trait_bun_caini,
            "trait_bun_pisici": listing.trait_bun_pisici,
            "trait_obisnuit_casa": listing.trait_obisnuit_casa,
            "trait_obisnuit_lesa": listing.trait_obisnuit_lesa,
            "trait_nu_latla": listing.trait_nu_latla,
            "trait_apartament": listing.trait_apartament,
            "trait_se_adapteaza": listing.trait_se_adapteaza,
            "trait_tolereaza_singur": listing.trait_tolereaza_singur,
            "trait_necesita_experienta": listing.trait_necesita_experienta,
            "traits_empty": not any([
                trait("trait_jucaus"), trait("trait_iubitor"), trait("trait_protector"), trait("trait_energic"),
                trait("trait_linistit"), trait("trait_bun_copii"), trait("trait_bun_caini"), trait("trait_bun_pisici"),
                trait("trait_obisnuit_casa"), trait("trait_obisnuit_lesa"), trait("trait_nu_latla"), trait("trait_apartament"),
                trait("trait_se_adapteaza"), trait("trait_tolereaza_singur"), trait("trait_necesita_experienta")
            ]),
        }
        return render(request, "anunturi/mypet_add.html", _mypet_form_trait_labels_ctx(ctx))

    current_species = (listing.species or "").strip().lower()
    species_mode = current_species if current_species in ("dog", "cat") else "other"
    species_custom = ""
    if species_mode == "other" and current_species:
        species_custom = listing.species

    ctx = {
        "listing": listing,
        "form_locked": True,
        "error": None,
        "name": listing.name or "",
        "species": listing.species or "dog",
        "species_mode": species_mode,
        "species_custom": species_custom,
        "size": listing.size or "",
        "age_label": listing.age_label or "",
        "city": listing.city or default_city,
        "county": listing.county or default_county,
        "color": listing.color or "",
        "sterilizat": listing.sterilizat or default_med,
        "vaccinat": listing.vaccinat or default_med,
        "carnet_sanatate": listing.carnet_sanatate or default_med,
        "cip": listing.cip or default_med,
        "sex": listing.sex or "",
        "greutate_aprox": listing.greutate_aprox or "",
        "probleme_medicale": listing.probleme_medicale or "",
        "cine_sunt": listing.cine_sunt or "",
        "detalii_animal": listing.detalii_animal or "",
        "age_choices": age_choices,
        "has_photo_1": bool(listing.photo_1),
        "has_photo_2": bool(listing.photo_2),
        "has_photo_3": bool(listing.photo_3),
        "trait_jucaus": listing.trait_jucaus,
        "trait_iubitor": listing.trait_iubitor,
        "trait_protector": listing.trait_protector,
        "trait_energic": listing.trait_energic,
        "trait_linistit": listing.trait_linistit,
        "trait_bun_copii": listing.trait_bun_copii,
        "trait_bun_caini": listing.trait_bun_caini,
        "trait_bun_pisici": listing.trait_bun_pisici,
        "trait_obisnuit_casa": listing.trait_obisnuit_casa,
        "trait_obisnuit_lesa": listing.trait_obisnuit_lesa,
        "trait_nu_latla": listing.trait_nu_latla,
        "trait_apartament": listing.trait_apartament,
        "trait_se_adapteaza": listing.trait_se_adapteaza,
        "trait_tolereaza_singur": listing.trait_tolereaza_singur,
        "trait_necesita_experienta": listing.trait_necesita_experienta,
        "traits_empty": not any([
            listing.trait_jucaus, listing.trait_iubitor, listing.trait_protector, listing.trait_energic,
            listing.trait_linistit, listing.trait_bun_copii, listing.trait_bun_caini, listing.trait_bun_pisici,
            listing.trait_obisnuit_casa, listing.trait_obisnuit_lesa, listing.trait_nu_latla, listing.trait_apartament,
            listing.trait_se_adapteaza, listing.trait_tolereaza_singur, listing.trait_necesita_experienta
        ]),
    }
    return render(request, "anunturi/mypet_add.html", _mypet_form_trait_labels_ctx(ctx))


def _i_love_pet_from_demo(dog: dict) -> dict:
    return {
        "pk": dog["id"],
        "nume": dog["nume"],
        "varsta": dog.get("varsta", ""),
        "descriere": dog.get("descriere", ""),
        "imagine_fallback": dog.get("imagine_fallback", DEMO_DOG_IMAGE),
        "imagine_url": "",
        "listing_available": True,
        "ilove_msg_demo": True,
        "ilove_msg_unread": 0,
        "ilove_msg_owner_inbox": False,
    }


def _i_love_pet_from_listing(listing: AnimalListing) -> dict:
    img_url = ""
    if listing.photo_1:
        try:
            img_url = listing.photo_1.url
        except Exception:
            img_url = ""
    return {
        "pk": listing.pk,
        "nume": listing.name or "—",
        "varsta": listing.age_label or "",
        "descriere": (listing.cine_sunt or listing.probleme_medicale or "")[:300],
        "imagine_fallback": DEMO_DOG_IMAGE,
        "imagine_url": img_url,
        "listing_available": bool(listing.is_published),
        "ilove_msg_demo": False,
        "ilove_msg_unread": 0,
        "ilove_msg_owner_inbox": False,
    }


def _i_love_site_cart_items(user):
    """Articole în coșul de cumpărături (pagina /i-love/cos/)."""
    if not user.is_authenticated:
        return []
    try:
        return list(
            SiteCartItem.objects.filter(user=user).order_by("-created_at")[:SITE_CART_MAX_ITEMS]
        )
    except Exception:
        return []


_TITLE_LEI_TAIL = re.compile(r"(\d+(?:[.,]\d+)?)\s*lei\b", re.IGNORECASE)


def _site_cart_title_last_lei_amount(title: str) -> Decimal | None:
    """Ultimul număr dinainte de „lei” din titlu (ex. linii publicitate); altfel None."""
    if not title:
        return None
    matches = _TITLE_LEI_TAIL.findall(title)
    if not matches:
        return None
    raw = matches[-1].replace(",", ".")
    try:
        return Decimal(raw).quantize(Decimal("0.01"))
    except Exception:
        return None


SITE_CART_KIND_LABELS = {
    SiteCartItem.KIND_SERVICII_OFFER: "Servicii (ofertă partener)",
    SiteCartItem.KIND_SHOP: "Shop",
    SiteCartItem.KIND_SHOP_CUSTOM: "Shop — produse personalizate",
    SiteCartItem.KIND_SHOP_FOTO: "Shop — magazin foto",
    SiteCartItem.KIND_PUBLICITATE: "Publicitate",
    SiteCartItem.KIND_PROMO_A2: "Promovare animal (MyPet / A2)",
}

SITE_CART_EU_PAID_KINDS = {
    SiteCartItem.KIND_PUBLICITATE,
    SiteCartItem.KIND_PROMO_A2,
    SiteCartItem.KIND_SHOP_CUSTOM,
    SiteCartItem.KIND_SHOP_FOTO,
}


def _site_cart_buyer_prefill(user) -> dict:
    """Date cumpărător din cont + UserProfile (fișă)."""
    full_name = (user.get_full_name() or user.username or "").strip()
    email = (user.email or "").strip()
    out = {
        "buyer_full_name": full_name,
        "buyer_email": email,
        "buyer_phone": "",
        "buyer_county": "",
        "buyer_city": "",
        "buyer_address": "",
        "buyer_company_display": "",
        "buyer_company_legal": "",
        "buyer_company_cui": "",
    }
    try:
        prof = user.profile
    except UserProfile.DoesNotExist:
        return out
    out["buyer_phone"] = (prof.phone or "").strip()
    out["buyer_county"] = (prof.judet or "").strip()
    out["buyer_city"] = (prof.oras or "").strip()
    disp = (prof.company_display_name or "").strip()
    legal = (prof.company_legal_name or "").strip()
    out["buyer_company_display"] = disp or legal
    out["buyer_company_legal"] = legal
    out["buyer_company_cui"] = (prof.company_cui or "").strip()
    addr = (prof.company_address or "").strip()
    cj = (prof.company_judet or "").strip()
    co = (prof.company_oras or "").strip()
    if addr or cj or co:
        out["buyer_address"] = " ".join(x for x in (addr, cj, co) if x).strip()[:500]
    return out


def _site_cart_build_checkout_snapshot(user):
    """Linii coș curente + total estimativ (parser lei din titlu)."""
    items = list(
        SiteCartItem.objects.filter(user=user).order_by("-created_at")[:SITE_CART_MAX_ITEMS]
    )
    lines = []
    total = Decimal("0.00")
    unpriced = 0
    for it in items:
        lei = _site_cart_title_last_lei_amount(it.title)
        if lei is not None:
            total += lei
        else:
            unpriced += 1
        lines.append(
            {
                "ref_key": it.ref_key,
                "kind": it.kind,
                "kind_label": SITE_CART_KIND_LABELS.get(it.kind, it.kind),
                "title": it.title,
                "detail_url": it.detail_url or "",
                "line_lei": str(lei) if lei is not None else None,
            }
        )
    return items, lines, total.quantize(Decimal("0.01")), unpriced


def _site_cart_publicitate_lines_from_checkout(lines: list[dict]) -> tuple[list[dict], list[str]]:
    """
    Extrage liniile publicitate din snapshot-ul de checkout (coș general)
    și le convertește în schema acceptată de _publicitate_parse_cart_lines.
    """
    out: list[dict] = []
    ref_keys: list[str] = []
    for row in lines:
        if (row.get("kind") or "").strip() != SiteCartItem.KIND_PUBLICITATE:
            continue
        title = (row.get("title") or "").strip()
        parts = [p.strip() for p in title.split("·")]
        if len(parts) < 4:
            continue
        code = parts[1]
        qty_m = re.search(r"cant\.\s*(\d+)\s+([^\s·]+)", parts[2], flags=re.IGNORECASE)
        if not qty_m:
            continue
        try:
            qty = int(qty_m.group(1))
        except (TypeError, ValueError):
            continue
        unit = (qty_m.group(2) or "").strip() or "luna"
        section = ""
        detail_url = (row.get("detail_url") or "").strip()
        if detail_url:
            try:
                q = parse_qs(urlparse(detail_url).query or "")
                section = (q.get("sect") or [""])[0].strip().lower()
            except Exception:
                section = ""
        if not section:
            section = (parts[0] or "").strip().lower()
        if section not in PUBLICITATE_SLOT_MAP:
            continue
        cat = _publicitate_catalog_row(section, code)
        if not cat:
            continue
        out.append(
            {
                "section": section,
                "code": code,
                "unit": unit,
                "unit_price": str(cat["price"]),
                "qty": qty,
                "note": "",
                "start_date": "",
            }
        )
        rk = (row.get("ref_key") or "").strip()
        if rk:
            ref_keys.append(rk)
    return out, ref_keys


def _site_cart_checkout_create_publicitate_order(request, checkout_lines: list[dict], payment_ref: str):
    """
    Din checkout-ul coșului general, creează comandă Publicitate (PAID) pentru
    liniile de tip publicitate, astfel încât să apară în „Comenzile mele publicitare”.
    Returnează (order_or_none, ref_keys_consumed).
    """
    raw_lines, pub_ref_keys = _site_cart_publicitate_lines_from_checkout(checkout_lines)
    if not raw_lines:
        return None, []
    validated, total, _adjustments, err = _publicitate_parse_cart_lines(raw_lines)
    if err is not None:
        msg = "Liniile de publicitate din coș nu pot fi procesate acum."
        try:
            payload = json.loads((err.content or b"{}").decode() or "{}")
            msg = (payload.get("error") or msg).strip() or msg
        except Exception:
            pass
        raise ValueError(msg)
    order = PublicitateOrder.objects.create(
        user=request.user,
        status=PublicitateOrder.STATUS_PAID,
        total_lei=total,
        payment_provider="site_cart_checkout",
        payment_ref=(payment_ref or "")[:80],
        paid_at=timezone.now(),
    )
    for row in validated:
        PublicitateOrderLine.objects.create(order=order, **row)
    _apply_publicitate_paid_order(order)
    try:
        access = _ensure_publicitate_creative_for_order(order)
        _send_publicitate_creative_email(order, access)
    except Exception:
        logging.getLogger(__name__).exception("publicitate_creative_email_site_cart_checkout")
    return order, pub_ref_keys


def _site_cart_line_is_donation(line: dict) -> bool:
    """Detectează donațiile din coș chiar dacă tipul dedicat nu e încă modelat în KIND_CHOICES."""
    kind = (line.get("kind") or "").strip().lower()
    ref_key = (line.get("ref_key") or "").strip().lower()
    title = (line.get("title") or "").strip().lower()
    if kind in {"donatie", "donatii", "donation", "donations"}:
        return True
    if ref_key.startswith(("donatie:", "donatii:", "donation:", "donations:")):
        return True
    return "donat" in title or "donat" in ref_key


def _site_cart_eu_owner_usernames() -> set[str]:
    """
    Useri tratați ca owner EU-ADOPT pentru routingul owner-based.
    Config opțional: SITE_EU_OWNER_USERS="admin,euadopt_shop".
    """
    out = {"admin", "euadopt_shop"}
    raw = (getattr(settings, "SITE_EU_OWNER_USERS", None) or "").strip()
    if raw:
        out |= {x.strip().lower() for x in raw.split(",") if x.strip()}
    return out


def _site_cart_owner_for_line(line: dict) -> dict:
    """
    Returnează owner-ul economic al unei linii de coș.
    Pentru tipuri fără owner explicit în model (ex. shop demo), întoarce owner necunoscut.
    """
    kind = (line.get("kind") or "").strip()
    ref_key = (line.get("ref_key") or "").strip()

    # Tipuri gestionate direct de EU-ADOPT în modelul curent.
    if kind in {
        SiteCartItem.KIND_PUBLICITATE,
        SiteCartItem.KIND_SHOP_CUSTOM,
        SiteCartItem.KIND_SHOP_FOTO,
    } or _site_cart_line_is_donation(line):
        return {
            "owner_user_id": None,
            "owner_username": "euadopt_shop",
            "owner_source": "eu_system",
        }

    if kind == SiteCartItem.KIND_SERVICII_OFFER and ref_key.startswith("servicii_offer:"):
        try:
            offer_id = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            offer_id = 0
        if offer_id:
            off = (
                CollaboratorServiceOffer.objects.filter(pk=offer_id)
                .select_related("collaborator")
                .only("collaborator_id", "collaborator__username")
                .first()
            )
            if off and off.collaborator_id:
                return {
                    "owner_user_id": off.collaborator_id,
                    "owner_username": (off.collaborator.username or "").strip().lower(),
                    "owner_source": "offer_collaborator",
                }

    if kind == SiteCartItem.KIND_PROMO_A2 and ref_key.startswith("promo_a2:"):
        try:
            pet_id = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            pet_id = 0
        if pet_id:
            pet = AnimalListing.objects.filter(pk=pet_id).only("owner_id").first()
            if pet and pet.owner_id:
                owner = User.objects.filter(pk=pet.owner_id).only("username").first()
                return {
                    "owner_user_id": pet.owner_id,
                    "owner_username": ((owner.username if owner else "") or "").strip().lower(),
                    "owner_source": "animal_owner",
                }

    # shop demo (shop:tab:idx) nu are încă owner persistent pe produs.
    return {
        "owner_user_id": None,
        "owner_username": "",
        "owner_source": "unknown",
    }


def _site_cart_split_fulfillment(lines: list[dict]) -> tuple[list[dict], list[dict]]:
    """
    Separă liniile:
    - eu_paid: unde încasează EU-ADOPT
    - partner_direct: unde plata rămâne direct între client și colaborator
    """
    eu_paid = []
    partner_direct = []
    eu_owner_usernames = _site_cart_eu_owner_usernames()
    for row in lines:
        kind = (row.get("kind") or "").strip()
        owner = _site_cart_owner_for_line(row)
        owner_username = (owner.get("owner_username") or "").strip().lower()
        is_eu_paid = (
            kind in SITE_CART_EU_PAID_KINDS
            or _site_cart_line_is_donation(row)
            or owner.get("owner_source") == "eu_system"
            or (owner_username and owner_username in eu_owner_usernames)
        )
        row_out = dict(row)
        row_out["fulfillment_target"] = "eu_paid" if is_eu_paid else "partner_direct"
        row_out["owner_user_id"] = owner.get("owner_user_id")
        row_out["owner_username"] = owner.get("owner_username")
        row_out["owner_source"] = owner.get("owner_source")
        if is_eu_paid:
            eu_paid.append(row_out)
        else:
            partner_direct.append(row_out)
    return eu_paid, partner_direct


def _site_cart_partner_offer_ids_from_lines(lines: list[dict]) -> list[int]:
    out: list[int] = []
    seen: set[int] = set()
    for row in lines:
        if (row.get("kind") or "").strip() != SiteCartItem.KIND_SERVICII_OFFER:
            continue
        ref_key = (row.get("ref_key") or "").strip()
        if not ref_key.startswith("servicii_offer:"):
            continue
        try:
            oid = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            continue
        if oid > 0 and oid not in seen:
            seen.add(oid)
            out.append(oid)
    return out


def _checkout_buyer_snapshot_from_intent(request, intent: SiteCartCheckoutIntent) -> dict:
    buyer_user = request.user if getattr(request.user, "is_authenticated", False) else None
    return {
        "email": (intent.buyer_email or "").strip(),
        "name": (intent.buyer_full_name or "").strip() or (buyer_user.username if buyer_user else "Utilizator"),
        "phone": (intent.buyer_phone or "").strip(),
        "locality": ", ".join(x for x in [(intent.buyer_city or "").strip(), (intent.buyer_county or "").strip()] if x),
        "user": buyer_user,
    }


def _issue_partner_direct_claims_from_checkout(request, intent: SiteCartCheckoutIntent, partner_lines: list[dict]) -> dict:
    """
    Pentru liniile partner_direct eligibile (servicii_offer), emite cod comun buyer+colaborator
    și trimite aceleași tipuri de notificări/email ca fluxul public_offer_request.
    """
    offer_ids = _site_cart_partner_offer_ids_from_lines(partner_lines)
    if not offer_ids:
        return {"issued": 0, "failed": 0, "codes": []}

    buyer = _checkout_buyer_snapshot_from_intent(request, intent)
    dest_email = buyer.get("email") or ""
    issued = 0
    failed = 0
    codes: list[str] = []
    for offer_id in offer_ids:
        code = None
        offer = None
        collab = None
        try:
            with transaction.atomic():
                offer = (
                    CollaboratorServiceOffer.objects.select_for_update()
                    .filter(is_active=True, pk=offer_id)
                    .select_related("collaborator")
                    .first()
                )
                if not offer or not _collab_offer_is_valid_today(offer):
                    failed += 1
                    continue
                collab = offer.collaborator
                collab_mail = (collab.email or "").strip() if collab else ""
                if not collab or not collab_mail:
                    failed += 1
                    continue
                claimed = CollaboratorOfferClaim.objects.filter(offer_id=offer.pk).count()
                if offer.quantity_available is not None and claimed >= int(offer.quantity_available):
                    failed += 1
                    continue
                code = _generate_collab_offer_code()
                CollaboratorOfferClaim.objects.create(
                    offer=offer,
                    code=code,
                    buyer_user=buyer["user"],
                    buyer_email=dest_email,
                    buyer_name_snapshot=buyer["name"],
                    buyer_phone_snapshot=(buyer["phone"][:40] if buyer["phone"] else ""),
                    buyer_locality_snapshot=(buyer["locality"][:200] if buyer["locality"] else ""),
                )
                if offer.quantity_available is not None:
                    new_count = claimed + 1
                    if new_count >= int(offer.quantity_available):
                        offer.is_active = False
                        offer.save(update_fields=["is_active", "updated_at"])
        except Exception:
            logging.exception("checkout partner claim create failed offer=%s", offer_id)
            failed += 1
            continue

        if not code or offer is None or collab is None:
            failed += 1
            continue

        try:
            if buyer.get("user"):
                _inbox.create_inbox_notification(
                    buyer["user"],
                    _inbox.KIND_OFFER_CLAIM_BUYER,
                    "Ofertă solicitată din checkout",
                    f"Cod {code}: {offer.title}. Datele au fost trimise pe email.",
                    link_url=reverse("servicii"),
                    metadata={"offer_id": offer.pk, "claim_code": code, "source": "site_cart_checkout"},
                )
            _inbox.create_inbox_notification(
                collab,
                _inbox.KIND_OFFER_CLAIM_COLLABORATOR,
                "Solicitare nouă din checkout",
                f"Cod {code}: {offer.title}. Verifică emailul pentru datele solicitantului.",
                link_url=reverse("collab_offers_control") + "?open_messages=1",
                metadata={"offer_id": offer.pk, "claim_code": code, "source": "site_cart_checkout"},
            )
        except Exception:
            logging.exception("checkout partner claim inbox failed offer=%s", offer.pk)

        cabinet_txt = _cabinet_block_for_buyer_email(collab)
        buyer_subject = f"EU-Adopt – cod ofertă {code}: {offer.title}"
        buyer_body = (
            f"Bună {buyer['name']},\n\n"
            f"Codul ofertei (îl au și partenerul și tu): {code}\n\n"
            f"Ofertă: {offer.title}\n\n"
            f"--- Date partener (contact) ---\n{cabinet_txt}\n\n"
        )
        if offer.description:
            buyer_body += f"--- Descriere ---\n{offer.description}\n\n"
        if offer.price_hint:
            buyer_body += f"Preț indicat: {offer.price_hint}\n"
        if offer.discount_percent:
            buyer_body += f"Discount: {offer.discount_percent}%\n"
        buyer_body += "\n---\nEU-Adopt\n"

        collab_subject = f"EU-Adopt – solicitare ofertă [{code}] {offer.title}"
        collab_body = (
            "Ai o nouă solicitare din checkout pentru ofertă.\n\n"
            f"Cod ofertă (același ca la client): {code}\n"
            f"Titlu ofertă: {offer.title}\n\n"
            f"--- Date cumpărător ---\n"
            f"Nume: {buyer['name']}\n"
            f"Email: {dest_email}\n"
        )
        if buyer["phone"]:
            collab_body += f"Telefon: {buyer['phone']}\n"
        if buyer["locality"]:
            collab_body += f"Localitate: {buyer['locality']}\n"
        collab_body += "\n---\nEU-Adopt\n"

        cabinet_maps_url = _cabinet_maps_url_for_buyer_email(collab)
        if cabinet_maps_url:
            buyer_body += f"Navigare la partener (hartă): {cabinet_maps_url}\n"
        buyer_maps_html = _html_email_maps_cta_button(cabinet_maps_url, "DU-MĂ LA LOCAȚIE")
        buyer_html = (
            f"<p>Bună {escape(buyer['name'])},</p>"
            f"<p>Codul ofertei (îl au și partenerul și tu): <strong>{escape(code)}</strong></p>"
            f"<p>Ofertă: <strong>{escape(offer.title)}</strong></p>"
            f"<p><strong>Date partener (contact)</strong></p>"
            f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(cabinet_txt)}</pre>"
        )
        if offer.description:
            buyer_html += f"<p><strong>Descriere</strong><br>{escape(offer.description)}</p>"
        if offer.price_hint:
            buyer_html += f"<p>Preț indicat: {escape(offer.price_hint)}</p>"
        if offer.discount_percent:
            buyer_html += f"<p>Discount: {escape(str(offer.discount_percent))}%</p>"
        buyer_html += buyer_maps_html + "<p>—<br>EU-Adopt</p>"

        buyer_loc_url = _buyer_maps_url_for_collab_email(buyer)
        if buyer_loc_url:
            collab_body += f"Navigare la solicitant (hartă): {buyer_loc_url}\n"
        collab_maps_html = _html_email_maps_cta_button(buyer_loc_url, "DU-MĂ LA LOCAȚIE")
        collab_buyer_block = f"Nume: {buyer['name']}\nEmail: {dest_email}\n"
        if buyer["phone"]:
            collab_buyer_block += f"Telefon: {buyer['phone']}\n"
        if buyer["locality"]:
            collab_buyer_block += f"Localitate: {buyer['locality']}\n"
        collab_html = (
            "<p>Ai o nouă solicitare din checkout pentru ofertă.</p>"
            f"<p>Cod ofertă (același ca la client): <strong>{escape(code)}</strong><br>"
            f"Titlu ofertă: <strong>{escape(offer.title)}</strong></p>"
            "<p><strong>Date cumpărător</strong></p>"
            f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(collab_buyer_block)}</pre>"
            + collab_maps_html
            + "<p>—<br>EU-Adopt</p>"
        )

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
        buyer_uname = buyer["user"].username if buyer.get("user") else (dest_email.split("@", 1)[0] if "@" in dest_email else None)
        collab_mail = (collab.email or "").strip()
        mail_ok = True
        try:
            send_mail_text_and_html(
                email_subject_for_user(buyer_uname, buyer_subject),
                buyer_body,
                from_email,
                [dest_email],
                buyer_html,
                mail_kind="offer_claim_buyer",
            )
        except Exception:
            logging.exception("checkout partner claim buyer mail failed offer=%s", offer.pk)
            mail_ok = False
        try:
            send_mail_text_and_html(
                email_subject_for_user(collab.username, collab_subject),
                collab_body,
                from_email,
                [collab_mail],
                collab_html,
                mail_kind="offer_claim_collaborator",
            )
        except Exception:
            logging.exception("checkout partner claim collab mail failed offer=%s", offer.pk)
            mail_ok = False

        if mail_ok:
            issued += 1
            codes.append(code)
        else:
            failed += 1

    return {"issued": issued, "failed": failed, "codes": codes}


SITE_CART_PAYMENT_METHOD_UI = [
    {
        "value": SiteCartCheckoutIntent.PAYMENT_CARD_ONLINE,
        "label": "Card bancar online (Visa / Mastercard)",
        "help": "Procesatorul de plată se leagă la confirmare; după trimiterea cererii vei primi instrucțiuni pe e-mail.",
    },
    {
        "value": SiteCartCheckoutIntent.PAYMENT_BANK_TRANSFER,
        "label": "Transfer bancar / ordin de plată (OP)",
        "help": "Date cont și referință comandă îți sunt comunicate după validarea cererii.",
    },
    {
        "value": SiteCartCheckoutIntent.PAYMENT_COMPANY_INVOICE,
        "label": "Factură pe firmă",
        "help": "Folosim CUI și datele firmă din fișă; poți completa corecții în formular înainte de trimitere.",
    },
]


def _site_cart_checkout_staff_recipient_emails() -> list[str]:
    raw = (getattr(settings, "SITE_CART_CHECKOUT_STAFF_EMAILS", None) or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()][:12]
    return _publicitate_creative_staff_recipient_emails()


def _send_site_cart_checkout_staff_email(request, intent: SiteCartCheckoutIntent) -> None:
    recipients = _site_cart_checkout_staff_recipient_emails()
    if not recipients:
        return
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or None
    if not from_email:
        return
    pm_label = dict(SiteCartCheckoutIntent.PAYMENT_CHOICES).get(intent.payment_method, intent.payment_method)
    buyer_type_label = dict(SiteCartCheckoutIntent.BUYER_TYPE_CHOICES).get(intent.buyer_type, intent.buyer_type)
    try:
        admin_path = reverse("admin:home_sitecartcheckoutintent_change", args=[intent.pk])
        base = (getattr(settings, "SITE_BASE_URL", None) or "").strip().rstrip("/")
        admin_hint = f"{base}{admin_path}" if base else admin_path
    except Exception:
        admin_hint = f"admin SiteCartCheckoutIntent #{intent.pk}"
    eu_paid_lines, partner_lines = _site_cart_split_fulfillment(intent.lines_json or [])
    eu_paid_txt = []
    for row in eu_paid_lines:
        eu_paid_txt.append(
            f"- [{row.get('kind_label', row.get('kind', ''))}] {row.get('title', '')} "
            f"(ref {row.get('ref_key', '')}) sumă titlu: {row.get('line_lei', '—')}"
        )
    partner_txt = []
    for row in partner_lines:
        partner_txt.append(
            f"- [{row.get('kind_label', row.get('kind', ''))}] {row.get('title', '')} "
            f"(ref {row.get('ref_key', '')}) sumă titlu: {row.get('line_lei', '—')}"
        )
    body = "\n".join(
        [
            f"Cerere plată coș site #{intent.pk}",
            f"Utilizator: {intent.user.username} (id {intent.user_id}) — {intent.user.email or '-'}",
            f"Tip cumpărător: {buyer_type_label}",
            f"Mod plată: {pm_label}",
            "",
            "Date cumpărător (formular):",
            f"Nume: {intent.buyer_full_name}",
            f"E-mail: {intent.buyer_email}",
            f"Telefon: {intent.buyer_phone or '-'}",
            f"Județ: {intent.buyer_county or '-'} | Oraș: {intent.buyer_city or '-'}",
            f"Adresă / note adresă: {intent.buyer_address or '-'}",
            f"Firmă: {intent.buyer_company_display or '-'} | Juridic: {intent.buyer_company_legal or '-'} | CUI: {intent.buyer_company_cui or '-'}",
            f"Mesaj client: {(intent.buyer_note or '').strip() or '-'}",
            "",
            f"Total estimativ: {intent.total_lei} lei | Articole fără sumă în titlu: {intent.unpriced_count}",
            "",
            "Linii EU-ADOPT (încasare la EU-ADOPT):",
            "\n".join(eu_paid_txt) if eu_paid_txt else "(niciuna)",
            "",
            "Linii colaboratori (plată directă la colaborator):",
            "\n".join(partner_txt) if partner_txt else "(niciuna)",
            "",
            f"Admin: {admin_hint}",
        ]
    )
    try:
        EmailMessage(
            subject=f"[EU-Adopt staff] Plată coș #{intent.pk} — {intent.total_lei} lei",
            body=body,
            from_email=from_email,
            to=recipients[:8],
        ).send(fail_silently=False)
    except Exception:
        logging.getLogger(__name__).exception("site_cart_checkout_staff_email")
    buyer_copy = (
        f"Bună,\n\n"
        f"Am înregistrat cererea ta de plată pentru coșul de cumpărături (referință #{intent.pk}).\n"
        f"Total estimativ: {intent.total_lei} lei.\n"
        f"Mod de plată ales (pentru liniile EU-ADOPT): {pm_label}.\n"
        f"Pentru liniile colaboratorilor, plata se face direct la colaborator.\n\n"
        f"Echipa EU-ADOPT te contactează pentru pasul următor.\n\n"
        f"— EU-ADOPT"
    )
    try:
        if intent.buyer_email:
            EmailMessage(
                subject=f"[EU-Adopt] Cerere plată coș #{intent.pk} înregistrată",
                body=buyer_copy,
                from_email=from_email,
                to=[intent.buyer_email],
            ).send(fail_silently=True)
    except Exception:
        pass


def i_love_cos_view(request):
    """Pagina dedicată coșului (oferte/produse marcate cu 🛒), separată de lista inimioare."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('i_love_cos')}")
    cart_items = _i_love_site_cart_items(request.user)
    total_lei = Decimal("0.00")
    unpriced = 0
    for it in cart_items:
        v = _site_cart_title_last_lei_amount(it.title)
        if v is not None:
            total_lei += v
        else:
            unpriced += 1
    return render(
        request,
        "anunturi/i_love_cos.html",
        {
            "cart_items": cart_items,
            "cart_total_lei": total_lei,
            "cart_total_lei_display": f"{total_lei:.2f}".replace(".", ","),
            "cart_unpriced_count": unpriced,
        },
    )


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def site_cart_checkout_view(request):
    """Formular plată unificat: date din fișă + moduri de plată pentru tot coșul site."""
    items, lines, total_lei, unpriced = _site_cart_build_checkout_snapshot(request.user)
    if not items:
        messages.info(request, "Coșul este gol. Adaugă articole înainte de plată.")
        return redirect("i_love_cos")
    eu_paid_lines, partner_direct_lines = _site_cart_split_fulfillment(lines)
    has_eu_paid = bool(eu_paid_lines)
    has_partner_direct = bool(partner_direct_lines)

    allowed_pm = {x["value"] for x in SITE_CART_PAYMENT_METHOD_UI}
    allowed_buyer_types = {x[0] for x in SiteCartCheckoutIntent.BUYER_TYPE_CHOICES}
    form_errors: list[str] = []
    prefill = _site_cart_buyer_prefill(request.user)
    buyer_note_value = ""
    selected_buyer_type = SiteCartCheckoutIntent.BUYER_TYPE_PF
    selected_payment = ""

    if request.method == "POST":
        buyer_type = (request.POST.get("buyer_type") or "").strip()
        buyer_full_name = (request.POST.get("buyer_full_name") or "").strip()[:160]
        buyer_email = (request.POST.get("buyer_email") or "").strip()[:254].lower()
        buyer_phone = (request.POST.get("buyer_phone") or "").strip()[:40]
        buyer_county = (request.POST.get("buyer_county") or "").strip()[:120]
        buyer_city = (request.POST.get("buyer_city") or "").strip()[:120]
        buyer_address = (request.POST.get("buyer_address") or "").strip()[:500]
        buyer_company_display = (request.POST.get("buyer_company_display") or "").strip()[:255]
        buyer_company_legal = (request.POST.get("buyer_company_legal") or "").strip()[:255]
        buyer_company_cui = (request.POST.get("buyer_company_cui") or "").strip()[:40]
        buyer_note = (request.POST.get("buyer_note") or "").strip()[:600]
        buyer_note_value = buyer_note
        selected_buyer_type = buyer_type if buyer_type in allowed_buyer_types else SiteCartCheckoutIntent.BUYER_TYPE_PF
        payment_method = (request.POST.get("payment_method") or "").strip()
        selected_payment = payment_method

        prefill = {
            "buyer_full_name": buyer_full_name,
            "buyer_email": buyer_email,
            "buyer_phone": buyer_phone,
            "buyer_county": buyer_county,
            "buyer_city": buyer_city,
            "buyer_address": buyer_address,
            "buyer_company_display": buyer_company_display,
            "buyer_company_legal": buyer_company_legal,
            "buyer_company_cui": buyer_company_cui,
        }

        if not buyer_full_name:
            form_errors.append("Numele complet este obligatoriu.")
        if not buyer_email or "@" not in buyer_email:
            form_errors.append("E-mailul este obligatoriu și trebuie să fie valid.")
        if buyer_type not in allowed_buyer_types:
            form_errors.append("Alege tipul cumpărătorului: persoană fizică sau juridică.")
        if selected_buyer_type == SiteCartCheckoutIntent.BUYER_TYPE_PJ:
            if not buyer_company_legal:
                form_errors.append("Pentru persoană juridică, denumirea juridică este obligatorie.")
            if not buyer_company_cui:
                form_errors.append("Pentru persoană juridică, CUI/CIF este obligatoriu.")
        if has_eu_paid and payment_method not in allowed_pm:
            form_errors.append("Alege un mod de plată din listă.")
        if not has_eu_paid:
            payment_method = SiteCartCheckoutIntent.PAYMENT_BANK_TRANSFER

        if not form_errors:
            pub_order = None
            try:
                with transaction.atomic():
                    intent = SiteCartCheckoutIntent.objects.create(
                        user=request.user,
                        buyer_type=selected_buyer_type,
                        payment_method=payment_method,
                        buyer_full_name=buyer_full_name,
                        buyer_email=buyer_email,
                        buyer_phone=buyer_phone,
                        buyer_county=buyer_county,
                        buyer_city=buyer_city,
                        buyer_address=buyer_address,
                        buyer_company_display=buyer_company_display,
                        buyer_company_legal=buyer_company_legal,
                        buyer_company_cui=buyer_company_cui,
                        lines_json=lines,
                        total_lei=total_lei,
                        unpriced_count=unpriced,
                        buyer_note=buyer_note,
                    )
                    pub_order, pub_ref_keys = _site_cart_checkout_create_publicitate_order(
                        request,
                        lines,
                        payment_ref=f"SITECART-{intent.pk}",
                    )
                    if pub_ref_keys:
                        SiteCartItem.objects.filter(user=request.user, ref_key__in=pub_ref_keys).delete()
            except Exception:
                logging.getLogger(__name__).exception("site_cart_checkout_create")
                messages.error(request, "Nu am putut salva cererea. Încearcă din nou.")
                return redirect("site_cart_checkout")

            _send_site_cart_checkout_staff_email(request, intent)
            partner_claim_result = _issue_partner_direct_claims_from_checkout(
                request, intent, partner_direct_lines
            )
            request.session["site_cart_checkout_partner_codes"] = partner_claim_result.get("codes", [])[:24]
            request.session.modified = True
            if partner_claim_result.get("issued"):
                messages.success(
                    request,
                    f"Au fost emise coduri comune pentru {partner_claim_result['issued']} ofertă(e) colaborator.",
                )
            if partner_claim_result.get("failed"):
                messages.warning(
                    request,
                    "Unele coduri pentru colaboratori nu au putut fi emise sau trimise acum. Verifică e-mailurile și disponibilitatea ofertelor.",
                )
            if pub_order is not None:
                request.session[PUBLICITATE_SESSION_LAST_PAID] = pub_order.pk
                request.session.modified = True
                messages.success(
                    request,
                    f"Publicitatea a fost înregistrată în Comenzile mele publicitare (comanda #{pub_order.pk}).",
                )
            return redirect(f"{reverse('site_cart_checkout_success')}?id={intent.pk}")

    return render(
        request,
        "anunturi/i_love_cos_checkout.html",
        {
            "checkout_lines": lines,
            "eu_paid_lines": eu_paid_lines,
            "partner_direct_lines": partner_direct_lines,
            "has_eu_paid": has_eu_paid,
            "has_partner_direct": has_partner_direct,
            "checkout_total_lei": total_lei,
            "checkout_total_display": f"{total_lei:.2f}".replace(".", ","),
            "checkout_unpriced_count": unpriced,
            "form_prefill": prefill,
            "buyer_note": buyer_note_value,
            "form_errors": form_errors,
            "buyer_types": SiteCartCheckoutIntent.BUYER_TYPE_CHOICES,
            "selected_buyer_type": selected_buyer_type,
            "payment_methods": SITE_CART_PAYMENT_METHOD_UI,
            "selected_payment": selected_payment,
        },
    )


@login_required
def site_cart_checkout_success_view(request):
    intent_id = (request.GET.get("id") or "").strip()
    intent = None
    if intent_id.isdigit():
        intent = SiteCartCheckoutIntent.objects.filter(
            pk=int(intent_id), user=request.user
        ).first()
    partner_codes = request.session.pop("site_cart_checkout_partner_codes", []) or []
    if not isinstance(partner_codes, list):
        partner_codes = []
    partner_codes = [str(x).strip() for x in partner_codes if str(x).strip()][:24]
    request.session.modified = True
    return render(
        request,
        "anunturi/i_love_cos_checkout_success.html",
        {"intent": intent, "partner_codes": partner_codes},
    )


def i_love_view(request):
    """Pagina I Love: animalele bifate cu inimioară (demo DEMO_DOGS + anunțuri AnimalListing)."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('i_love')}")

    ids = list(WishlistItem.objects.filter(user=request.user).order_by("-created_at").values_list("animal_id", flat=True))
    by_demo = {d["id"]: d for d in DEMO_DOGS}
    db_ids = [i for i in ids if i not in by_demo]
    listings = {}
    if db_ids:
        listings = {x.pk: x for x in AnimalListing.objects.filter(pk__in=db_ids)}

    pets = []
    for animal_id in ids:
        if animal_id in by_demo:
            pets.append(_i_love_pet_from_demo(by_demo[animal_id]))
        elif animal_id in listings:
            pets.append(_i_love_pet_from_listing(listings[animal_id]))

    user = request.user
    active_since = _messages_active_since()
    owned_wish_pks = [p["pk"] for p in pets if not p.get("ilove_msg_demo") and listings.get(p["pk"], None) and listings[p["pk"]].owner_id == user.id]
    unread_owned = {}
    if owned_wish_pks:
        for row in (
            PetMessage.objects.filter(
                animal_id__in=owned_wish_pks,
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            )
            .values("animal_id")
            .annotate(c=Count("id"))
        ):
            unread_owned[int(row["animal_id"])] = int(row["c"])
    for p in pets:
        if p.get("ilove_msg_demo"):
            continue
        pk = int(p["pk"])
        lst = listings.get(pk)
        if not lst:
            continue
        if lst.owner_id == user.id:
            p["ilove_msg_owner_inbox"] = True
            p["ilove_msg_unread"] = int(unread_owned.get(pk, 0))
        else:
            p["ilove_msg_owner_inbox"] = False
            p["ilove_msg_unread"] = int(
                PetMessage.objects.filter(
                    animal_id=pk,
                    receiver=user,
                    sender_id=lst.owner_id,
                    is_read=False,
                    created_at__gte=active_since,
                ).count()
            )

    return render(
        request,
        "anunturi/i_love.html",
        {"pets": pets, "wishlist_ids": set(ids)},
    )


@require_POST
@csrf_protect
def wishlist_toggle_view(request):
    """Toggle inimioară pentru un animal."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    try:
        animal_id = int((request.POST.get("animal_id") or "").strip())
    except Exception:
        return JsonResponse({"ok": False, "error": "invalid_animal_id"}, status=400)

    obj = WishlistItem.objects.filter(user=request.user, animal_id=animal_id).first()
    if obj:
        obj.delete()
        active = False
    else:
        WishlistItem.objects.create(user=request.user, animal_id=animal_id)
        active = True

    wish_count = WishlistItem.objects.filter(animal_id=animal_id).count()
    user_wishlist_count = WishlistItem.objects.filter(user=request.user).count()
    return JsonResponse({
        "ok": True,
        "active": active,
        "animal_id": animal_id,
        "wish_count": wish_count,
        "user_wishlist_count": user_wishlist_count,
    })


@require_POST
@csrf_protect
def adoption_bonus_cart_unlock_view(request):
    """După „Salvează alegerile” pe Servicii: permite iconița coș pe oferte (același AR ca în sesiune)."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    try:
        ar_id = int((request.POST.get("adoption_request_id") or "").strip())
    except (TypeError, ValueError):
        return JsonResponse({"ok": False, "error": "invalid"}, status=400)
    ar = AdoptionRequest.objects.filter(
        pk=ar_id,
        adopter=request.user,
        status__in=(
            AdoptionRequest.STATUS_PENDING,
            AdoptionRequest.STATUS_ACCEPTED,
        ),
    ).first()
    if not ar:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    if ar.bonus_servicii_locked_at is None:
        ar.bonus_servicii_locked_at = timezone.now()
        ar.save(update_fields=["bonus_servicii_locked_at", "updated_at"])
    request.session[SESSION_ADOPTION_BONUS_CART_UNLOCK_AR] = ar_id
    request.session[SESSION_ADOPTION_BONUS_SHOW_LOCKED_NOTICE_AR] = ar_id
    request.session.modified = True
    return JsonResponse({"ok": True})


@require_POST
@csrf_protect
def site_cart_toggle_view(request):
    """Adaugă / scoate articol din coșul de cumpărături (iconița 🛒 din navbar)."""
    if not request.user.is_authenticated:
        return JsonResponse({"ok": False, "error": "login_required"}, status=401)
    kind = (request.POST.get("kind") or "").strip()
    ref_key = (request.POST.get("ref_key") or "").strip()[:96]
    title = (request.POST.get("title") or "").strip()[:220]
    detail_url = _safe_site_cart_detail_url(request.POST.get("detail_url") or "")
    allowed_kinds = {
        SiteCartItem.KIND_SERVICII_OFFER,
        SiteCartItem.KIND_SHOP,
        SiteCartItem.KIND_SHOP_CUSTOM,
        SiteCartItem.KIND_SHOP_FOTO,
        SiteCartItem.KIND_PUBLICITATE,
        SiteCartItem.KIND_PROMO_A2,
    }
    if kind not in allowed_kinds:
        return JsonResponse({"ok": False, "error": "invalid_kind"}, status=400)
    if not ref_key or not title:
        return JsonResponse({"ok": False, "error": "missing_fields"}, status=400)

    if kind == SiteCartItem.KIND_SERVICII_OFFER:
        if not ref_key.startswith("servicii_offer:"):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        try:
            pk = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        if not CollaboratorServiceOffer.objects.filter(pk=pk, is_active=True).exists():
            return JsonResponse({"ok": False, "error": "offer_gone"}, status=400)
    elif kind == SiteCartItem.KIND_SHOP:
        if not re.match(r"^shop:[a-z]+:\d+$", ref_key):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
    elif kind == SiteCartItem.KIND_SHOP_CUSTOM:
        if ref_key != "shop_custom:page":
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
    elif kind == SiteCartItem.KIND_SHOP_FOTO:
        if not ref_key.startswith("shop_foto:"):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        try:
            idx = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        if idx < 0 or idx >= 200:
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
    elif kind == SiteCartItem.KIND_PUBLICITATE:
        if not re.match(r"^pub:[a-f0-9]{16}$", ref_key):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
    elif kind == SiteCartItem.KIND_PROMO_A2:
        if not ref_key.startswith("promo_a2:"):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        try:
            pet_pk = int(ref_key.split(":", 1)[1])
        except (IndexError, ValueError):
            return JsonResponse({"ok": False, "error": "bad_ref"}, status=400)
        pet_ok = AnimalListing.objects.filter(
            pk=pet_pk,
            owner=request.user,
            is_published=True,
            species__in=["dog", "cat"],
        ).exists()
        if not pet_ok:
            return JsonResponse({"ok": False, "error": "promo_pet_invalid"}, status=400)

    obj = SiteCartItem.objects.filter(user=request.user, ref_key=ref_key).first()
    if obj:
        obj.delete()
        active = False
    else:
        n = SiteCartItem.objects.filter(user=request.user).count()
        if n >= SITE_CART_MAX_ITEMS:
            return JsonResponse({"ok": False, "error": "cart_full"}, status=400)
        SiteCartItem.objects.create(
            user=request.user,
            ref_key=ref_key,
            kind=kind,
            title=title,
            detail_url=detail_url,
        )
        active = True
    cnt = SiteCartItem.objects.filter(user=request.user).count()
    return JsonResponse(
        {"ok": True, "active": active, "ref_key": ref_key, "user_site_cart_count": cnt}
    )


@require_POST
@csrf_protect
def pet_track_event_view(request, pk: int):
    """
    Tracking pentru MyPet:
    - media_view: click pe poză/video (deschidere în notă)
    - share_click: click pe butonul Distribuie (încercare share)
    """
    event = (request.POST.get("event") or "").strip()
    if event not in {"media_view", "share_click"}:
        return JsonResponse({"ok": False, "error": "invalid_event"}, status=400)

    # Acceptăm și neautentificat (adoptator), dar doar pentru anunțuri publicate
    qs = AnimalListing.objects.filter(pk=pk, is_published=True)
    updated = 0
    if event == "media_view":
        updated = qs.update(media_views=F("media_views") + 1)
    elif event == "share_click":
        updated = qs.update(share_clicks=F("share_clicks") + 1)
    if not updated:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    return JsonResponse({"ok": True})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_observatii_update_view(request, pk: int):
    """
    Autosave pentru caseta de observații din MyPet.
    Doar proprietarul poate edita.
    """
    pet = get_object_or_404(AnimalListing, pk=pk, owner=request.user)
    # Păstrăm textul exact cum a fost introdus (fără strip), ca userul să vadă aceeași valoare după refresh.
    text = (request.POST.get("observatii") or "")
    # Limită pentru a evita payload-uri uriașe
    if len(text) > 5000:
        text = text[:5000]
    pet.observatii = text
    pet.save(update_fields=["observatii"])
    return JsonResponse({"ok": True, "observatii": pet.observatii})


@login_required
@require_POST
@csrf_protect
def pet_send_message_view(request, pk: int):
    """Mesaj nou trimis din fișa publică a animalului către owner."""
    pet = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    if pet.owner_id == request.user.id:
        return JsonResponse({"ok": False, "error": "Nu poți trimite mesaj către tine."}, status=400)
    if not _adopter_messaging_allowed(pet, request.user):
        return JsonResponse(
            {
                "ok": False,
                "error": "Nu poți trimite mesaj în această situație (cont, anunț sau animal deja adoptat).",
            },
            status=403,
        )
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    PetMessage.objects.create(
        animal=pet,
        sender=request.user,
        receiver=pet.owner,
        body=text,
        is_read=False,
    )
    return JsonResponse({"ok": True})


def _owner_pet_message_unread_counts_map(user):
    """
    Pentru proprietar: id animal (string) -> număr mesaje necitite (receiver=user, fereastra activă).
    Aliniat cu agregarea din mypet_view (PetMessage, is_read=False, created_at >= active_since).
    """
    if not user or not getattr(user, "is_authenticated", False):
        return {}
    active_since = _messages_active_since()
    owned_ids = list(AnimalListing.objects.filter(owner=user).values_list("pk", flat=True))
    if not owned_ids:
        return {}
    out = {}
    for row in (
        PetMessage.objects.filter(
            animal_id__in=owned_ids,
            receiver=user,
            is_read=False,
            created_at__gte=active_since,
        )
        .values("animal_id")
        .annotate(c=Count("id"))
    ):
        out[str(int(row["animal_id"]))] = int(row["c"])
    return out


def _adopter_pet_message_unread_total(user):
    """Total mesaje pet necitite ca adoptator (receiver=user, animalul nu îți aparține)."""
    if not user or not getattr(user, "is_authenticated", False):
        return 0
    active_since = _messages_active_since()
    return int(
        PetMessage.objects.filter(
            receiver=user,
            is_read=False,
            created_at__gte=active_since,
        )
        .exclude(animal__owner_id=user.id)
        .count()
    )


def _mypet_message_badge_payload(user):
    """JSON comun: plic navbar + plicuri pe rânduri MyPet + inbox adoptator."""
    nav = get_navbar_unread_counts(user)
    return {
        "navbar_unread_total": int(nav.get("total") or 0),
        "owner_pet_unread": _owner_pet_message_unread_counts_map(user),
        "adopter_pet_unread_total": _adopter_pet_message_unread_total(user),
    }


@login_required
@mypet_pf_org_required_json
def mypet_messages_unread_badges_view(request):
    """GET: sincronizare contoare mesaje (navbar + rânduri animal + adoptator)."""
    if request.method != "GET":
        return JsonResponse({"ok": False, "error": "Metodă nepermisă."}, status=405)
    payload = _mypet_message_badge_payload(request.user)
    return JsonResponse({"ok": True, **payload})


@login_required
@mypet_pf_org_required_json
def mypet_messages_list_view(request, pk: int):
    """Lista conversațiilor (grupare pe expeditor) pentru un pet deținut de userul curent."""
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    pet = get_object_or_404(AnimalListing, pk=pk, owner=request.user)
    base_qs = PetMessage.objects.filter(animal=pet)
    if scope == "active":
        base_qs = base_qs.filter(created_at__gte=active_since)
    else:
        base_qs = base_qs.filter(created_at__lt=active_since, created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
    qs = (
        base_qs
        .values("sender_id")
        .annotate(last_at=Max("created_at"))
        .order_by("-last_at")
    )
    out = []
    for row in qs:
        sender_id = row["sender_id"]
        if sender_id == request.user.id:
            continue
        last_msg = (
            PetMessage.objects
            .filter(animal=pet, sender_id=sender_id)
            .filter(created_at__gte=active_since if scope == "active" else now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
            .filter(created_at__lt=active_since if scope == "archived" else now + timezone.timedelta(days=36500))
            .order_by("-created_at")
            .first()
        )
        unread_qs = PetMessage.objects.filter(animal=pet, sender_id=sender_id, receiver=request.user, is_read=False)
        if scope == "active":
            unread_qs = unread_qs.filter(created_at__gte=active_since)
        else:
            unread_qs = unread_qs.filter(created_at__lt=active_since, created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
        unread = unread_qs.count()
        sender_user = getattr(last_msg, "sender", None)
        sender_name = ""
        if sender_user:
            sender_name = (f"{sender_user.first_name} {sender_user.last_name}").strip() or sender_user.username
        out.append({
            "sender_id": sender_id,
            "sender_name": sender_name or f"User {sender_id}",
            "animal_id": pet.pk,
            "animal_name": pet.name or f"Pet #{pet.pk}",
            "animal_photo_url": (pet.photo_1.url if getattr(pet, "photo_1", None) else ""),
            "animal_is_active": bool(getattr(pet, "is_published", False)),
            "animal_url": (reverse("pets_single", args=[pet.pk]) if getattr(pet, "is_published", False) else ""),
            "last_message": (last_msg.body[:80] + "…") if (last_msg and len(last_msg.body) > 80) else (last_msg.body if last_msg else ""),
            "unread_count": unread,
            "last_at": row["last_at"].isoformat() if row.get("last_at") else "",
        })
    sender_ids = [int(x["sender_id"]) for x in out]
    if sender_ids:
        q_in = PetMessage.objects.filter(
            animal=pet,
            receiver=request.user,
            sender_id__in=sender_ids,
        )
        if scope == "active":
            q_in = q_in.filter(created_at__gte=active_since)
        else:
            q_in = q_in.filter(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        ur_map = {
            int(x["sender_id"]): x["t"]
            for x in q_in.filter(is_read=False).values("sender_id").annotate(t=Max("created_at"))
        }
        ia_map = {
            int(x["sender_id"]): x["t"]
            for x in q_in.values("sender_id").annotate(t=Max("created_at"))
        }

        def _mypet_owner_list_ts(o):
            sid = int(o["sender_id"])
            u = int(o.get("unread_count") or 0)
            if u > 0:
                return ur_map.get(sid) or ia_map.get(sid)
            return ia_map.get(sid)

        for o in out:
            ts = _mypet_owner_list_ts(o)
            o["_sort_ts"] = ts
        out.sort(
            key=lambda o: (
                0 if int(o.get("unread_count") or 0) > 0 else 1,
                -((o["_sort_ts"].timestamp() if o.get("_sort_ts") else 0)),
            )
        )
        for o in out:
            o.pop("_sort_ts", None)
    badges = _mypet_message_badge_payload(request.user)
    return JsonResponse({"ok": True, "threads": out, "scope": scope, **badges})


@login_required
@mypet_pf_org_required_json
def mypet_messages_thread_view(request, pk: int, sender_id: int):
    """Thread între owner și un user pentru un pet; la deschidere marchează mesajele ca citite."""
    active_since = _messages_active_since()
    pet = get_object_or_404(AnimalListing, pk=pk, owner=request.user)
    PetMessage.objects.filter(animal=pet, sender_id=sender_id, receiver=request.user, is_read=False, created_at__gte=active_since).update(is_read=True)
    qs = (
        PetMessage.objects
        .filter(animal=pet, created_at__gte=active_since)
        .filter(Q(sender_id=sender_id, receiver=request.user) | Q(sender=request.user, receiver_id=sender_id))
        .order_by("created_at")
    )
    items = []
    for msg in qs:
        items.append({
            "id": msg.id,
            "from_owner": msg.sender_id == request.user.id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
            "is_read": bool(msg.is_read),
        })
    user = request.user
    unread_total = PetMessage.objects.filter(receiver=user, is_read=False, created_at__gte=active_since).count()
    adoption_payload = None
    ar = (
        AdoptionRequest.objects.filter(animal=pet, adopter_id=sender_id)
        .order_by("-created_at")
        .first()
    )
    if ar:
        now = timezone.now()
        expires_at = getattr(ar, "accepted_expires_at", None)
        is_expired = bool(expires_at and expires_at < now)
        has_waitlist = AdoptionRequest.objects.filter(
            animal=pet,
            status=AdoptionRequest.STATUS_PENDING,
        ).exists()
        ext_ct = int(getattr(ar, "extension_count", 0) or 0)
        can_extend_base = ar.status in {
            AdoptionRequest.STATUS_ACCEPTED,
            AdoptionRequest.STATUS_EXPIRED,
        } and ext_ct < 2
        # Aliniat cu rândul MyPet: fără coadă + expirat → fără prelungire / următor în UI.
        can_extend = can_extend_base and not (
            ar.status == AdoptionRequest.STATUS_EXPIRED and not has_waitlist
        )
        can_next = ar.status in {
            AdoptionRequest.STATUS_ACCEPTED,
            AdoptionRequest.STATUS_EXPIRED,
        } and has_waitlist
        adoption_payload = {
            "id": ar.id,
            "status": ar.status,
            "can_accept": ar.status == AdoptionRequest.STATUS_PENDING,
            "can_reject": ar.status == AdoptionRequest.STATUS_PENDING,
            "accepted_expires_at": expires_at.isoformat() if expires_at else "",
            "is_expired": is_expired or ar.status == AdoptionRequest.STATUS_EXPIRED,
            "can_extend": can_extend,
            "can_next": can_next,
        }
    badges = _mypet_message_badge_payload(user)
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "unread_total": unread_total,
            **badges,
            "adoption_request": adoption_payload,
        }
    )


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_messages_reply_view(request, pk: int, sender_id: int):
    """Răspuns owner către un adoptator pentru un pet."""
    pet = get_object_or_404(AnimalListing, pk=pk, owner=request.user)
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    target = get_user_model().objects.filter(pk=sender_id).first()
    if not target:
        return JsonResponse({"ok": False, "error": "Destinatar inexistent."}, status=404)
    PetMessage.objects.create(
        animal=pet,
        sender=request.user,
        receiver=target,
        body=text,
        is_read=False,
    )
    badges = _mypet_message_badge_payload(request.user)
    return JsonResponse({"ok": True, **badges})


@login_required
def adopter_messages_list_view(request):
    """
    Lista conversațiilor pentru adoptator (grupare pe animal).
    Răspuns JSON pentru fetch din MyPet; la navigare din browser (ex. „Deschide” din inbox)
    redirecționăm către MyPet cu deschidere automată a modului adoptator.
    """
    if (request.headers.get("Sec-Fetch-Mode") or "").lower() == "navigate":
        return redirect(reverse("mypet") + "?open_messages=1")
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    user = request.user
    base_qs = PetMessage.objects.filter(Q(sender=user) | Q(receiver=user)).exclude(animal__owner=user)
    if scope == "active":
        base_qs = base_qs.filter(created_at__gte=active_since)
    else:
        base_qs = base_qs.filter(created_at__lt=active_since, created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
    qs = (
        base_qs
        .values("animal_id")
        .annotate(last_at=Max("created_at"))
        .order_by("-last_at")
    )
    out = []
    for row in qs:
        animal_id = int(row["animal_id"])
        pet = AnimalListing.objects.filter(pk=animal_id).select_related("owner").first()
        if not pet:
            continue
        owner = pet.owner
        last_msg = (
            PetMessage.objects
            .filter(animal_id=animal_id)
            .filter(created_at__gte=active_since if scope == "active" else now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
            .filter(created_at__lt=active_since if scope == "archived" else now + timezone.timedelta(days=36500))
            .filter(Q(sender=user, receiver=owner) | Q(sender=owner, receiver=user))
            .order_by("-created_at")
            .first()
        )
        unread_qs = PetMessage.objects.filter(animal_id=animal_id, sender=owner, receiver=user, is_read=False)
        if scope == "active":
            unread_qs = unread_qs.filter(created_at__gte=active_since)
        else:
            unread_qs = unread_qs.filter(created_at__lt=active_since, created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS))
        unread = unread_qs.count()
        owner_name = (f"{owner.first_name} {owner.last_name}").strip() if owner else ""
        out.append({
            "animal_id": animal_id,
            "animal_name": getattr(pet, "name", "") or f"Pet #{animal_id}",
            "animal_photo_url": (pet.photo_1.url if getattr(pet, "photo_1", None) else ""),
            "animal_is_active": bool(getattr(pet, "is_published", False)),
            "animal_url": (reverse("pets_single", args=[animal_id]) if getattr(pet, "is_published", False) else ""),
            "owner_id": owner.id if owner else None,
            "owner_name": owner_name or (owner.username if owner else "Owner"),
            "last_message": (last_msg.body[:80] + "…") if (last_msg and len(last_msg.body) > 80) else (last_msg.body if last_msg else ""),
            "unread_count": unread,
            "last_at": row["last_at"].isoformat() if row.get("last_at") else "",
        })
    if out:
        aids = [int(o["animal_id"]) for o in out]
        owner_sub = AnimalListing.objects.filter(pk=OuterRef("animal_id")).values("owner_id")
        if scope == "active":
            q_time = Q(created_at__gte=active_since)
        else:
            q_time = Q(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        base_pm = (
            PetMessage.objects.filter(animal_id__in=aids, receiver=user)
            .filter(q_time)
            .annotate(_oid=Subquery(owner_sub[:1]))
            .filter(sender_id=F("_oid"))
        )
        ur_animal = {
            int(x["animal_id"]): x["t"]
            for x in base_pm.filter(is_read=False).values("animal_id").annotate(t=Max("created_at"))
        }
        ia_animal = {
            int(x["animal_id"]): x["t"]
            for x in base_pm.values("animal_id").annotate(t=Max("created_at"))
        }
        for o in out:
            aid = int(o["animal_id"])
            u = int(o.get("unread_count") or 0)
            if u > 0:
                o["_sort_ts"] = ur_animal.get(aid) or ia_animal.get(aid)
            else:
                o["_sort_ts"] = ia_animal.get(aid)

        def _adopter_list_sort_key(o):
            t = o.get("_sort_ts")
            return (0 if int(o.get("unread_count") or 0) > 0 else 1, -(t.timestamp() if t else 0))

        out.sort(key=_adopter_list_sort_key)
        for o in out:
            o.pop("_sort_ts", None)
    badges = _mypet_message_badge_payload(request.user)
    return JsonResponse({"ok": True, "threads": out, "scope": scope, **badges})


@login_required
def adopter_messages_thread_view(request, pk: int):
    """
    Thread adoptator <-> owner pentru un animal.
    Răspuns JSON pentru fetch din MyPet; la navigare în browser redirecționăm (evită pagină JSON brut).
    """
    if (request.headers.get("Sec-Fetch-Mode") or "").lower() == "navigate":
        pet = AnimalListing.objects.filter(pk=pk).first()
        if pet and getattr(pet, "is_published", False) and pet.owner_id != request.user.id:
            return redirect(reverse("pets_single", args=[pk]))
        return redirect(reverse("mypet") + "?open_messages=1")
    active_since = _messages_active_since()
    user = request.user
    pet = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    if pet.owner_id == user.id:
        return JsonResponse({"ok": False, "error": "Folosește inbox-ul owner."}, status=400)
    owner = pet.owner
    PetMessage.objects.filter(animal=pet, sender=owner, receiver=user, is_read=False, created_at__gte=active_since).update(is_read=True)
    qs = (
        PetMessage.objects
        .filter(animal=pet, created_at__gte=active_since)
        .filter(Q(sender=user, receiver=owner) | Q(sender=owner, receiver=user))
        .order_by("created_at")
    )
    items = []
    for msg in qs:
        items.append({
            "id": msg.id,
            "from_me": msg.sender_id == user.id,
            "from_owner": msg.sender_id == owner.id,
            "body": msg.body,
            "created_at": msg.created_at.isoformat(),
            "is_read": bool(msg.is_read),
        })
    unread_total = PetMessage.objects.filter(receiver=user, is_read=False, created_at__gte=active_since).count()
    badges = _mypet_message_badge_payload(user)
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "animal_name": pet.name or "",
            "unread_total": unread_total,
            **badges,
        }
    )


@login_required
@require_POST
@csrf_protect
def adopter_messages_reply_view(request, pk: int):
    """
    Reply adoptator către owner pentru un animal.
    """
    user = request.user
    pet = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    if pet.owner_id == user.id:
        return JsonResponse({"ok": False, "error": "Folosește inbox-ul owner."}, status=400)
    if not _adopter_messaging_allowed(pet, user):
        return JsonResponse(
            {
                "ok": False,
                "error": "Nu poți trimite mesaj în această situație (cont, anunț sau animal deja adoptat).",
            },
            status=403,
        )
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    PetMessage.objects.create(
        animal=pet,
        sender=user,
        receiver=pet.owner,
        body=text,
        is_read=False,
    )
    badges = _mypet_message_badge_payload(user)
    return JsonResponse({"ok": True, **badges})


def _collab_context_choice_keys():
    return {c[0] for c in CollabServiceMessage.CONTEXT_CHOICES}


def _normalize_collab_context_type(raw) -> str:
    s = (raw or "").strip().lower() or CollabServiceMessage.CONTEXT_GENERAL
    return s if s in _collab_context_choice_keys() else CollabServiceMessage.CONTEXT_GENERAL


def _collab_thread_peer_user_id(msg: CollabServiceMessage, collaborator_id: int) -> int:
    return msg.receiver_id if msg.sender_id == collaborator_id else msg.sender_id


def _collab_context_label(context_type: str) -> str:
    return dict(CollabServiceMessage.CONTEXT_CHOICES).get(context_type, context_type)


@login_required
def collab_inbox_list_view(request):
    """Lista thread-uri servicii/produse pentru colaborator (Magazinul meu)."""
    if not _user_can_use_magazinul_meu(request):
        return JsonResponse({"ok": False, "error": "Acces interzis."}, status=403)
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    user = request.user
    base = CollabServiceMessage.objects.filter(collaborator=user)
    if scope == "active":
        base = base.filter(created_at__gte=active_since)
    else:
        base = base.filter(
            created_at__lt=active_since,
            created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
        )
    threads_map = {}
    for m in base.order_by("-created_at"):
        peer = _collab_thread_peer_user_id(m, user.id)
        key = (peer, m.context_type, m.context_ref or "")
        if key not in threads_map:
            threads_map[key] = m
    UserModel = get_user_model()
    out = []
    for (client_id, ct, cref), last in threads_map.items():
        client = UserModel.objects.filter(pk=client_id).first()
        cname = ""
        if client:
            cname = (f"{client.first_name} {client.last_name}").strip() or client.username
        unread_qs = CollabServiceMessage.objects.filter(
            collaborator=user,
            context_type=ct,
            context_ref=cref,
            sender_id=client_id,
            receiver=user,
            is_read=False,
        )
        if scope == "active":
            unread_qs = unread_qs.filter(created_at__gte=active_since)
        else:
            unread_qs = unread_qs.filter(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        unread = unread_qs.count()
        last_unread_in = unread_qs.aggregate(t=Max("created_at")).get("t")
        any_in = CollabServiceMessage.objects.filter(
            collaborator=user,
            context_type=ct,
            context_ref=cref,
            sender_id=client_id,
            receiver=user,
        )
        if scope == "active":
            any_in = any_in.filter(created_at__gte=active_since)
        else:
            any_in = any_in.filter(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        last_in_any = any_in.aggregate(t=Max("created_at")).get("t")
        sort_ts = last_unread_in if unread > 0 else (last_in_any or last.created_at)
        preview = last.body or ""
        if len(preview) > 80:
            preview = preview[:80] + "…"
        out.append(
            {
                "client_id": client_id,
                "client_name": cname or f"User {client_id}",
                "context_type": ct,
                "context_ref": cref,
                "context_label": _collab_context_label(ct),
                "last_message": preview,
                "unread_count": unread,
                "last_at": last.created_at.isoformat() if last.created_at else "",
                "_sort_ts": sort_ts,
            }
        )
    out.sort(
        key=lambda x: (
            0 if int(x.get("unread_count") or 0) > 0 else 1,
            -((x["_sort_ts"].timestamp() if x.get("_sort_ts") else 0)),
        )
    )
    for x in out:
        x.pop("_sort_ts", None)
    return JsonResponse({"ok": True, "threads": out, "scope": scope})


@login_required
def collab_inbox_thread_view(request):
    """Thread colaborator ↔ client pentru un context."""
    if not _user_can_use_magazinul_meu(request):
        return JsonResponse({"ok": False, "error": "Acces interzis."}, status=403)
    try:
        client_id = int(request.GET.get("client_id") or 0)
    except ValueError:
        client_id = 0
    if not client_id:
        return JsonResponse({"ok": False, "error": "Lipsește client_id."}, status=400)
    ct = _normalize_collab_context_type(request.GET.get("context_type"))
    cref = (request.GET.get("context_ref") or "").strip()[:120]
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    collab = request.user
    base_filter = {
        "collaborator": collab,
        "context_type": ct,
        "context_ref": cref,
    }
    if scope == "active":
        time_q = Q(created_at__gte=active_since)
    else:
        time_q = Q(
            created_at__lt=active_since,
            created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
        )
    CollabServiceMessage.objects.filter(
        **base_filter,
        sender_id=client_id,
        receiver=collab,
        is_read=False,
    ).filter(time_q).update(is_read=True)
    qs = (
        CollabServiceMessage.objects.filter(**base_filter)
        .filter(Q(sender=collab, receiver_id=client_id) | Q(sender_id=client_id, receiver=collab))
        .filter(time_q)
        .order_by("created_at")
    )
    items = []
    for msg in qs:
        items.append(
            {
                "id": msg.id,
                "from_me": msg.sender_id == collab.id,
                "from_collaborator": msg.sender_id == collab.id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat(),
                "is_read": bool(msg.is_read),
            }
        )
    unread_total = CollabServiceMessage.objects.filter(
        receiver=collab,
        collaborator=collab,
        is_read=False,
        created_at__gte=active_since,
    ).count()
    nav_unread = get_navbar_unread_counts(collab)
    client_card = None
    cli = get_user_model().objects.filter(pk=client_id).first()
    if cli:
        client_card = _collab_peer_location_card(cli)
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "context_label": _collab_context_label(ct),
            "unread_total": unread_total,
            "navbar_unread_total": nav_unread["total"],
            "client_card": client_card,
        }
    )


@login_required
@require_POST
@csrf_protect
def collab_inbox_reply_view(request):
    """Răspuns colaborator către client."""
    if not _user_can_use_magazinul_meu(request):
        return JsonResponse({"ok": False, "error": "Acces interzis."}, status=403)
    try:
        client_id = int(request.POST.get("client_id") or 0)
    except ValueError:
        client_id = 0
    if not client_id:
        return JsonResponse({"ok": False, "error": "Lipsește client_id."}, status=400)
    ct = _normalize_collab_context_type(request.POST.get("context_type"))
    cref = (request.POST.get("context_ref") or "").strip()[:120]
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    if client_id == request.user.id:
        return JsonResponse({"ok": False, "error": "Destinatar invalid."}, status=400)
    CollabServiceMessage.objects.create(
        collaborator=request.user,
        context_type=ct,
        context_ref=cref,
        sender=request.user,
        receiver_id=client_id,
        body=text,
        is_read=False,
    )
    return JsonResponse({"ok": True})


@login_required
def collab_client_inbox_list_view(request):
    """Inbox client: conversații cu colaboratori (PF/ONG)."""
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    user = request.user
    base = CollabServiceMessage.objects.filter(Q(sender=user) | Q(receiver=user)).exclude(
        collaborator=user
    )
    if scope == "active":
        base = base.filter(created_at__gte=active_since)
    else:
        base = base.filter(
            created_at__lt=active_since,
            created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
        )
    threads_map = {}
    for m in base.order_by("-created_at"):
        cid = m.collaborator_id
        key = (cid, m.context_type, m.context_ref or "")
        if key not in threads_map:
            threads_map[key] = m
    UserModel = get_user_model()
    out = []
    for (collab_id, ct, cref), last in threads_map.items():
        collab_u = UserModel.objects.filter(pk=collab_id).first()
        cname = ""
        if collab_u:
            cname = (f"{collab_u.first_name} {collab_u.last_name}").strip() or collab_u.username
        unread_qs = CollabServiceMessage.objects.filter(
            collaborator_id=collab_id,
            context_type=ct,
            context_ref=cref,
            sender_id=collab_id,
            receiver=user,
            is_read=False,
        )
        if scope == "active":
            unread_qs = unread_qs.filter(created_at__gte=active_since)
        else:
            unread_qs = unread_qs.filter(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        unread = unread_qs.count()
        last_unread_in = unread_qs.aggregate(t=Max("created_at")).get("t")
        any_in = CollabServiceMessage.objects.filter(
            collaborator_id=collab_id,
            context_type=ct,
            context_ref=cref,
            sender_id=collab_id,
            receiver=user,
        )
        if scope == "active":
            any_in = any_in.filter(created_at__gte=active_since)
        else:
            any_in = any_in.filter(
                created_at__lt=active_since,
                created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
            )
        last_in_any = any_in.aggregate(t=Max("created_at")).get("t")
        sort_ts = last_unread_in if unread > 0 else (last_in_any or last.created_at)
        preview = last.body or ""
        if len(preview) > 80:
            preview = preview[:80] + "…"
        out.append(
            {
                "collaborator_id": collab_id,
                "collaborator_name": cname or f"Colaborator {collab_id}",
                "context_type": ct,
                "context_ref": cref,
                "context_label": _collab_context_label(ct),
                "last_message": preview,
                "unread_count": unread,
                "last_at": last.created_at.isoformat() if last.created_at else "",
                "_sort_ts": sort_ts,
            }
        )
    out.sort(
        key=lambda x: (
            0 if int(x.get("unread_count") or 0) > 0 else 1,
            -((x["_sort_ts"].timestamp() if x.get("_sort_ts") else 0)),
        )
    )
    for x in out:
        x.pop("_sort_ts", None)
    return JsonResponse({"ok": True, "threads": out, "scope": scope})


@login_required
def collab_client_thread_view(request):
    """Thread din perspectiva clientului."""
    try:
        collab_id = int(request.GET.get("collaborator_id") or 0)
    except ValueError:
        collab_id = 0
    if not collab_id:
        return JsonResponse({"ok": False, "error": "Lipsește collaborator_id."}, status=400)
    ct = _normalize_collab_context_type(request.GET.get("context_type"))
    cref = (request.GET.get("context_ref") or "").strip()[:120]
    scope = (request.GET.get("scope") or "active").strip().lower()
    if scope not in {"active", "archived"}:
        scope = "active"
    now = timezone.now()
    active_since = _messages_active_since()
    user = request.user
    collab = get_object_or_404(get_user_model(), pk=collab_id)
    if scope == "active":
        time_q = Q(created_at__gte=active_since)
    else:
        time_q = Q(
            created_at__lt=active_since,
            created_at__gte=now - timezone.timedelta(days=MESSAGE_DELETE_DAYS),
        )
    CollabServiceMessage.objects.filter(
        collaborator=collab,
        context_type=ct,
        context_ref=cref,
        sender=collab,
        receiver=user,
        is_read=False,
    ).filter(time_q).update(is_read=True)
    qs = (
        CollabServiceMessage.objects.filter(
            collaborator=collab,
            context_type=ct,
            context_ref=cref,
        )
        .filter(Q(sender=user, receiver=collab) | Q(sender=collab, receiver=user))
        .filter(time_q)
        .order_by("created_at")
    )
    items = []
    for msg in qs:
        items.append(
            {
                "id": msg.id,
                "from_me": msg.sender_id == user.id,
                "from_collaborator": msg.sender_id == collab.id,
                "body": msg.body,
                "created_at": msg.created_at.isoformat(),
                "is_read": bool(msg.is_read),
            }
        )
    collab_client_unread = (
        CollabServiceMessage.objects.filter(receiver=user, is_read=False, created_at__gte=active_since)
        .exclude(collaborator=user)
        .count()
    )
    nav_unread = get_navbar_unread_counts(user)
    partner_card = _partner_location_card_for_client(collab)
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "context_label": _collab_context_label(ct),
            "unread_total": collab_client_unread,
            "navbar_unread_total": nav_unread["total"],
            "partner_card": partner_card,
        }
    )


@login_required
@require_POST
@csrf_protect
def collab_client_reply_view(request):
    """Răspuns client către colaborator."""
    try:
        collab_id = int(request.POST.get("collaborator_id") or 0)
    except ValueError:
        collab_id = 0
    if not collab_id:
        return JsonResponse({"ok": False, "error": "Lipsește collaborator_id."}, status=400)
    collab = get_object_or_404(get_user_model(), pk=collab_id)
    ap = getattr(collab, "account_profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return JsonResponse({"ok": False, "error": "Destinatarul nu este colaborator."}, status=400)
    ct = _normalize_collab_context_type(request.POST.get("context_type"))
    cref = (request.POST.get("context_ref") or "").strip()[:120]
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    if request.user.id == collab_id:
        return JsonResponse({"ok": False, "error": "Nu poți trimite către tine."}, status=400)
    CollabServiceMessage.objects.create(
        collaborator=collab,
        context_type=ct,
        context_ref=cref,
        sender=request.user,
        receiver=collab,
        body=text,
        is_read=False,
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
@csrf_protect
def collab_contact_message_view(request):
    """Primul mesaj (sau continuare) de la client către colaborator."""
    try:
        collaborator_id = int(request.POST.get("collaborator_id") or 0)
    except ValueError:
        collaborator_id = 0
    if not collaborator_id:
        return JsonResponse({"ok": False, "error": "Lipsește collaborator_id."}, status=400)
    collab = get_object_or_404(get_user_model(), pk=collaborator_id)
    ap = getattr(collab, "account_profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return JsonResponse({"ok": False, "error": "Destinatarul nu este colaborator."}, status=400)
    if request.user.id == collaborator_id:
        return JsonResponse({"ok": False, "error": "Nu poți trimite către tine."}, status=400)
    ct = _normalize_collab_context_type(request.POST.get("context_type"))
    cref = (request.POST.get("context_ref") or "").strip()[:120]
    text = (request.POST.get("message") or "").strip()
    if not text:
        return JsonResponse({"ok": False, "error": "Mesajul este gol."}, status=400)
    if len(text) > 2000:
        text = text[:2000]
    CollabServiceMessage.objects.create(
        collaborator=collab,
        context_type=ct,
        context_ref=cref,
        sender=request.user,
        receiver=collab,
        body=text,
        is_read=False,
    )
    return JsonResponse({"ok": True})


@login_required
@require_POST
@csrf_protect
def pet_adoption_request_view(request, pk: int):
    """
    PF: cere adopția din fișă. Creează cerere + mesaj fără PII structurată
    (detaliile personale merg pe email doar după accept).
    """
    pet = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    _sync_animal_adoption_state(pet)
    if pet.adoption_state == AnimalListing.ADOPTION_STATE_ADOPTED:
        return JsonResponse({"ok": False, "error": "Acest animal este deja adoptat."}, status=400)
    if pet.owner_id == request.user.id:
        return JsonResponse({"ok": False, "error": "Nu poți solicita adopția propriului anunț."}, status=400)
    ap = getattr(request.user, "account_profile", None)
    if ap and not ap.can_adopt_animals:
        return JsonResponse(
            {"ok": False, "error": "Tipul de cont nu poate solicita adopții."},
            status=403,
        )

    last = (
        AdoptionRequest.objects.filter(animal=pet, adopter=request.user)
        .order_by("-created_at")
        .first()
    )
    if last:
        if last.status == AdoptionRequest.STATUS_PENDING:
            request.session[SESSION_ADOPTION_BONUS_AR] = last.pk
            return JsonResponse({"ok": True, "already": "pending", "adoption_request_id": last.pk})
        if last.status == AdoptionRequest.STATUS_ACCEPTED:
            request.session[SESSION_ADOPTION_BONUS_AR] = last.pk
            return JsonResponse({"ok": True, "already": "accepted", "adoption_request_id": last.pk})
        if last.status == AdoptionRequest.STATUS_FINALIZED:
            return JsonResponse({"ok": False, "error": "Adopția pentru acest animal este deja finalizată."}, status=400)

    body = (
        "Am trimis o cerere de adopție pentru acest animal prin EU-Adopt. "
        "Datele mele de contact îți vor fi disponibile după ce accepți cererea în MyPet → Mesaje."
    )
    has_active_accepted = AdoptionRequest.objects.filter(
        animal=pet,
        status=AdoptionRequest.STATUS_ACCEPTED,
    ).filter(Q(accepted_expires_at__isnull=True) | Q(accepted_expires_at__gte=timezone.now())).exists()

    with transaction.atomic():
        ar = AdoptionRequest.objects.create(
            animal=pet,
            adopter=request.user,
            status=AdoptionRequest.STATUS_PENDING,
        )
        PetMessage.objects.create(
            animal=pet,
            sender=request.user,
            receiver=pet.owner,
            body=body,
            is_read=False,
        )
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
    _inbox.create_inbox_notification(
        pet.owner,
        _inbox.KIND_ADOPTION_REQUEST_OWNER,
        "Cerere nouă de adopție",
        f"{request.user.get_full_name() or request.user.username} a trimis o cerere pentru „{pet_label}”.",
        link_url=reverse("mypet") + f"?open_messages=1&open_pet_messages={pet.pk}",
        metadata={"pet_id": pet.pk, "adoption_request_id": ar.pk},
    )
    _inbox.create_inbox_notification(
        request.user,
        _inbox.KIND_ADOPTION_REQUEST_ADOPTER,
        "Cererea ta de adopție a fost trimisă",
        f"Pentru „{pet_label}”. Vei fi anunțat când proprietarul răspunde.",
        link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={pet.pk}",
        metadata={"pet_id": pet.pk, "adoption_request_id": ar.pk},
    )
    _send_adoption_request_owner_email(ar)
    _send_adoption_request_adopter_email(ar)
    if has_active_accepted:
        _send_adoption_waiting_list_email(ar)
    _sync_animal_adoption_state(pet)
    request.session[SESSION_ADOPTION_BONUS_AR] = ar.pk
    return JsonResponse(
        {"ok": True, "queued": bool(has_active_accepted), "adoption_request_id": ar.pk},
    )


@login_required
@require_POST
@csrf_protect
def adoption_bonus_offer_toggle_view(request):
    """Inimioară ofertă Servicii legată de cerere adopție (max 1 / categorie)."""
    try:
        rid = int((request.POST.get("adoption_request_id") or "").strip())
        oid = int((request.POST.get("offer_id") or "").strip())
    except ValueError:
        return JsonResponse({"ok": False, "error": "Date invalide."}, status=400)
    ar = get_object_or_404(
        AdoptionRequest,
        pk=rid,
        adopter=request.user,
    )
    if getattr(ar, "bonus_servicii_locked_at", None):
        return JsonResponse(
            {"ok": False, "error": "Ofertele bonus au fost deja salvate și nu mai pot fi modificate."},
            status=403,
        )
    if ar.status not in (
        AdoptionRequest.STATUS_PENDING,
        AdoptionRequest.STATUS_ACCEPTED,
    ):
        return JsonResponse({"ok": False, "error": "Cererea nu permite selecții bonus."}, status=400)
    offer = get_object_or_404(CollaboratorServiceOffer, pk=oid, is_active=True)
    if not _collab_offer_is_valid_today(offer):
        return JsonResponse({"ok": False, "error": "Oferta nu este disponibilă."}, status=400)
    ad_cn = _norm_county_str(_adopter_profile_county_raw(request.user))
    if ad_cn and _offer_collab_county_norm(offer) != ad_cn:
        return JsonResponse({"ok": False, "error": "Oferta nu este în județul tău."}, status=403)

    existing = AdoptionBonusSelection.objects.filter(
        adoption_request=ar,
        partner_kind=offer.partner_kind,
    ).first()
    if existing and existing.offer_id == offer.pk:
        existing.delete()
        return JsonResponse({"ok": True, "selected": False, "partner_kind": offer.partner_kind})

    if existing:
        existing.offer = offer
        existing.save(update_fields=["offer", "updated_at"])
    else:
        AdoptionBonusSelection.objects.create(
            adoption_request=ar,
            offer=offer,
            partner_kind=offer.partner_kind,
        )
    return JsonResponse({"ok": True, "selected": True, "partner_kind": offer.partner_kind, "offer_id": offer.pk})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_adoption_accept_view(request, req_id: int):
    ad_req = get_object_or_404(
        AdoptionRequest,
        pk=req_id,
        animal__owner=request.user,
    )
    ok, msg, _ = _apply_owner_decision_for_request(ad_req, "accept")
    if not ok:
        return JsonResponse({"ok": False, "error": msg}, status=400)
    return JsonResponse({"ok": True, "message": msg})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_adoption_reject_view(request, req_id: int):
    ad_req = get_object_or_404(
        AdoptionRequest,
        pk=req_id,
        animal__owner=request.user,
    )
    ok, msg, _ = _apply_owner_decision_for_request(ad_req, "reject")
    if not ok:
        return JsonResponse({"ok": False, "error": msg}, status=400)
    return JsonResponse({"ok": True, "message": msg})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_adoption_finalize_view(request, req_id: int):
    ar = get_object_or_404(
        AdoptionRequest,
        pk=req_id,
        animal__owner=request.user,
        status=AdoptionRequest.STATUS_ACCEPTED,
    )
    pet = ar.animal
    fin_time = timezone.now()
    with transaction.atomic():
        ar.status = AdoptionRequest.STATUS_FINALIZED
        ar.finalized_at = fin_time
        ar.save(update_fields=["status", "finalized_at", "updated_at"])
        UserAdoption.objects.update_or_create(
            user=ar.adopter,
            animal_id=pet.pk,
            defaults={
                "animal_name": pet.name or f"Animal #{pet.pk}",
                "animal_type": pet.species or "dog",
                "source": "mypet_adoption_flow",
                "status": "completed",
            },
        )
        pet.adoption_state = AnimalListing.ADOPTION_STATE_ADOPTED
        pet.save(update_fields=["adoption_state", "updated_at"])
    _process_adoption_finalize_bonus(ar)
    pet_label_fin = (pet.name or f"Animal #{pet.pk}").strip()
    _inbox.create_inbox_notification(
        request.user,
        _inbox.KIND_ADOPTION_FINALIZED_OWNER,
        "Adopție finalizată",
        f"Ai marcat adopția ca finalizată pentru „{pet_label_fin}”.",
        link_url=reverse("mypet") + f"?open_messages=1&open_pet_messages={pet.pk}",
        metadata={"pet_id": pet.pk, "adoption_request_id": ar.pk},
    )
    _inbox.create_inbox_notification(
        ar.adopter,
        _inbox.KIND_ADOPTION_FINALIZED_ADOPTER,
        "Adopție finalizată",
        f"Adopția pentru „{pet_label_fin}” a fost finalizată. Îți mulțumim!",
        link_url=reverse("mypet") + f"?open_messages=1&open_adopter_animal={pet.pk}",
        metadata={"pet_id": pet.pk, "adoption_request_id": ar.pk},
    )
    return JsonResponse({"ok": True})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_adoption_extend_view(request, req_id: int):
    ar = get_object_or_404(
        AdoptionRequest,
        pk=req_id,
        animal__owner=request.user,
    )
    with transaction.atomic():
        locked_qs = AdoptionRequest.objects.select_for_update().filter(animal=ar.animal)
        ar = locked_qs.filter(pk=ar.pk).first()
        if not ar:
            return JsonResponse({"ok": False, "error": "Cererea nu mai există."}, status=404)
        if ar.status not in {AdoptionRequest.STATUS_ACCEPTED, AdoptionRequest.STATUS_EXPIRED}:
            return JsonResponse({"ok": False, "error": "Cererea nu poate fi prelungită în starea curentă."}, status=400)
        if ar.status == AdoptionRequest.STATUS_EXPIRED and not ar.accepted_at:
            return JsonResponse(
                {"ok": False, "error": "Prelungirea se aplică doar după ce o cerere a fost acceptată."},
                status=400,
            )
        if locked_qs.filter(status=AdoptionRequest.STATUS_ACCEPTED).exclude(pk=ar.pk).exists():
            return JsonResponse(
                {"ok": False, "error": "Există deja o altă adopție activă pentru acest animal."},
                status=400,
            )
        ext = int(getattr(ar, "extension_count", 0) or 0)
        if ext >= 2:
            return JsonResponse({"ok": False, "error": "S-a atins limita maximă de 2 prelungiri."}, status=400)
        ar.status = AdoptionRequest.STATUS_ACCEPTED
        ar.extension_count = ext + 1
        ar.accepted_at = timezone.now()
        ar.accepted_expires_at = timezone.now() + timezone.timedelta(days=7)
        ar.save(update_fields=["status", "extension_count", "accepted_at", "accepted_expires_at", "updated_at"])
    _sync_animal_adoption_state(ar.animal)
    return JsonResponse({"ok": True, "extension_count": ar.extension_count})


@login_required
@mypet_pf_org_required_json
@require_POST
@csrf_protect
def mypet_adoption_next_view(request, req_id: int):
    ar = get_object_or_404(
        AdoptionRequest,
        pk=req_id,
        animal__owner=request.user,
    )
    if ar.status not in {AdoptionRequest.STATUS_ACCEPTED, AdoptionRequest.STATUS_EXPIRED}:
        return JsonResponse({"ok": False, "error": "Poți trece la următorul doar dintr-o adopție activă/expirată."}, status=400)
    if ar.status == AdoptionRequest.STATUS_EXPIRED and not ar.accepted_at:
        return JsonResponse(
            {"ok": False, "error": "„Următorul” este disponibil după o cerere acceptată care a expirat, nu pentru cereri închise fără răspuns."},
            status=400,
        )
    pet = ar.animal
    with transaction.atomic():
        locked_qs = AdoptionRequest.objects.select_for_update().filter(animal=pet)
        ar = locked_qs.filter(pk=ar.pk).first()
        if not ar:
            return JsonResponse({"ok": False, "error": "Cererea nu mai există."}, status=404)
        if ar.status not in {AdoptionRequest.STATUS_ACCEPTED, AdoptionRequest.STATUS_EXPIRED}:
            return JsonResponse({"ok": False, "error": "Poți trece la următorul doar dintr-o adopție activă/expirată."}, status=400)
        if ar.status == AdoptionRequest.STATUS_EXPIRED and not ar.accepted_at:
            return JsonResponse(
                {"ok": False, "error": "„Următorul” este disponibil după o cerere acceptată care a expirat, nu pentru cereri închise fără răspuns."},
                status=400,
            )
        if ar.status == AdoptionRequest.STATUS_ACCEPTED:
            ar.status = AdoptionRequest.STATUS_EXPIRED
            ar.save(update_fields=["status", "updated_at"])
        if locked_qs.filter(status=AdoptionRequest.STATUS_ACCEPTED).exists():
            return JsonResponse(
                {"ok": False, "error": "Există deja o adopție activă pentru acest animal."},
                status=400,
            )
        nxt = locked_qs.filter(status=AdoptionRequest.STATUS_PENDING).order_by("created_at", "pk").first()
        if not nxt:
            _sync_animal_adoption_state(pet)
            return JsonResponse({"ok": False, "error": "Nu există un utilizator următor în lista de așteptare."}, status=400)
        nxt.status = AdoptionRequest.STATUS_ACCEPTED
        nxt.accepted_at = timezone.now()
        nxt.accepted_expires_at = timezone.now() + timezone.timedelta(days=7)
        nxt.save(update_fields=["status", "accepted_at", "accepted_expires_at", "updated_at"])
    _send_adoption_accept_emails(nxt)
    PetMessage.objects.create(
        animal=nxt.animal,
        sender=request.user,
        receiver=nxt.adopter,
        body=(
            "Ai fost selectat din lista de așteptare. Cererea ta de adopție este acum activă "
            "și datele de contact au fost trimise pe email."
        ),
        is_read=False,
    )
    _sync_animal_adoption_state(pet)
    return JsonResponse({"ok": True, "next_request_id": nxt.pk})


def _cabinet_contact_lines_for_email(user):
    """Text pentru email: date firmă din UserProfile + email user."""
    prof = getattr(user, "profile", None)
    lines = []
    if prof:
        if prof.company_display_name:
            lines.append(f"Denumire: {prof.company_display_name}")
        if user.email:
            lines.append(f"Email cabinet: {user.email}")
        if prof.phone:
            lines.append(f"Telefon: {prof.phone}")
        addr_bits = [prof.company_address, prof.company_oras, prof.company_judet]
        addr = ", ".join(x for x in addr_bits if x)
        if addr:
            lines.append(f"Adresă / localitate: {addr}")
        if prof.company_cui:
            cui = prof.company_cui
            if getattr(prof, "company_cui_has_ro", False):
                cui = "RO " + cui
            lines.append(f"CUI: {cui}")
    if not lines and user.email:
        lines.append(f"Email: {user.email}")
    return "\n".join(lines) if lines else "(completează date firmă în contul colaborator)"


_OFFER_CODE_ALPHABET = "ABCDEFGHJKLMNPQRSTUVWXYZ23456789"


def _generate_collab_offer_code() -> str:
    for _ in range(32):
        code = "".join(secrets.choice(_OFFER_CODE_ALPHABET) for _ in range(10))
        if not CollaboratorOfferClaim.objects.filter(code=code).exists():
            return code
    return secrets.token_hex(6).upper()


def _buyer_snapshot_for_offer_request(request, post_name: str, post_email: str) -> dict:
    """Nume, email, telefon, localitate pentru email colaborator (din cont dacă e logat)."""
    email = (post_email or "").strip()
    name = (post_name or "").strip()
    phone = ""
    locality = ""
    buyer_user = request.user if getattr(request.user, "is_authenticated", False) else None
    if buyer_user:
        email = (buyer_user.email or email or "").strip()
        fn = (buyer_user.first_name or "").strip()
        ln = (buyer_user.last_name or "").strip()
        name = (f"{fn} {ln}".strip() or buyer_user.get_full_name() or buyer_user.username or name).strip()
        prof = getattr(buyer_user, "profile", None)
        if prof:
            phone = (prof.phone or "").strip()
            loc_bits = [x for x in [prof.oras, prof.judet] if x and str(x).strip()]
            locality = ", ".join(loc_bits)
    return {
        "email": email,
        "name": name or "Utilizator",
        "phone": phone,
        "locality": locality,
        "user": buyer_user,
    }


def _user_is_public_offer_transport_blocked(user) -> bool:
    """
    Transportatorii nu pot solicita oferte din Servicii (flux dedicat /transport/).
    Aliniază cu _servicii_saloane_qs_exclude_transportatori (tip transport + profil operator).
    """
    if not getattr(user, "is_authenticated", False):
        return False
    prof = getattr(user, "profile", None)
    if prof and (prof.collaborator_type or "").strip().lower() == "transport":
        return True
    return TransportOperatorProfile.objects.filter(user_id=user.pk).exists()


def _user_can_request_public_collab_offer(user) -> bool:
    return (
        getattr(user, "is_authenticated", False)
        and not _user_is_public_offer_transport_blocked(user)
    )


def _google_maps_search_url_from_query(query: str) -> str:
    q = (query or "").strip()
    if not q:
        return ""
    return f"https://www.google.com/maps/search/?api=1&query={quote(q, safe='')}"


def _user_location_maps_query(user) -> str:
    """
    Șir pentru căutare Google Maps: firmă (ONG / colaborator) sau localitate PF.
    """
    prof = getattr(user, "profile", None)
    if not prof:
        return ""
    ap = getattr(user, "account_profile", None)
    role = getattr(ap, "role", None) if ap else None
    if role in (AccountProfile.ROLE_ORG, AccountProfile.ROLE_COLLAB):
        parts = []
        for bit in (prof.company_address, prof.company_oras, prof.company_judet):
            s = (bit or "").strip()
            if s:
                parts.append(s)
        if parts:
            blob = " ".join(parts).lower()
            if "românia" not in blob and "romania" not in blob:
                parts.append("România")
            return ", ".join(parts)
    parts = []
    for bit in (prof.oras, prof.judet):
        s = (bit or "").strip()
        if s:
            parts.append(s)
    if parts:
        parts.append("România")
        return ", ".join(parts)
    return ""


def _html_email_maps_cta_button(maps_url: str, label: str = "DU-MĂ LA LOCAȚIE") -> str:
    if not maps_url:
        return ""
    safe_href = escape(maps_url, quote=True)
    safe_label = escape(label)
    return (
        f'<p style="margin:18px 0 10px;">'
        f'<a href="{safe_href}" style="display:inline-block;padding:12px 20px;'
        "background:#1565c0;color:#fff;text-decoration:none;border-radius:10px;"
        f'font-weight:700;font-family:system-ui,sans-serif;">{safe_label}</a></p>'
    )


def _collab_peer_location_card(client_user) -> dict:
    """
    Date afișabile pentru colaborator: locație client (PF localitate / firmă ONG)
    + link Maps pentru navigare.
    """
    name = (f"{client_user.first_name} {client_user.last_name}").strip() or client_user.username
    prof = getattr(client_user, "profile", None)
    ap = getattr(client_user, "account_profile", None)
    role = getattr(ap, "role", None) if ap else None
    lines: list[str] = []
    if role == AccountProfile.ROLE_ORG and prof:
        if (prof.company_display_name or "").strip():
            lines.append(f"Firmă / ONG: {(prof.company_display_name or '').strip()}")
        if (prof.company_address or "").strip():
            lines.append(f"Adresă: {(prof.company_address or '').strip()}")
        loc = ", ".join(
            x
            for x in [(prof.company_oras or "").strip(), (prof.company_judet or "").strip()]
            if x
        )
        if loc:
            lines.append(f"Localitate: {loc}")
    elif prof:
        loc = ", ".join(x for x in [(prof.oras or "").strip(), (prof.judet or "").strip()] if x)
        if loc:
            lines.append(f"Localitate: {loc}")
    phone = (prof.phone or "").strip() if prof else ""
    if phone:
        lines.append(f"Telefon: {phone}")
    em = (client_user.email or "").strip()
    if em:
        lines.append(f"Email: {em}")
    q = _user_location_maps_query(client_user)
    maps_url = _google_maps_search_url_from_query(q) if q else ""
    share_text = q or "\n".join(lines)
    return {
        "client_name": name,
        "lines": lines,
        "maps_url": maps_url,
        "share_text": (share_text or name).strip(),
    }


def _partner_location_card_for_client(collaborator_user) -> dict:
    """
    Fișă locație partener (colaborator) pentru clientul PF/ONG care deschide conversația.
    """
    prof = getattr(collaborator_user, "profile", None)
    display = ""
    if prof and (prof.company_display_name or "").strip():
        display = (prof.company_display_name or "").strip()
    if not display:
        display = (
            f"{collaborator_user.first_name} {collaborator_user.last_name}".strip()
            or collaborator_user.username
        )
    lines: list[str] = []
    lines.append(f"Partener: {display}")
    if prof and (prof.company_address or "").strip():
        lines.append(f"Adresă: {(prof.company_address or '').strip()}")
    loc = ""
    if prof:
        loc = ", ".join(
            x
            for x in [(prof.company_oras or "").strip(), (prof.company_judet or "").strip()]
            if x
        )
    if loc:
        lines.append(f"Localitate: {loc}")
    phone = (prof.phone or "").strip() if prof else ""
    if phone:
        lines.append(f"Telefon: {phone}")
    em = (collaborator_user.email or "").strip()
    if em:
        lines.append(f"Email: {em}")
    q = _user_location_maps_query(collaborator_user)
    maps_url = _google_maps_search_url_from_query(q) if q else ""
    share_text = q or display
    return {
        "partner_name": display,
        "lines": lines,
        "maps_url": maps_url,
        "share_text": (share_text or display).strip(),
    }


def _cabinet_block_for_buyer_email(collab_user) -> str:
    """Text pentru cumpărător: cabinet, telefon, persoană contact, email, adresă firmă dacă există."""
    prof = getattr(collab_user, "profile", None)
    contact_person = (collab_user.get_full_name() or "").strip() or collab_user.username
    lines = []
    if prof and (prof.company_display_name or "").strip():
        lines.append(f"Cabinet / partener: {prof.company_display_name.strip()}")
    else:
        lines.append(f"Cabinet / partener: {contact_person}")
    if prof and (prof.phone or "").strip():
        lines.append(f"Telefon: {prof.phone.strip()}")
    if collab_user.email:
        lines.append(f"Email: {collab_user.email}")
    lines.append(f"Persoană de contact: {contact_person}")
    if prof:
        addr = (prof.company_address or "").strip()
        if addr:
            lines.append(f"Adresă: {addr}")
        loc_bits = [x for x in [(prof.company_oras or "").strip(), (prof.company_judet or "").strip()] if x]
        if loc_bits:
            lines.append(f"Localitate: {', '.join(loc_bits)}")
    return "\n".join(lines)


def _cabinet_maps_url_for_buyer_email(collab_user) -> str:
    return _google_maps_search_url_from_query(_user_location_maps_query(collab_user))


def _buyer_maps_url_for_collab_email(buyer: dict) -> str:
    """Link Maps pentru solicitant (email către colaborator)."""
    u = buyer.get("user")
    if u:
        return _google_maps_search_url_from_query(_user_location_maps_query(u))
    loc = (buyer.get("locality") or "").strip()
    return _google_maps_search_url_from_query(loc) if loc else ""


def _redirect_after_public_offer_request(request, pk: int):
    ref = (request.META.get("HTTP_REFERER") or "").lower()
    if "servicii" in ref:
        return redirect(reverse("servicii") + "#S3")
    return redirect(reverse("public_offer_detail", args=[pk]))


def _ro_today() -> date:
    """Dată calendaristică locală (setări Django; RO = același fus pe teritoriu)."""
    return timezone.localdate()


def _parse_post_date_iso(s: str):
    s = (s or "").strip()
    if not s:
        return None
    try:
        return datetime.strptime(s, "%Y-%m-%d").date()
    except ValueError:
        return None


def _normalize_external_url(raw: str) -> str:
    """
    Normalizează URL extern de produs:
    - gol => ""
    - fără schemă => prefixăm https://
    - validăm strict http/https
    """
    val = (raw or "").strip()
    if not val:
        return ""
    if "://" not in val:
        val = "https://" + val
    validator = URLValidator(schemes=["http", "https"])
    try:
        validator(val)
    except DjangoValidationError:
        raise ValueError("Linkul produsului trebuie să fie un URL valid (http:// sau https://).")
    return val


def _validate_collab_product_sheet(uploaded_file) -> str:
    """
    Validare simplă pentru fișa tehnică uploadată de colaborator.
    Returnează mesaj eroare gol dacă fișierul este valid.
    """
    if not uploaded_file:
        return ""
    fn = (getattr(uploaded_file, "name", "") or "").strip().lower()
    if not fn:
        return "Fișierul pentru fișa tehnică nu are nume valid."
    if not (fn.endswith(".pdf") or fn.endswith(".doc") or fn.endswith(".docx")):
        return "Fișa tehnică trebuie să fie PDF, DOC sau DOCX."
    # plafon pragmatic pentru upload public
    size = int(getattr(uploaded_file, "size", 0) or 0)
    if size > 10 * 1024 * 1024:
        return "Fișa tehnică este prea mare (maxim 10 MB)."
    return ""


def _parse_collab_species_checks(post) -> tuple[bool, bool, bool]:
    """
    Bife specii (câini/pisici/altele), minim una obligatorie.
    """
    dog = bool(post.get("species_dog"))
    cat = bool(post.get("species_cat"))
    other = bool(post.get("species_other"))
    return dog, cat, other


def _parse_collab_offer_target_filters(post) -> dict:
    """
    Câmpuri țintă din POST (specie, talie, sex, vârstă, sterilizare).
    Valorile invalide revin la „all” / default.
    """
    M = CollaboratorServiceOffer

    def pick(key: str, allowed: set, default: str) -> str:
        v = (post.get(key) or default).strip()
        return v if v in allowed else default

    return {
        "target_species": pick(
            "target_species",
            {c for c, _ in M.TARGET_SPECIES_CHOICES},
            M.TARGET_SPECIES_ALL,
        ),
        "target_size": pick(
            "target_size",
            {c for c, _ in M.TARGET_SIZE_CHOICES},
            M.TARGET_SIZE_ALL,
        ),
        "target_sex": pick(
            "target_sex",
            {c for c, _ in M.TARGET_SEX_CHOICES},
            M.TARGET_SEX_ALL,
        ),
        "target_age_band": pick(
            "target_age_band",
            {c for c, _ in M.TARGET_AGE_CHOICES},
            M.TARGET_AGE_ALL,
        ),
        "target_sterilized": pick(
            "target_sterilized",
            {c for c, _ in M.TARGET_STERIL_CHOICES},
            M.TARGET_STERIL_ALL,
        ),
    }


def _collab_offer_target_filters_for_tip(tip: str, post) -> dict:
    """
    Magazin: citește filtrele din POST.
    Cabinet / servicii: aceeași fișă de serviciu, fără potrivire produs — totul rămâne „oricare”.
    """
    M = CollaboratorServiceOffer
    if tip == M.PARTNER_KIND_MAGAZIN:
        return _parse_collab_offer_target_filters(post)
    return {
        "target_species": M.TARGET_SPECIES_ALL,
        "target_size": M.TARGET_SIZE_ALL,
        "target_sex": M.TARGET_SEX_ALL,
        "target_age_band": M.TARGET_AGE_ALL,
        "target_sterilized": M.TARGET_STERIL_ALL,
    }


def _collab_offer_valid_public_qs(base_qs):
    """Oferte în fereastra de date; NULL pe margini = fără limită (oferte vechi)."""
    today = _ro_today()
    return base_qs.filter(
        (Q(valid_from__isnull=True) | Q(valid_from__lte=today))
        & (Q(valid_until__isnull=True) | Q(valid_until__gte=today))
    )


def _collab_offer_is_valid_today(offer) -> bool:
    today = _ro_today()
    if offer.valid_from is not None and today < offer.valid_from:
        return False
    if offer.valid_until is not None and today > offer.valid_until:
        return False
    return True


def _client_ip_for_rate_limit(request) -> str:
    xff = (request.META.get("HTTP_X_FORWARDED_FOR") or "").strip()
    if xff:
        return xff.split(",")[0].strip() or "unknown"
    return (request.META.get("REMOTE_ADDR") or "").strip() or "unknown"


def _public_offer_request_rate_limited(request, pk: int) -> bool:
    """
    Limitează abuzul: max. 15 solicitări reușite / 10 min / IP / ofertă
    și max. 50 / oră / IP la nivel global (toate ofertele).
    """
    ip = _client_ip_for_rate_limit(request)
    per_offer = cache.get(f"collab_orl_po:{ip}:{pk}")
    if per_offer is not None and int(per_offer) >= 15:
        return True
    global_key = f"collab_orl_gl:{ip}"
    g = cache.get(global_key)
    if g is not None and int(g) >= 50:
        return True
    return False


def _public_offer_request_rate_limit_touch(request, pk: int) -> None:
    """Incrementează contoare după o solicitare înregistrată cu succes."""
    ip = _client_ip_for_rate_limit(request)
    po_key = f"collab_orl_po:{ip}:{pk}"
    gl_key = f"collab_orl_gl:{ip}"
    try:
        cache.incr(po_key)
    except ValueError:
        cache.add(po_key, 1, 600)
    try:
        cache.incr(gl_key)
    except ValueError:
        cache.add(gl_key, 1, 3600)


@login_required
@collab_magazin_required
@require_POST
def collab_offer_add_view(request):
    ap = getattr(request.user, "account_profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return redirect("home")
    tip = _collaborator_tip_partener(request)
    if tip == "transport":
        return redirect("transport_operator_panel")
    if tip not in ("cabinet", "servicii", "magazin"):
        messages.error(request, "Tip partener necunoscut.")
        return redirect("collab_offers_control")
    title = (request.POST.get("title") or "").strip()
    description = (request.POST.get("description") or "").strip()[:500]
    external_url_raw = (request.POST.get("external_url") or "").strip()[:500]
    external_url = ""
    price_hint = (request.POST.get("price_hint") or "").strip()[:80]
    discount_raw = (request.POST.get("discount_percent") or "").strip()
    discount_percent = None
    if discount_raw.isdigit():
        d = int(discount_raw)
        if 1 <= d <= 100:
            discount_percent = d
    qty_raw = (request.POST.get("quantity_available") or "").strip()
    quantity_available = None
    if qty_raw.isdigit():
        q = int(qty_raw)
        if 0 < q <= 999_999:
            quantity_available = q
    valid_from = _parse_post_date_iso(request.POST.get("valid_from"))
    valid_until = _parse_post_date_iso(request.POST.get("valid_until"))
    image = request.FILES.get("image")
    product_sheet_file = request.FILES.get("product_sheet")
    species_dog, species_cat, species_other = _parse_collab_species_checks(request.POST)
    errs = []
    if not title:
        errs.append(
            "Completează titlul produsului."
            if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN
            else "Completează titlul serviciului."
        )
    if not image:
        errs.append("Alege o imagine pentru ofertă.")
    if not quantity_available:
        errs.append("Introdu numărul de oferte valabile (minimum 1). Oferta iese din lista publică când se epuizează locurile.")
    if not valid_from:
        errs.append("Alege data de început a valabilității ofertei.")
    if not valid_until:
        errs.append("Alege data de sfârșit a valabilității ofertei.")
    if valid_from and valid_until and valid_until < valid_from:
        errs.append("Data de sfârșit trebuie să fie după sau egală cu data de început.")
    if not (species_dog or species_cat or species_other):
        errs.append("Selectează cel puțin o categorie specie: Câini, Pisici sau Altele.")
    if tip in (
        CollaboratorServiceOffer.PARTNER_KIND_CABINET,
        CollaboratorServiceOffer.PARTNER_KIND_SERVICII,
        CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN,
    ):
        if not price_hint:
            errs.append("Completează prețul (ex. 200 lei).")
        if discount_percent is None:
            errs.append("Introdu discountul (1–100%).")
    external_url = ""
    if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN:
        try:
            external_url = _normalize_external_url(external_url_raw)
        except ValueError as exc:
            errs.append(str(exc))
        if not external_url:
            errs.append("La tipul Magazin / Pet-shop, completează linkul produsului (site extern).")
        sheet_err = _validate_collab_product_sheet(product_sheet_file)
        if sheet_err:
            errs.append(sheet_err)
    if errs:
        for e in errs:
            messages.error(request, e)
        return redirect("collab_offer_new")
    tf = _collab_offer_target_filters_for_tip(tip, request.POST)
    CollaboratorServiceOffer.objects.create(
        collaborator=request.user,
        partner_kind=tip,
        title=title,
        description=description,
        external_url=external_url,
        price_hint=price_hint,
        discount_percent=discount_percent,
        quantity_available=quantity_available,
        valid_from=valid_from,
        valid_until=valid_until,
        image=image,
        product_sheet=product_sheet_file if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN else None,
        species_dog=species_dog,
        species_cat=species_cat,
        species_other=species_other,
        **tf,
    )
    messages.success(request, "Oferta a fost publicată (pagina Oferte parteneri).")
    return redirect("collab_offers_control")


@login_required
@collab_magazin_required
@require_POST
def collab_offer_toggle_active_view(request, pk: int):
    tip = _collaborator_tip_partener(request)
    if tip == "transport":
        return redirect("transport_operator_panel")
    offer = get_object_or_404(
        CollaboratorServiceOffer, pk=pk, collaborator=request.user, partner_kind=tip
    )
    offer.is_active = not offer.is_active
    offer.save(update_fields=["is_active"])
    if offer.is_active:
        messages.success(request, "Oferta este activă (apare în listări publice).")
    else:
        messages.success(request, "Oferta a fost dezactivată.")
    return redirect("collab_offers_control")


@login_required
@collab_magazin_required
@require_POST
def collab_offer_delete_view(request, pk: int):
    tip = _collaborator_tip_partener(request)
    if tip == "transport":
        return redirect("transport_operator_panel")
    offer = get_object_or_404(
        CollaboratorServiceOffer, pk=pk, collaborator=request.user, partner_kind=tip
    )
    offer.delete()
    messages.success(request, "Oferta a fost ștearsă.")
    return redirect("collab_offers_control")


def _user_can_use_publicitate(request) -> bool:
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return True
    try:
        ap = getattr(user, "account_profile", None)
        return bool(ap and ap.role == AccountProfile.ROLE_COLLAB)
    except Exception:
        return False


# Catalog tarife publicitate (sursă unică: coș, validare comandă, viitor gateway plată).
PUBLICITATE_SLOT_MAP = {
    "home": [
        {"code": "A5.1", "title": "Home – coloană stânga A5.1", "types": ["image", "link", "video"], "unit": "luna", "price": 120},
        {"code": "A5.2", "title": "Home – coloană stânga A5.2", "types": ["image", "link", "video"], "unit": "luna", "price": 120},
        {"code": "A5.3", "title": "Home – coloană stânga A5.3", "types": ["image", "link", "video"], "unit": "luna", "price": 120},
        {"code": "A6.1", "title": "Home – coloană dreapta A6.1", "types": ["image", "link", "video"], "unit": "luna", "price": 110},
        {"code": "A6.2", "title": "Home – coloană dreapta A6.2", "types": ["image", "link", "video"], "unit": "luna", "price": 110},
        {"code": "A6.3", "title": "Home – coloană dreapta A6.3", "types": ["image", "link", "video"], "unit": "luna", "price": 110},
        {
            "code": "Burtieră",
            "title": "Home – bandă galbenă (burtieră)",
            "types": ["text", "link", "video"],
            "unit": "luna",
            "price": 150,
        },
    ],
    "pt": [
        {"code": "P4.3", "title": "PT P4.3", "types": ["image", "link", "video"], "unit": "luna", "price": 100},
        {"code": "P5.1", "title": "PT P5.1", "types": ["image", "link", "video"], "unit": "luna", "price": 95},
        {"code": "P5.2", "title": "PT P5.2", "types": ["image", "link", "video"], "unit": "luna", "price": 95},
        {"code": "P5.3", "title": "PT P5.3", "types": ["image", "link", "video"], "unit": "luna", "price": 95},
    ],
    "servicii": [
        {"code": "S2.2", "title": "Servicii S2.2", "types": ["image", "link", "video"], "unit": "luna", "price": 130},
        {"code": "S2.3", "title": "Servicii S2.3", "types": ["image", "link", "video"], "unit": "luna", "price": 130},
        {"code": "S6.1", "title": "Servicii S6.1", "types": ["image", "link", "video"], "unit": "luna", "price": 115},
        {"code": "S6.2", "title": "Servicii S6.2", "types": ["image", "link", "video"], "unit": "luna", "price": 115},
    ],
    "transport": [
        {"code": "TDR.1", "title": "Transport R1", "types": ["image", "link", "video"], "unit": "ora", "price": 4},
        {"code": "TDR.2", "title": "Transport R2", "types": ["image", "link", "video"], "unit": "ora", "price": 4},
        {"code": "TDR.3", "title": "Transport R3", "types": ["image", "link", "video"], "unit": "ora", "price": 4},
    ],
    "shop": [
        {"code": "SH4.1", "title": "Shop SH4.1", "types": ["image", "link", "video"], "unit": "luna", "price": 140},
        {"code": "SH4.2", "title": "Shop SH4.2", "types": ["image", "link", "video"], "unit": "luna", "price": 140},
        {"code": "SH4.3", "title": "Shop SH4.3", "types": ["image", "link", "video"], "unit": "luna", "price": 140},
        {"code": "SH5.1", "title": "Shop SH5.1", "types": ["image", "link", "video"], "unit": "luna", "price": 125},
        {"code": "SH5.2", "title": "Shop SH5.2", "types": ["image", "link", "video"], "unit": "luna", "price": 125},
        {"code": "SH5.3", "title": "Shop SH5.3", "types": ["image", "link", "video"], "unit": "luna", "price": 125},
    ],
    "mypet": [
        {"code": "MP.L1", "title": "MyPet L1", "types": ["image", "link", "video"], "unit": "luna", "price": 90},
        {"code": "MP.L2", "title": "MyPet L2", "types": ["image", "link", "video"], "unit": "luna", "price": 90},
        {"code": "MP.L3", "title": "MyPet L3", "types": ["image", "link", "video"], "unit": "luna", "price": 90},
    ],
    "i_love": [
        {"code": "IL.L1", "title": "I Love L1", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "IL.L2", "title": "I Love L2", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "IL.R1", "title": "I Love R1", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "IL.R2", "title": "I Love R2", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
    ],
    # Hartă tip I Love, sloturi independente (CC*) pentru fluxul „Coș pub.”
    "cos_pub": [
        {"code": "CC1", "title": "Coș pub. CC1", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "CC2", "title": "Coș pub. CC2", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "CC3", "title": "Coș pub. CC3", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
        {"code": "CC4", "title": "Coș pub. CC4", "types": ["image", "link", "video"], "unit": "luna", "price": 85},
    ],
}


def _publicitate_register_strip_band_catalog():
    """Adaugă P1.1–P1.36, P3.1–P3.36, S1.1–S1.36, S7.1–S7.36 în catalog (idempotent)."""
    pt_rows = PUBLICITATE_SLOT_MAP.get("pt") or []
    if any((r.get("code") == "P1.1") for r in pt_rows):
        return
    strip_price_pt = 48
    strip_price_sw = 48
    for band, title in (("P1", "PT bandă P1"), ("P3", "PT bandă P3")):
        for n in range(1, 37):
            PUBLICITATE_SLOT_MAP["pt"].append(
                {
                    "code": f"{band}.{n}",
                    "title": f"{title} – celulă {n}",
                    "types": ["image", "link", "video"],
                    "unit": "luna",
                    "price": strip_price_pt,
                }
            )
    for band, title in (("S1", "Servicii bandă S1"), ("S7", "Servicii bandă S7")):
        for n in range(1, 37):
            PUBLICITATE_SLOT_MAP["servicii"].append(
                {
                    "code": f"{band}.{n}",
                    "title": f"{title} – celulă {n}",
                    "types": ["image", "link", "video"],
                    "unit": "luna",
                    "price": strip_price_sw,
                }
            )


_publicitate_register_strip_band_catalog()

# Burtieră HOME: un singur text/link per linie de coș; două conținuri = două linii (două achiziții).
PUBLICITATE_BURTIERA_NOTE_MAXLEN = 100

# Taburi navigare hartă publicitate (+ pagina Coș dedicată); `code` = query `sect=` pe hartă.
PUBLICITATE_NAV_SECTIONS = [
    {"code": "home", "label": "Home"},
    {"code": "pt", "label": "PT"},
    {"code": "servicii", "label": "Servicii"},
    {"code": "transport", "label": "Transport"},
    {"code": "shop", "label": "Shop"},
    {"code": "mypet", "label": "MyPet"},
    # Nu e pagina /i-love/ (inimioare); e doar secțiunea de hartă pentru spații pe layout-ul „I Love”.
    {"code": "i_love", "label": "Spații I Love"},
    {"code": "cos_pub", "label": "Coș pub."},
]

PUBLICITATE_SESSION_CHECKOUT_ORDER = "pub_checkout_order_id"
PUBLICITATE_SESSION_LAST_PAID = "pub_last_paid_order_id"


def _publicitate_catalog_row(section: str, code: str):
    for row in PUBLICITATE_SLOT_MAP.get(section) or []:
        if row.get("code") == code:
            return row
    return None


def _buyer_note_to_pt_slot_json(buyer_note: str) -> str:
    """Produce JSON salvat în ReclamaSlotNote.text pentru sloturi PT (acceptat de _pt_pub_slot_parse_note)."""
    note = (buyer_note or "").strip()
    if not note:
        return json.dumps(
            {
                "img": "images/parteneri/placeholder.jpg",
                "link": "",
                "alt": "Comandă plătită – completați creative în admin sau comandați cu JSON în notă.",
            },
            ensure_ascii=False,
        )
    try:
        data = json.loads(note)
        if isinstance(data, dict):
            img_v = (data.get("img") or "").strip()
            video_v = (data.get("video") or "").strip()
            if img_v or video_v:
                return json.dumps(data, ensure_ascii=False)
    except json.JSONDecodeError:
        pass
    if note.startswith(("http://", "https://")):
        try:
            URLValidator()(note)
            return json.dumps({"img": note, "link": note, "alt": ""}, ensure_ascii=False)
        except DjangoValidationError:
            pass
    return json.dumps(
        {
            "img": "images/parteneri/placeholder.jpg",
            "link": "",
            "alt": note[:240],
        },
        ensure_ascii=False,
    )


def _apply_publicitate_line_to_site(line: PublicitateOrderLine, order: PublicitateOrder):
    """După plată demo: aplică pe site unde există integrare (PT + benzi PT/Servicii + burtieră HOME)."""
    note = (line.buyer_note or "").strip()
    if line.section == PT_PUB_NOTE_SECTION and (
        line.slot_code in PT_PUB_SLOT_CODES or line.slot_code in PT_STRIP_RENT_SLOT_CODES
    ):
        body = _buyer_note_to_pt_slot_json(note)
        ReclamaSlotNote.objects.update_or_create(
            section=PT_PUB_NOTE_SECTION,
            slot_code=line.slot_code,
            defaults={"text": body, "updated_by": order.user},
        )
        return
    if line.section == SERVICII_PUB_NOTE_SECTION and line.slot_code in SERVICII_STRIP_RENT_SLOT_CODES:
        body = _buyer_note_to_pt_slot_json(note)
        ReclamaSlotNote.objects.update_or_create(
            section=SERVICII_PUB_NOTE_SECTION,
            slot_code=line.slot_code,
            defaults={"text": body, "updated_by": order.user},
        )
        return
    if line.section == "home" and line.slot_code in HOME_SIDEBAR_SLOT_CODES:
        body = _buyer_note_to_pt_slot_json(note)
        ReclamaSlotNote.objects.update_or_create(
            section="home",
            slot_code=line.slot_code,
            defaults={"text": body, "updated_by": order.user},
        )
        return
    if line.section == "home" and line.slot_code == "Burtieră" and note:
        ReclamaSlotNote.objects.update_or_create(
            section="home",
            slot_code="Burtieră",
            defaults={"text": note[:8000], "updated_by": order.user},
        )


def _apply_publicitate_paid_order(order: PublicitateOrder):
    for line in order.lines.all():
        _publicitate_ensure_line_schedule_and_code(order, line)
        if line.activated_at:
            _apply_publicitate_line_to_site(line, order)


def _publicitate_duration_td(unit_label: str, quantity: int) -> timezone.timedelta:
    q = max(1, int(quantity or 1))
    ul = (unit_label or "").strip().lower()
    if "ora" in ul:
        return timezone.timedelta(hours=q)
    if "zi" in ul:
        return timezone.timedelta(days=q)
    return timezone.timedelta(days=30 * q)


def _publicitate_first_available_start(
    section: str, slot_code: str, desired_start: datetime, duration: timezone.timedelta
) -> tuple[datetime, bool]:
    """
    Returnează primul start disponibil pentru slot.
    Dacă perioada dorită e liberă, păstrează desired_start.
    Dacă este overlap, mută start-ul după primul capăt ocupat relevant.
    """
    start = desired_start
    moved = False
    # max 180 iterații de siguranță (evită loop accidental în date corupte)
    for _ in range(180):
        end = start + duration
        conflict = (
            PublicitateOrderLine.objects.filter(
                order__status=PublicitateOrder.STATUS_PAID,
                section=section,
                slot_code=slot_code,
                starts_at__isnull=False,
                ends_at__isnull=False,
                starts_at__lt=end,
                ends_at__gt=start,
            )
            .order_by("ends_at")
            .first()
        )
        if not conflict:
            return start, moved
        moved = True
        start = conflict.ends_at
    return start, moved


def _publicitate_build_validation_code(order: PublicitateOrder, line: PublicitateOrderLine) -> str:
    """Cod scurt pe linie, stabil și verificabil pentru reactivare manuală."""
    raw = f"PUB:{order.pk}:{line.pk}:{line.section}:{line.slot_code}"
    digest = hashlib.sha1(raw.encode("utf-8")).hexdigest()[:10].upper()
    return f"PV-{digest}"


def _publicitate_ensure_line_schedule_and_code(order: PublicitateOrder, line: PublicitateOrderLine) -> None:
    if line.starts_at and line.ends_at and line.validation_code:
        return
    base_start = order.paid_at or timezone.now()
    duration = _publicitate_duration_td(line.unit_label, line.quantity)
    starts_at = line.starts_at or base_start
    ends_at = line.ends_at or (starts_at + duration)
    validation_code = line.validation_code or _publicitate_build_validation_code(order, line)
    line.starts_at = starts_at
    line.ends_at = ends_at
    line.validation_code = validation_code
    line.save(update_fields=["starts_at", "ends_at", "validation_code"])


def _publicitate_harta_context(request, pub_nav: str) -> dict:
    """Context comun pentru harta `/publicitate/` și fluxul complet `/publicitate/cos/` (același șablon, 3 coloane)."""
    sections = PUBLICITATE_NAV_SECTIONS
    valid_codes = {s["code"] for s in sections}
    raw_sect = (request.GET.get("sect") or "").strip().lower()
    if raw_sect in valid_codes:
        selected_section = raw_sect
    elif pub_nav == "cos" and not raw_sect:
        selected_section = "cos_pub"
    else:
        selected_section = "home"
    my_pub_orders_total = 0
    my_pub_orders_pending_materials = 0
    if getattr(request.user, "is_authenticated", False) and _user_can_use_publicitate(request):
        paid_qs = PublicitateOrder.objects.filter(
            user=request.user, status=PublicitateOrder.STATUS_PAID
        ).order_by("-pk")[:120]
        my_pub_orders_total = paid_qs.count()
        for o in paid_qs:
            if not PublicitateOrderCreativeAccess.objects.filter(order=o).exists():
                continue
            if PublicitateLineCreative.objects.filter(
                line__order=o,
                status=PublicitateLineCreative.STATUS_PENDING,
            ).exists():
                my_pub_orders_pending_materials += 1

    return {
        "pub_sections": sections,
        "pub_nav": pub_nav,
        "pub_selected_section": selected_section,
        "pub_slot_map": PUBLICITATE_SLOT_MAP,
        "pub_a2_images": [d.get("imagine_fallback") for d in DEMO_DOGS if d.get("imagine_fallback")][:12],
        "pub_a13_images": list(HERO_SLIDER_IMAGES or []),
        "reclama_burtiera_display_text": _get_home_burtiera_text(),
        "reclama_burtiera_speed_seconds": _get_home_burtiera_speed_seconds(),
        "pub_site_contact_email": (
            (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or "euadopt@gmail.com"
        ),
        "pub_strip_p1_cells": _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P1),
        "pub_strip_p3_cells": _enrich_pub_strip_sequence("pt", PUB_STRIP_SEQ_P3),
        "pub_strip_s1_cells": _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S1),
        "pub_strip_s7_cells": _enrich_pub_strip_sequence("servicii", PUB_STRIP_SEQ_S7),
        "pub_my_orders_url": reverse("publicitate_my_orders"),
        "pub_my_orders_total": my_pub_orders_total,
        "pub_my_orders_pending_materials": my_pub_orders_pending_materials,
    }


@login_required
def publicitate_harta_view(request):
    if not _user_can_use_publicitate(request):
        messages.info(
            request,
            "Pagina Publicitate este pentru conturi colaborator (admin are acces pentru operare rapidă).",
        )
        return redirect("home")
    return render(request, "anunturi/publicitate_harta.html", _publicitate_harta_context(request, "harta"))


@login_required
def publicitate_cos_view(request):
    """Aceeași interfață ca harta (Detalii slot | Hartă | Coș), pentru achiziție pe pagina dedicată coșului."""
    if not _user_can_use_publicitate(request):
        messages.info(
            request,
            "Pagina Publicitate este pentru conturi colaborator (admin are acces pentru operare rapidă).",
        )
        return redirect("home")
    return render(request, "anunturi/publicitate_harta.html", _publicitate_harta_context(request, "cos"))


@login_required
def publicitate_my_orders_view(request):
    """Model agendă publicitate: tab-uri + tabel + reactivare pe cod validare."""
    if not _user_can_use_publicitate(request):
        messages.info(
            request,
            "Pagina Publicitate este pentru conturi colaborator (admin are acces pentru operare rapidă).",
        )
        return redirect("home")

    tab = (request.GET.get("tab") or "de_incarcat").strip().lower()
    if tab not in {"de_incarcat", "active", "trecute"}:
        tab = "de_incarcat"

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip().lower()
        if action == "reactivate":
            line_id_raw = (request.POST.get("line_id") or "").strip()
            code = (request.POST.get("validation_code") or "").strip().upper()
            try:
                line_id = int(line_id_raw)
            except (TypeError, ValueError):
                line_id = 0
            line = (
                PublicitateOrderLine.objects.select_related("order")
                .filter(pk=line_id, order__user=request.user, order__status=PublicitateOrder.STATUS_PAID)
                .first()
            )
            if not line:
                messages.error(request, "Linia selectată nu a fost găsită.")
            else:
                _publicitate_ensure_line_schedule_and_code(line.order, line)
                target = (
                    PublicitateOrderLine.objects.select_related("order")
                    .filter(
                        order__user=request.user,
                        order__status=PublicitateOrder.STATUS_PAID,
                        validation_code=code,
                        section=line.section,
                        slot_code=line.slot_code,
                    )
                    .first()
                )
                if not target:
                    messages.error(
                        request,
                        "Cod invalid pentru această casetă. Cumpără o perioadă liberă și folosește codul primit după plată.",
                    )
                else:
                    _publicitate_ensure_line_schedule_and_code(target.order, target)
                    now = timezone.now()
                    if target.activated_at:
                        messages.info(request, "Codul introdus a fost deja folosit pentru activare.")
                    elif not (target.starts_at and target.ends_at and target.starts_at <= now <= target.ends_at):
                        messages.error(
                            request,
                            "Codul există, dar perioada plătită nu este activă acum. Alege o perioadă disponibilă și activă.",
                        )
                    else:
                        if (line.buyer_note or "").strip():
                            target.buyer_note = line.buyer_note[:8000]
                        target.activated_at = now
                        target.reactivation_count = int(target.reactivation_count or 0) + 1
                        target.save(update_fields=["buyer_note", "activated_at", "reactivation_count"])
                        _apply_publicitate_line_to_site(target, target.order)
                        messages.success(
                            request,
                            (
                                f"Reclama a fost activată în slotul plătit {target.section.upper()}/{target.slot_code} "
                                f"pentru perioada {target.starts_at.strftime('%Y-%m-%d')} – {target.ends_at.strftime('%Y-%m-%d')}."
                            ),
                        )
            return redirect(f"{reverse('publicitate_my_orders')}?tab=trecute")

    now = timezone.now()
    orders = (
        PublicitateOrder.objects.filter(user=request.user, status=PublicitateOrder.STATUS_PAID)
        .prefetch_related("lines__creative_bundle")
        .order_by("-pk")[:120]
    )
    rows = []
    for order in orders:
        access = PublicitateOrderCreativeAccess.objects.filter(order=order).first()
        for line in order.lines.all():
            _publicitate_ensure_line_schedule_and_code(order, line)
            b = getattr(line, "creative_bundle", None)
            material_status = "live" if (b and b.status == PublicitateLineCreative.STATUS_LIVE) else "pending"
            has_materials = material_status == "live"
            is_active = bool(line.starts_at and line.ends_at and line.starts_at <= now <= line.ends_at)
            is_past = bool(line.ends_at and line.ends_at < now)
            is_pending_upload = not has_materials
            if is_pending_upload:
                bucket = "de_incarcat"
            elif is_active:
                bucket = "active"
            elif is_past:
                bucket = "trecute"
            else:
                bucket = "active"
            rows.append(
                {
                    "bucket": bucket,
                    "order": order,
                    "line": line,
                    "materials_url": reverse("publicitate_creative_order", kwargs={"order_id": order.pk}),
                    "material_status": material_status,
                    "material_status_label": ("Încărcat" if has_materials else "Neîncărcat"),
                    "period_status_label": ("Activă" if is_active else ("Trecută" if is_past else "Planificată")),
                    "activation_status_label": ("Activată" if line.activated_at else "Neactivată"),
                    "access_expires_at": (access.expires_at if access else None),
                }
            )

    ctx = {
        "pub_tab": tab,
        "pub_rows_current": [r for r in rows if r["bucket"] == tab],
        "pub_count_de_incarcat": sum(1 for r in rows if r["bucket"] == "de_incarcat"),
        "pub_count_active": sum(1 for r in rows if r["bucket"] == "active"),
        "pub_count_trecute": sum(1 for r in rows if r["bucket"] == "trecute"),
    }
    return render(request, "anunturi/publicitate_my_orders.html", ctx)


def _publicitate_parse_cart_lines(lines_in):
    """
    Validează linii coș publicitate (același reguli ca la checkout).
    Returnează (validated, total_lei, adjustments, None) sau (None, None, None, JsonResponse).
    """
    if not isinstance(lines_in, list) or not lines_in:
        return None, None, None, JsonResponse({"ok": False, "error": "Coșul este gol."}, status=400)
    validated = []
    total = Decimal("0.00")
    adjustments = []
    now = timezone.now()
    for raw in lines_in:
        if not isinstance(raw, dict):
            return None, None, None, JsonResponse({"ok": False, "error": "Linie invalidă."}, status=400)
        section = (raw.get("section") or "").strip().lower()
        code = (raw.get("code") or "").strip()
        cat = _publicitate_catalog_row(section, code)
        if not cat:
            return None, None, None, JsonResponse(
                {"ok": False, "error": f"Slot necunoscut: {section}/{code}"}, status=400
            )
        try:
            unit_price = Decimal(str(raw.get("unit_price")))
        except Exception:
            return None, None, None, JsonResponse({"ok": False, "error": "Preț invalid."}, status=400)
        catalog_price = Decimal(str(cat["price"]))
        if unit_price != catalog_price:
            return None, None, None, JsonResponse(
                {"ok": False, "error": "Prețul nu corespunde catalogului. Reîncarcă pagina."}, status=400
            )
        qty_raw = raw.get("qty", 1)
        try:
            qty = int(qty_raw)
        except (TypeError, ValueError):
            qty = 0
        if qty < 1 or qty > 12:
            return None, None, None, JsonResponse({"ok": False, "error": "Perioada trebuie să fie 1–12."}, status=400)
        unit_label = (raw.get("unit") or cat.get("unit") or "luna").strip()[:32]
        if unit_label != (cat.get("unit") or ""):
            unit_label = cat.get("unit") or "luna"
        raw_start = (raw.get("start_date") or "").strip()
        desired_start = now
        if raw_start:
            try:
                d = datetime.strptime(raw_start, "%Y-%m-%d").date()
                desired_start = timezone.make_aware(datetime.combine(d, datetime.min.time()))
            except Exception:
                desired_start = now
        if desired_start < now:
            desired_start = now
        duration = _publicitate_duration_td(unit_label, qty)
        starts_at, moved = _publicitate_first_available_start(section, code, desired_start, duration)
        ends_at = starts_at + duration
        if moved:
            adjustments.append(
                {
                    "section": section,
                    "code": code,
                    "from": desired_start.strftime("%Y-%m-%d"),
                    "to": starts_at.strftime("%Y-%m-%d"),
                }
            )
        line_total = (catalog_price * qty).quantize(Decimal("0.01"))
        total += line_total
        note = (raw.get("note") or "").strip()
        if section == "home" and code == "Burtieră":
            if not note:
                return None, None, None, JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            "Burtieră: completați nota (link sau mesaj scurt) înainte de comandă. "
                            f"Maximum {PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere; două conținuri = două linii în coș."
                        ),
                    },
                    status=400,
                )
            if len(note) > PUBLICITATE_BURTIERA_NOTE_MAXLEN:
                return None, None, None, JsonResponse(
                    {
                        "ok": False,
                        "error": (
                            f"Burtieră: nota are maximum {PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere. "
                            "Pentru două texte sau două linkuri diferite, adăugați două poziții în coș (două linii separate)."
                        ),
                    },
                    status=400,
                )
        else:
            note = note[:8000]
        validated.append(
            {
                "section": section,
                "slot_code": code,
                "title_snapshot": (cat.get("title") or code)[:220],
                "unit_label": unit_label,
                "unit_price_lei": catalog_price,
                "quantity": qty,
                "line_total_lei": line_total,
                "buyer_note": note,
                "starts_at": starts_at,
                "ends_at": ends_at,
            }
        )
    return validated, total.quantize(Decimal("0.01")), adjustments, None


@login_required
@require_POST
def publicitate_checkout_create_view(request):
    """Primește coșul JSON, validează tarifele pe server, creează comanda `pending_payment`."""
    if not _user_can_use_publicitate(request):
        return JsonResponse({"ok": False, "error": "Acces nepermis."}, status=403)
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON invalid."}, status=400)
    lines_in = body.get("lines")
    validated, total, adjustments, err = _publicitate_parse_cart_lines(lines_in)
    if err:
        return err
    try:
        with transaction.atomic():
            order = PublicitateOrder.objects.create(
                user=request.user,
                status=PublicitateOrder.STATUS_PENDING,
                total_lei=total,
                payment_provider="demo",
            )
            for row in validated:
                PublicitateOrderLine.objects.create(order=order, **row)
    except Exception as exc:
        logging.getLogger(__name__).exception("publicitate_checkout_create")
        return JsonResponse({"ok": False, "error": "Nu am putut salva comanda."}, status=500)

    request.session[PUBLICITATE_SESSION_CHECKOUT_ORDER] = order.pk
    return JsonResponse(
        {
            "ok": True,
            "redirect": reverse("publicitate_checkout_demo"),
            "order_id": order.pk,
            "adjustments": adjustments,
        }
    )


@login_required
@require_POST
def publicitate_transfer_to_site_cart_view(request):
    """Mută liniile din coșul publicitate (browser) în coșul de cumpărături din site (SiteCartItem)."""
    if not _user_can_use_publicitate(request):
        return JsonResponse({"ok": False, "error": "Acces nepermis."}, status=403)
    try:
        body = json.loads(request.body.decode() or "{}")
    except json.JSONDecodeError:
        return JsonResponse({"ok": False, "error": "JSON invalid."}, status=400)
    lines_in = body.get("lines")
    validated, _total, adjustments, err = _publicitate_parse_cart_lines(lines_in)
    if err:
        return err
    n_existing = SiteCartItem.objects.filter(user=request.user).count()
    if n_existing + len(validated) > SITE_CART_MAX_ITEMS:
        return JsonResponse(
            {
                "ok": False,
                "error": (
                    f"Coșul site are deja {n_existing} articole; nu încap toate liniile "
                    f"(limită {SITE_CART_MAX_ITEMS})."
                ),
            },
            status=400,
        )
    base_path = reverse("publicitate_harta")
    try:
        with transaction.atomic():
            for row in validated:
                ref_key = "pub:" + uuid.uuid4().hex[:16]
                sec = row["section"]
                code = row["slot_code"]
                qty = row["quantity"]
                unit = row["unit_label"]
                lt = row["line_total_lei"]
                snap = row["title_snapshot"]
                title = f"{sec.upper()} · {code} · cant. {qty} {unit} · {lt} lei — {snap}"
                if len(title) > 220:
                    title = title[:217] + "…"
                du = f"{base_path}?sect={quote(sec)}"
                if len(du) > 500:
                    du = base_path[:500]
                SiteCartItem.objects.create(
                    user=request.user,
                    ref_key=ref_key,
                    kind=SiteCartItem.KIND_PUBLICITATE,
                    title=title,
                    detail_url=_safe_site_cart_detail_url(du),
                )
    except Exception:
        logging.getLogger(__name__).exception("publicitate_transfer_to_site_cart")
        return JsonResponse({"ok": False, "error": "Nu am putut salva în coș."}, status=500)
    payload = {"ok": True, "redirect": reverse("i_love_cos")}
    if adjustments:
        payload["notice"] = (
            "Unele casete au fost mutate automat la prima perioadă liberă. "
            "Verifică datele în coșul tău publicitar."
        )
        payload["adjustments"] = adjustments[:20]
    return JsonResponse(payload)


@login_required
def publicitate_checkout_demo_view(request):
    if not _user_can_use_publicitate(request):
        messages.info(request, "Pagina Publicitate este pentru conturi colaborator sau admin.")
        return redirect("home")
    oid = request.session.get(PUBLICITATE_SESSION_CHECKOUT_ORDER)
    if not oid:
        messages.info(request, "Nu există o comandă în așteptare. Adaugă sloturi în coș și încearcă din nou.")
        return redirect("publicitate_harta")
    order = PublicitateOrder.objects.filter(
        pk=oid, user=request.user, status=PublicitateOrder.STATUS_PENDING
    ).first()
    if order is None:
        request.session.pop(PUBLICITATE_SESSION_CHECKOUT_ORDER, None)
        messages.info(request, "Comanda nu mai este validă.")
        return redirect("publicitate_harta")
    return render(
        request,
        "anunturi/publicitate_checkout_demo.html",
        {
            "pub_order": order,
            "pub_order_lines": list(order.lines.all()),
        },
    )


@login_required
@require_POST
def publicitate_checkout_demo_confirm_view(request):
    """
    Simulare plată (demo). La go-live cu procesator real:
    - nu mai folosiți neapărat acest POST; redirect către gateway + webhook/return URL.
    - la confirmare plată validă: același bloc atomic (select_for_update), setați
      order.status=PAID, payment_provider, payment_ref, paid_at, apoi
      _apply_publicitate_paid_order(order) — aceeași funcție ca aici.
    """
    if not _user_can_use_publicitate(request):
        return redirect("home")
    oid = request.session.get(PUBLICITATE_SESSION_CHECKOUT_ORDER)
    if not oid:
        messages.info(request, "Sesiune expirată.")
        return redirect("publicitate_harta")
    try:
        with transaction.atomic():
            order = PublicitateOrder.objects.select_for_update().filter(pk=oid, user=request.user).first()
            if order is None:
                request.session.pop(PUBLICITATE_SESSION_CHECKOUT_ORDER, None)
                messages.error(request, "Comanda nu a fost găsită.")
                return redirect("publicitate_harta")
            if order.status == PublicitateOrder.STATUS_PAID:
                request.session.pop(PUBLICITATE_SESSION_CHECKOUT_ORDER, None)
                request.session[PUBLICITATE_SESSION_LAST_PAID] = order.pk
                try:
                    access = _ensure_publicitate_creative_for_order(order)
                    _send_publicitate_creative_email(order, access)
                except Exception:
                    logging.getLogger(__name__).exception("publicitate_creative_email_idempotent")
                return redirect("publicitate_checkout_demo_success")
            if order.status != PublicitateOrder.STATUS_PENDING:
                messages.error(request, "Comanda nu poate fi plătită.")
                return redirect("publicitate_harta")
            order.status = PublicitateOrder.STATUS_PAID
            order.payment_ref = f"DEMO-{order.pk}"
            order.paid_at = timezone.now()
            order.save(update_fields=["status", "payment_ref", "paid_at", "updated_at"])
            _apply_publicitate_paid_order(order)
    except Exception:
        logging.getLogger(__name__).exception("publicitate_checkout_demo_confirm")
        messages.error(request, "Eroare la confirmarea plății demo.")
        return redirect("publicitate_checkout_demo")

    try:
        access = _ensure_publicitate_creative_for_order(order)
        _send_publicitate_creative_email(order, access)
    except Exception:
        logging.getLogger(__name__).exception("publicitate_creative_email_after_pay")

    request.session.pop(PUBLICITATE_SESSION_CHECKOUT_ORDER, None)
    request.session[PUBLICITATE_SESSION_LAST_PAID] = order.pk
    _inbox.create_inbox_notification(
        request.user,
        _inbox.KIND_PUBLICITATE_PAID,
        "Plată publicitate confirmată",
        f"Comandă #{order.pk} (plată demo). Sloturile au fost rezervate conform fluxului curent.",
        link_url=reverse("publicitate_checkout_demo_success"),
        metadata={"publicitate_order_id": order.pk},
    )
    messages.success(request, f"Plată demo reușită. Comandă #{order.pk}.")
    return redirect("publicitate_checkout_demo_success")


@login_required
def publicitate_checkout_demo_success_view(request):
    if not _user_can_use_publicitate(request):
        return redirect("home")
    last_id = request.session.get(PUBLICITATE_SESSION_LAST_PAID)
    order = None
    if last_id:
        order = PublicitateOrder.objects.filter(pk=last_id, user=request.user).first()
    pub_creative_form_url = None
    if order:
        try:
            acc = order.creative_access
            if acc and timezone.now() <= acc.expires_at:
                base = (getattr(settings, "SITE_BASE_URL", None) or "").strip().rstrip("/")
                if base:
                    pub_creative_form_url = (
                        f"{base}{reverse('publicitate_creative_token', kwargs={'token': acc.secret_token})}"
                    )
        except PublicitateOrderCreativeAccess.DoesNotExist:
            pass
    return render(
        request,
        "anunturi/publicitate_checkout_demo_success.html",
        {
            "pub_order": order,
            "pub_creative_form_url": pub_creative_form_url,
        },
    )


def _pub_creative_review_hours() -> int:
    try:
        return max(1, int(getattr(settings, "PUBLICITATE_CREATIVE_REVIEW_HOURS", 12)))
    except (TypeError, ValueError):
        return 12


def _pub_creative_token_days() -> int:
    try:
        return max(1, int(getattr(settings, "PUBLICITATE_CREATIVE_TOKEN_DAYS", 90)))
    except (TypeError, ValueError):
        return 90


def _pub_creative_max_upload_bytes() -> int:
    try:
        mb = max(1, int(getattr(settings, "PUBLICITATE_CREATIVE_MAX_UPLOAD_MB", 4)))
    except (TypeError, ValueError):
        mb = 4
    return mb * 1024 * 1024


def _ensure_publicitate_creative_for_order(order: PublicitateOrder) -> PublicitateOrderCreativeAccess:
    """Creează token + rânduri materiale per linie (idempotent)."""
    token_days = _pub_creative_token_days()
    access, _created = PublicitateOrderCreativeAccess.objects.get_or_create(
        order=order,
        defaults={
            "secret_token": secrets.token_hex(32),
            "expires_at": timezone.now() + timezone.timedelta(days=token_days),
        },
    )
    for line in order.lines.all():
        PublicitateLineCreative.objects.get_or_create(line=line, defaults={})
    return access


def _send_publicitate_creative_email(order: PublicitateOrder, access: PublicitateOrderCreativeAccess) -> None:
    if access.email_sent_at:
        return
    to = (order.user.email or "").strip()
    if not to:
        return
    base = (getattr(settings, "SITE_BASE_URL", None) or "").strip().rstrip("/")
    if not base:
        return
    form_url = f"{base}{reverse('publicitate_creative_token', kwargs={'token': access.secret_token})}"
    subject = email_subject_for_user(order.user.username, "EU-Adopt: încărcați materialele pentru comanda publicitate")
    code_lines = []
    for line in order.lines.all():
        _publicitate_ensure_line_schedule_and_code(order, line)
        code_lines.append(f"- {line.section.upper()}/{line.slot_code}: {line.validation_code}")
    code_text = "\n".join(code_lines[:60]) if code_lines else "-"
    body_txt = (
        f"Bună,\n\n"
        f"Plata pentru comanda publicitate #{order.pk} a fost înregistrată.\n"
        f"Completați formularul (poză, link, detalii) pentru fiecare slot comandat:\n{form_url}\n\n"
        f"Coduri validare casetă (reactivare):\n{code_text}\n\n"
        f"Linkul expiră la {access.expires_at.strftime('%Y-%m-%d %H:%M')} (ora serverului).\n"
        f"După trimitere, materialele se aplică pe site acolo unde există integrare automată (ex. PT P4.3/P5.x, burtieră HOME).\n\n"
        f"— EU-Adopt"
    )
    html = (
        f"<p>Bună,</p>"
        f"<p>Plata pentru <strong>comanda publicitate #{order.pk}</strong> a fost înregistrată.</p>"
        f"<p>Deschideți formularul și încărcați materialele (poză, link, detalii) per slot:</p>"
        f'<p><a href="{escape(form_url)}">Formular materiale publicitate</a></p>'
        f"<p><strong>Coduri validare casetă</strong> (reactivare):<br>{escape(code_text).replace(chr(10), '<br>')}</p>"
        f"<p><small>Expiră: {escape(str(access.expires_at))}</small></p>"
        f"<p>— EU-Adopt</p>"
    )
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or None
    if not from_email:
        return
    try:
        send_mail_text_and_html(
            subject,
            body_txt,
            from_email,
            [to],
            html_body=html,
            mail_kind="publicitate_creative",
        )
    except Exception:
        logging.getLogger(__name__).exception("publicitate_creative_send_mail")
        return
    access.email_sent_at = timezone.now()
    access.save(update_fields=["email_sent_at"])


def _publicitate_creative_staff_recipient_emails() -> list[str]:
    """
    Destinatari notificări materiale publicitate (staff).
    Ordine: PUBLICITATE_CREATIVE_STAFF_EMAILS → ADMINS → DEFAULT_FROM_EMAIL (implicit operațional, fără .env extra).
    """
    raw = (getattr(settings, "PUBLICITATE_CREATIVE_STAFF_EMAILS", None) or "").strip()
    if raw:
        return [x.strip() for x in raw.split(",") if x.strip()][:12]
    out: list[str] = []
    admins = getattr(settings, "ADMINS", None) or ()
    for _name, em in admins:
        e = (em or "").strip()
        if e and e not in out:
            out.append(e)
    if out:
        return out[:8]
    fallback = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip()
    if fallback:
        return [fallback]
    return []


def _send_staff_publicitate_materials_submitted(request, order: PublicitateOrder, summaries: list[tuple[str, str]]) -> None:
    """Notifică echipa după ce clientul a trimis materiale (una sau mai multe linii)."""
    recipients = _publicitate_creative_staff_recipient_emails()
    if not summaries or not recipients:
        return
    from_email = (getattr(settings, "DEFAULT_FROM_EMAIL", None) or "").strip() or None
    if not from_email:
        return
    base = (getattr(settings, "SITE_BASE_URL", None) or "").strip().rstrip("/")
    try:
        admin_path = reverse("admin:home_publicitateorder_change", args=[order.pk])
        admin_hint = f"{base}{admin_path}" if base else admin_path
    except Exception:
        admin_hint = f"{base}/admin/" if base else f"Comanda #{order.pk}"
    body_lines = "\n".join(f"- {code}: {preview[:400]}" for code, preview in summaries)
    subject = f"[EU-Adopt staff] Materiale publicitate trimise — comanda #{order.pk}"
    body_txt = (
        f"Comandă publicitate #{order.pk} — utilizator: {order.user.username} ({order.user.email or 'fără email'}).\n"
        f"Sloturi actualizate:\n{body_lines}\n\n"
        f"Admin: {admin_hint}\n"
        f"Fereastră verificare recomandată: {_pub_creative_review_hours()} h de la trimitere.\n"
    )
    html = (
        f"<p><strong>Comandă #{order.pk}</strong> — {escape(order.user.username)} "
        f"({escape(order.user.email or '')})</p>"
        f"<p>Sloturi actualizate:</p><pre style=\"white-space:pre-wrap;font-size:0.9rem;\">{escape(body_lines)}</pre>"
        f"<p><a href=\"{escape(admin_hint)}\">Deschide în admin</a></p>"
    )
    try:
        send_mail_text_and_html(
            subject,
            body_txt,
            from_email,
            recipients,
            html_body=html,
            mail_kind="publicitate_creative_staff",
        )
    except Exception:
        logging.getLogger(__name__).exception("publicitate_creative_staff_notify")


def _publicitate_unpack_notes_meta(raw_notes: str) -> tuple[str, str, str]:
    raw = (raw_notes or "").strip()
    if not raw:
        return "", "", ""
    try:
        data = json.loads(raw)
    except json.JSONDecodeError:
        return raw, "", ""
    if not isinstance(data, dict):
        return raw, "", ""
    note = (data.get("note") or "").strip()
    price = (data.get("price") or "").strip()[:24]
    discount = (data.get("discount") or "").strip()[:8]
    return note, price, discount


def _publicitate_pack_notes_meta(note: str, price: str, discount: str) -> str:
    note_v = (note or "").strip()[:8000]
    price_v = (price or "").strip()[:24]
    discount_v = (discount or "").strip()[:8]
    if not price_v and not discount_v:
        return note_v
    return json.dumps(
        {"note": note_v, "price": price_v, "discount": discount_v},
        ensure_ascii=False,
    )


def _bundle_to_buyer_note(request, bundle: PublicitateLineCreative) -> str:
    notes, price, discount = _publicitate_unpack_notes_meta(bundle.extra_notes or "")
    link = (bundle.external_link or "").strip()
    img_url = ""
    video_url = ""
    if bundle.image:
        try:
            img_url = request.build_absolute_uri(bundle.image.url)
        except Exception:
            img_url = bundle.image.url or ""
    if bundle.video:
        try:
            video_url = request.build_absolute_uri(bundle.video.url)
        except Exception:
            video_url = bundle.video.url or ""
    if img_url or video_url:
        return json.dumps(
            {
                "img": img_url,
                "video": video_url,
                "link": link,
                "alt": notes[:240],
                "price": price,
                "discount": discount,
            },
            ensure_ascii=False,
        )
    if link:
        return link
    return notes


def _line_creative_has_post_data(request, line_pk: int) -> bool:
    if request.FILES.get(f"image_{line_pk}"):
        return True
    if request.FILES.get(f"video_{line_pk}"):
        return True
    if (request.POST.get(f"link_{line_pk}") or "").strip():
        return True
    if (request.POST.get(f"notes_{line_pk}") or "").strip():
        return True
    if (request.POST.get(f"price_{line_pk}") or "").strip():
        return True
    if (request.POST.get(f"discount_{line_pk}") or "").strip():
        return True
    return False


@require_http_methods(["GET", "POST"])
@csrf_protect
def publicitate_creative_by_token_view(request, token: str):
    token = (token or "").strip().lower()
    if len(token) != 64 or any(c not in "0123456789abcdef" for c in token):
        return render(
            request,
            "anunturi/publicitate_creative_gate.html",
            {"pub_creative_error": "Link invalid."},
            status=404,
        )
    access = PublicitateOrderCreativeAccess.objects.select_related("order", "order__user").filter(secret_token=token).first()
    if access is None:
        return render(
            request,
            "anunturi/publicitate_creative_gate.html",
            {"pub_creative_error": "Link invalid sau expirat."},
            status=404,
        )
    if timezone.now() > access.expires_at:
        return render(
            request,
            "anunturi/publicitate_creative_gate.html",
            {"pub_creative_error": "Acest link a expirat. Autentificați-vă în cont și deschideți materialele din secțiunea dedicată sau contactați suportul."},
            status=410,
        )
    return _publicitate_creative_form_response(request, access)


@login_required
@require_http_methods(["GET", "POST"])
@csrf_protect
def publicitate_creative_by_order_view(request, order_id: int):
    if not _user_can_use_publicitate(request):
        messages.info(request, "Acces publicitate doar pentru conturi autorizate.")
        return redirect("home")
    order = get_object_or_404(PublicitateOrder, pk=order_id, user=request.user)
    if order.status != PublicitateOrder.STATUS_PAID:
        messages.error(request, "Comanda nu este plătită.")
        return redirect("account")
    access = PublicitateOrderCreativeAccess.objects.filter(order=order).first()
    if access is None:
        access = _ensure_publicitate_creative_for_order(order)
    if timezone.now() > access.expires_at:
        messages.error(request, "Linkul de materiale a expirat.")
        return redirect("account")
    return _publicitate_creative_form_response(request, access)


def _publicitate_creative_form_response(request, access: PublicitateOrderCreativeAccess):
    order = access.order
    lines = list(order.lines.select_related("creative_bundle").order_by("id"))
    for _line in lines:
        _note, _price, _discount = _publicitate_unpack_notes_meta((_line.creative_bundle.extra_notes or ""))
        _line.creative_price = _price
        _line.creative_discount = _discount
        _line.creative_price_input = re.sub(r"\s*lei\s*$", "", _price, flags=re.IGNORECASE).strip()
        _line.creative_discount_input = re.sub(r"\s*%\s*$", "", _discount).strip()
    max_b = _pub_creative_max_upload_bytes()
    review_h = _pub_creative_review_hours()

    if request.method == "POST":
        applied = 0
        errors = []
        staff_summaries: list[tuple[str, str]] = []
        try:
            with transaction.atomic():
                for line in lines:
                    bundle = line.creative_bundle
                    pk = line.pk
                    is_burtiera = line.section == "home" and line.slot_code == "Burtieră"
                    if not _line_creative_has_post_data(request, pk):
                        continue
                    up = request.FILES.get(f"image_{pk}")
                    vp = request.FILES.get(f"video_{pk}")
                    if is_burtiera and (up or vp):
                        errors.append(
                            f"{line.slot_code}: pentru burtieră nu se încarcă media — folosiți doar link sau text "
                            f"(maximum {PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere)."
                        )
                        continue
                    if up and vp:
                        errors.append(f"{line.slot_code}: încărcați fie imagine, fie video, nu ambele.")
                        continue
                    if up and up.size > max_b:
                        errors.append(f"{line.slot_code}: fișierul depășește limita de {max_b // (1024 * 1024)} MB.")
                        continue
                    if vp and vp.size > max_b:
                        errors.append(f"{line.slot_code}: video depășește limita de {max_b // (1024 * 1024)} MB.")
                        continue
                    if vp:
                        ct = (getattr(vp, "content_type", "") or "").lower()
                        if not ct.startswith("video/"):
                            errors.append(f"{line.slot_code}: fișier video invalid (acceptat MP4/WebM/Ogg).")
                            continue
                    link = (request.POST.get(f"link_{pk}") or "").strip()[:500]
                    prev_note, _prev_price, _prev_discount = _publicitate_unpack_notes_meta(bundle.extra_notes or "")
                    notes = (request.POST.get(f"notes_{pk}") or "").strip()[:8000]
                    price_raw = (request.POST.get(f"price_{pk}") or "").strip()
                    discount_raw = (request.POST.get(f"discount_{pk}") or "").strip()
                    if price_raw and re.match(r"^\d+(?:[.,]\d{1,2})?$", price_raw):
                        price_raw = f"{price_raw} lei"
                    if discount_raw and re.match(r"^\d{1,3}$", discount_raw):
                        discount_raw = f"{discount_raw}%"
                    price = price_raw[:24]
                    discount = discount_raw[:8]
                    if is_burtiera:
                        if link and notes:
                            errors.append(
                                f"{line.slot_code}: pentru burtieră completați fie link, fie mesajul benzii, nu ambele."
                            )
                            continue
                        if len(link) > PUBLICITATE_BURTIERA_NOTE_MAXLEN:
                            errors.append(
                                f"{line.slot_code}: linkul are maximum {PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere."
                            )
                            continue
                        if len(notes) > PUBLICITATE_BURTIERA_NOTE_MAXLEN:
                            errors.append(
                                f"{line.slot_code}: mesajul benzii are maximum "
                                f"{PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere."
                            )
                            continue
                        if not link and not notes:
                            errors.append(
                                f"{line.slot_code}: pentru burtieră completați fie link, fie mesajul benzii "
                                f"(maximum {PUBLICITATE_BURTIERA_NOTE_MAXLEN} caractere)."
                            )
                            continue
                    else:
                        if discount and not re.match(r"^\d{1,3}%$", discount):
                            errors.append(f"{line.slot_code}: discount invalid. Format acceptat: 20%.")
                            continue
                        if not notes:
                            notes = prev_note
                    if link:
                        try:
                            URLValidator()(link)
                        except DjangoValidationError:
                            errors.append(f"{line.slot_code}: link invalid (folosiți https://…).")
                            continue
                    if up:
                        if bundle.video:
                            bundle.video.delete(save=False)
                            bundle.video = None
                        bundle.image.save(up.name, up, save=False)
                    elif vp:
                        if bundle.image:
                            bundle.image.delete(save=False)
                            bundle.image = None
                        bundle.video.save(vp.name, vp, save=False)
                    bundle.external_link = link
                    bundle.extra_notes = _publicitate_pack_notes_meta(notes, price, discount)
                    buyer = _bundle_to_buyer_note(request, bundle)
                    if not (buyer or "").strip():
                        errors.append(f"{line.slot_code}: lipsește conținut util.")
                        continue
                    buyer_cap = PUBLICITATE_BURTIERA_NOTE_MAXLEN if is_burtiera else 8000
                    line.buyer_note = buyer[:buyer_cap]
                    now = timezone.now()
                    # La trimiterea materialelor marcăm activată linia când perioada e activă.
                    if (
                        not line.activated_at
                        and line.starts_at
                        and line.ends_at
                        and line.starts_at <= now <= line.ends_at
                    ):
                        line.activated_at = now
                        line.save(update_fields=["buyer_note", "activated_at"])
                    else:
                        line.save(update_fields=["buyer_note"])
                    _apply_publicitate_line_to_site(line, order)
                    bundle.status = PublicitateLineCreative.STATUS_LIVE
                    bundle.submitted_at = now
                    bundle.live_at = now
                    bundle.review_until = now + timezone.timedelta(hours=review_h)
                    bundle.save()
                    applied += 1
                    staff_summaries.append((f"{line.section.upper()}/{line.slot_code}", buyer))
        except Exception:
            logging.getLogger(__name__).exception("publicitate_creative_submit")
            errors.append("Eroare la salvare. Reîncercați.")

        if applied > 0 and staff_summaries:
            _send_staff_publicitate_materials_submitted(request, order, staff_summaries)

        if errors:
            for e in errors[:5]:
                messages.error(request, e)
        elif applied == 0:
            messages.warning(
                request,
                "Nu s-a trimis nimic: completați cel puțin o linie (poză, link sau detalii) și apăsați din nou „Trimite materialele”.",
            )
        else:
            messages.success(
                request,
                f"Materiale trimise pentru {applied} slot(uri). S-au aplicat pe site unde există integrare automată. "
                f"Aveți până la ~{review_h} h pentru verificare internă (contactați suportul dacă e nevoie de corecție).",
            )
        return redirect(request.path)

    all_live = (
        all(line.creative_bundle.status == PublicitateLineCreative.STATUS_LIVE for line in lines) if lines else True
    )
    return render(
        request,
        "anunturi/publicitate_creative_form.html",
        {
            "pub_access": access,
            "pub_order": order,
            "pub_lines": lines,
            "pub_max_mb": max_b // (1024 * 1024),
            "pub_review_hours": review_h,
            "pub_all_live": all_live,
        },
    )


def reset_publicitate_line_creative_bundle(creative: PublicitateLineCreative) -> None:
    """
    Staff admin: șterge fișierul, golește câmpurile, revocă buyer_note și reaplică pe site (placeholder PT / fără burtieră).
    """
    line = creative.line
    order = line.order
    with transaction.atomic():
        if creative.image:
            creative.image.delete(save=False)
        if creative.video:
            creative.video.delete(save=False)
        creative.image = None
        creative.video = None
        creative.external_link = ""
        creative.extra_notes = ""
        creative.status = PublicitateLineCreative.STATUS_PENDING
        creative.submitted_at = None
        creative.live_at = None
        creative.review_until = None
        creative.save()
        line.buyer_note = ""
        line.save(update_fields=["buyer_note"])
        _apply_publicitate_line_to_site(line, order)


def _tp_parse_coord_deg(raw) -> float | None:
    try:
        s = (raw or "").strip().replace(",", ".")
        if not s:
            return None
        v = float(s)
        if math.isnan(v) or abs(v) > 180:
            return None
        return v
    except (TypeError, ValueError):
        return None


def _tp_haversine_km(lat1: float, lon1: float, lat2: float, lon2: float) -> float:
    r = 6371.0
    p1, p2 = math.radians(lat1), math.radians(lat2)
    d1 = math.radians(lat2 - lat1)
    d2 = math.radians(lon2 - lon1)
    a = math.sin(d1 / 2) ** 2 + math.cos(p1) * math.cos(p2) * math.sin(d2 / 2) ** 2
    c = 2 * math.atan2(math.sqrt(a), math.sqrt(max(0.0, 1.0 - a)))
    return round(r * c, 1)


def _tp_transport_op_can_view_job(user, job: TransportDispatchJob) -> bool:
    if not user or not getattr(user, "is_authenticated", False) or not job:
        return False
    if job.assigned_transporter_id == user.id:
        return True
    return TransportDispatchRecipient.objects.filter(job=job, transporter=user).exists()


def _tp_google_maps_directions_url(tvr: TransportVeterinaryRequest) -> str:
    plat = _tp_parse_coord_deg(getattr(tvr, "plecare_lat", None))
    plng = _tp_parse_coord_deg(getattr(tvr, "plecare_lng", None))
    slat = _tp_parse_coord_deg(getattr(tvr, "sosire_lat", None))
    slng = _tp_parse_coord_deg(getattr(tvr, "sosire_lng", None))
    if plat is not None and plng is not None and slat is not None and slng is not None:
        return f"https://www.google.com/maps/dir/?api=1&origin={plat},{plng}&destination={slat},{slng}"
    po = quote((tvr.plecare or "").strip())
    so = quote((tvr.sosire or "").strip())
    if po and so:
        return f"https://www.google.com/maps/dir/?api=1&origin={po}&destination={so}"
    if so:
        return f"https://www.google.com/maps/search/?api=1&query={so}"
    if po:
        return f"https://www.google.com/maps/search/?api=1&query={po}"
    return ""


def _tp_waze_nav_url(lat: float | None, lng: float | None, address: str) -> str:
    if lat is not None and lng is not None:
        return f"https://waze.com/ul?ll={lat}%2C{lng}&navigate=yes"
    q = quote((address or "").strip())
    if q:
        return f"https://waze.com/ul?q={q}&navigate=yes"
    return ""


def _tp_osm_embed_url(tvr: TransportVeterinaryRequest) -> str:
    plat = _tp_parse_coord_deg(getattr(tvr, "plecare_lat", None))
    plng = _tp_parse_coord_deg(getattr(tvr, "plecare_lng", None))
    slat = _tp_parse_coord_deg(getattr(tvr, "sosire_lat", None))
    slng = _tp_parse_coord_deg(getattr(tvr, "sosire_lng", None))
    if plat is None or plng is None or slat is None or slng is None:
        return ""
    min_lon, max_lon = min(plng, slng), max(plng, slng)
    min_lat, max_lat = min(plat, slat), max(plat, slat)
    pad = 0.025
    bbox = f"{min_lon - pad},{min_lat - pad},{max_lon + pad},{max_lat + pad}"
    return f"https://www.openstreetmap.org/export/embed.html?bbox={bbox}&layer=mapnik"


@login_required
@collab_magazin_required
def transport_operator_job_detail_view(request, job_id: int):
    """JSON: detalii cerere pentru transportator (panou); acces doar dacă e invitat sau asignat la job."""
    gate = _transport_operator_panel_gate(request)
    if gate is not None:
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    job = TransportDispatchJob.objects.select_related("tvr", "tvr__user", "tvr__related_animal").filter(pk=job_id).first()
    if not job:
        return JsonResponse({"ok": False, "error": "not_found"}, status=404)
    if not _tp_transport_op_can_view_job(request.user, job):
        return JsonResponse({"ok": False, "error": "forbidden"}, status=403)
    tvr = job.tvr
    cu = tvr.user
    phone = ""
    if cu:
        prof = getattr(cu, "profile", None)
        if prof and getattr(prof, "phone", None):
            phone = (prof.phone or "").strip()
    full_name = ""
    if cu:
        full_name = (f"{cu.first_name} {cu.last_name}").strip() or ""
    plat = _tp_parse_coord_deg(getattr(tvr, "plecare_lat", None))
    plng = _tp_parse_coord_deg(getattr(tvr, "plecare_lng", None))
    slat = _tp_parse_coord_deg(getattr(tvr, "sosire_lat", None))
    slng = _tp_parse_coord_deg(getattr(tvr, "sosire_lng", None))
    straight_km = None
    if plat is not None and plng is not None and slat is not None and slng is not None:
        straight_km = _tp_haversine_km(plat, plng, slat, slng)
    animal_label = ""
    ra = getattr(tvr, "related_animal", None)
    if ra is not None:
        animal_label = (getattr(ra, "name", None) or f"Anunț #{getattr(ra, 'pk', '')}") or ""
    payload = {
        "ok": True,
        "job_id": job.pk,
        "job_status": job.status,
        "job_status_label": job.get_status_display(),
        "tvr_id": tvr.pk,
        "created_at": tvr.created_at.isoformat() if getattr(tvr, "created_at", None) else "",
        "judet": tvr.judet or "",
        "oras": tvr.oras or "",
        "plecare": tvr.plecare or "",
        "sosire": tvr.sosire or "",
        "plecare_lat": tvr.plecare_lat or "",
        "plecare_lng": tvr.plecare_lng or "",
        "sosire_lat": tvr.sosire_lat or "",
        "sosire_lng": tvr.sosire_lng or "",
        "data_raw": tvr.data_raw or "",
        "ora_raw": tvr.ora_raw or "",
        "nr_caini": int(tvr.nr_caini or 0),
        "route_scope": tvr.route_scope or "",
        "route_scope_label": tvr.get_route_scope_display(),
        "urgency_window": tvr.urgency_window or "",
        "urgency_label": tvr.get_urgency_window_display(),
        "related_animal_id": int(tvr.related_animal_id) if getattr(tvr, "related_animal_id", None) else None,
        "related_animal_label": animal_label,
        "related_animal_url": (
            reverse("pets_single", args=[int(tvr.related_animal_id)])
            if getattr(tvr, "related_animal_id", None)
            else ""
        ),
        "client_username": (cu.username if cu else "") or "",
        "client_email": (cu.email if cu else "") or "",
        "client_full_name": full_name,
        "client_phone": phone,
        "straight_line_km": straight_km,
        "maps_google_directions": _tp_google_maps_directions_url(tvr),
        "maps_waze_start": _tp_waze_nav_url(plat, plng, tvr.plecare or ""),
        "maps_waze_end": _tp_waze_nav_url(slat, slng, tvr.sosire or ""),
        "maps_osm_embed": _tp_osm_embed_url(tvr),
    }
    return JsonResponse(payload)


@login_required
@collab_magazin_required
def transport_operator_panel_view(request):
    """Panou transportator: comenzi (în dezvoltare), capacitate, status aprobare."""
    ap = getattr(request.user, "account_profile", None)
    prof = getattr(request.user, "profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return redirect("home")
    if (getattr(prof, "collaborator_type", None) or "").strip().lower() != "transport":
        return redirect("collab_offers_control")
    TransportOperatorProfile.objects.get_or_create(
        user=request.user,
        defaults={
            "approval_status": TransportOperatorProfile.APPROVAL_PENDING,
            "transport_national": True,
            "transport_international": False,
            "max_caini": 1,
            "max_pisici": 1,
        },
    )
    from .transport_dispatch import maybe_expire_job

    me = request.user
    jobs_active = list(
        TransportDispatchJob.objects.filter(
            assigned_transporter=me,
            status=TransportDispatchJob.STATUS_ASSIGNED,
        )
        .select_related("tvr", "tvr__user")
        .order_by("-assigned_at", "-updated_at")[:50]
    )
    jobs_completed = list(
        TransportDispatchJob.objects.filter(
            assigned_transporter=me,
            status=TransportDispatchJob.STATUS_COMPLETED,
        )
        .select_related("tvr", "tvr__user")
        .order_by("-updated_at")[:80]
    )
    pending_invites = []
    for r in (
        TransportDispatchRecipient.objects.filter(
            transporter=me,
            status=TransportDispatchRecipient.ST_PENDING,
        )
        .select_related("job", "job__tvr", "job__tvr__user")
        .order_by("-job__created_at")[:40]
    ):
        maybe_expire_job(r.job)
        r.job.refresh_from_db()
        if r.job.status == TransportDispatchJob.STATUS_OPEN:
            pending_invites.append(r)

    return render(
        request,
        "anunturi/transport_operator_panou.html",
        {
            "transport_jobs_active": jobs_active,
            "transport_jobs_completed": jobs_completed,
            "transport_pending_invites": pending_invites,
            "tp_count_pending": len(pending_invites),
            "tp_count_active": len(jobs_active),
            "tp_count_completed": len(jobs_completed),
            "tp_job_detail_url_base": reverse("transport_operator_job_detail", args=[0]),
        },
    )


@login_required
@collab_magazin_required
def collab_offers_control_view(request):
    tip = _collaborator_tip_partener(request)
    if tip == "transport":
        return redirect(reverse("transport_operator_panel"))
    offers_qs = (
        CollaboratorServiceOffer.objects.filter(collaborator=request.user, partner_kind=tip)
        .annotate(claims_c=Count("claims"))
        .order_by("-created_at")[:100]
    )
    offers = list(offers_qs)
    for o in offers:
        if o.quantity_available is not None:
            o.remaining_slots = max(0, int(o.quantity_available) - int(o.claims_c))
        else:
            o.remaining_slots = None
    vet_kpi_offers_total = len(offers)
    vet_kpi_offers_active = sum(1 for o in offers if o.is_active)
    vet_kpi_offers_inactive = vet_kpi_offers_total - vet_kpi_offers_active
    vet_kpi_claims_total = sum(int(getattr(o, "claims_c", 0) or 0) for o in offers)
    vet_kpi_slots_remaining_sum = sum(
        int(o.remaining_slots) for o in offers if o.remaining_slots is not None
    )
    recent_claims = list(
        CollaboratorOfferClaim.objects.filter(
            offer__collaborator=request.user, offer__partner_kind=tip
        )
        .select_related("offer")
        .order_by("-created_at")[:200]
    )
    return render(
        request,
        "anunturi/magazinul_meu_oferte_control.html",
        {
            "collab_offers": offers,
            "collab_recent_claims": recent_claims,
            "open_messages": (request.GET.get("open_messages") or "").strip() == "1",
            "tip_just_updated": (request.GET.get("tip_updated") or "").strip() == "1",
            "collab_tip_partener": tip,
            "vet_kpi_offers_total": vet_kpi_offers_total,
            "vet_kpi_offers_active": vet_kpi_offers_active,
            "vet_kpi_offers_inactive": vet_kpi_offers_inactive,
            "vet_kpi_claims_total": vet_kpi_claims_total,
            "vet_kpi_slots_remaining_sum": vet_kpi_slots_remaining_sum,
            "ro_today": _ro_today(),
        },
    )


@login_required
@collab_magazin_required
def collab_offer_new_view(request):
    if _collaborator_tip_partener(request) == "transport":
        return redirect("transport_operator_panel")
    M = CollaboratorServiceOffer
    return render(
        request,
        "anunturi/magazinul_meu_oferte_nou.html",
        {
            "collab_tip_partener": _collaborator_tip_partener(request),
            "tf": {
                "sp": M.TARGET_SPECIES_ALL,
                "sz": M.TARGET_SIZE_ALL,
                "sex": M.TARGET_SEX_ALL,
                "age": M.TARGET_AGE_ALL,
                "st": M.TARGET_STERIL_ALL,
            },
            "tf_species_dog": False,
            "tf_species_cat": False,
            "tf_species_other": False,
        },
    )


@login_required
@collab_magazin_required
@require_http_methods(["GET", "POST"])
def collab_offer_edit_view(request, pk: int):
    tip = _collaborator_tip_partener(request)
    if tip == "transport":
        return redirect("transport_operator_panel")
    offer = get_object_or_404(
        CollaboratorServiceOffer, pk=pk, collaborator=request.user, partner_kind=tip
    )
    ap = getattr(request.user, "account_profile", None)
    if not ap or ap.role != AccountProfile.ROLE_COLLAB:
        return redirect("home")
    if tip not in ("cabinet", "servicii", "magazin"):
        messages.error(request, "Tip partener necunoscut.")
        return redirect("collab_offers_control")

    claims_count = CollaboratorOfferClaim.objects.filter(offer=offer).count()

    if request.method == "POST":
        old_valid_from = offer.valid_from
        old_valid_until = offer.valid_until
        old_quantity_available = offer.quantity_available
        title = (request.POST.get("title") or "").strip()
        description = (request.POST.get("description") or "").strip()[:500]
        external_url_raw = (request.POST.get("external_url") or "").strip()[:500]
        external_url = ""
        price_hint = (request.POST.get("price_hint") or "").strip()[:80]
        discount_raw = (request.POST.get("discount_percent") or "").strip()
        discount_percent = None
        if discount_raw.isdigit():
            d = int(discount_raw)
            if 1 <= d <= 100:
                discount_percent = d
        qty_raw = (request.POST.get("quantity_available") or "").strip()
        quantity_available = None
        if qty_raw.isdigit():
            q = int(qty_raw)
            if 0 < q <= 999_999:
                if q < claims_count:
                    messages.error(
                        request,
                        f"Numărul de oferte valabile nu poate fi mai mic decât solicitările deja înregistrate ({claims_count}).",
                    )
                    return redirect(reverse("collab_offer_edit", args=[pk]))
                quantity_available = q
        valid_from = _parse_post_date_iso(request.POST.get("valid_from"))
        valid_until = _parse_post_date_iso(request.POST.get("valid_until"))
        image = request.FILES.get("image")
        product_sheet_file = request.FILES.get("product_sheet")
        species_dog, species_cat, species_other = _parse_collab_species_checks(request.POST)
        errs = []
        if not title:
            errs.append(
                "Completează titlul produsului."
                if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN
                else "Completează titlul serviciului."
            )
        if not quantity_available:
            errs.append(
                "Introdu numărul de oferte valabile (minimum 1). Valoarea nu poate fi sub numărul de solicitări existente."
            )
        if not valid_from:
            errs.append("Alege data de început a valabilității ofertei.")
        if not valid_until:
            errs.append("Alege data de sfârșit a valabilității ofertei.")
        if valid_from and valid_until and valid_until < valid_from:
            errs.append("Data de sfârșit trebuie să fie după sau egală cu data de început.")
        if not (species_dog or species_cat or species_other):
            errs.append("Selectează cel puțin o categorie specie: Câini, Pisici sau Altele.")
        if tip in (
            CollaboratorServiceOffer.PARTNER_KIND_CABINET,
            CollaboratorServiceOffer.PARTNER_KIND_SERVICII,
            CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN,
        ):
            if not price_hint:
                errs.append("Completează prețul (ex. 200 lei).")
            if discount_percent is None:
                errs.append("Introdu discountul (1–100%).")
        external_url = ""
        if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN:
            try:
                external_url = _normalize_external_url(external_url_raw)
            except ValueError as exc:
                errs.append(str(exc))
            if not external_url:
                errs.append("La tipul Magazin / Pet-shop, completează linkul produsului (site extern).")
            sheet_err = _validate_collab_product_sheet(product_sheet_file)
            if sheet_err:
                errs.append(sheet_err)
        if errs:
            for e in errs:
                messages.error(request, e)
            return redirect(reverse("collab_offer_edit", args=[pk]))
        tf = _collab_offer_target_filters_for_tip(tip, request.POST)
        offer.title = title
        offer.description = description
        offer.external_url = external_url
        offer.price_hint = price_hint
        offer.discount_percent = discount_percent
        offer.quantity_available = quantity_available
        offer.valid_from = valid_from
        offer.valid_until = valid_until
        offer.target_species = tf["target_species"]
        offer.target_size = tf["target_size"]
        offer.target_sex = tf["target_sex"]
        offer.target_age_band = tf["target_age_band"]
        offer.target_sterilized = tf["target_sterilized"]
        offer.species_dog = species_dog
        offer.species_cat = species_cat
        offer.species_other = species_other
        if tip == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN and product_sheet_file:
            offer.product_sheet = product_sheet_file
        if tip != CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN and offer.product_sheet:
            offer.product_sheet = None
        if valid_from != old_valid_from or valid_until != old_valid_until:
            offer.expiry_notice_sent_for_valid_until = None
        if quantity_available != old_quantity_available:
            offer.low_stock_notice_sent = False
        update_fields = [
            "title",
            "description",
            "external_url",
            "price_hint",
            "discount_percent",
            "quantity_available",
            "valid_from",
            "valid_until",
            "target_species",
            "target_size",
            "target_sex",
            "target_age_band",
            "target_sterilized",
            "species_dog",
            "species_cat",
            "species_other",
            "product_sheet",
            "updated_at",
        ]
        if valid_from != old_valid_from or valid_until != old_valid_until:
            update_fields.append("expiry_notice_sent_for_valid_until")
        if quantity_available != old_quantity_available:
            update_fields.append("low_stock_notice_sent")
        if image:
            offer.image = image
            update_fields.append("image")
        offer.save(update_fields=update_fields)
        messages.success(request, "Oferta a fost actualizată.")
        return redirect("collab_offers_control")

    quantity_floor = max(1, int(claims_count))
    return render(
        request,
        "anunturi/magazinul_meu_oferte_edit.html",
        {
            "offer": offer,
            "collab_tip_partener": tip,
            "claims_count": claims_count,
            "quantity_floor": quantity_floor,
            "tf": {
                "sp": offer.target_species,
                "sz": offer.target_size,
                "sex": offer.target_sex,
                "age": offer.target_age_band,
                "st": offer.target_sterilized,
            },
            "tf_species_dog": bool(offer.species_dog),
            "tf_species_cat": bool(offer.species_cat),
            "tf_species_other": bool(offer.species_other),
        },
    )


def public_offer_detail_view(request, pk: int):
    offer = get_object_or_404(
        _collab_offer_valid_public_qs(
            CollaboratorServiceOffer.objects.filter(is_active=True)
            .select_related("collaborator")
            .annotate(claims_count=Count("claims", distinct=True))
        ),
        pk=pk,
    )
    _attach_public_offer_stock(offer)
    return render(
        request,
        "anunturi/oferta_partener_detail.html",
        {
            "offer": offer,
            "can_request_public_collab_offer": _user_can_request_public_collab_offer(
                request.user
            ),
        },
    )


@require_POST
@csrf_protect
def public_offer_request_view(request, pk: int):
    detail_next = reverse("public_offer_detail", args=[pk])
    if not request.user.is_authenticated:
        messages.info(
            request,
            "Intră în cont sau creează cont pentru a solicita oferta.",
        )
        return redirect_to_login(detail_next, login_url=reverse("login"))

    if _user_is_public_offer_transport_blocked(request.user):
        messages.error(
            request,
            "Conturile de transportatori nu pot solicita oferte din Servicii; folosește zona Transport.",
        )
        return _redirect_after_public_offer_request(request, pk)

    post_name = (request.POST.get("name") or "").strip()
    post_email = (request.POST.get("email") or "").strip()
    buyer = _buyer_snapshot_for_offer_request(request, post_name, post_email)
    dest_email = buyer["email"]
    if not dest_email:
        messages.error(
            request,
            "Completează adresa de email în cont ca să primești confirmarea și datele cabinetului.",
        )
        return _redirect_after_public_offer_request(request, pk)

    offer_preview = get_object_or_404(
        _collab_offer_valid_public_qs(
            CollaboratorServiceOffer.objects.filter(is_active=True).select_related("collaborator")
        ),
        pk=pk,
    )
    collab = offer_preview.collaborator
    collab_mail = (collab.email or "").strip()
    if not collab_mail:
        messages.error(
            request,
            "Momentan nu putem trimite solicitarea: cabinetul nu are email configurat.",
        )
        return _redirect_after_public_offer_request(request, pk)

    if _public_offer_request_rate_limited(request, pk):
        messages.error(
            request,
            "Ai trimis prea multe solicitări recent. Încearcă din nou peste câteva minute.",
        )
        return _redirect_after_public_offer_request(request, pk)

    code = None
    offer = None
    try:
        with transaction.atomic():
            offer = (
                CollaboratorServiceOffer.objects.select_for_update()
                .filter(is_active=True, pk=pk)
                .first()
            )
            if not offer:
                messages.error(request, "Oferta nu mai este disponibilă.")
                return _redirect_after_public_offer_request(request, pk)
            if not _collab_offer_is_valid_today(offer):
                messages.error(
                    request,
                    "Oferta nu mai este în perioada de valabilitate.",
                )
                return _redirect_after_public_offer_request(request, pk)
            claimed = CollaboratorOfferClaim.objects.filter(offer_id=offer.pk).count()
            if offer.quantity_available is not None:
                if claimed >= int(offer.quantity_available):
                    messages.error(
                        request,
                        "Oferta nu mai are locuri disponibile.",
                    )
                    return _redirect_after_public_offer_request(request, pk)
            code = _generate_collab_offer_code()
            CollaboratorOfferClaim.objects.create(
                offer=offer,
                code=code,
                buyer_user=buyer["user"],
                buyer_email=dest_email,
                buyer_name_snapshot=buyer["name"],
                buyer_phone_snapshot=(buyer["phone"][:40] if buyer["phone"] else ""),
                buyer_locality_snapshot=(buyer["locality"][:200] if buyer["locality"] else ""),
            )
            if offer.quantity_available is not None:
                new_count = claimed + 1
                if new_count >= int(offer.quantity_available):
                    offer.is_active = False
                    offer.save(update_fields=["is_active", "updated_at"])
    except Exception:
        logging.exception("public_offer_request atomic failed pk=%s", pk)
        messages.error(request, "A apărut o eroare. Încearcă din nou.")
        return _redirect_after_public_offer_request(request, pk)

    if not code or offer is None:
        return _redirect_after_public_offer_request(request, pk)

    _public_offer_request_rate_limit_touch(request, pk)

    bu = buyer.get("user")
    if bu:
        _inbox.create_inbox_notification(
            bu,
            _inbox.KIND_OFFER_CLAIM_BUYER,
            "Ofertă solicitată",
            f"Cod {code}: {offer.title}. Datele au fost trimise pe email.",
            link_url=reverse("servicii"),
            metadata={"offer_id": offer.pk, "claim_code": code},
        )
    _inbox.create_inbox_notification(
        collab,
        _inbox.KIND_OFFER_CLAIM_COLLABORATOR,
        "Solicitare nouă pentru ofertă",
        f"Cod {code}: {offer.title}. Verifică emailul pentru datele solicitantului.",
        link_url=reverse("collab_offers_control") + "?open_messages=1",
        metadata={"offer_id": offer.pk, "claim_code": code},
    )

    cabinet_txt = _cabinet_block_for_buyer_email(collab)
    buyer_subject = f"EU-Adopt – cod ofertă {code}: {offer.title}"
    buyer_body = (
        f"Bună {buyer['name']},\n\n"
        f"Codul ofertei (îl au și cabinetul și tu): {code}\n\n"
        f"Ofertă: {offer.title}\n\n"
        f"--- Date cabinet (contact) ---\n{cabinet_txt}\n\n"
    )
    if offer.description:
        buyer_body += f"--- Descriere ---\n{offer.description}\n\n"
    if offer.price_hint:
        buyer_body += f"Preț indicat: {offer.price_hint}\n"
    if offer.discount_percent:
        buyer_body += f"Discount: {offer.discount_percent}%\n"
    buyer_body += "\n---\nEU-Adopt\n"

    collab_subject = f"EU-Adopt – solicitare ofertă [{code}] {offer.title}"
    collab_body = (
        f"Ai o nouă solicitare pentru ofertă.\n\n"
        f"Cod ofertă (același ca la cumpărător): {code}\n"
        f"Titlu ofertă: {offer.title}\n\n"
        f"--- Date cumpărător ---\n"
        f"Nume: {buyer['name']}\n"
        f"Email: {dest_email}\n"
    )
    if buyer["phone"]:
        collab_body += f"Telefon: {buyer['phone']}\n"
    if buyer["locality"]:
        collab_body += f"Localitate: {buyer['locality']}\n"
    collab_body += "\n---\nEU-Adopt\n"

    cabinet_maps_url = _cabinet_maps_url_for_buyer_email(collab)
    if cabinet_maps_url:
        buyer_body += f"Navigare la cabinet (hartă): {cabinet_maps_url}\n"
    buyer_maps_html = _html_email_maps_cta_button(cabinet_maps_url, "DU-MĂ LA LOCAȚIE")
    buyer_html = (
        f"<p>Bună {escape(buyer['name'])},</p>"
        f"<p>Codul ofertei (îl au și cabinetul și tu): <strong>{escape(code)}</strong></p>"
        f"<p>Ofertă: <strong>{escape(offer.title)}</strong></p>"
        f"<p><strong>Date cabinet (contact)</strong></p>"
        f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(cabinet_txt)}</pre>"
    )
    if offer.description:
        buyer_html += f"<p><strong>Descriere</strong><br>{escape(offer.description)}</p>"
    if offer.price_hint:
        buyer_html += f"<p>Preț indicat: {escape(offer.price_hint)}</p>"
    if offer.discount_percent:
        buyer_html += f"<p>Discount: {escape(str(offer.discount_percent))}%</p>"
    buyer_html += buyer_maps_html + "<p>—<br>EU-Adopt</p>"

    buyer_loc_url = _buyer_maps_url_for_collab_email(buyer)
    if buyer_loc_url:
        collab_body += f"Navigare la solicitant (hartă): {buyer_loc_url}\n"
    collab_maps_html = _html_email_maps_cta_button(buyer_loc_url, "DU-MĂ LA LOCAȚIE")
    collab_buyer_block = f"Nume: {buyer['name']}\nEmail: {dest_email}\n"
    if buyer["phone"]:
        collab_buyer_block += f"Telefon: {buyer['phone']}\n"
    if buyer["locality"]:
        collab_buyer_block += f"Localitate: {buyer['locality']}\n"
    collab_html = (
        "<p>Ai o nouă solicitare pentru ofertă.</p>"
        f"<p>Cod ofertă (același ca la cumpărător): <strong>{escape(code)}</strong><br>"
        f"Titlu ofertă: <strong>{escape(offer.title)}</strong></p>"
        "<p><strong>Date cumpărător</strong></p>"
        f"<pre style=\"white-space:pre-wrap;font-family:inherit;\">{escape(collab_buyer_block)}</pre>"
        + collab_maps_html
        + "<p>—<br>EU-Adopt</p>"
    )

    mail_errors = []
    buyer_uname = buyer["user"].username if buyer.get("user") else None
    if not buyer_uname and dest_email:
        buyer_uname = dest_email.split("@", 1)[0] if "@" in dest_email else None
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        send_mail_text_and_html(
            email_subject_for_user(buyer_uname, buyer_subject),
            buyer_body,
            from_email,
            [dest_email],
            buyer_html,
            mail_kind="offer_claim_buyer",
        )
    except Exception:
        logging.exception("send_mail buyer offer claim")
        mail_errors.append("cumpărător")
    try:
        send_mail_text_and_html(
            email_subject_for_user(collab.username, collab_subject),
            collab_body,
            from_email,
            [collab_mail],
            collab_html,
            mail_kind="offer_claim_collaborator",
        )
    except Exception:
        logging.exception("send_mail collab offer claim")
        mail_errors.append("cabinet")

    if mail_errors:
        messages.warning(
            request,
            "Solicitarea a fost înregistrată, dar unele emailuri nu s-au putut trimite acum. Verifică datele din cont sau încearcă din nou.",
        )
    else:
        messages.success(
            request,
            f"Ți-am trimis pe email codul ofertei ({code}) și datele cabinetului. Colaboratorul a fost anunțat. Verifică și Spam.",
        )
    return _redirect_after_public_offer_request(request, pk)