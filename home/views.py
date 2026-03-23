"""
Home views. Layout HOME înghețat: v. HOME_SLOTS.md
A0=navbar, A1=hero, A2=grid 4×3, A3=mission bar, A4=footer, A5=left sidebar (3), A6=right sidebar (3).
REGULĂ: Orice modificare în home (punct, virgulă, orice) doar cu aprobarea titularului, cu parolă.
"""
import logging
import random
import secrets
from datetime import date, datetime
from copy import deepcopy
from itertools import cycle
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.db.models import Count, Q, Max
from django.db.models import F
from django.core.files.base import ContentFile
from django.core.validators import URLValidator
from django.core.exceptions import ValidationError as DjangoValidationError
from django.conf import settings
from django.core.mail import send_mail
from django.db import transaction
import os
from django.views.decorators.http import require_POST, require_http_methods
from django.core.cache import cache
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .data import DEMO_DOGS, DEMO_DOG_IMAGE, A2_QUOTE_POOL, HERO_SLIDER_IMAGES
from .models import (
    WishlistItem,
    AnimalListing,
    UserAdoption,
    AccountProfile,
    UserProfile,
    PetMessage,
    CollabServiceMessage,
    AdoptionRequest,
    CollaboratorServiceOffer,
    CollaboratorOfferClaim,
)
from django.contrib.auth import get_user_model
from functools import wraps
from django.contrib import messages


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


def _user_can_use_magazinul_meu(request):
    """
    Pagina Magazinul meu: colaboratori (cabinet / servicii / magazin).
    Staff: doar când „Vezi ca colaborator”.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        return request.session.get("view_as_role") == "collaborator"
    try:
        ap = getattr(user, "account_profile", None)
        return bool(ap and ap.role == AccountProfile.ROLE_COLLAB)
    except Exception:
        return False


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


def _collaborator_tip_partener(request) -> str:
    """
    Valoare din înregistrare colaborator (tip_partener): cabinet | servicii | magazin.
    Cabinet și servicii folosesc același template; magazin are pagină separată (produse).
    Pentru staff cu „Vezi ca colaborator”, tipul vine din sesiune (preview Magazinul meu).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return "servicii"
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        if request.session.get("view_as_role") == "collaborator":
            st = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
            if st in ("cabinet", "servicii", "magazin"):
                return st
            return "servicii"
    try:
        prof = getattr(user, "profile", None)
        tip = (getattr(prof, "collaborator_type", None) or "").strip().lower()
    except Exception:
        tip = ""
    if tip in ("cabinet", "servicii", "magazin"):
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
    """Mesaje libere (textarea Send) doar după ce owner a acceptat cererea de adopție."""
    if not user or not user.is_authenticated:
        return False
    return AdoptionRequest.objects.filter(
        animal=pet,
        adopter=user,
        status=AdoptionRequest.STATUS_ACCEPTED,
    ).exists()


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
    """După accept: owner primește date adoptator; adoptator primește date owner."""
    pet = ar.animal
    owner = pet.owner
    adopter = ar.adopter
    pet_label = (pet.name or f"Animal #{pet.pk}").strip()
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
        f"Aplicația EU-Adopt\n"
    )
    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", None) or "noreply@euadopt.ro"
    try:
        if owner.email:
            send_mail(sub_owner, body_owner, from_email, [owner.email], fail_silently=False)
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_accept_email_owner: %s", exc)
    try:
        if adopter.email:
            send_mail(sub_adopter, body_adopter, from_email, [adopter.email], fail_silently=False)
    except Exception as exc:
        logging.getLogger(__name__).exception("adoption_accept_email_adopter: %s", exc)


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


def home_view(request):
    if request.resolver_match.url_name == "pets_all" and request.GET.get("go"):
        try:
            pk = int(request.GET.get("go"))
            return redirect(reverse("pets_single", args=[pk]))
        except (ValueError, TypeError):
            pass
    if request.resolver_match.url_name == "pets_all":
        # PT (P2): filtre de căutare (judet / marime / varsta / sex) – active pe parametri GET.
        selected_judet = (request.GET.get("judet") or "").strip()
        selected_marime = (request.GET.get("marime") or "").strip()
        selected_varsta = (request.GET.get("varsta") or "").strip()
        selected_sex = (request.GET.get("sex") or "").strip()
        selected_species = (request.GET.get("species") or "").strip().lower()
        if selected_species not in {"dog", "cat", "other"}:
            selected_species = ""

        selected_traits = request.GET.getlist("traits")
        if len(selected_traits) == 1 and "," in selected_traits[0]:
            selected_traits = [t.strip() for t in selected_traits[0].split(",") if t.strip()]
        allowed_traits = {
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
        }
        selected_traits = [t for t in selected_traits if t in allowed_traits]

        filter_active = any([selected_judet, selected_marime, selected_varsta, selected_sex, selected_species]) or bool(selected_traits)

        # Filtre COMPLETE (pentru viitor): opțiuni din listă fixă, nu din DB,
        # ca să apară județele/taliile/vârstele/sexurile indiferent de ce e deja înregistrat.
        judet_choices = [
            "Alba",
            "Arad",
            "Argeș",
            "Bacău",
            "Bihor",
            "Bistrița-Năsăud",
            "Botoșani",
            "Brăila",
            "Brașov",
            "București",
            "Buzău",
            "Călărași",
            "Caraș-Severin",
            "Cluj",
            "Constanța",
            "Covasna",
            "Dâmbovița",
            "Dolj",
            "Galați",
            "Giurgiu",
            "Gorj",
            "Harghita",
            "Hunedoara",
            "Ialomița",
            "Iași",
            "Ilfov",
            "Maramureș",
            "Mehedinți",
            "Mureș",
            "Neamț",
            "Olt",
            "Prahova",
            "Sălaj",
            "Satu Mare",
            "Sibiu",
            "Suceava",
            "Teleorman",
            "Timiș",
            "Tulcea",
            "Vâlcea",
            "Vaslui",
            "Vrancea",
        ]
        marime_choices = ["mica", "medie", "mare"]
        varsta_choices = [
            "<1 an",
            "1 an",
            "2 ani",
            "3 ani",
            "4 ani",
            "5 ani",
            "6 ani",
            "7 ani",
            "8 ani",
            "9 ani",
            "10+ ani",
        ]
        sex_choices = ["m", "f"]

        qs_base = AnimalListing.objects.filter(is_published=True)

        # P2: câinii din DB (AnimalListing).
        # Dacă sunt filtre active, nu mai folosim fallback demo (ca să fie filtrarea "completă").
        p2_list = []
        if not filter_active:
            db_pets = list(qs_base.order_by("-created_at")[:200])
            if db_pets:
                for listing in db_pets:
                    p2_list.append({
                        "pk": listing.pk,
                        "nume": listing.name or "—",
                        "imagine": listing.photo_1,
                        "imagine_2": listing.photo_2,
                        "imagine_3": listing.photo_3,
                        "imagine_fallback": DEMO_DOG_IMAGE,
                        "traits": [],
                    })
            else:
                # fallback demo (doar când nu există filtre)
                for d in DEMO_DOGS:
                    p2_list.append({
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    })

            n = len(p2_list)
            need = (4 - n % 4) % 4  # completează ultimul rând la 4
            if need and p2_list:
                for i, d in enumerate(cycle(DEMO_DOGS)):
                    if i >= need:
                        break
                    p2_list.append({
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    })

            # Demo: ~10 rânduri în scroll (40 celule)
            if p2_list and len(p2_list) <= 12:
                extra = 40
                for i, d in enumerate(cycle(DEMO_DOGS)):
                    if i >= extra:
                        break
                    p2_list.append({
                        "pk": d["id"],
                        "nume": d["nume"],
                        "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                        "traits": (d.get("traits") or [])[:2],
                    })
        else:
            # Când filtrele sunt active: nu amestecăm DEMO_DOGS cu rezultate filtrate.
            qs = qs_base
            if selected_judet:
                qs = qs.filter(county__iexact=selected_judet)
            if selected_marime:
                qs = qs.filter(size__iexact=selected_marime)
            if selected_varsta:
                qs = qs.filter(age_label__iexact=selected_varsta)
            if selected_sex:
                qs = qs.filter(sex__iexact=selected_sex)
            if selected_species:
                qs = qs.filter(species__iexact=selected_species)

            db_candidates = list(qs.order_by("-created_at")[:200])
            if db_candidates:
                if selected_traits:
                    # Sortare: mai întâi câinii care bifează cele mai multe trăsături selectate,
                    # apoi restul în ordine descrescătoare.
                    scored = []
                    for listing in db_candidates:
                        match_count = 0
                        for tr in selected_traits:
                            if getattr(listing, tr, False):
                                match_count += 1
                        scored.append((listing, match_count))

                    scored.sort(key=lambda x: (x[1], x[0].created_at), reverse=True)
                    # Dacă există potriviri (>0), nu afișăm direct cei cu 0 decât dacă trebuie.
                    positive = [obj for obj, cnt in scored if cnt > 0]
                    ordered = positive if positive else [obj for obj, _ in scored]
                else:
                    ordered = db_candidates

                for listing in ordered:
                    p2_list.append({
                        "pk": listing.pk,
                        "nume": listing.name or "—",
                        "imagine": listing.photo_1,
                        "imagine_2": listing.photo_2,
                        "imagine_3": listing.photo_3,
                        "imagine_fallback": DEMO_DOG_IMAGE,
                        "traits": [],
                    })

            n = len(p2_list)
            need = (4 - n % 4) % 4
            if need and p2_list:
                snapshot = list(p2_list)
                for i, d in enumerate(cycle(snapshot)):
                    if i >= need:
                        break
                    p2_list.append(d)

            # păstrăm scrollul (dacă e destul de puțin, repetăm doar din rezultatele filtrate)
            if p2_list and len(p2_list) < 40:
                snapshot = list(p2_list)
                for d in cycle(snapshot):
                    if len(p2_list) >= 40:
                        break
                    p2_list.append(d)

        p2_pets = p2_list[:12]
        p2_pets_rest = p2_list[12:]
        # P1 și P3: benzi cu poze (aceleași imagini demo, repetate pentru strip)
        strip_pets = []
        for i, d in enumerate(cycle(DEMO_DOGS)):
            if i >= 20:
                break
            strip_pets.append({"imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE)})
        wishlist_ids = set()
        if request.user.is_authenticated:
            try:
                wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
            except Exception:
                pass
        return render(request, "anunturi/pt.html", {
            "p2_pets": p2_pets,
            "p2_pets_rest": p2_pets_rest,
            "strip_pets": strip_pets,
            "wishlist_ids": wishlist_ids,
            "judet_choices": judet_choices,
            "marime_choices": marime_choices,
            "varsta_choices": varsta_choices,
            "sex_choices": sex_choices,
            "selected_judet": selected_judet,
            "selected_marime": selected_marime,
            "selected_varsta": selected_varsta,
            "selected_sex": selected_sex,
            "selected_species": selected_species,
        })

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
    return render(request, "anunturi/home_v2.html", {
        "a2_pets": a2_pets,
        "a2_quote_pool": A2_QUOTE_POOL,
        "a2_compact": is_home,
        "left_sidebar_partners": [None, None, None],
        "right_sidebar_partners": [None, None, None],
        "hero_slider_images": hero_slider_images,
        "adopted_animals": 0,
        "active_animals": len(DEMO_DOGS),
        "show_welcome_demo": show_welcome_demo,
        "wishlist_ids": wishlist_ids,
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
                        subject="Resetare parolă – EU-Adopt",
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
    if User.objects.filter(email=email).exists():
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
    if User.objects.filter(email=email).exists():
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
        profile.collaborator_type = ""
        profile.save()
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
            subject="Verificare email – EU-Adopt",
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
            subject="Verificare email – EU-Adopt (retrimis)",
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


def signup_organizatie_view(request):
    """Formular înregistrare – Adăpost / ONG / Firmă. La POST: validează, salvează în sesiune, redirect SMS. La GET: prefill din sesiune dacă user a dat Back din SMS."""
    if request.method != "POST":
        ctx = {}
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
    elif User.objects.filter(email=email).exists():
        field_errors["email"] = "Acest email este deja folosit."
    if not denumire:
        field_errors["denumire"] = "Denumirea organizației este obligatorie."
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
            "accept_termeni": accept_termeni,
            "accept_gdpr": accept_gdpr,
            "email_opt_in": email_opt_in,
            "is_public_shelter": is_public_shelter if is_public_shelter_val in ("yes", "no") else None,
            "parola1": parola1, "parola2": parola2,
        }
        return _no_cache_response(render(request, "anunturi/signup_organizatie.html", {"field_errors": field_errors, "form_prefill": prefill}))

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
        ctx = {}
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
    tip_partener = (request.POST.get("tip_partener") or "").strip()
    parola1 = request.POST.get("parola1") or ""
    parola2 = request.POST.get("parola2") or ""
    accept_termeni = request.POST.get("accept_termeni_col") == "on"
    accept_gdpr = request.POST.get("accept_gdpr_col") == "on"
    email_opt_in = request.POST.get("email_opt_in_col") == "on"

    errors = []
    if tip_partener not in ("cabinet", "servicii", "magazin"):
        errors.append("Trebuie să alegi tipul de partener: Cabinet veterinar, Servicii sau Magazin.")
    if not email:
        errors.append("Email obligatoriu.")
    if User.objects.filter(email=email).exists():
        errors.append("Acest email este deja folosit.")
    if not denumire:
        errors.append("Denumirea este obligatorie.")
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
            "email": email,
            "telefon": telefon,
            "tip_partener": tip_partener if tip_partener in ("cabinet", "servicii", "magazin") else "",
            "accept_termeni": accept_termeni,
            "accept_gdpr": accept_gdpr,
            "email_opt_in": email_opt_in,
            "parola1": parola1, "parola2": parola2,
        }
        return render(request, "anunturi/signup_colaborator.html", {"signup_errors": errors, "form_prefill": prefill})

    request.session["signup_pending"] = {
        "role": "collaborator",
        "denumire": denumire,
        "denumire_societate": denumire_societate,
        "cui": cui,
        "cui_cu_ro": cui_cu_ro if cui_cu_ro in ("da", "nu") else "nu",
        "pers_contact": pers_contact,
        "email": email,
        "telefon": telefon.strip(),
        "judet": judet,
        "oras": oras,
        "password": parola1,
        "accept_termeni": accept_termeni,
        "accept_gdpr": accept_gdpr,
        "email_opt_in": email_opt_in,
    }
    return redirect(reverse("signup_verificare_sms"))


def _servicii_offers_for_kind(partner_kind: str, max_n: int = 24):
    """Oferte publice pentru S3/S5/S4 după partner_kind (snapshot la creare), nu după bifa curentă din profil."""
    try:
        base = CollaboratorServiceOffer.objects.filter(is_active=True, partner_kind=partner_kind)
        offers = list(
            _collab_offer_valid_public_qs(base)
            .select_related("collaborator")
            .order_by("-created_at")[:max_n]
        )
        pad = max(0, max_n - len(offers))
        return offers, [None] * pad
    except Exception:
        return [], [None] * max_n


def servicii_view(request):
    """Pagina Servicii – S1/S3 benzi ca PT, strip_pets pentru poze."""
    strip_pets = []
    for i, d in enumerate(cycle(DEMO_DOGS)):
        if i >= 20:
            break
        strip_pets.append({"imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE)})
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
    return render(
        request,
        "anunturi/servicii.html",
        {
            "strip_pets": strip_pets,
            "vet_offers": vet_offers,
            "vet_offer_empty_slots": vet_offer_empty_slots,
            "groom_offers": groom_offers,
            "groom_offer_empty_slots": groom_offer_empty_slots,
            "shop_offers": shop_offers,
            "shop_offer_empty_slots": shop_offer_empty_slots,
        },
    )


def transport_view(request):
    """Pagina Transport – wrapper TW, layout ca PW/SW."""
    return render(request, "anunturi/transport.html", {})


def custi_view(request):
    """Pagina cuștilor / harta cuștilor autocarului."""
    return render(request, "anunturi/custi.html", {})


def shop_view(request):
    """Pagina Shop (placeholder)."""
    return render(request, "anunturi/shop.html", {})


def shop_comanda_personalizate_view(request):
    """Pagina simplă de comandă produse personalizate (tricouri, șepci, zgărzi gravate etc.)."""
    return render(request, "anunturi/shop_comanda_personalizate.html", {})


def shop_magazin_foto_view(request):
    """Pagina magazin foto – cumpără poze de la ONG-uri."""
    return render(request, "anunturi/shop_magazin_foto.html", {})


def dog_profile_view(request, pk):
    """
    Fișa câinelui (PT) – afișează datele reale din AnimalListing.

    Layoutul din `pets-single.html` folosește un obiect `pet` cu câmpuri istorice
    (imagine, imagine_2, imagine_3, descriere etc.). Pentru lista MyPet / PT
    mapăm câmpurile din AnimalListing pe aceste nume, fără să schimbăm șablonul.
    """
    from django.shortcuts import get_object_or_404

    listing = get_object_or_404(AnimalListing, pk=pk, is_published=True)

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
    }

    adoption_request_status = None
    adopter_messaging_unlocked = False
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
        if last_ar and last_ar.status == AdoptionRequest.STATUS_ACCEPTED:
            adopter_messaging_unlocked = True

    ctx = {
        "pet": pet,
        "can_send_pet_message": bool(request.user.is_authenticated and request.user.pk != listing.owner_id),
        "pet_owner_id": listing.owner_id,
        "adoption_request_status": adoption_request_status,
        "adopter_messaging_unlocked": adopter_messaging_unlocked,
    }
    return render(request, "anunturi/pets-single.html", ctx)


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


@login_required
def admin_analysis_home_view(request):
    """Pagina centrală Analiză (doar pentru admin/staff)."""
    if not (request.user.is_superuser or request.user.is_staff):
        return redirect(reverse("home"))
    view_as_role = request.session.get("view_as_role") or None
    view_as_collab_tip = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
    if view_as_collab_tip not in ("cabinet", "servicii", "magazin"):
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
            if tip in ("cabinet", "servicii", "magazin"):
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
        if not company_cui:
            errors.append("CUI/CIF este obligatoriu.")
        if not company_judet:
            errors.append("Județul firmei este obligatoriu.")
        if not company_oras:
            errors.append("Orașul/localitatea firmei este obligatorie.")
        if account_profile.role == AccountProfile.ROLE_COLLAB:
            if collaborator_type not in ("cabinet", "servicii", "magazin"):
                errors.append("Tipul de colaborator trebuie să fie Cabinet, Servicii sau Magazin.")
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
    if User.objects.filter(email__iexact=email).exclude(pk=user.pk).exists():
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
            send_mail(subject="Confirmă noul email – EU-Adopt", message=plain, from_email=None, recipient_list=[email], fail_silently=False, html_message=html)
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
            send_mail(subject="Confirmă noul email – EU-Adopt", message=plain, from_email=None, recipient_list=[data["email"]], fail_silently=False, html_message=html)
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
        full_phone = f"{data.get('phone_country', '')} {data.get('phone', '')}".strip()
        profile.phone = full_phone
        profile.judet = data.get("judet", "")
        profile.oras = data.get("oras", "")
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in_wishlist", False)
        profile.save()
    else:
        user.email = new_email
        user.save(update_fields=["email"])
    request.session.pop("edit_pending", None)
    return redirect(reverse("account") + "?updated=1")


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
    if pet_ids:
        for ar in AdoptionRequest.objects.filter(
            animal_id__in=pet_ids,
            status=AdoptionRequest.STATUS_ACCEPTED,
        ).order_by("-accepted_at", "-pk"):
            aid = int(ar.animal_id)
            if aid not in accepted_map:
                accepted_map[aid] = ar.pk
    for p in pets:
        if p is None:
            continue
        parts = []
        npc = pending_counts.get(p.pk, 0)
        if npc:
            parts.append(f"Așteptare ({npc})")
        if p.pk in accepted_map:
            parts.append("Adopție acceptată")
        p.adoption_row_label = " · ".join(parts) if parts else "—"
        p.adoption_finalize_id = accepted_map.get(p.pk)
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
    })


@login_required
@collab_magazin_required
def magazinul_meu_view(request):
    """
    Ruta /magazinul-meu/ redirecționează către pagina de control oferte (prima pagină colaborator).
    Păstrăm URL-ul pentru compatibilitate; query-urile (ex. open_messages, tip_updated) se propagă.
    """
    target = reverse("collab_offers_control")
    if request.GET:
        target += "?" + request.GET.urlencode()
    return redirect(target)


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

    age_choices = [
        "<1 an",
        "1 an",
        "2 ani",
        "3 ani",
        "4 ani",
        "5 ani",
        "6 ani",
        "7 ani",
        "8 ani",
        "9 ani",
        "10+ ani",
    ]

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        species = (request.POST.get("species") or "dog").strip() or "dog"
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
        # Trăsături (checkboxes: prezente în POST când sunt bifate)
        def trait(name):
            return name in request.POST
        error = None
        # Toate câmpurile sunt obligatorii (în afară de bifele de potrivire adoptator)
        required = [
            ("name", name, "Te rugăm să completezi numele câinelui."),
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
        return render(request, "anunturi/mypet_add.html", ctx)

    ctx = {
        "error": None,
        "name": "",
        "species": "dog",
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
    return render(request, "anunturi/mypet_add.html", ctx)


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

    age_choices = [
        "<1 an", "1 an", "2 ani", "3 ani", "4 ani", "5 ani",
        "6 ani", "7 ani", "8 ani", "9 ani", "10+ ani",
    ]

    if request.method == "POST":
        name = (request.POST.get("name") or "").strip()
        species = (request.POST.get("species") or "dog").strip() or "dog"
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

        def trait(name):
            return name in request.POST

        error = None
        required = [
            ("name", name, "Te rugăm să completezi numele câinelui."),
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
            "error": error,
            "name": name,
            "species": species,
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
        return render(request, "anunturi/mypet_add.html", ctx)

    ctx = {
        "listing": listing,
        "error": None,
        "name": listing.name or "",
        "species": listing.species or "dog",
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
    return render(request, "anunturi/mypet_add.html", ctx)


def i_love_view(request):
    """Pagina I Love: câinii pe care userul i-a marcat cu inimioară."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('i_love')}")

    ids = list(WishlistItem.objects.filter(user=request.user).order_by("-created_at").values_list("animal_id", flat=True))
    by_id = {d["id"]: d for d in DEMO_DOGS}
    pets = []
    for animal_id in ids:
        d = by_id.get(animal_id)
        if d:
            pets.append({
                "pk": d["id"],
                "nume": d["nume"],
                "varsta": d.get("varsta", ""),
                "descriere": d.get("descriere", ""),
                "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
            })
    return render(request, "anunturi/i_love.html", {"pets": pets, "wishlist_ids": set(ids)})


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
                "error": "Mesajele libere sunt disponibile după ce organizația acceptă cererea de adopție (butonul „VREAU SA-L ADOPT”).",
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
    # Necitite primele, apoi celelalte; ordinea inițială (-last_at) rămâne în fiecare grup.
    out.sort(key=lambda x: 0 if int(x.get("unread_count") or 0) > 0 else 1)
    return JsonResponse({"ok": True, "threads": out, "scope": scope})


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
    collab_client_unread = (
        CollabServiceMessage.objects.filter(
            receiver=user, is_read=False, created_at__gte=active_since
        )
        .exclude(collaborator=user)
        .count()
    )
    adoption_payload = None
    ar = (
        AdoptionRequest.objects.filter(animal=pet, adopter_id=sender_id)
        .order_by("-created_at")
        .first()
    )
    if ar:
        adoption_payload = {
            "id": ar.id,
            "status": ar.status,
            "can_accept": ar.status == AdoptionRequest.STATUS_PENDING,
            "can_reject": ar.status == AdoptionRequest.STATUS_PENDING,
        }
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "unread_total": unread_total,
            "navbar_unread_total": unread_total + collab_client_unread,
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
    return JsonResponse({"ok": True})


@login_required
def adopter_messages_list_view(request):
    """
    Lista conversațiilor pentru adoptator (grupare pe animal).
    """
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
    # Necitite primele, apoi celelalte; ordinea inițială (-last_at) rămâne în fiecare grup.
    out.sort(key=lambda x: 0 if int(x.get("unread_count") or 0) > 0 else 1)
    return JsonResponse({"ok": True, "threads": out, "scope": scope})


@login_required
def adopter_messages_thread_view(request, pk: int):
    """
    Thread adoptator <-> owner pentru un animal.
    """
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
    collab_client_unread = (
        CollabServiceMessage.objects.filter(
            receiver=user, is_read=False, created_at__gte=active_since
        )
        .exclude(collaborator=user)
        .count()
    )
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "animal_name": pet.name or "",
            "unread_total": unread_total,
            "navbar_unread_total": unread_total + collab_client_unread,
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
                "error": "Poți trimite mesaje după acceptarea cererii de adopție de către organizație.",
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
    return JsonResponse({"ok": True})


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
            }
        )
    out.sort(key=lambda x: 0 if int(x.get("unread_count") or 0) > 0 else 1)
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
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "context_label": _collab_context_label(ct),
            "unread_total": unread_total,
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
            }
        )
    out.sort(key=lambda x: 0 if int(x.get("unread_count") or 0) > 0 else 1)
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
    pet_unread = PetMessage.objects.filter(
        receiver=user, is_read=False, created_at__gte=active_since
    ).count()
    return JsonResponse(
        {
            "ok": True,
            "messages": items,
            "context_label": _collab_context_label(ct),
            "unread_total": collab_client_unread,
            "navbar_unread_total": pet_unread + collab_client_unread,
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
            return JsonResponse({"ok": True, "already": "pending"})
        if last.status == AdoptionRequest.STATUS_ACCEPTED:
            return JsonResponse({"ok": True, "already": "accepted"})
        if last.status == AdoptionRequest.STATUS_FINALIZED:
            return JsonResponse({"ok": False, "error": "Adopția pentru acest animal este deja finalizată."}, status=400)

    body = (
        "Am trimis o cerere de adopție pentru acest animal prin EU-Adopt. "
        "Datele mele de contact îți vor fi disponibile după ce accepți cererea în MyPet → Mesaje."
    )
    with transaction.atomic():
        AdoptionRequest.objects.create(
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
    return JsonResponse({"ok": True})


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
    if ad_req.status != AdoptionRequest.STATUS_PENDING:
        return JsonResponse({"ok": False, "error": "Cererea nu mai poate fi acceptată."}, status=400)
    if AdoptionRequest.objects.filter(
        animal=ad_req.animal,
        status=AdoptionRequest.STATUS_ACCEPTED,
    ).exists():
        return JsonResponse(
            {
                "ok": False,
                "error": "Există deja o adopție acceptată pentru acest animal. Finalizează sau rezolvă mai întâi situația curentă.",
            },
            status=400,
        )
    with transaction.atomic():
        AdoptionRequest.objects.filter(
            animal=ad_req.animal,
            status=AdoptionRequest.STATUS_PENDING,
        ).exclude(pk=ad_req.pk).update(status=AdoptionRequest.STATUS_REJECTED)
        ad_req.status = AdoptionRequest.STATUS_ACCEPTED
        ad_req.accepted_at = timezone.now()
        ad_req.save(update_fields=["status", "accepted_at", "updated_at"])
    _send_adoption_accept_emails(ad_req)
    PetMessage.objects.create(
        animal=ad_req.animal,
        sender=request.user,
        receiver=ad_req.adopter,
        body=(
            "Am acceptat cererea ta de adopție. Datele de contact au fost trimise pe email; "
            "poți folosi și această conversație pentru detalii suplimentare."
        ),
        is_read=False,
    )
    return JsonResponse({"ok": True})


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
    if ad_req.status != AdoptionRequest.STATUS_PENDING:
        return JsonResponse({"ok": False, "error": "Cererea nu mai poate fi respinsă."}, status=400)
    ad_req.status = AdoptionRequest.STATUS_REJECTED
    ad_req.save(update_fields=["status", "updated_at"])
    PetMessage.objects.create(
        animal=ad_req.animal,
        sender=request.user,
        receiver=ad_req.adopter,
        body="Cererea de adopție nu a fost acceptată. Îți mulțumim pentru interes.",
        is_read=False,
    )
    return JsonResponse({"ok": True})


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
    with transaction.atomic():
        ar.status = AdoptionRequest.STATUS_FINALIZED
        ar.save(update_fields=["status", "updated_at"])
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
        pet.is_published = False
        pet.save(update_fields=["is_published", "updated_at"])
    return JsonResponse({"ok": True})


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


def _cabinet_block_for_buyer_email(collab_user) -> str:
    """Text pentru cumpărător: cabinet, telefon, persoană contact, email."""
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
    return "\n".join(lines)


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
    offer = get_object_or_404(
        CollaboratorServiceOffer, pk=pk, collaborator=request.user, partner_kind=tip
    )
    offer.delete()
    messages.success(request, "Oferta a fost ștearsă.")
    return redirect("collab_offers_control")


@login_required
@collab_magazin_required
def collab_offers_control_view(request):
    tip = _collaborator_tip_partener(request)
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
            "tf_species_dog": True,
            "tf_species_cat": True,
            "tf_species_other": True,
        },
    )


@login_required
@collab_magazin_required
@require_http_methods(["GET", "POST"])
def collab_offer_edit_view(request, pk: int):
    tip = _collaborator_tip_partener(request)
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


def public_offers_list_view(request):
    offers = list(
        _collab_offer_valid_public_qs(
            CollaboratorServiceOffer.objects.filter(is_active=True).select_related("collaborator")
        ).order_by("-created_at")[:200]
    )
    return render(
        request,
        "anunturi/oferte_parteneri.html",
        {"offers": offers},
    )


def public_offer_detail_view(request, pk: int):
    offer = get_object_or_404(
        _collab_offer_valid_public_qs(
            CollaboratorServiceOffer.objects.filter(is_active=True).select_related("collaborator")
        ),
        pk=pk,
    )
    return render(
        request,
        "anunturi/oferta_partener_detail.html",
        {"offer": offer},
    )


@require_POST
@csrf_protect
def public_offer_request_view(request, pk: int):
    post_name = (request.POST.get("name") or "").strip()
    post_email = (request.POST.get("email") or "").strip()
    buyer = _buyer_snapshot_for_offer_request(request, post_name, post_email)
    dest_email = buyer["email"]
    if not dest_email:
        messages.error(
            request,
            "Introdu adresa de email ca să primești confirmarea și datele cabinetului.",
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

    mail_errors = []
    try:
        send_mail(buyer_subject, buyer_body, None, [dest_email], fail_silently=False)
    except Exception:
        logging.exception("send_mail buyer offer claim")
        mail_errors.append("cumpărător")
    try:
        send_mail(collab_subject, collab_body, None, [collab_mail], fail_silently=False)
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