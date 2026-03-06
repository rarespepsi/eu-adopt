from django.shortcuts import render, get_object_or_404, redirect
from django.http import JsonResponse, HttpResponse, HttpResponseForbidden, HttpResponseRedirect
from django.urls import reverse
from django.utils.http import urlencode
from urllib.parse import quote
from django.templatetags.static import static
from django.core.paginator import Paginator
from django.conf import settings
from django.contrib import messages
from django.contrib.auth import login, logout, get_user_model
from django.contrib.auth.decorators import login_required, user_passes_test
from django.contrib.auth.models import Group
from django.views.generic import TemplateView
from django.contrib.auth.views import LoginView as AuthLoginView
from django.utils.text import slugify
from datetime import datetime, date, timedelta
from django.utils import timezone

# Backend folosit la login() după înregistrare (când există mai multe AUTHENTICATION_BACKENDS)
def _auth_backend_for_login():
    return settings.AUTHENTICATION_BACKENDS[0]

from django.db.models import Q, Exists, OuterRef
from django.core.exceptions import ValidationError
from .models import (
    JUDET_CHOICES,
    Pet,
    PetFavorite,
    AdoptionRequest,
    Profile,
    UserProfile,
    OngProfile,
    ACTIVE_DUPLICATE_CHECK_STATUSES,
    REZERVAT_STATUS,
    APPROVED_RESERVATION_STATUSES,
    BLOCK_DUPLICATE_REQUEST_STATUSES,
    BeneficiaryPartner,
    CouponClaim,
    BENEFICIARY_CATEGORY_VET,
    BENEFICIARY_CATEGORY_GROOMING,
    BENEFICIARY_CATEGORY_SHOP,
)
from .forms import (
    AdoptionRequestForm,
    UserRegistrationForm,
    UserProfileForm,
    OrgRequiredPage2Form,
    RegisterPFForm,
    RegisterSRLForm,
    RegisterONGForm,
    PetAdaugaForm,
    PET_ADAUGA_SECTIONS,
    MatchQuizForm,
)
from accounts.models import UserMatchProfile
from .match_utils import compute_matches
from .adoption_platform import (
    platform_validation_passes,
    send_adoption_request_to_ong,
    send_adoption_request_confirmation_to_adoptor,
    run_validation_link,
    send_adoption_finalized_email,
    send_adoption_finalized_notice_to_owner,
    approve_first_adoption_request,
    accept_adoption_request_by_owner,
)
from .contest_service import get_active_contest, get_contest_leaderboard, get_remaining_days
from .welcome_email import send_welcome_email
from .beneficiary_emails import send_coupon_claim_email_to_partner, send_coupon_confirmation_to_adoptor


SESSION_KEY_MATCH_QUIZ_DRAFT = "match_quiz_draft"


class LoginViewRedirectVerify(AuthLoginView):
    """
    Login: după succes mergem la URL-ul „next” sau la home (LOGIN_REDIRECT_URL).
    Dacă în sesiune există match_quiz_draft (chestionar completat de nelogat), redirect la /match/results/
    pentru salvare automată și afișare potriviri.
    """

    def get_success_url(self):
        if self.request.session.get(SESSION_KEY_MATCH_QUIZ_DRAFT):
            return reverse("match_results")
        return super().get_success_url()


def logout_view(request):
    """Deconectare (acceptă GET ca link din meniu) și redirect la Acasă ca vizitator."""
    logout(request)
    response = HttpResponseRedirect(reverse("home"))
    response["Cache-Control"] = "no-store, no-cache, must-revalidate, max-age=0"
    response["Pragma"] = "no-cache"
    return response


def user_phone_verified(user):
    """True dacă userul are telefon verificat (UserProfile.phone_verified). Folosit pentru PF și org (SRL/ONG).
    Excepție: userul „adrian” (cont admin/probă) este considerat verificat."""
    if not user or not user.is_authenticated:
        return False
    if getattr(user, "username", None) == "adrian":
        return True
    up = getattr(user, "user_profile", None)
    return getattr(up, "phone_verified", False) if up else False


def require_phone_verified(view_func):
    """Decorator: dacă user autentificat dar fără phone_verified, redirect la verificare telefon cu mesaj."""
    from functools import wraps
    @wraps(view_func)
    def _wrapped(request, *args, **kwargs):
        if not request.user.is_authenticated:
            return view_func(request, *args, **kwargs)
        if not user_phone_verified(request.user):
            messages.warning(
                request,
                "Trebuie să vă verificați numărul de telefon înainte de a folosi această funcție. "
                "Verificați telefonul acum.",
            )
            verify_url = reverse("signup_verificare_telefon")
            next_path = request.get_full_path()
            if next_path and next_path.startswith("/") and "//" not in next_path.split("/")[:2]:
                from urllib.parse import urlencode
                verify_url += "?" + urlencode({"next": next_path})
            return redirect(verify_url)
        return view_func(request, *args, **kwargs)
    return _wrapped


def _get_contact_for_pet_from_user(user):
    """Returnează dict cu judet, ong_email, ong_address, ong_contact_person, ong_phone, ong_visiting_hours din fișa ONG sau profil PF."""
    out = {
        "judet": "",
        "ong_email": "",
        "ong_address": "",
        "ong_contact_person": "",
        "ong_phone": "",
        "ong_visiting_hours": "",
    }
    if not user or not user.is_authenticated:
        return out
    # ONG / SRL
    try:
        op = user.ong_profile
        out["judet"] = (getattr(op, "judet", "") or "").strip()
        out["ong_email"] = (getattr(op, "email", None) or user.email or "").strip()
        out["ong_address"] = (getattr(op, "oras", "") or "").strip()
        out["ong_contact_person"] = (
            getattr(op, "persoana_responsabila_adoptii", "") or getattr(op, "reprezentant_legal", "") or ""
        ).strip()
        out["ong_phone"] = (getattr(op, "telefon", "") or "").strip()
        return out
    except (OngProfile.DoesNotExist, AttributeError):
        pass
    # Persoană fizică: UserProfile
    try:
        up = user.user_profile
        out["judet"] = (getattr(up, "judet", "") or "").strip()
        out["ong_email"] = (getattr(up, "email", None) or user.email or "").strip()
        out["ong_address"] = (getattr(up, "oras", "") or "").strip()
        nume = (getattr(up, "nume", "") or "").strip()
        prenume = (getattr(up, "prenume", "") or "").strip()
        out["ong_contact_person"] = f"{nume} {prenume}".strip() or user.get_full_name() or ""
        out["ong_phone"] = (getattr(up, "telefon", "") or "").strip()
        return out
    except (UserProfile.DoesNotExist, AttributeError):
        pass
    out["ong_email"] = (user.email or "").strip()
    return out


def _get_adoption_form_initial(user):
    """Completează date pentru formularul de adopție din profilul membrului. Motivația (mesaj) rămâne goală."""
    if not user or not user.is_authenticated:
        return {}
    initial = {}
    # Persoană fizică: UserProfile
    try:
        up = user.user_profile
        nume = (getattr(up, "nume", "") or "").strip()
        prenume = (getattr(up, "prenume", "") or "").strip()
        initial["nume_complet"] = f"{nume} {prenume}".strip() or user.get_full_name() or ""
        initial["email"] = getattr(up, "email", None) or user.email or ""
        initial["telefon"] = getattr(up, "telefon", "") or ""
        oras = getattr(up, "oras", "") or ""
        initial["adresa"] = oras
    except (UserProfile.DoesNotExist, AttributeError):
        up = None
    # ONG / organizație: OngProfile
    if not initial.get("nume_complet") or not initial.get("email") or not initial.get("telefon"):
        try:
            op = user.ong_profile
            if not initial.get("nume_complet"):
                initial["nume_complet"] = (
                    getattr(op, "persoana_responsabila_adoptii", "") or
                    getattr(op, "reprezentant_legal", "") or
                    getattr(op, "denumire_legala", "") or
                    user.get_full_name() or ""
                ).strip()
            if not initial.get("email"):
                initial["email"] = getattr(op, "email", None) or user.email or ""
            if not initial.get("telefon"):
                initial["telefon"] = getattr(op, "telefon", "") or ""
            if not initial.get("adresa"):
                o = getattr(op, "oras", "") or ""
                j = getattr(op, "judet", "") or ""
                initial["adresa"] = ", ".join(filter(None, [o, j]))
        except (OngProfile.DoesNotExist, AttributeError):
            pass
    # Fallback: User + Profile
    if not initial.get("nume_complet"):
        initial["nume_complet"] = user.get_full_name() or ""
    if not initial.get("email"):
        initial["email"] = user.email or ""
    if not initial.get("telefon") and hasattr(user, "profile"):
        try:
            initial["telefon"] = getattr(user.profile, "phone", "") or ""
        except (Profile.DoesNotExist, AttributeError):
            pass
    # Motivația nu se completează automat – o completează adoptatorul
    return initial


def home(request):
    # Contori pentru navbar A0 și mission bar
    active_animals = Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").count()
    active_dogs_count = Pet.objects.filter(status="adoptable", tip="dog").exclude(adoption_status="adopted").count()
    adopted_animals = Pet.objects.filter(status="adopted").count()
    
    # A3 - Animals of the Month (4x2 grid = 8 animale)
    featured = list(Pet.objects.filter(featured=True, status="adoptable").exclude(adoption_status="adopted")[:8])
    # Completăm până la 8 dacă sunt mai puține
    if len(featured) < 8:
        ids = {p.pk for p in featured}
        available = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").exclude(pk__in=ids).order_by("-data_adaugare"))
        import itertools
        if available:
            for p in itertools.islice(itertools.cycle(available), 8 - len(featured)):
                featured.append(p)
        elif featured:
            for p in itertools.islice(itertools.cycle(featured), 8 - len(featured)):
                featured.append(p)
    
    # A4 - New Entries grid (7 columns, unlimited rows)
    # Algorithm: Build complete rows only, mix fillers naturally
    import itertools
    
    # 1. Build primary list: ACTIVE animals (unique, newest first)
    active_list = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare"))
    active_ids = {p.pk for p in active_list}
    
    # 2. Build filler pools (can repeat across sessions but not adjacent)
    processing_pool = [p for p in Pet.objects.filter(status="pending").order_by("-data_adaugare") if p.pk not in active_ids]
    adopted_pool = [p for p in Pet.objects.filter(status="adopted").order_by("-data_adaugare") if p.pk not in active_ids]
    showcase_pool = [p for p in Pet.objects.filter(status="showcase_archive").order_by("-data_adaugare") if p.pk not in active_ids]
    
    # 3. Build rows: each row must be FULL (7 items) or not exist
    new_entries = []
    used_ids = set()
    active_index = 0
    
    def get_filler_from_pool(pool, avoid_pet_id=None):
        """Get next filler from pool, prefer unused, avoid specific pet if needed"""
        if not pool:
            return None
        
        # Try unused first
        for pet in pool:
            if pet.pk not in used_ids and pet.pk != avoid_pet_id:
                return pet
        
        # Allow reuse if needed (but avoid same pet as last)
        for pet in pool:
            if pet.pk != avoid_pet_id:
                return pet
        
        return None
    
    # Build complete rows
    while active_index < len(active_list):
        row = []
        row_processing_count = 0
        last_filler_pet_id = None
        
        # Fill row with active animals first
        while len(row) < 7 and active_index < len(active_list):
            pet = active_list[active_index]
            if pet.pk not in used_ids:
                row.append(pet)
                used_ids.add(pet.pk)
            active_index += 1
        
        # If row is incomplete, fill with mix strategy
        if len(row) < 7:
            needed = 7 - len(row)
            
            # Determine mix pattern based on row composition
            # If only 1 active item, use balanced mix (not all processing)
            if len(row) == 1:
                # Balanced mix: processing, adopted, showcase, processing, adopted, showcase
                mix_pattern = ['processing', 'adopted', 'showcase', 'processing', 'adopted', 'showcase']
            else:
                # Normal mix with max 2 processing per row
                mix_pattern = ['processing', 'adopted', 'showcase', 'adopted', 'showcase', 'processing']
            
            # Fill remaining slots
            for slot_idx in range(needed):
                # Get desired type from mix pattern
                pattern_idx = slot_idx % len(mix_pattern)
                desired_type = mix_pattern[pattern_idx]
                
                # Avoid adjacent duplicates (skip if same type as last filler)
                if last_filler_pet_id:
                    last_pet = next((p for p in row if p.pk == last_filler_pet_id), None)
                    if last_pet:
                        last_type = last_pet.status
                        if (desired_type == 'processing' and last_type == 'pending') or \
                           (desired_type == 'adopted' and last_type == 'adopted') or \
                           (desired_type == 'showcase' and last_type == 'showcase_archive'):
                            # Try next type in pattern
                            pattern_idx = (pattern_idx + 1) % len(mix_pattern)
                            desired_type = mix_pattern[pattern_idx]
                
                # Check processing limit (max 2 per row)
                if desired_type == 'processing' and row_processing_count >= 2:
                    # Try other types
                    for alt_type in ['adopted', 'showcase']:
                        if alt_type in mix_pattern:
                            desired_type = alt_type
                            break
                    if desired_type == 'processing':
                        # Can't add more processing, try other types
                        for alt_type in ['adopted', 'showcase']:
                            pet = get_filler_from_pool(
                                adopted_pool if alt_type == 'adopted' else showcase_pool,
                                last_filler_pet_id
                            )
                            if pet:
                                row.append(pet)
                                used_ids.add(pet.pk)
                                last_filler_pet_id = pet.pk
                                break
                        else:
                            # No fillers available, stop filling this row
                            break
                        continue
                
                # Get filler item
                pool = None
                if desired_type == 'processing':
                    pool = processing_pool
                elif desired_type == 'adopted':
                    pool = adopted_pool
                elif desired_type == 'showcase':
                    pool = showcase_pool
                
                pet = get_filler_from_pool(pool, last_filler_pet_id)
                
                if pet:
                    row.append(pet)
                    used_ids.add(pet.pk)
                    last_filler_pet_id = pet.pk
                    if desired_type == 'processing':
                        row_processing_count += 1
                else:
                    # Try any available filler type as fallback
                    for fallback_type in ['adopted', 'showcase', 'processing']:
                        fallback_pool = None
                        if fallback_type == 'processing':
                            fallback_pool = processing_pool
                        elif fallback_type == 'adopted':
                            fallback_pool = adopted_pool
                        elif fallback_type == 'showcase':
                            fallback_pool = showcase_pool
                        
                        if fallback_pool:
                            pet = get_filler_from_pool(fallback_pool, last_filler_pet_id)
                            if pet:
                                row.append(pet)
                                used_ids.add(pet.pk)
                                last_filler_pet_id = pet.pk
                                if fallback_type == 'processing':
                                    row_processing_count += 1
                                break
                    else:
                        # No fillers available, stop filling this row
                        break
            
            # Only add row if it's complete (7 items)
            if len(row) == 7:
                new_entries.extend(row)
            else:
                # Incomplete row, stop building
                break
        else:
            # Row is complete with active animals only
            new_entries.extend(row)
    
    # A1 - Moving animal strip + hero slider (3–4 poze fundal)
    strip_pets = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:40])
    if strip_pets and len(strip_pets) < 12:
        import itertools
        strip_pets = list(itertools.islice(itertools.cycle(strip_pets), 24))
    hero_slider_pets = strip_pets[:4]  # A1 – 3–4 poze care se schimbă la câteva secunde, siglele peste

    # A2 (16) + col stânga (3) + col dreapta (3) = 22 poze câini în casete
    import itertools as it
    pool_ids = {p.pk for p in featured}
    slot_pool = list(featured)
    for p in strip_pets:
        if p.pk not in pool_ids and len(slot_pool) < 22:
            slot_pool.append(p)
            pool_ids.add(p.pk)
    if len(slot_pool) < 22 and slot_pool:
        slot_pool = list(it.islice(it.cycle(slot_pool), 22))
    a2_pets = slot_pool[:16]
    left_col_pets = slot_pool[16:19]
    right_col_pets = slot_pool[19:22]
    # Pad cu None dacă nu avem suficiente (template afișează fallback)
    while len(a2_pets) < 16:
        a2_pets.append(None)
    while len(left_col_pets) < 3:
        left_col_pets.append(None)
    while len(right_col_pets) < 3:
        right_col_pets.append(None)

    # A5 / A6 – parteneri (magazine, cabinete veterinar etc.) – logo-uri care se încadrează în casetă
    sidebar_partners = list(
        BeneficiaryPartner.objects.filter(is_active=True)
        .order_by("category", "order", "name")[:6]
    )
    left_sidebar_partners = sidebar_partners[:3]
    right_sidebar_partners = sidebar_partners[3:6]
    while len(left_sidebar_partners) < 3:
        left_sidebar_partners.append(None)
    while len(right_sidebar_partners) < 3:
        right_sidebar_partners.append(None)

    # Date concurs
    contest = get_active_contest()
    remaining_days = get_remaining_days(contest) if contest else 0
    top_users = get_contest_leaderboard(limit=10, contest=contest) if contest else []

    return render(request, "anunturi/home_v2.html", {
        "active_animals": active_animals,
        "active_dogs_count": active_dogs_count,
        "adopted_animals": adopted_animals,
        "featured_pets": featured[:8],  # A3 - Animals of the Month (4x2)
        "new_entries": new_entries,  # A4 - New Entries grid
        "strip_pets": strip_pets,  # A1 - Moving strip
        "hero_slider_pets": hero_slider_pets,
        "a2_pets": a2_pets,
        "left_col_pets": left_col_pets,
        "right_col_pets": right_col_pets,
        "left_sidebar_partners": left_sidebar_partners,
        "right_sidebar_partners": right_sidebar_partners,
        "contest": contest,
        "remaining_days": remaining_days,
        "top_users": top_users,
        "a2_slots": range(16),  # A2 – 4×4
    })


User = get_user_model()


def site_search_view(request):
    """Căutare în site: nume animal, nume societate/adăpost, nume colaborator. Parametru GET: s."""
    q = (request.GET.get("s") or request.GET.get("q") or "").strip()
    pets = []
    orgs = []
    collaborators = []
    if q:
        q_lower = q.lower()
        # Animale (nume) – exclude showcase_archive
        pets = list(
            Pet.objects.exclude(status="showcase_archive")
            .filter(nume__icontains=q)
            .order_by("-data_adaugare")[:30]
        )
        # Societăți / adăposturi (OngProfile: denumire, contact)
        orgs = list(
            OngProfile.objects.filter(
                Q(denumire_legala__icontains=q)
                | Q(persoana_responsabila_adoptii__icontains=q)
                | Q(reprezentant_legal__icontains=q)
            ).distinct()[:20]
        )
        # Colaboratori (User în grupul Colaborator)
        try:
            colaborator_group = Group.objects.get(name="Colaborator")
            collaborators = list(
                User.objects.filter(groups=colaborator_group)
                .filter(
                    Q(username__icontains=q)
                    | Q(first_name__icontains=q)
                    | Q(last_name__icontains=q)
                )
                .distinct()[:20]
            )
        except Group.DoesNotExist:
            pass
    return render(
        request,
        "anunturi/cauta.html",
        {
            "query": q,
            "pets": pets,
            "orgs": orgs,
            "collaborators": collaborators,
        },
    )


PETS_PER_PAGE = 12


SESSION_KEY_PETS_ALL_FILTERS = "pets_all_filters"


def pets_all(request):
    # Reset explicit: șterge filtrele salvate în sesiune și redirect fără parametri
    if request.GET.get("reset") == "1":
        if SESSION_KEY_PETS_ALL_FILTERS in request.session:
            del request.session[SESSION_KEY_PETS_ALL_FILTERS]
        return HttpResponseRedirect(reverse("pets_all"))

    # Filtre din formular: tip, sex, marime, judet, varsta – persistate în sesiune
    filter_keys = ("tip", "sex", "marime", "judet", "varsta")
    from_get = {}
    for k in filter_keys:
        v = (request.GET.get(k) or "").strip() or None
        if v is not None:
            from_get[k] = v

    if from_get:
        request.session[SESSION_KEY_PETS_ALL_FILTERS] = from_get
        effective = from_get
    else:
        effective = request.session.get(SESSION_KEY_PETS_ALL_FILTERS) or {}

    tip = effective.get("tip")
    sex = effective.get("sex") or ""
    marime = effective.get("marime") or ""
    judet = (effective.get("judet") or "").strip().lower()
    varsta = effective.get("varsta") or ""

    # Annotare has_active_requests și is_reserved pentru badge-uri fără N+1
    has_active = AdoptionRequest.objects.filter(
        pet_id=OuterRef("pk"), status__in=ACTIVE_DUPLICATE_CHECK_STATUSES
    )
    has_rezervat = AdoptionRequest.objects.filter(
        pet_id=OuterRef("pk"), status=REZERVAT_STATUS
    )
    qs = Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").annotate(
        has_active_requests=Exists(has_active),
        is_reserved=Exists(has_rezervat),
    ).order_by("-data_adaugare")
    if tip in ("dog", "cat", "other"):
        qs = qs.filter(tip=tip)
    vip = request.GET.get("vip")
    if vip == "1":
        qs = qs.filter(featured=True)
    if sex in ("male", "female"):
        qs = qs.filter(sex=sex)
    if marime in ("small", "medium", "large", "xlarge"):
        qs = qs.filter(marime=marime)
    if judet:
        qs = qs.filter(judet=judet)
    if varsta.isdigit():
        v = int(varsta)
        if 0 <= v <= 16:
            qs = qs.filter(varsta_aproximativa=v)
    # Filtre din Matching (Găsește-mi prietenul ideal) – doar din GET, nu se salvează în sesiune
    tags_copii = request.GET.get("tags_copii")
    if tags_copii == "1":
        qs = qs.filter(Q(tags__icontains="copii") | Q(tags__icontains="kids") | Q(tags__icontains="children"))
    locuinta = request.GET.get("locuinta")
    if locuinta == "apartament":
        qs = qs.filter(marime__in=["small", "medium"])
    elif locuinta == "curte":
        qs = qs.filter(marime__in=["medium", "large", "xlarge"])
    # Listă random pentru P2: până la 16 căsuțe (4x4), din toată lista filtrată (nu doar pagina curentă).
    # Dacă sunt mai puține animale, le repetăm ciclic ca să umplem toate cele 16 sloturi.
    pets_for_p2 = []
    qs_for_p2_base = list(qs[:60])
    if qs_for_p2_base:
        import random
        import itertools
        random.shuffle(qs_for_p2_base)
        pets_for_p2 = list(itertools.islice(itertools.cycle(qs_for_p2_base), 16))

    paginator = Paginator(qs, PETS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    try:
        page_number = max(1, int(page_number))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)
    # Query string pentru linkuri paginare
    q = dict(effective)
    q.pop("page", None)
    pagination_query = urlencode(q) if q else ""
    # Poze pentru burtiera mică (bandă deasupra slider-ului mare); dacă sunt puține, le dublăm
    strip_pets = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:40])
    if strip_pets and len(strip_pets) < 12:
        import itertools
        strip_pets = list(itertools.islice(itertools.cycle(strip_pets), 24))
    # Poziția în coadă pentru cererile active ale userului curent (pentru fiecare animal din listă)
    user_request_position_by_pet_id = {}
    user_has_request_for_pet = set()
    if request.user.is_authenticated and page_obj.object_list:
        pet_ids = [p.pk for p in page_obj.object_list]
        for ar in AdoptionRequest.objects.filter(
            adopter=request.user,
            pet_id__in=pet_ids,
            status__in=ACTIVE_DUPLICATE_CHECK_STATUSES,
        ).values_list("pet_id", "queue_position"):
            user_request_position_by_pet_id[ar[0]] = ar[1]
        # Pentru badge „Cerere trimisă”: orice cerere (orice status) a userului pentru acest animal
        user_has_request_for_pet = set(
            AdoptionRequest.objects.filter(adopter=request.user, pet_id__in=pet_ids).values_list("pet_id", flat=True)
        )
    total_dogs = Pet.objects.filter(status="adoptable", tip="dog").exclude(adoption_status="adopted").count()
    total_cats = Pet.objects.filter(status="adoptable", tip="cat").exclude(adoption_status="adopted").count()
    total_other = Pet.objects.filter(status="adoptable", tip="other").exclude(adoption_status="adopted").count()
    total_all = total_dogs + total_cats + total_other
    return render(request, "anunturi/pets-all.html", {
        "page_obj": page_obj,
        "pets": page_obj.object_list,
        "p2_pets": pets_for_p2,
        "current_tip": tip,
        "current_vip": vip,
        "current_sex": sex,
        "current_marime": marime,
        "current_judet": judet,
        "current_varsta": varsta,
        "pet_varsta_choices": Pet.VARSTA_APROX_CHOICES,
        "current_locuinta": request.GET.get("locuinta", ""),
        "current_tags_copii": request.GET.get("tags_copii", ""),
        "strip_pets": strip_pets,
        "pagination_query": pagination_query,
        "pet_sex_choices": Pet.SEX_CHOICES,
        "pet_marime_choices": Pet.MARIME_CHOICES,
        "pet_judet_choices": Pet.JUDET_CHOICES,
        "locuinta_choices": [("", "— Toate —"), ("apartament", "Apartament"), ("curte", "Curte")],
        "tags_copii_choices": [("", "— Toate —"), ("1", "Ok cu copii")],
        "user_request_position_by_pet_id": user_request_position_by_pet_id,
        "user_has_request_for_pet": user_has_request_for_pet,
        "total_dogs": total_dogs,
        "total_cats": total_cats,
        "total_other": total_other,
        "total_all": total_all,
    })


def wishlist_view(request):
    """Pagina listă „Te plac” – animalele salvate de utilizator. Neautentificat → login."""
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("login"), urlencode({"next": request.build_absolute_uri(reverse("wishlist"))})))
    favorites = PetFavorite.objects.filter(user=request.user).select_related("pet").order_by("-created_at")
    return render(request, "anunturi/wishlist.html", {"favorites": list(favorites)})


def wishlist_toggle(request, pk):
    """Adaugă sau scoate animalul din wishlist. Neautentificat: POST → 403, GET → redirect la login. Adăugarea necesită telefon verificat."""
    pet = get_object_or_404(Pet, pk=pk)
    if not request.user.is_authenticated:
        if request.method == "POST":
            return HttpResponseForbidden("Autentificare necesară pentru a modifica lista „Te plac”.")
        next_path = "{}?add_to_wishlist=1".format(reverse("pets_single", kwargs={"pk": pk}))
        next_url = request.build_absolute_uri(next_path)
        return redirect("{}?next={}".format(reverse("login"), urlencode({"next": next_url})))
    action = (request.GET.get("action") or request.POST.get("action", "toggle")).strip().lower()
    if action == "remove":
        PetFavorite.objects.filter(user=request.user, pet=pet).delete()
    else:
        if not user_phone_verified(request.user):
            messages.warning(
                request,
                "Trebuie să vă verificați numărul de telefon pentru a adăuga prieteni în lista „Te plac”. Verificați telefonul acum.",
            )
            return redirect("signup_verificare_telefon")
        PetFavorite.objects.get_or_create(user=request.user, pet=pet)
    # Redirect înapoi: referer sau pagina animalului
    next_url = request.GET.get("next") or request.POST.get("next") or request.META.get("HTTP_REFERER")
    if next_url and next_url.startswith("/") and "//" not in next_url.split("/")[:2]:
        return redirect(next_url)
    return redirect("pets_single", pk=pk)


def wishlist_unsubscribe(request, signed):
    """Dezabonare notificări wishlist via link din email (signed)."""
    from django.core.signing import BadSignature, Signer
    from django.contrib.auth import get_user_model
    User = get_user_model()
    signer = Signer()
    try:
        user_id = signer.unsign(signed)
    except BadSignature:
        return render(request, "anunturi/wishlist_unsubscribe.html", {"success": False})
    try:
        user = User.objects.get(pk=int(user_id))
    except (ValueError, User.DoesNotExist):
        return render(request, "anunturi/wishlist_unsubscribe.html", {"success": False})
    profile = getattr(user, "profile", None)
    if profile:
        profile.email_opt_in_wishlist = False
        profile.save(update_fields=["email_opt_in_wishlist"])
    return render(request, "anunturi/wishlist_unsubscribe.html", {"success": True})


def match_quiz_view(request):
    """
    Pagina chestionar „Găsește-mi prietenul ideal”. GET: formular 1 coloană. POST: salvare (logat în UserMatchProfile,
    nelogat în session) și redirect/afișare: logat → rezultate, nelogat → mesaj „Am găsit X potriviri. Te rugăm să te autentifici.”
    """
    if request.method == "POST":
        form = MatchQuizForm(request.POST)
        if form.is_valid():
            data = form.cleaned_data
            if request.user.is_authenticated:
                profile, _ = UserMatchProfile.objects.update_or_create(
                    user=request.user,
                    defaults={
                        "housing": data.get("housing") or "",
                        "experience": data.get("experience") or "",
                        "activity_level": data.get("activity_level") or "",
                        "time_available": data.get("time_available") or "",
                        "has_kids": data.get("has_kids"),
                        "has_cat": data.get("has_cat"),
                        "has_dog": data.get("has_dog"),
                        "size_preference": data.get("size_preference") or "",
                        "age_preference": data.get("age_preference") or "",
                    },
                )
                return redirect("match_results")
            # Nelogat: salvez în sesiune și afișez mesaj cu numărul de potriviri
            draft = {k: v for k, v in data.items() if k in [
                "housing", "experience", "activity_level", "time_available",
                "has_kids", "has_cat", "has_dog", "size_preference", "age_preference",
            ]}
            request.session[SESSION_KEY_MATCH_QUIZ_DRAFT] = draft
            request.session.modified = True
            matches = compute_matches(draft, limit=12)
            count = len(matches)
            return render(request, "anunturi/match_quiz_done_anon.html", {
                "match_count": count,
                "login_url": "{}?next={}".format(reverse("login"), quote(reverse("match_results"))),
            })
        # form invalid
    else:
        initial = {}
        if request.user.is_authenticated:
            try:
                profile = request.user.match_profile
                initial = {
                    "housing": profile.housing or "",
                    "experience": profile.experience or "",
                    "activity_level": profile.activity_level or "",
                    "time_available": profile.time_available or "",
                    "has_kids": profile.has_kids,
                    "has_cat": profile.has_cat,
                    "has_dog": profile.has_dog,
                    "size_preference": profile.size_preference or "",
                    "age_preference": profile.age_preference or "",
                }
            except UserMatchProfile.DoesNotExist:
                pass
        else:
            initial = request.session.get(SESSION_KEY_MATCH_QUIZ_DRAFT) or {}
        form = MatchQuizForm(initial=initial)
    return render(request, "anunturi/match_quiz.html", {"form": form})


def match_results_view(request):
    """
    Rezultate potriviri. Doar pentru user autentificat. Dacă în sesiune există match_quiz_draft (după login),
    salvează automat în UserMatchProfile și afișează top 12. Altfel afișează pe baza profilului salvat.
    """
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("login"), quote(reverse("match_results"))))
    draft = request.session.pop(SESSION_KEY_MATCH_QUIZ_DRAFT, None)
    if draft:
        UserMatchProfile.objects.update_or_create(
            user=request.user,
            defaults={
                "housing": draft.get("housing") or "",
                "experience": draft.get("experience") or "",
                "activity_level": draft.get("activity_level") or "",
                "time_available": draft.get("time_available") or "",
                "has_kids": draft.get("has_kids"),
                "has_cat": draft.get("has_cat"),
                "has_dog": draft.get("has_dog"),
                "size_preference": draft.get("size_preference") or "",
                "age_preference": draft.get("age_preference") or "",
            },
            )
    try:
        profile = request.user.match_profile
    except UserMatchProfile.DoesNotExist:
        profile = None
    if not profile or not any([getattr(profile, f, None) for f in [
        "housing", "experience", "activity_level", "time_available",
        "size_preference", "age_preference",
    ]]):
        return redirect("match_quiz")
    matches = compute_matches(profile, limit=12)
    return render(request, "anunturi/match_results.html", {"matches": matches})


def pets_single(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    # După login: adaugă la wishlist dacă a venit cu add_to_wishlist=1
    if request.user.is_authenticated and request.GET.get("add_to_wishlist"):
        PetFavorite.objects.get_or_create(user=request.user, pet=pet)
        return redirect("pets_single", pk=pk)
    initial = _get_adoption_form_initial(request.user) if request.user.is_authenticated else None
    form = AdoptionRequestForm(initial=initial) if initial else AdoptionRequestForm()
    # Related dogs: same county, similar size, similar age, random fallback (exclude current, max 4)
    related_qs = Pet.objects.filter(status="adoptable").exclude(pk=pet.pk).order_by("-data_adaugare")
    same_county = list(related_qs.filter(judet=pet.judet)) if pet.judet else []
    same_size = list(related_qs.filter(marime=pet.marime).exclude(marime="")) if pet.marime else []
    same_age = list(related_qs.filter(varsta_aproximativa=pet.varsta_aproximativa)) if pet.varsta_aproximativa is not None else []
    seen = {pet.pk}
    related_pets = []
    for p in same_county + same_size + same_age + list(related_qs):
        if p.pk not in seen and len(related_pets) < 4:
            related_pets.append(p)
            seen.add(p.pk)
    user_adoption_request = None
    if request.user.is_authenticated:
        user_adoption_request = (
            AdoptionRequest.objects.filter(pet=pet, adopter=request.user)
            .exclude(status__in=["cancelled", "rejected", "finalized"])
            .order_by("data_cerere")
            .first()
        )
    is_owner = _user_is_pet_owner(request.user, pet) if request.user.is_authenticated else False
    pet_cereri = list(AdoptionRequest.objects.filter(pet=pet).select_related("adopter").order_by("data_cerere")) if is_owner else []
    return render(request, "anunturi/pets-single.html", {
        "pet": pet,
        "adoption_form": form,
        "related_pets": related_pets[:4],
        "user_adoption_request": user_adoption_request,
        "is_owner": is_owner,
        "pet_cereri": pet_cereri,
    })


def api_pets_by_ids(request):
    """API JSON: returnează lista de pets pentru ID-uri date (pentru secțiunea 'Prietenii pe care i-ai vizitat')."""
    ids_param = (request.GET.get("ids") or "").strip()
    if not ids_param:
        return JsonResponse({"pets": []})
    try:
        ids = [int(x.strip()) for x in ids_param.split(",") if x.strip()]
    except (TypeError, ValueError):
        return JsonResponse({"pets": []})
    ids = ids[:10]  # max 10
    pets_by_id = {p.pk: p for p in Pet.objects.filter(pk__in=ids)}
    pets = [pets_by_id[i] for i in ids if i in pets_by_id]
    result = []
    for p in pets:
        img_url = ""
        if p.imagine:
            img_url = p.imagine.url
        elif p.imagine_fallback:
            img_url = static(p.imagine_fallback)
        else:
            img_url = static("images/pets/charlie-275x275.jpg")
        result.append({
            "id": p.pk,
            "nume": p.nume,
            "imagine_url": request.build_absolute_uri(img_url),
            "link": request.build_absolute_uri("/pet/{}/".format(p.pk)),
        })
    return JsonResponse({"pets": result})


def pet_ask_view(request, pk):
    """Pagina „Întreabă despre mine” – AI răspunde la întrebări despre animalul curent."""
    pet = get_object_or_404(Pet, pk=pk)
    return render(request, "anunturi/pet-ask.html", {"pet": pet})


@require_phone_verified
def adoption_form_page(request, pk):
    """Pagină separată cu formularul de adopție. Se deschide la click pe „Vreau să adopt”. Doar GET; POST merge la adoption_request_submit."""
    pet = get_object_or_404(Pet, pk=pk)
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("login"), urlencode({"next": request.build_absolute_uri()})))
    if pet.adoption_status in ("adopted", "unavailable"):
        messages.info(request, "Acest animal nu mai este disponibil pentru adopție.")
        return redirect("pets_single", pk=pk)
    user_adoption_request = (
        AdoptionRequest.objects.filter(pet=pet, adopter=request.user)
        .exclude(status__in=["cancelled", "rejected", "finalized"])
        .first()
    )
    if user_adoption_request:
        messages.info(request, "Ai deja o cerere pentru acest animal.")
        return redirect("pets_single", pk=pk)
    initial = _get_adoption_form_initial(request.user)
    form = AdoptionRequestForm(initial=initial) if initial else AdoptionRequestForm()
    return render(request, "anunturi/adoption_form_page.html", {
        "pet": pet,
        "adoption_form": form,
    })


def adoption_request_submit(request, pk):
    """POST: trimite cerere adopție. Doar utilizatori autentificați. Guest → 403."""
    pet = get_object_or_404(Pet, pk=pk)
    if not request.user.is_authenticated:
        if request.method == "POST":
            return HttpResponseForbidden("Autentificare necesară pentru a trimite o cerere de adopție.")
        return redirect("{}?next={}".format(reverse("login"), urlencode({"next": request.build_absolute_uri(reverse("pets_single", kwargs={"pk": pk}))})))
    if request.method != "POST":
        return redirect("pets_single", pk=pk)
    # Când animalul e rezervat, permitem doar cereri „listă de așteptare” (status=waitlist), nu cereri noi normale

    adopter = request.user

    # Toate categoriile (PF + org): telefon verificat obligatoriu pentru a trimite cerere
    if adopter and not user_phone_verified(adopter):
        messages.error(
            request,
            "Trebuie să vă verificați numărul de telefon înainte de a trimite o cerere de adopție. "
            "Verificați telefonul acum.",
        )
        return redirect("signup_verificare_telefon")

    # Blochează dacă userul are deja o cerere activă (PENDING/APPROVED/WAITLIST etc.)
    if adopter:
        existing = AdoptionRequest.objects.filter(pet=pet, adopter=adopter).first()
        if existing and existing.status in BLOCK_DUPLICATE_REQUEST_STATUSES:
            messages.info(request, "Ai deja o cerere pentru acest animal. Verifică statusul cererii tale.")
            return redirect("pets_single", pk=pk)

    # Rate limit: max X cereri noi / 24h per PF
    if adopter:
        since = timezone.now() - timedelta(hours=24)
        count_24h = AdoptionRequest.objects.filter(adopter=adopter, data_cerere__gte=since).count()
        limit = getattr(settings, "PF_DAILY_ADOPTION_REQUEST_LIMIT", 5)
        if count_24h >= limit:
            messages.error(
                request,
                f"Ai atins limita de {limit} cereri în ultimele 24 de ore. Încearcă mâine.",
            )
            return redirect("pets_single", pk=pk)

    form = AdoptionRequestForm(request.POST)
    if not form.is_valid():
        if request.POST.get("from_adopt_page"):
            return render(request, "anunturi/adoption_form_page.html", {"pet": pet, "adoption_form": form})
        related_qs = Pet.objects.filter(status="adoptable").exclude(pk=pet.pk).order_by("-data_adaugare")
        same_county = list(related_qs.filter(judet=pet.judet)) if pet.judet else []
        same_size = list(related_qs.filter(marime=pet.marime).exclude(marime="")) if pet.marime else []
        same_age = list(related_qs.filter(varsta_aproximativa=pet.varsta_aproximativa)) if pet.varsta_aproximativa is not None else []
        seen = {pet.pk}
        related_pets = []
        for p in same_county + same_size + same_age + list(related_qs):
            if p.pk not in seen and len(related_pets) < 4:
                related_pets.append(p)
                seen.add(p.pk)
        return render(request, "anunturi/pets-single.html", {
            "pet": pet,
            "adoption_form": form,
            "related_pets": related_pets[:4],
        })

    # Duplicat activ (redundant cu regula de mai sus, păstrat ca safety)
    if adopter and AdoptionRequest.objects.filter(
        pet=pet, adopter=adopter, status__in=ACTIVE_DUPLICATE_CHECK_STATUSES
    ).exists():
        messages.error(request, "Ai deja o cerere activă pentru acest animal.")
        return redirect("pets_single", pk=pk)

    # O singură cerere per animal per email (și pentru neautentificați)
    email = form.cleaned_data.get("email", "").strip().lower()
    if AdoptionRequest.objects.filter(pet=pet, email__iexact=email).exists():
        form.add_error(
            None,
            "Ați trimis deja o cerere de adopție pentru acest animal. Nu se poate trimite o a doua cerere de la același email.",
        )
        if request.POST.get("from_adopt_page"):
            return render(request, "anunturi/adoption_form_page.html", {"pet": pet, "adoption_form": form})
        related_qs = Pet.objects.filter(status="adoptable").exclude(pk=pet.pk).order_by("-data_adaugare")
        same_county = list(related_qs.filter(judet=pet.judet)) if pet.judet else []
        same_size = list(related_qs.filter(marime=pet.marime).exclude(marime="")) if pet.marime else []
        same_age = list(related_qs.filter(varsta_aproximativa=pet.varsta_aproximativa)) if pet.varsta_aproximativa is not None else []
        seen = {pet.pk}
        related_pets = []
        for p in same_county + same_size + same_age + list(related_qs):
            if p.pk not in seen and len(related_pets) < 4:
                related_pets.append(p)
                seen.add(p.pk)
        return render(request, "anunturi/pets-single.html", {
            "pet": pet,
            "adoption_form": form,
            "related_pets": related_pets[:4],
        })

    # Un singur request per (pet, adopter): dacă există deja unul terminal (cancelled/rejected/finalized), îl reactualizăm
    existing = AdoptionRequest.objects.filter(pet=pet, adopter=adopter).first() if adopter else None
    if existing and existing.status in ("cancelled", "rejected", "finalized"):
        for attr in ("nume_complet", "email", "telefon", "adresa", "mesaj"):
            setattr(existing, attr, form.cleaned_data.get(attr, getattr(existing, attr)))
        existing.email = email
        existing.status = "waitlist" if getattr(pet, "adoption_status", None) == "reserved" else "pending"
        existing.queue_position = (
            AdoptionRequest.objects.filter(pet=pet).exclude(status__in=["cancelled", "rejected", "finalized"]).count() + 1
        )
        existing.save()
        send_adoption_request_to_ong(existing, request)
        send_adoption_request_confirmation_to_adoptor(existing)
        _sent_url = reverse("adoption_request_sent", kwargs={"pk": existing.pk})
        if request.POST.get("from_adopt_page"):
            _sent_url += "?caseta=1"
        return redirect(_sent_url)

    adoption_request = form.save(commit=False)
    adoption_request.pet = pet
    adoption_request.email = email
    adoption_request.status = "waitlist" if getattr(pet, "adoption_status", None) == "reserved" else "pending"
    adoption_request.adopter = adopter
    adoption_request.owner = getattr(pet, "added_by_user", None)
    adoption_request.queue_position = (
        AdoptionRequest.objects.filter(pet=pet).exclude(status__in=["cancelled", "rejected", "finalized"]).count() + 1
    )

    try:
        adoption_request.full_clean()
    except ValidationError as e:
        if getattr(e, "message_dict", None):
            msgs = e.message_dict.get("__all__", [])
            msg = msgs[0] if msgs else "Ai deja o cerere activă pentru acest animal."
        else:
            msg = list(e.messages)[0] if e.messages else "Ai deja o cerere activă pentru acest animal."
        messages.error(request, msg)
        return redirect("pets_single", pk=pk)

    adoption_request.save()

    # Email către owner + confirmare către adoptator
    send_adoption_request_to_ong(adoption_request, request)
    send_adoption_request_confirmation_to_adoptor(adoption_request)
    _sent_url = reverse("adoption_request_sent", kwargs={"pk": adoption_request.pk})
    if request.POST.get("from_adopt_page"):
        _sent_url += "?caseta=1"
    return redirect(_sent_url)


def adoption_request_sent(request, pk):
    """Pagina „Cerere trimisă” – pk este id-ul AdoptionRequest. Doar adoptatorul sau owner-ul pot vedea."""
    if not request.user.is_authenticated:
        return redirect("{}?next={}".format(reverse("login"), urlencode({"next": request.build_absolute_uri()})))
    adoption_request = get_object_or_404(AdoptionRequest, pk=pk)
    pet = adoption_request.pet
    if adoption_request.adopter_id != request.user.pk and not _user_is_pet_owner(request.user, pet):
        return HttpResponseForbidden("Nu aveți permisiunea să vizualizați această cerere.")
    return render(request, "anunturi/adoption_request_sent.html", {
        "adoption_request": adoption_request,
        "pet": pet,
        "show_caseta": request.GET.get("caseta") == "1",
    })


def adoption_validate_token_view(request, token):
    """
    Pagina la care ajunge ONG-ul când dă click pe linkul din emailul de validare cerere adopție.
    Găsește cererea după validation_token, execută run_validation_link, redirecționează cu mesaj.
    """
    adoption_request = AdoptionRequest.objects.filter(validation_token=token).select_related("pet").first()
    if not adoption_request:
        messages.error(request, "Link invalid sau deja utilizat.")
        return redirect("home")
    success, error_message = run_validation_link(adoption_request)
    if success:
        messages.success(request, "Cererea a fost validată. Adoptatorul a fost notificat și a primit datele de contact.")
    else:
        messages.error(request, error_message or "Validarea nu a putut fi finalizată.")
    return redirect("home")


def _user_is_pet_owner(user, pet):
    """True dacă userul este proprietarul animalului (l-a adăugat sau e owner pe cereri)."""
    if not user or not user.is_authenticated or not pet:
        return False
    if getattr(pet, "added_by_user_id", None) == user.pk:
        return True
    if pet.ong_email and hasattr(user, "ong_profile") and user.ong_profile and (user.ong_profile.email or "").strip().lower() == (pet.ong_email or "").strip().lower():
        return True
    return AdoptionRequest.objects.filter(pet=pet, owner=user).exists()


@login_required
def adoption_finalize_view(request, request_id):
    """
    POST: marchează adopția ca finalizată.
    Setează PET adoption_status=adopted, status=adopted; REQUEST status=finalized; trimite email adoptatorului.
    Cere confirmare (param confirm=1).
    """
    adoption_request = get_object_or_404(AdoptionRequest, pk=request_id)
    pet = adoption_request.pet
    if not _user_is_pet_owner(request.user, pet):
        messages.error(request, "Nu aveți permisiunea să finalizați această adopție.")
        return redirect("pets_single", pk=pet.pk)
    if request.method != "POST":
        return redirect("pets_single", pk=pet.pk)
    if request.POST.get("confirm") != "1":
        messages.warning(request, "Confirmați acțiunea pentru a marca adopția ca finalizată.")
        return redirect("pets_single", pk=pet.pk)
    if adoption_request.status not in APPROVED_RESERVATION_STATUSES:
        messages.error(request, "Doar o cerere aprobată (rezervată) poate fi finalizată.")
        return redirect("pets_single", pk=pet.pk)
    if pet.adoption_status != "reserved":
        messages.error(request, "Animalul nu este în stare rezervată.")
        return redirect("pets_single", pk=pet.pk)

    adoption_request.status = "finalized"
    adoption_request.finalized_at = timezone.now()
    adoption_request.finalized_by = request.user
    adoption_request.save(update_fields=["status", "finalized_at", "finalized_by"])
    pet.adoption_status = "adopted"
    pet.status = "adopted"
    pet.reserved_for_request = None
    pet.save(update_fields=["adoption_status", "status", "reserved_for_request"])
    send_adoption_finalized_email(adoption_request)
    send_adoption_finalized_notice_to_owner(adoption_request)
    messages.success(request, f"Adopția pentru {pet.nume} a fost marcată ca finalizată. Adoptatorul a fost notificat.")
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("cont_ong")
    return redirect(next_url)


@login_required
def adoption_cancel_reservation_view(request, request_id):
    """
    POST: anulează rezervarea. PET=available, REQUEST=cancelled.
    Opțional: notifică prima cerere din listă (waitlist/pending).
    """
    adoption_request = get_object_or_404(AdoptionRequest, pk=request_id)
    pet = adoption_request.pet
    if not _user_is_pet_owner(request.user, pet):
        messages.error(request, "Nu aveți permisiunea să anulați această rezervare.")
        return redirect("pets_single", pk=pet.pk)
    if request.method != "POST":
        return redirect("pets_single", pk=pet.pk)
    if adoption_request.status not in APPROVED_RESERVATION_STATUSES:
        messages.error(request, "Doar o cerere aprobată poate fi anulată.")
        return redirect("pets_single", pk=pet.pk)

    adoption_request.status = "cancelled"
    adoption_request.cancelled_at = timezone.now()
    adoption_request.save(update_fields=["status", "cancelled_at"])
    pet.adoption_status = "available"
    pet.status = "adoptable"
    pet.reserved_for_request = None
    pet.save(update_fields=["adoption_status", "status", "reserved_for_request"])

    # Opțional: notifică prima cerere în așteptare (pending/waitlist) sau o promovează
    success, _err, promoted = approve_first_adoption_request(pet)
    if success and promoted:
        messages.success(request, "Rezervarea a fost anulată. Prima persoană din listă a fost notificată.")
    else:
        messages.success(request, "Rezervarea a fost anulată. Animalul este din nou disponibil.")
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("cont_ong")
    return redirect(next_url)


def _get_posted_pets(user):
    """Animale pe care userul le poate gestiona (adăpost/ONG sau added_by_user)."""
    if not user or not user.is_authenticated:
        return Pet.objects.none()
    profile = getattr(user, "ong_profile", None)
    if profile and (profile.email or "").strip():
        return Pet.objects.filter(
            Q(ong_email=profile.email) | Q(added_by_user=user)
        ).distinct().order_by("-data_adaugare")
    return Pet.objects.filter(added_by_user=user).order_by("-data_adaugare")


@login_required
def my_posted_pets_view(request):
    """
    Dashboard „Câinii mei” – tabel cu animalele postate de user + cereri + acțiuni.
    Doar pentru conturi care au drept de postare (au animale via ong_email sau added_by_user).
    """
    pets = _get_posted_pets(request.user)
    if not pets.exists():
        messages.info(request, "Nu aveți animale postate. Adăugați un animal din cont.")
        return redirect("cont_ong")

    pet_ids = list(pets.values_list("pk", flat=True))
    # Cereri per pet: approved (una), pending+waitlist (count + listă)
    requests_by_pet = {}
    for ar in AdoptionRequest.objects.filter(pet_id__in=pet_ids).select_related("pet", "adopter").order_by("data_cerere"):
        pid = ar.pet_id
        if pid not in requests_by_pet:
            requests_by_pet[pid] = {"approved": None, "pending_waitlist": [], "count_pending_waitlist": 0}
        if ar.status in APPROVED_RESERVATION_STATUSES:
            requests_by_pet[pid]["approved"] = ar
        elif ar.status in ("pending", "new", "approved_platform", "waitlist"):
            requests_by_pet[pid]["pending_waitlist"].append(ar)
    for pid in requests_by_pet:
        requests_by_pet[pid]["count_pending_waitlist"] = len(requests_by_pet[pid]["pending_waitlist"])

    show_requests_pet_id = request.GET.get("pet")
    show_requests_pet = None
    show_requests_data = None
    if show_requests_pet_id:
        try:
            pk = int(show_requests_pet_id)
            show_requests_pet = pets.filter(pk=pk).first()
            if show_requests_pet and pk in pet_ids:
                show_requests_data = requests_by_pet.get(pk, {"approved": None, "pending_waitlist": [], "count_pending_waitlist": 0})
            else:
                show_requests_pet = None
        except (ValueError, TypeError):
            pass

    default_data = {"approved": None, "pending_waitlist": [], "count_pending_waitlist": 0}
    pets_with_data = [(pet, requests_by_pet.get(pet.pk, default_data)) for pet in list(pets)]
    return render(request, "anunturi/my-posted-pets.html", {
        "pets_with_data": pets_with_data,
        "show_requests_pet": show_requests_pet,
        "show_requests_data": show_requests_data,
        "APPROVED_RESERVATION_STATUSES": APPROVED_RESERVATION_STATUSES,
    })


@login_required
def accept_adoption_request_view(request, request_id):
    """
    POST: owner acceptă cererea selectată. Request -> APPROVED, pet -> RESERVED, celelalte -> WAITLIST.
    """
    adoption_request = get_object_or_404(AdoptionRequest, pk=request_id)
    pet = adoption_request.pet
    if not _user_is_pet_owner(request.user, pet):
        messages.error(request, "Nu aveți permisiunea să acceptați această cerere.")
        return redirect("my_posted_pets")
    if request.method != "POST":
        return redirect("my_posted_pets")
    success, err = accept_adoption_request_by_owner(adoption_request)
    if success:
        messages.success(request, f"Ai acceptat cererea pentru {pet.nume}. Adoptatorul a fost notificat.")
    else:
        messages.error(request, err or "Acțiunea nu a putut fi efectuată.")
    next_url = request.POST.get("next") or request.GET.get("next") or reverse("my_posted_pets")
    return redirect(next_url)


def signup_view(request):
    # Dacă utilizatorul este deja autentificat, redirecționează către profilul său
    if request.user.is_authenticated:
        from django.contrib.auth.models import Group
        is_ong = request.user.groups.filter(name="Asociație").exists()
        if is_ong:
            return redirect("cont_ong")
        else:
            return redirect("cont_profil")
    next_url = (request.GET.get("next") or "").strip()
    if next_url and not (next_url.startswith("/") and "//" not in next_url.split("/")[:2]):
        next_url = ""
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user, request=request)
            tip = form.cleaned_data.get("tip_cont", "pf")
            if tip == "pf":
                UserProfile.objects.get_or_create(user=user, defaults={
                    "nume": (form.cleaned_data.get("nume") or "").strip(),
                    "prenume": (form.cleaned_data.get("prenume") or "").strip(),
                    "telefon": (form.cleaned_data.get("telefon") or "").strip(),
                    "oras": (form.cleaned_data.get("oras") or "").strip(),
                })
                phone = (form.cleaned_data.get("telefon") or "").strip()
            elif tip in ("srl_pfa_af", "ong"):
                sub = form.cleaned_data.get("tip_org_organizatie") or form.cleaned_data.get("tip_org_ong") or "ong"
                OngProfile.objects.get_or_create(user=user, defaults={
                    "denumire_legala": (form.cleaned_data.get("denumire_legala") or "").strip(),
                    "cui": (form.cleaned_data.get("cui") or "").strip(),
                    "email": (form.cleaned_data.get("email_contact") or "").strip(),
                    "judet": (form.cleaned_data.get("judet") or "").strip(),
                    "oras": (form.cleaned_data.get("oras_org") or "").strip(),
                    "telefon": (form.cleaned_data.get("telefon_org") or "").strip(),
                    "persoana_responsabila_adoptii": (form.cleaned_data.get("persoana_responsabila_adoptii") or "").strip(),
                    "reprezentant_legal": (form.cleaned_data.get("reprezentant_legal") or "").strip(),
                    "tip_organizatie": sub if sub in ("srl", "pfa", "ong", "af") else "ong",
                })
                phone = (form.cleaned_data.get("telefon_org") or "").strip()
            else:
                phone = ""
            login(request, user, backend=_auth_backend_for_login())
            request.session["signup_phone_masked"] = _mask_phone(phone)
            if next_url:
                request.session["next_after_profile_save"] = next_url
            messages.success(request, "Cont creat. Introduceți codul SMS trimis la telefon pentru a finaliza.")
            url = reverse("signup_verificare_telefon")
            if next_url:
                url += "?next=" + quote(next_url)
            return redirect(url)
    else:
        form = UserRegistrationForm()
    return render(request, "registration/signup.html", {"form": form})


def _validate_sms_code_and_mark_verified(request, profile):
    """Validează codul din request (6 casete) și setează profile.phone_verified. Returnează True dacă valid."""
    from django.conf import settings
    from django.utils import timezone
    code_entered = _sms_code_from_request(request)
    if not code_entered or len(code_entered) != 6:
        return False
    session_code = request.session.get("sms_verification_code")
    session_ts = request.session.get("sms_verification_sent_at")
    dev_code = getattr(settings, "SMS_DEV_CODE", "") or ""
    valid = False
    if session_code and session_ts and (timezone.now().timestamp() - session_ts) < 600:
        valid = code_entered == session_code
    if not valid and dev_code and code_entered == dev_code:
        valid = True
    if valid:
        profile.phone_verified = True
        profile.save(update_fields=["phone_verified"])
        for key in ("sms_verification_code", "sms_verification_sent_at", "sms_verification_phone"):
            request.session.pop(key, None)
        return True
    return False


def _sms_sent_and_valid(session, max_age_seconds=600):
    """True dacă s-a trimis deja un cod SMS și nu a expirat."""
    from django.utils import timezone
    sent_at = session.get("sms_verification_sent_at")
    return bool(sent_at and (timezone.now().timestamp() - sent_at) < max_age_seconds)


def signup_verificare_telefon_view(request):
    """Pagina după înregistrare: date profil + cod SMS. Categoria 2 (SRL/ONG): și câmpuri obligatorii (adrese, CUI, adăpost public)."""
    if not request.user.is_authenticated:
        messages.info(request, "Trebuie să fiți autentificat. Logați-vă apoi mergeți la Cont → Profil.")
        return redirect("login")
    if request.method == "GET":
        next_url = (request.GET.get("next") or "").strip()
        if next_url and next_url.startswith("/") and "//" not in next_url.split("/")[:2]:
            request.session["next_after_profile_save"] = next_url
    profile, created = UserProfile.objects.get_or_create(user=request.user)
    profile_main = getattr(request.user, "profile", None)
    is_org = profile_main and getattr(profile_main, "account_type", None) in ("company", "ngo")
    ong_profile = None
    if is_org:
        ong_profile, _ = OngProfile.objects.get_or_create(
            user=request.user,
            defaults={"tip_organizatie": "srl" if getattr(profile_main, "account_type", None) == "company" else "ong"},
        )
    if created and ong_profile:
        if ong_profile.telefon:
            profile.telefon = ong_profile.telefon
        profile.email = (request.user.email or "").strip() or profile.email
        name = (getattr(ong_profile, "reprezentant_legal", "") or getattr(ong_profile, "persoana_responsabila_adoptii", "") or "").strip()
        if name:
            profile.nume = name
        profile.save()
    phone_masked = request.session.get("signup_phone_masked") or _mask_phone(profile.telefon) or "***"
    sms_sent = _sms_sent_and_valid(request.session)
    ctx_base = {
        "profile": profile,
        "phone_masked": phone_masked,
        "next_url": request.session.get("next_after_profile_save") or request.GET.get("next") or "",
        "is_org": is_org,
    }
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        org_form = OrgRequiredPage2Form(request.POST, instance=ong_profile) if is_org and ong_profile else None
        if is_org and org_form and not org_form.is_valid():
            ctx_base["form"] = form
            ctx_base["org_form"] = org_form
            ctx_base["sms_sent"] = _sms_sent_and_valid(request.session)
            messages.error(request, "Completați toate câmpurile obligatorii pentru organizație (adrese, CUI, adăpost public).")
            return render(request, "registration/signup_verificare_telefon.html", ctx_base)
        if is_org and org_form and org_form.is_valid():
            org_form.save()
        if form.is_valid():
            form.save()
            request.session["signup_phone_masked"] = _mask_phone(form.cleaned_data.get("telefon") or "")
            code_entered = _sms_code_from_request(request)
            if code_entered:
                if _validate_sms_code_and_mark_verified(request, profile):
                    messages.success(request, "Profil salvat și telefon verificat. Bine ați venit!")
                    return _safe_next_redirect(request, "cont")
                messages.error(request, "Cod incorect sau expirat. Încercați din nou sau apăsați din nou «Trimite SMS» pentru un cod nou.")
            else:
                phone = (profile.telefon or "").strip()
                if phone:
                    from django.conf import settings
                    from django.utils import timezone
                    from .sms import send_sms_verification
                    import random
                    dev_code = getattr(settings, "SMS_DEV_CODE", "") or ""
                    code = dev_code if dev_code and len(dev_code) == 6 else "".join(str(random.randint(0, 9)) for _ in range(6))
                    request.session["sms_verification_code"] = code
                    request.session["sms_verification_sent_at"] = timezone.now().timestamp()
                    request.session["sms_verification_phone"] = phone
                    if send_sms_verification(phone, code):
                        messages.success(request, "Cod trimis pe SMS. Introduceți cele 6 cifre și apăsați «Validează cod 6 cifre».")
                    else:
                        messages.error(request, "Nu s-a putut trimite SMS. Verificați numărul de telefon.")
                    return redirect("signup_verificare_telefon")
                else:
                    messages.warning(request, "Completați numărul de telefon în câmpul de mai sus și apăsați din nou butonul.")
        else:
            messages.error(request, "Corectați erorile din formular.")
        ctx_base["form"] = form
        ctx_base["org_form"] = OrgRequiredPage2Form(instance=ong_profile) if is_org and ong_profile else None
        ctx_base["sms_sent"] = _sms_sent_and_valid(request.session)
        return render(request, "registration/signup_verificare_telefon.html", ctx_base)
    form = UserProfileForm(instance=profile)
    org_form = OrgRequiredPage2Form(instance=ong_profile) if is_org and ong_profile else None
    ctx_base["form"] = form
    ctx_base["org_form"] = org_form
    ctx_base["sms_sent"] = sms_sent
    return render(request, "registration/signup_verificare_telefon.html", ctx_base)


def register_choose_type(request):
    """Pasul 1: Alege tipul contului (PF, SRL, ONG)."""
    if request.user.is_authenticated:
        return redirect("cont")
    import itertools
    import random
    footer_strip_pets = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:48])
    if not footer_strip_pets:
        footer_strip_pets = []
    elif len(footer_strip_pets) < 12:
        # Puține poze: dublăm/triplăm aleatoriu până la cel puțin 24
        target = max(24, len(footer_strip_pets) * 3)
        extra = list(random.choices(footer_strip_pets, k=target - len(footer_strip_pets)))
        footer_strip_pets = footer_strip_pets + extra
        random.shuffle(footer_strip_pets)
    return render(request, "registration/register_choose_type.html", {"footer_strip_pets": footer_strip_pets})


def _mask_phone(phone):
    """Maschează telefonul pentru afișare (ex: 0753017424 -> 075***7424)."""
    phone = (phone or "").strip()
    digits = "".join(c for c in phone if c.isdigit())
    if len(digits) < 7:
        return "***"
    return digits[:3] + "***" + digits[-4:]


def register_pf(request):
    """Înregistrare Persoană Fizică. După creare, redirect obligatoriu la verificare SMS."""
    if request.user.is_authenticated:
        return redirect("cont")
    next_url = (request.GET.get("next") or "").strip()
    if next_url and not (next_url.startswith("/") and "//" not in next_url.split("/")[:2]):
        next_url = ""
    if request.method == "POST":
        form = RegisterPFForm(request.POST, request.FILES)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user, request=request)
            login(request, user, backend=_auth_backend_for_login())
            profile = getattr(user, "user_profile", None)
            phone = (profile.telefon if profile else "") or ""
            request.session["signup_phone_masked"] = _mask_phone(phone)
            if next_url:
                request.session["next_after_profile_save"] = next_url
            messages.success(request, "Cont creat. Introduceți codul SMS trimis la telefon pentru a finaliza.")
            url = reverse("signup_verificare_telefon")
            if next_url:
                url += "?next=" + quote(next_url)
            return redirect(url)
    else:
        form = RegisterPFForm()
    return render(request, "registration/register_pf.html", {"form": form})


def register_srl(request):
    """Înregistrare SRL / Firmă. După creare, redirect obligatoriu la verificare SMS."""
    if request.user.is_authenticated:
        return redirect("cont")
    next_url = (request.GET.get("next") or "").strip()
    if next_url and not (next_url.startswith("/") and "//" not in next_url.split("/")[:2]):
        next_url = ""
    if request.method == "POST":
        form = RegisterSRLForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user, request=request)
            login(request, user, backend=_auth_backend_for_login())
            phone = (form.cleaned_data.get("phone") or "").strip()
            request.session["signup_phone_masked"] = _mask_phone(phone)
            if next_url:
                request.session["next_after_profile_save"] = next_url
            messages.success(request, "Cont creat. Introduceți codul SMS trimis la telefon pentru a finaliza.")
            url = reverse("signup_verificare_telefon")
            if next_url:
                url += "?next=" + quote(next_url)
            return redirect(url)
    else:
        form = RegisterSRLForm()
    return render(request, "registration/register_srl.html", {"form": form})


def register_ong(request):
    """Înregistrare ONG / Asociație / Fundație. După creare, redirect obligatoriu la verificare SMS."""
    if request.user.is_authenticated:
        return redirect("cont")
    next_url = (request.GET.get("next") or "").strip()
    if next_url and not (next_url.startswith("/") and "//" not in next_url.split("/")[:2]):
        next_url = ""
    if request.method == "POST":
        form = RegisterONGForm(request.POST)
        if form.is_valid():
            user = form.save()
            send_welcome_email(user, request=request)
            login(request, user, backend=_auth_backend_for_login())
            phone = (form.cleaned_data.get("phone") or "").strip()
            request.session["signup_phone_masked"] = _mask_phone(phone)
            if next_url:
                request.session["next_after_profile_save"] = next_url
            messages.success(request, "Cont creat. Introduceți codul SMS trimis la telefon pentru a finaliza.")
            url = reverse("signup_verificare_telefon")
            if next_url:
                url += "?next=" + quote(next_url)
            return redirect(url)
    else:
        form = RegisterONGForm()
    return render(request, "registration/register_ong.html", {"form": form})


def register_organizatie(request):
    """Pagină intermediară UI: alegere SRL/SA sau ONG/Asociație. Fără logică nouă – doar 2 link-uri către rutele existente."""
    if request.user.is_authenticated:
        return redirect("cont")
    return render(request, "registration/register_organizatie.html")


def register_colaborator(request):
    """Înregistrare Colaborator – placeholder; formularul poate fi extins ulterior."""
    if request.user.is_authenticated:
        return redirect("cont")
    return render(request, "registration/register_colaborator.html")


def cont_view(request):
    """Pagina principală de cont - direcționează către profilul corespunzător"""
    if not request.user.is_authenticated:
        return redirect("login")
    # Preferăm Profile.account_type dacă există
    profile = getattr(request.user, "profile", None)
    if profile:
        if profile.account_type == "ngo":
            return redirect("cont_ong")
        if profile.account_type == "company":
            return redirect("cont_ong")  # SRL folosește aceeași zonă ONG pentru animale
        return redirect("cont_profil")
    # Fallback: grupul Asociație
    from django.contrib.auth.models import Group
    if request.user.groups.filter(name="Asociație").exists():
        return redirect("cont_ong")
    return redirect("cont_profil")


def _sms_code_from_request(request):
    """Extrage codul din 6 casete sms_code_1..6."""
    parts = [request.POST.get(f"sms_code_{i}", "").strip() for i in range(1, 7)]
    return "".join(parts) if all(p.isdigit() for p in parts) else ""


def _safe_next_redirect(request, default="home"):
    """Redirect la next din session sau POST, doar dacă e URL intern (începe cu /)."""
    next_url = request.session.pop("next_after_profile_save", None) or request.POST.get("next") or request.GET.get("next")
    if next_url and next_url.strip().startswith("/") and "//" not in next_url.strip().split("/")[:2]:
        return redirect(next_url.strip())
    return redirect(default)

def cont_profil_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    profile_main = getattr(request.user, "profile", None)
    if not profile_main:
        profile_main = Profile.objects.create(user=request.user, account_type="individual")
    # Păstrăm „next” pentru redirect după salvare (ex: înapoi la pagina animalului)
    if request.method == "GET":
        next_url = request.GET.get("next", "").strip()
        if next_url and next_url.startswith("/") and "//" not in next_url.split("/")[:2]:
            request.session["next_after_profile_save"] = next_url
    if request.method == "POST":
        opt_in = request.POST.get("email_opt_in_wishlist") in ("on", "1", "true")
        profile_main.email_opt_in_wishlist = opt_in
        profile_main.save(update_fields=["email_opt_in_wishlist"])

        # Validare SMS: buton "Validare"
        if request.POST.get("action") == "validare":
            from django.conf import settings
            from django.utils import timezone
            from .sms import send_sms_verification
            import random

            phone = (profile.telefon or "").strip()
            code_entered = _sms_code_from_request(request)

            if code_entered:
                if _validate_sms_code_and_mark_verified(request, profile):
                    messages.success(request, "Telefon verificat cu succes.")
                    return redirect("cont_profil")
                messages.error(request, "Cod incorect sau expirat. Încercați din nou sau solicitați un cod nou.")
            elif phone:
                dev_code = getattr(settings, "SMS_DEV_CODE", "") or ""
                code = dev_code if dev_code and len(dev_code) == 6 else "".join(str(random.randint(0, 9)) for _ in range(6))
                request.session["sms_verification_code"] = code
                request.session["sms_verification_sent_at"] = timezone.now().timestamp()
                request.session["sms_verification_phone"] = phone
                if send_sms_verification(phone, code):
                    messages.success(request, "Cod trimis pe SMS. Introduceți cele 6 cifre mai jos.")
                else:
                    messages.error(request, "Nu s-a putut trimite SMS. Verificați numărul de telefon.")
                return redirect("cont_profil")
            else:
                messages.warning(request, "Completați mai întâi numărul de telefon și salvați profilul.")

        # La „Salvează profilul”: dacă utilizatorul a completat codul SMS, validăm și acesta
        code_entered = _sms_code_from_request(request)
        if code_entered and request.POST.get("action") != "validare":
            from django.conf import settings
            from django.utils import timezone
            dev_code = getattr(settings, "SMS_DEV_CODE", "") or ""
            session_code = request.session.get("sms_verification_code")
            session_ts = request.session.get("sms_verification_sent_at")
            valid = False
            if session_code and session_ts and (timezone.now().timestamp() - session_ts) < 600:
                valid = code_entered == session_code
            if not valid and dev_code and code_entered == dev_code:
                valid = True
            if valid:
                profile.phone_verified = True
                profile.save(update_fields=["phone_verified"])
                for key in ("sms_verification_code", "sms_verification_sent_at", "sms_verification_phone"):
                    request.session.pop(key, None)

        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            if request.POST.get("action") != "validare":
                messages.success(request, "Profil actualizat.")
            return _safe_next_redirect(request, "home")
    else:
        form = UserProfileForm(instance=profile)
    next_url = request.session.get("next_after_profile_save") or request.GET.get("next") or request.POST.get("next") or ""
    # Animalele adăugate de user (pentru MyPets – listă în cont)
    my_pets = Pet.objects.filter(added_by_user=request.user).order_by("-data_adaugare")
    my_pets_count_total = my_pets.count()
    # În procedura de adoptie = animale care au cel puțin o cerere de adoptie aprobată
    approved_statuses = ["approved", "approved_ong", "approved_platform"]
    my_pets_with_approved = my_pets.filter(adoption_requests__status__in=approved_statuses).distinct()
    my_pets_count_in_procedura = my_pets_with_approved.count()
    my_pets_in_procedura_ids = set(my_pets_with_approved.values_list("pk", flat=True))
    my_pets_count_adopted = my_pets.filter(status="adopted").count()
    return render(request, "anunturi/cont-profil.html", {
        "form": form,
        "profile_main": profile_main,
        "profile": profile,
        "next_url": next_url,
        "my_pets": my_pets,
        "my_pets_count_total": my_pets_count_total,
        "my_pets_count_in_procedura": my_pets_count_in_procedura,
        "my_pets_in_procedura_ids": my_pets_in_procedura_ids,
        "my_pets_count_adopted": my_pets_count_adopted,
    })


def cont_ong_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    profile = getattr(request.user, "ong_profile", None)
    # Poza user pentru fișa clientului (UserProfile.poza_1; ONG nu are poza pe OngProfile)
    user_photo = None
    try:
        up = UserProfile.objects.get(user=request.user)
        if up.poza_1:
            user_photo = up.poza_1
    except UserProfile.DoesNotExist:
        pass
    # Animale: fie cu ong_email = email ONG, fie adăugate de user (added_by_user) – ca să apară și în MyPets
    if profile and profile.email:
        pets = Pet.objects.filter(Q(ong_email=profile.email) | Q(added_by_user=request.user)).distinct().order_by("-data_adaugare")
    else:
        pets = Pet.objects.filter(added_by_user=request.user).order_by("-data_adaugare")
    pets_count_total = pets.count()
    # În procedura de adoptie = animale care au cel puțin o cerere de adoptie aprobată (de user/ONG)
    approved_statuses = ["approved", "approved_ong", "approved_platform"]
    pets_with_approved_request = pets.filter(adoption_requests__status__in=approved_statuses).distinct()
    pets_count_in_procedura = pets_with_approved_request.count()
    pets_in_procedura_ids = set(pets_with_approved_request.values_list("pk", flat=True))
    pets_count_adopted = pets.filter(status="adopted").count()
    # Rezervări active: cereri APPROVED pentru animale ale adăpostului, cu pet încă reserved
    rezervari_active = list(
        AdoptionRequest.objects.filter(
            pet__in=pets,
            status__in=APPROVED_RESERVATION_STATUSES,
            pet__adoption_status="reserved",
        ).select_related("pet", "adopter").order_by("-data_cerere")
    )
    return render(request, "anunturi/cont-ong.html", {
        "profile": profile,
        "pets": pets,
        "user_photo": user_photo,
        "pets_count_total": pets_count_total,
        "pets_count_in_procedura": pets_count_in_procedura,
        "pets_in_procedura_ids": pets_in_procedura_ids,
        "pets_count_adopted": pets_count_adopted,
        "rezervari_active": rezervari_active,
    })


def _unique_slug_for_pet(nume):
    """Generează un slug unic pornind de la nume."""
    base = slugify(nume) or "animal"
    base = base[:120]
    slug = base
    n = 0
    while Pet.objects.filter(slug=slug).exists():
        n += 1
        suffix = f"-{n}"
        slug = (base[: 120 - len(suffix)] + suffix) if len(base) + len(suffix) > 120 else base + suffix
    return slug


@require_phone_verified
def cont_adauga_animal_view(request):
    """Fișă înregistrare animal pentru persoană fizică. Max 4 animale pe lună per user. Necesită telefon verificat."""
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin:anunturi_pet_add")

    # Limită 4 anunțuri pe lună pentru PF
    from django.utils import timezone
    start_of_month = timezone.now().replace(day=1, hour=0, minute=0, second=0, microsecond=0)
    count_luna = Pet.objects.filter(added_by_user=request.user, data_adaugare__gte=start_of_month).count()
    if count_luna >= 4 and request.method != "POST":
        messages.warning(request, "Ați atins limita de 4 prieteni adăugați în luna curentă. Încercați luna viitoare.")
        return redirect("cont_profil")

    if request.method == "POST":
        form = PetAdaugaForm(request.POST, request.FILES)
        if form.is_valid():
            if count_luna >= 4:
                messages.warning(request, "Ați atins limita de 4 prieteni în luna curentă. Încercați luna viitoare.")
                return redirect("cont_profil")
            pet = form.save(commit=False)
            contact = _get_contact_for_pet_from_user(request.user)
            pet.judet = contact["judet"]
            pet.ong_email = contact["ong_email"]
            pet.ong_address = contact["ong_address"]
            pet.ong_contact_person = contact["ong_contact_person"]
            pet.ong_phone = contact["ong_phone"]
            pet.ong_visiting_hours = contact["ong_visiting_hours"]
            pet.slug = _unique_slug_for_pet(pet.nume)
            pet.status = "adoptable"
            pet.added_by_user = request.user
            pet.save()
            messages.success(request, f"Animalul „{pet.nume}” a fost adăugat. Îl veți vedea în lista de prieteni.")
            return redirect("pets_single", pk=pet.pk)
    else:
        form = PetAdaugaForm()
    form_sections = [(t, [form[f] for f in n if f in form.fields]) for t, n in PET_ADAUGA_SECTIONS]
    return render(request, "anunturi/cont-adauga-animal.html", {"form": form, "form_sections": form_sections})


@require_phone_verified
def cont_ong_adauga_view(request):
    """Fișă înregistrare animal pentru ONG/SRL. Fără limită de animale pe lună. Necesită telefon verificat."""
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin:anunturi_pet_add")

    if request.method == "POST":
        form = PetAdaugaForm(request.POST, request.FILES)
        if form.is_valid():
            pet = form.save(commit=False)
            contact = _get_contact_for_pet_from_user(request.user)
            pet.judet = contact["judet"]
            pet.ong_email = contact["ong_email"]
            pet.ong_address = contact["ong_address"]
            pet.ong_contact_person = contact["ong_contact_person"]
            pet.ong_phone = contact["ong_phone"]
            pet.ong_visiting_hours = contact["ong_visiting_hours"]
            pet.slug = _unique_slug_for_pet(pet.nume)
            pet.status = "adoptable"
            pet.added_by_user = request.user
            pet.save()
            messages.success(request, f"Animalul „{pet.nume}” a fost adăugat.")
            return redirect("cont_ong")
    else:
        form = PetAdaugaForm()
    form_sections = [(t, [form[f] for f in n if f in form.fields]) for t, n in PET_ADAUGA_SECTIONS]
    return render(request, "anunturi/cont-ong-adauga.html", {"form": form, "form_sections": form_sections})


def _parse_bulk_common(request):
    """Extrage și validează datele comune din POST. Returnează (errors_dict, data_dict)."""
    err = {}
    data = {}
    data["judet"] = (request.POST.get("common_judet") or "").strip()
    data["localitate"] = (request.POST.get("common_localitate") or "").strip()
    data["adresa"] = (request.POST.get("common_adresa") or "").strip()
    data["pickup"] = (request.POST.get("common_pickup") or "").strip()
    data["phone"] = (request.POST.get("common_phone") or "").strip()
    data["email"] = (request.POST.get("common_email") or "").strip()
    adapost = (request.POST.get("common_adapost_public") or "").strip().lower()
    if adapost not in ("da", "nu"):
        err["common_adapost_public"] = "Răspundeți obligatoriu: Sunteți adăpost public? DA sau NU."
    data["adapost_public"] = adapost == "da"
    if not data["judet"]:
        err["common_judet"] = "Selectați județul."
    if not data["adresa"]:
        err["common_adresa"] = "Adresa completă a organizației este obligatorie."
    if not data["phone"]:
        err["common_phone"] = "Telefonul de contact este obligatoriu."
    if not data["email"]:
        err["common_email"] = "Emailul de contact este obligatoriu."
    return err, data


def _parse_bulk_dog(request, index, adapost_public):
    """Extrage datele unui card câine. Returnează (errors_list, data_dict sau None)."""
    prefix = f"dog_{index}_"
    data = {}
    data["nume"] = (request.POST.get(prefix + "nume") or "").strip()
    data["tip"] = (request.POST.get(prefix + "tip") or "").strip() or "dog"
    data["sex"] = (request.POST.get(prefix + "sex") or "").strip()
    data["age_years"] = request.POST.get(prefix + "age_years")
    data["marime"] = (request.POST.get(prefix + "marime") or "").strip()
    data["descriere"] = (request.POST.get(prefix + "descriere") or "").strip()
    data["cip"] = (request.POST.get(prefix + "cip") or "").strip()
    data["vaccin"] = (request.POST.get(prefix + "vaccin") or "").strip()
    data["carnet_sanatate"] = (request.POST.get(prefix + "carnet_sanatate") or "").strip()
    data["sterilizat"] = request.POST.get(prefix + "sterilizat") == "on"
    if not data["nume"]:
        return (["Numele câinelui este obligatoriu."], None)
    if data["tip"] not in ("dog", "cat", "other"):
        data["tip"] = "dog"
    if data["sex"] not in ("male", "female"):
        return ([f"Câine {index + 1}: selectați sexul."], None)
    try:
        ay = int(data["age_years"]) if data["age_years"] not in (None, "") else None
    except (TypeError, ValueError):
        ay = None
    if ay is None:
        return ([f"Câine „{data['nume']}”: vârsta (ani) este obligatorie și trebuie să fie număr întreg."], None)
    if not (0 <= ay <= 20):
        return ([f"Câine „{data['nume']}”: vârsta trebuie între 0 și 20 ani."], None)
    data["age_years"] = ay
    if adapost_public:
        if not data["cip"]:
            return ([f"Câine „{data['nume']}”: pentru adăpost public, CIP este obligatoriu."], None)
        if not data["carnet_sanatate"]:
            return ([f"Câine „{data['nume']}”: pentru adăpost public, carnetul de sănătate este obligatoriu."], None)
        data["sterilizat"] = True
    data["imagine"] = request.FILES.get(prefix + "imagine")
    data["imagine_2"] = request.FILES.get(prefix + "imagine_2")
    data["imagine_3"] = request.FILES.get(prefix + "imagine_3")
    if not data["imagine"] or not data["imagine_2"] or not data["imagine_3"]:
        return ([f"Câine „{data['nume']}”: sunt obligatorii minim 3 poze."], None)
    return ([], data)


@require_phone_verified
def cont_bulk_add_dogs_view(request):
    """Adăugare în serie (bulk) câini pentru ONG/adăpost. Aceleași condiții de acces ca cont_ong_adauga."""
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin:anunturi_pet_add")

    contact_initial = _get_contact_for_pet_from_user(request.user)
    ctx = {
        "judet_choices": Pet.JUDET_CHOICES,
        "tip_choices": Pet.TIP_CHOICES,
        "sex_choices": Pet.SEX_CHOICES,
        "marime_choices": Pet.MARIME_CHOICES,
        "contact_initial": contact_initial,
        "common_errors": {},
        "dog_errors": {},
    }

    if request.method == "POST":
        common_errors, common = _parse_bulk_common(request)
        ctx["common_errors"] = common_errors
        ctx["common_data"] = request.POST
        dog_count_val = request.POST.get("dog_count")
        try:
            dog_count = max(0, int(dog_count_val)) if dog_count_val else 0
        except (TypeError, ValueError):
            dog_count = 0
        if dog_count == 0:
            common_errors.setdefault("form_errors", [])
            common_errors["form_errors"].append("Adăugați cel puțin un câine (folosiți butonul „Adaugă încă un câine”).")
        dogs_data = []
        dog_errors = {}
        for i in range(dog_count):
            errs, d = _parse_bulk_dog(request, i, common.get("adapost_public", False))
            if errs:
                dog_errors[i] = errs
            elif d:
                dogs_data.append(d)
        if dog_errors:
            ctx["dog_errors"] = dog_errors
        if not common_errors and not dog_errors and dogs_data:
            ong_address = (common["localitate"] + ", " + common["adresa"]).strip(", ") or common["adresa"]
            for d in dogs_data:
                pet = Pet(
                    nume=d["nume"],
                    slug=_unique_slug_for_pet(d["nume"]),
                    tip=d["tip"],
                    sex=d["sex"],
                    age_years=d["age_years"],
                    marime=d["marime"] or "",
                    descriere=d["descriere"],
                    descriere_personalitate=d["descriere"][:500] if d["descriere"] else "",
                    judet=common["judet"],
                    ong_email=common["email"],
                    ong_address=ong_address,
                    ong_phone=common["phone"],
                    ong_pickup_address=common["pickup"],
                    ong_contact_person=contact_initial.get("ong_contact_person", ""),
                    ong_visiting_hours=contact_initial.get("ong_visiting_hours", ""),
                    adapost_public=common["adapost_public"],
                    cip=d["cip"],
                    vaccin=d["vaccin"],
                    carnet_sanatate=d["carnet_sanatate"],
                    sterilizat=d["sterilizat"],
                    status="adoptable",
                    adoption_status="available",
                    added_by_user=request.user,
                    rasa="Metis",
                )
                pet.imagine = d["imagine"]
                pet.imagine_2 = d["imagine_2"]
                pet.imagine_3 = d["imagine_3"]
                pet.save()
            messages.success(request, f"Au fost adăugați {len(dogs_data)} câini.")
            return redirect("cont_ong")
        ctx["dog_count"] = max(dog_count, 1)
        dog_count = ctx["dog_count"]
        dog_values = []
        for i in range(dog_count):
            p = request.POST
            dog_values.append({
                "nume": p.get("dog_%s_nume" % i) or "",
                "tip": p.get("dog_%s_tip" % i) or "dog",
                "sex": p.get("dog_%s_sex" % i) or "",
                "age_years": p.get("dog_%s_age_years" % i) or "",
                "marime": p.get("dog_%s_marime" % i) or "",
                "descriere": p.get("dog_%s_descriere" % i) or "",
                "cip": p.get("dog_%s_cip" % i) or "",
                "vaccin": p.get("dog_%s_vaccin" % i) or "",
                "carnet_sanatate": p.get("dog_%s_carnet_sanatate" % i) or "",
                "sterilizat": p.get("dog_%s_sterilizat" % i) == "on",
            })
        if not dog_values:
            dog_values = [{}]
        ctx["dog_values"] = dog_values
    else:
        ctx["common_data"] = {
            "common_judet": contact_initial.get("judet"),
            "common_localitate": "",
            "common_adresa": contact_initial.get("ong_address"),
            "common_pickup": "",
            "common_phone": contact_initial.get("ong_phone"),
            "common_email": contact_initial.get("ong_email") or request.user.email,
            "common_adapost_public": "",
        }
        ctx["dog_count"] = 1
        ctx["dog_values"] = [{}] * 1

    return render(request, "anunturi/cont-bulk-add-dogs.html", ctx)


# Statusuri considerate „adopție finalizată” pentru beneficii cupoane
def _user_has_finalized_adoption(user):
    """True dacă userul are cel puțin o cerere de adopție finalizată (status finalized sau approved/approved_ong)."""
    if not user or not user.is_authenticated:
        return False
    return AdoptionRequest.objects.filter(
        adopter=user,
        status__in=["finalized", "approved", "approved_ong"],
    ).exists()


def beneficii_adoptie_view(request):
    """Pagina Beneficii după adopție – cupoane parteneri. Acces: utilizatori logați; conținut complet doar dacă au cel puțin o adopție finalizată."""
    if not request.user.is_authenticated:
        messages.info(request, "Trebuie să vă autentificați pentru a vedea beneficiile.")
        return redirect("{}?next={}".format(reverse("login"), quote(request.build_absolute_uri())))

    has_finalized = _user_has_finalized_adoption(request.user)

    if request.method == "POST":
        action = (request.POST.get("action") or "").strip()
        if action == "claim":
            partner_id = request.POST.get("partner_id")
            try:
                partner = BeneficiaryPartner.objects.get(pk=partner_id, is_active=True)
            except (BeneficiaryPartner.DoesNotExist, ValueError):
                messages.error(request, "Partener invalid.")
            else:
                if not has_finalized:
                    messages.error(request, "Beneficiile sunt disponibile doar după finalizarea unei adopții.")
                else:
                    existing = CouponClaim.objects.filter(user=request.user, category=partner.category).first()
                    if existing:
                        messages.info(request, "Ai ales deja un cupon la această categorie.")
                    else:
                        claim = CouponClaim.objects.create(
                            user=request.user,
                            partner=partner,
                            category=partner.category,
                        )
                        send_coupon_claim_email_to_partner(claim)
                        send_coupon_confirmation_to_adoptor(claim)
                        messages.success(request, f"Ai ales cuponul: {partner.name}.")
                return redirect("beneficii_adoptie")
        elif action == "renounce":
            cat = (request.POST.get("category") or "").strip()
            if cat in (BENEFICIARY_CATEGORY_VET, BENEFICIARY_CATEGORY_GROOMING, BENEFICIARY_CATEGORY_SHOP):
                deleted, _ = CouponClaim.objects.filter(user=request.user, category=cat).delete()
                if deleted:
                    messages.success(request, "Ai renunțat la cuponul din această categorie.")
            return redirect("beneficii_adoptie")

    if not has_finalized:
        return render(request, "anunturi/beneficii-adoptie-info.html", {"has_finalized": False})

    partners_vet = list(BeneficiaryPartner.objects.filter(category=BENEFICIARY_CATEGORY_VET, is_active=True).order_by("order", "name"))
    partners_grooming = list(BeneficiaryPartner.objects.filter(category=BENEFICIARY_CATEGORY_GROOMING, is_active=True).order_by("order", "name"))
    partners_shop = list(BeneficiaryPartner.objects.filter(category=BENEFICIARY_CATEGORY_SHOP, is_active=True).order_by("order", "name"))
    claims_by_category = {
        c.category: c for c in CouponClaim.objects.filter(user=request.user).select_related("partner")
    }

    return render(request, "anunturi/beneficii-adoptie.html", {
        "has_finalized": has_finalized,
        "partners_vet": partners_vet,
        "partners_grooming": partners_grooming,
        "partners_shop": partners_shop,
        "claims_by_category": claims_by_category,
        "BENEFICIARY_CATEGORY_VET": BENEFICIARY_CATEGORY_VET,
        "BENEFICIARY_CATEGORY_GROOMING": BENEFICIARY_CATEGORY_GROOMING,
        "BENEFICIARY_CATEGORY_SHOP": BENEFICIARY_CATEGORY_SHOP,
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def analiza_view(request):
    """Pagina Analiza – doar pentru administratori: filtre și statistici (membri, animale, cereri)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    # Parametri filtre din GET
    data_from = request.GET.get("data_from", "")
    data_to = request.GET.get("data_to", "")
    status_pet = request.GET.get("status_pet", "")
    tip_pet = request.GET.get("tip_pet", "")
    judet = request.GET.get("judet", "")
    status_cerere = request.GET.get("status_cerere", "")

    # Perioadă (opțional) – pentru „în interval”
    qs_user = User.objects.all()
    qs_pet = Pet.objects.all()
    qs_cerere = AdoptionRequest.objects.all()

    if data_from:
        try:
            d = datetime.strptime(data_from, "%Y-%m-%d")
            qs_user = qs_user.filter(date_joined__date__gte=d.date())
            qs_pet = qs_pet.filter(data_adaugare__date__gte=d.date())
            qs_cerere = qs_cerere.filter(data_cerere__date__gte=d.date())
        except ValueError:
            pass
    if data_to:
        try:
            d = datetime.strptime(data_to, "%Y-%m-%d")
            qs_user = qs_user.filter(date_joined__date__lte=d.date())
            qs_pet = qs_pet.filter(data_adaugare__date__lte=d.date())
            qs_cerere = qs_cerere.filter(data_cerere__date__lte=d.date())
        except ValueError:
            pass
    if status_pet:
        qs_pet = qs_pet.filter(status=status_pet)
    if tip_pet:
        qs_pet = qs_pet.filter(tip=tip_pet)
    if judet:
        qs_pet = qs_pet.filter(judet=judet)
    if status_cerere:
        qs_cerere = qs_cerere.filter(status=status_cerere)

    # Statistici (tot și filtrat)
    stats = {
        "membri_total": User.objects.count(),
        "membri_filtrat": qs_user.count(),
        "animale_total": Pet.objects.count(),
        "animale_filtrat": qs_pet.count(),
        "animale_adoptable": Pet.objects.filter(status="adoptable").count(),
        "animale_adoptate": Pet.objects.filter(status="adopted").count(),
        "animale_in_procedura": Pet.objects.filter(status="pending").count(),
        "animale_showcase": Pet.objects.filter(status="showcase_archive").count(),
        "intrati_filtrat": qs_pet.filter(status="adoptable").count() if not status_pet else qs_pet.count(),
        "iesiti_filtrat": qs_pet.filter(status="adopted").count() if not status_pet else (qs_pet.filter(status="adopted").count() if status_pet == "adopted" else 0),
        "cereri_total": AdoptionRequest.objects.count(),
        "cereri_filtrat": qs_cerere.count(),
        "cereri_noua": AdoptionRequest.objects.filter(status__in=["new", "pending"]).count(),
        "cereri_aprobate_platforma": AdoptionRequest.objects.filter(status="approved_platform").count(),
        "cereri_validate_ong": AdoptionRequest.objects.filter(status="approved_ong").count(),
        "cereri_refuzate": AdoptionRequest.objects.filter(status="rejected").count(),
    }
    stats["intrati_filtrat"] = qs_pet.filter(status="adoptable").count()
    stats["iesiti_filtrat"] = qs_pet.filter(status="adopted").count()

    # Status membri
    stats["membri_activi"] = User.objects.filter(is_active=True).count()
    stats["membri_inactivi"] = User.objects.filter(is_active=False).count()
    stats["membri_staff"] = User.objects.filter(is_staff=True).count()
    stats["membri_superuser"] = User.objects.filter(is_superuser=True).count()
    stats["membri_nelogati_niciodata"] = User.objects.filter(last_login__isnull=True).count()
    stats["membri_cu_profil"] = Profile.objects.count()

    return render(request, "anunturi/analiza.html", {
        "stats": stats,
        "filters": {
            "data_from": data_from,
            "data_to": data_to,
            "status_pet": status_pet,
            "tip_pet": tip_pet,
            "judet": judet,
            "status_cerere": status_cerere,
        },
        "pet_status_choices": Pet.STATUS_CHOICES,
        "pet_tip_choices": Pet.TIP_CHOICES,
        "judet_choices": Pet.JUDET_CHOICES,
        "cerere_status_choices": AdoptionRequest.STATUS_CHOICES,
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def membri_list_view(request):
    """Lista membri – doar staff. Filtre: data_from, data_to, status (activi, inactivi, staff, superuser, nelogati, cu_profil)."""
    from django.contrib.auth import get_user_model
    User = get_user_model()

    qs = User.objects.all().order_by("-date_joined")
    data_from = request.GET.get("data_from", "")
    data_to = request.GET.get("data_to", "")
    status = request.GET.get("status", "")

    if data_from:
        try:
            d = datetime.strptime(data_from, "%Y-%m-%d")
            qs = qs.filter(date_joined__date__gte=d.date())
        except ValueError:
            pass
    if data_to:
        try:
            d = datetime.strptime(data_to, "%Y-%m-%d")
            qs = qs.filter(date_joined__date__lte=d.date())
        except ValueError:
            pass
    if status == "activi":
        qs = qs.filter(is_active=True)
    elif status == "inactivi":
        qs = qs.filter(is_active=False)
    elif status == "staff":
        qs = qs.filter(is_staff=True)
    elif status == "superuser":
        qs = qs.filter(is_superuser=True)
    elif status == "nelogati":
        qs = qs.filter(last_login__isnull=True)
    elif status == "cu_profil":
        qs = qs.filter(profile__isnull=False)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "anunturi/membri-list.html", {
        "page_obj": page_obj,
        "membri": page_obj.object_list,
        "filters": {"data_from": data_from, "data_to": data_to, "status": status},
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def analiza_animale_view(request):
    """Lista animale pentru Analiza – staff. Filtre ca în Analiza."""
    qs = Pet.objects.all().order_by("-data_adaugare")
    data_from = request.GET.get("data_from", "")
    data_to = request.GET.get("data_to", "")
    status_pet = request.GET.get("status_pet", "")
    tip_pet = request.GET.get("tip_pet", "")
    judet = request.GET.get("judet", "")

    if data_from:
        try:
            d = datetime.strptime(data_from, "%Y-%m-%d")
            qs = qs.filter(data_adaugare__date__gte=d.date())
        except ValueError:
            pass
    if data_to:
        try:
            d = datetime.strptime(data_to, "%Y-%m-%d")
            qs = qs.filter(data_adaugare__date__lte=d.date())
        except ValueError:
            pass
    if status_pet:
        qs = qs.filter(status=status_pet)
    if tip_pet:
        qs = qs.filter(tip=tip_pet)
    if judet:
        qs = qs.filter(judet=judet)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "anunturi/analiza-animale.html", {
        "page_obj": page_obj,
        "animale": page_obj.object_list,
        "filters": {"data_from": data_from, "data_to": data_to, "status_pet": status_pet, "tip_pet": tip_pet, "judet": judet},
        "pet_status_choices": Pet.STATUS_CHOICES,
        "pet_tip_choices": Pet.TIP_CHOICES,
        "judet_choices": Pet.JUDET_CHOICES,
    })


@login_required
@user_passes_test(lambda u: u.is_staff, login_url="/login/")
def analiza_cereri_view(request):
    """Lista cereri adopție pentru Analiza – staff. Filtre: data_from, data_to, status_cerere."""
    qs = AdoptionRequest.objects.select_related("pet").order_by("-data_cerere")
    data_from = request.GET.get("data_from", "")
    data_to = request.GET.get("data_to", "")
    status_cerere = request.GET.get("status_cerere", "")

    if data_from:
        try:
            d = datetime.strptime(data_from, "%Y-%m-%d")
            qs = qs.filter(data_cerere__date__gte=d.date())
        except ValueError:
            pass
    if data_to:
        try:
            d = datetime.strptime(data_to, "%Y-%m-%d")
            qs = qs.filter(data_cerere__date__lte=d.date())
        except ValueError:
            pass
    if status_cerere:
        qs = qs.filter(status=status_cerere)

    paginator = Paginator(qs, 25)
    page_obj = paginator.get_page(request.GET.get("page", 1))

    return render(request, "anunturi/analiza-cereri.html", {
        "page_obj": page_obj,
        "cereri": page_obj.object_list,
        "filters": {"data_from": data_from, "data_to": data_to, "status_cerere": status_cerere},
        "cerere_status_choices": AdoptionRequest.STATUS_CHOICES,
    })


def debug_send_test_email(request):
    """
    Endpoint temporar: trimite un email de test. Doar DEBUG sau staff.
    GET ?to=email@exemplu.ro sau setare DEBUG_TEST_EMAIL în .env.
    """
    import logging
    from django.conf import settings
    from django.core.mail import send_mail

    logger = logging.getLogger(__name__)
    if not settings.DEBUG and not (request.user.is_authenticated and request.user.is_staff):
        logger.warning("debug_send_test_email: acces refuzat (nu DEBUG, nu staff)")
        return HttpResponseForbidden("Acces interzis.")

    to_email = (request.GET.get("to") or "").strip() or getattr(settings, "DEBUG_TEST_EMAIL", "") or ""
    if not to_email or "@" not in to_email:
        msg = "Lipseste ?to=email@exemplu.ro sau DEBUG_TEST_EMAIL in .env"
        logger.warning("debug_send_test_email: %s", msg)
        return HttpResponse(msg, status=400)

    from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
    subject = "[EU-Adopt] Email de test"
    body = "Acesta este un email de test trimis de la endpoint-ul /debug/send-test-email/. Daca l-ai primit, SMTP-ul functioneaza."

    try:
        send_mail(subject, body, from_email, [to_email], fail_silently=False)
        logger.info("debug_send_test_email: trimis cu succes la %s", to_email)
        print(f"[DEBUG] send-test-email: OK trimis la {to_email}")
        return HttpResponse(f"Email trimis cu succes la {to_email}. Verifica inbox (si spam).")
    except Exception as e:
        logger.exception("debug_send_test_email: eroare la trimitere")
        print(f"[DEBUG] send-test-email: EXCEPTIE {e}")
        return HttpResponse(f"Eroare la trimitere: {e}", status=500)


def localitati_pe_judet_json_view(request):
    """Servește JSON-ul cu localitățile pe județ (slug keys). Pentru ro_counties_cities vedea ro_counties_cities_json_view."""
    import json
    path = settings.BASE_DIR / "static" / "data" / "localitati-pe-judet.json"
    if not path.exists():
        return JsonResponse({}, status=404)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        return JsonResponse(data)
    except Exception:
        return JsonResponse({}, status=500)


def ro_counties_cities_json_view(request):
    """Servește ro_counties_cities.json: { "Neamț": [...], ... } + by_slug: { "neamt": [...], ... } pentru formuri cu value=slug."""
    import json
    from anunturi.models import Pet
    path = settings.BASE_DIR / "static" / "data" / "ro_counties_cities.json"
    if not path.exists():
        return JsonResponse({"by_slug": {}}, status=404)
    try:
        with open(path, "r", encoding="utf-8") as f:
            data = json.load(f)
        labels = dict(Pet.JUDET_CHOICES)
        by_slug = {}
        for slug, label in labels.items():
            if label in data:
                by_slug[slug] = data[label]
        data["by_slug"] = by_slug
        return JsonResponse(data)
    except Exception:
        return JsonResponse({"by_slug": {}}, status=500)


def transport_view(request):
    """Pagina Transport: T1 (formular comandă transport) + T2. Procesează POST și afișează mesajul după zona colaboratorilor (în oraș / județ / țară)."""
    from django.conf import settings
    from anunturi.models import Pet
    from anunturi.models import UserProfile
    from django.urls import reverse
    judet_choices = [("", "— Alege județul —")] + list(Pet.JUDET_CHOICES)
    google_maps_api_key = getattr(settings, "GOOGLE_MAPS_API_KEY", "") or ""
    judet_labels = dict(Pet.JUDET_CHOICES)
    context = {
        "judet_choices": judet_choices,
        "google_maps_api_key": google_maps_api_key,
        "localitati_json_url": request.build_absolute_uri(reverse("localitati_pe_judet_json")),
        "user_judet": "",
        "user_oras": "",
        "transport_submitted": False,
        "transport_result": None,
        "transport_count": 0,
        "transport_oras": "",
        "transport_judet_label": "",
    }
    if request.user.is_authenticated:
        try:
            up = UserProfile.objects.get(user=request.user)
            context["user_judet"] = (getattr(up, "judet", "") or "").strip()
            context["user_oras"] = (getattr(up, "oras", "") or "").strip()
        except UserProfile.DoesNotExist:
            pass
        if not context["user_judet"] or not context["user_oras"]:
            try:
                from anunturi.models import OngProfile
                op = OngProfile.objects.filter(user=request.user).first()
                if op:
                    if not context["user_judet"]:
                        context["user_judet"] = (getattr(op, "legal_judet", "") or getattr(op, "pickup_judet", "") or "").strip()
                    if not context["user_oras"]:
                        context["user_oras"] = (getattr(op, "legal_locality", "") or getattr(op, "pickup_locality", "") or "").strip()
            except Exception:
                pass

    if request.method == "POST" and request.user.is_authenticated:
        judet = (request.POST.get("judet") or "").strip()
        oras = (request.POST.get("oras") or "").strip()
        plecare = (request.POST.get("plecare") or "").strip()
        sosire = (request.POST.get("sosire") or "").strip()
        if judet and oras and plecare and sosire:
            # TODO: când există model colaboratori – interogare reală după judet, oras, scope (în oraș / județ / țară)
            # Acum simulare: exemplu cu colaboratori în oraș (count=3) pentru orice cerere
            count_in_oras = 3  # placeholder – înlocuit cu query colaboratori activi în acel oraș
            count_in_judet = 2  # placeholder – înlocuit cu query colaboratori în județ (fără oraș)
            count_in_tara = 1   # placeholder – înlocuit cu query colaboratori scope „în țară”

            context["transport_submitted"] = True
            context["transport_oras"] = oras
            context["transport_judet_label"] = judet_labels.get(judet, judet)

            if count_in_oras > 0:
                context["transport_result"] = "in_oras"
                context["transport_count"] = count_in_oras
            elif count_in_judet > 0:
                context["transport_result"] = "in_judet"
                context["transport_count"] = count_in_judet
            elif count_in_tara > 0:
                context["transport_result"] = "in_tara"
            else:
                context["transport_result"] = "none"
        # dacă lipsește judet/oras, rămâne formularul cu erori (nu setăm transport_submitted)

    return render(request, "anunturi/transport.html", context)


cages_view = TemplateView.as_view(template_name="anunturi/cages.html")
prietenul_tau_v2_view = TemplateView.as_view(template_name="animals/prietenul_tau_v2.html")


def _servicii_offers(tag_pairs, category_label, badge_examples):
    """Listă oferte pentru carduri 3/4/5: card minimal + date pentru detail panel.
    ACUM: poze și texte aleatorii (loremflickr, texte fixe).
    VIITOR: când avem colaboratori reali, ofertele vor folosi poza și datele din fișa
    partenerului (ex. BeneficiaryPartner sau profil asociat): logo/poză, nume, ofertă, descriere, etc."""
    base_img = "https://loremflickr.com/300/300"
    out = []
    for i, tags in enumerate(tag_pairs):
        name = "{} {}".format(category_label, i + 1)
        badge = badge_examples[i % len(badge_examples)]
        out.append({
            "logo_url": "{}/{}".format(base_img, ",".join(tags)),
            "name": name,
            "badge": badge,
            "short_desc": "Ofertă partener Eu-adopt pentru adoptanți.",
            "panel_title": "Ofertă {}".format(name),
            "panel_description": "Descriere completă a ofertei. Beneficiile pentru adoptanți și condițiile de utilizare sunt detaliate mai jos.",
            "panel_includes": "Consult veterinar / produs / serviciu conform ofertei; prezentare cod partener.",
            "panel_location": "Locație și contact vor fi comunicate după finalizarea adopției.",
            "panel_validity": "Valabil 90 de zile de la finalizarea adopției.",
            "panel_conditions": "Oferta este valabilă pentru adoptanți care au finalizat adopția prin platformă. Prezentați codul primit pe email.",
        })
    return out


def servicii_view(request):
    import itertools
    strip_pets = list(
        Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:40]
    )
    if strip_pets and len(strip_pets) < 12:
        strip_pets = list(itertools.islice(itertools.cycle(strip_pets), 24))
    _vet_tags = [
        ("veterinary", "clinic"), ("dog", "veterinary"), ("cat", "veterinary"), ("vet", "animal"),
        ("veterinary", "dog"), ("pet", "clinic"), ("veterinary", "cat"), ("animal", "clinic"),
        ("veterinary", "pet"), ("dog", "clinic"), ("vet", "dog"), ("vet", "cat"),
    ]
    _shop_tags = [
        ("pet", "shop"), ("pet", "store"), ("dog", "shop"), ("cat", "shop"),
        ("pet", "store"), ("animal", "shop"), ("pet", "food"), ("dog", "store"),
        ("pet", "shop"), ("cat", "store"), ("pet", "products"), ("animal", "store"),
    ]
    _groom_tags = [
        ("dog", "grooming"), ("pet", "grooming"), ("dog", "bath"), ("cat", "grooming"),
        ("dog", "salon"), ("pet", "bath"), ("grooming", "dog"), ("dog", "hair"),
        ("pet", "salon"), ("dog", "grooming"), ("cat", "bath"), ("animal", "grooming"),
    ]
    # Oferte pentru zone 3/4/5. Momentan date aleatorii; la colaboratori reali → poza și date din fișa partenerului.
    slot3_offers = _servicii_offers(_vet_tags, "Cabinet vet", ["-10%", "Pachet Start", "Consultație la jumătate preț"])
    slot4_offers = _servicii_offers(_shop_tags, "Magazin", ["-15%", "Prima vizită gratuită", "Reducere 20%"])
    slot5_offers = _servicii_offers(_groom_tags, "Salon", ["-10%", "Băi 2+1 gratis", "Pachet cosmetica"])
    import json
    servicii_offers_json = json.dumps({"3": slot3_offers, "4": slot4_offers, "5": slot5_offers})
    # 2.1, 2.2, 2.3 – reclame mâncare (poze reale)
    slot2_ads = [
        {"url": "https://loremflickr.com/200/200/dog,food", "title": "Reclamă mâncare 1"},
        {"url": "https://loremflickr.com/200/200/cat,food", "title": "Reclamă mâncare 2"},
        {"url": "https://loremflickr.com/200/200/pet,food", "title": "Reclamă mâncare 3"},
    ]
    # Link comun de test – toate linkurile din casete duc aici (proba: Google)
    servicii_test_link = "https://www.google.com"
    # Caseta 7 – reclamă mare (pet store / Maxi Pet)
    slot7_ad = {
        "url": "https://loremflickr.com/400/400/pet,store",
        "title": "Reclamă Maxi Pet",
        "link": servicii_test_link,
    }
    selected_judet = ""
    servicii_user_photo_url = ""
    if request.user.is_authenticated:
        try:
            selected_judet = (getattr(request.user.user_profile, "judet", "") or "").strip()
        except (UserProfile.DoesNotExist, AttributeError):
            pass
        try:
            up = UserProfile.objects.get(user=request.user)
            if up.poza_1:
                servicii_user_photo_url = up.poza_1.url
        except UserProfile.DoesNotExist:
            pass
    return render(request, "anunturi/servicii.html", {
        "strip_pets": strip_pets,
        "slot3_offers": slot3_offers,
        "slot4_offers": slot4_offers,
        "slot5_offers": slot5_offers,
        "servicii_offers_json": servicii_offers_json,
        "slot2_ads": slot2_ads,
        "slot7_ad": slot7_ad,
        "servicii_test_link": servicii_test_link,
        "judet_choices": [("", "Județ")] + list(JUDET_CHOICES),
        "selected_judet": selected_judet,
        "servicii_user_photo_url": servicii_user_photo_url,
    })


shop_view = TemplateView.as_view(template_name="anunturi/shop.html")
contact_view = TemplateView.as_view(template_name="anunturi/contact.html")
termeni_view = TemplateView.as_view(template_name="anunturi/termeni.html")
schema_site_view = TemplateView.as_view(template_name="anunturi/schema-site.html")