from django.shortcuts import render, get_object_or_404, redirect
from django.core.paginator import Paginator
from django.contrib import messages
from django.contrib.auth import login
from django.views.generic import TemplateView

from .models import Pet, AdoptionRequest, Profile, UserProfile, OngProfile
from .forms import (
    AdoptionRequestForm,
    UserRegistrationForm,
    UserProfileForm,
    RegisterPFForm,
    RegisterSRLForm,
    RegisterONGForm,
)
from .adoption_platform import platform_validation_passes, send_adoption_request_to_ong
from .contest_service import get_active_contest, get_contest_leaderboard, get_remaining_days


def home(request):
    featured = list(Pet.objects.filter(featured=True, status="adoptable")[:6])
    latest_qs = Pet.objects.filter(status="adoptable").order_by("-data_adaugare")
    latest = list(latest_qs[:14])
    # Dacă sunt mai puțin de 6 la Animalele lunii, completăm până la 6 (2x3) cu cele mai noi
    if len(featured) < 6:
        ids = {p.pk for p in featured}
        available = list(latest_qs.exclude(pk__in=ids))
        # Dacă nu sunt suficiente, repetăm din cele disponibile
        import itertools
        if available:
            for p in itertools.islice(itertools.cycle(available), 6 - len(featured)):
                featured.append(p)
        else:
            # Dacă nu există deloc animale, repetăm din featured
            if featured:
                for p in itertools.islice(itertools.cycle(featured), 6 - len(featured)):
                    featured.append(p)
    latest = latest[:14]
    # Poze pentru burtiera mică (bandă deasupra slider-ului mare); dacă sunt puține, le dublăm
    strip_pets = list(Pet.objects.filter(status="adoptable").order_by("-data_adaugare")[:40])
    if strip_pets and len(strip_pets) < 12:
        import itertools
        strip_pets = list(itertools.islice(itertools.cycle(strip_pets), 24))
    
    # Date concurs
    contest = get_active_contest()
    remaining_days = get_remaining_days(contest) if contest else 0
    top_users = get_contest_leaderboard(limit=10, contest=contest) if contest else []
    
    return render(request, "anunturi/home.html", {
        "featured_pets": featured,
        "latest_pets": latest,
        "strip_pets": strip_pets,
        "contest": contest,
        "remaining_days": remaining_days,
        "top_users": top_users,
    })


PETS_PER_PAGE = 12


def pets_all(request):
    qs = Pet.objects.filter(status="adoptable").order_by("-data_adaugare")
    tip = request.GET.get("tip")
    if tip in ("dog", "cat", "other"):
        qs = qs.filter(tip=tip)
    vip = request.GET.get("vip")
    if vip == "1":
        qs = qs.filter(featured=True)
    paginator = Paginator(qs, PETS_PER_PAGE)
    page_number = request.GET.get("page", 1)
    try:
        page_number = max(1, int(page_number))
    except (TypeError, ValueError):
        page_number = 1
    page_obj = paginator.get_page(page_number)
    # Query string pentru linkuri paginare (păstrăm tip, vip, fără page)
    q = request.GET.copy()
    if "page" in q:
        q.pop("page")
    pagination_query = q.urlencode()
    # Poze pentru burtiera mică (bandă deasupra slider-ului mare); dacă sunt puține, le dublăm
    strip_pets = list(Pet.objects.filter(status="adoptable").order_by("-data_adaugare")[:40])
    if strip_pets and len(strip_pets) < 12:
        import itertools
        strip_pets = list(itertools.islice(itertools.cycle(strip_pets), 24))
    return render(request, "anunturi/pets-all.html", {
        "page_obj": page_obj,
        "pets": page_obj.object_list,
        "current_tip": tip,
        "current_vip": vip,
        "strip_pets": strip_pets,
        "pagination_query": pagination_query,
    })


def pets_single(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    form = AdoptionRequestForm()
    return render(request, "anunturi/pets-single.html", {
        "pet": pet,
        "adoption_form": form,
    })


def adoption_request_submit(request, pk):
    pet = get_object_or_404(Pet, pk=pk)
    if request.method != "POST":
        return redirect("pets_single", pk=pk)
    form = AdoptionRequestForm(request.POST)
    if not form.is_valid():
        return render(request, "anunturi/pets-single.html", {
            "pet": pet,
            "adoption_form": form,
        })
    adoption_request = form.save(commit=False)
    adoption_request.pet = pet
    adoption_request.status = "new"
    adoption_request.save()

    if platform_validation_passes(adoption_request):
        adoption_request.status = "approved_platform"
        adoption_request.save()
        send_adoption_request_to_ong(adoption_request, request)
        messages.success(request, "Cererea a fost trimisă. Vă vom contacta în curând.")
    else:
        messages.info(request, "Cererea a fost înregistrată. Echipa noastră o va verifica și vă vom contacta.")

    return redirect("pets_single", pk=pk)


def signup_view(request):
    # Dacă utilizatorul este deja autentificat, redirecționează către profilul său
    if request.user.is_authenticated:
        from django.contrib.auth.models import Group
        is_ong = request.user.groups.filter(name="Asociație").exists()
        if is_ong:
            return redirect("cont_ong")
        else:
            return redirect("cont_profil")
    if request.method == "POST":
        form = UserRegistrationForm(request.POST)
        if form.is_valid():
            user = form.save()
            tip = form.cleaned_data.get("tip_cont", "pf")
            if tip == "pf":
                UserProfile.objects.get_or_create(user=user, defaults={
                    "nume": (form.cleaned_data.get("nume") or "").strip(),
                    "prenume": (form.cleaned_data.get("prenume") or "").strip(),
                    "telefon": (form.cleaned_data.get("telefon") or "").strip(),
                    "oras": (form.cleaned_data.get("oras") or "").strip(),
                })
            elif tip in ("srl_pfa_af", "ong"):
                sub = form.cleaned_data.get("tip_org_organizatie") or form.cleaned_data.get("tip_org_ong") or "ong"
                OngProfile.objects.get_or_create(user=user, defaults={
                    "denumire_legala": (form.cleaned_data.get("denumire_legala") or "").strip(),
                    "cui": (form.cleaned_data.get("cui") or "").strip(),
                    "numar_registru": (form.cleaned_data.get("numar_registru") or "").strip(),
                    "email": (form.cleaned_data.get("email_contact") or "").strip(),
                    "judet": (form.cleaned_data.get("judet") or "").strip(),
                    "oras": (form.cleaned_data.get("oras_org") or "").strip(),
                    "telefon": (form.cleaned_data.get("telefon_org") or "").strip(),
                    "persoana_responsabila_adoptii": (form.cleaned_data.get("persoana_responsabila_adoptii") or "").strip(),
                    "reprezentant_legal": (form.cleaned_data.get("reprezentant_legal") or "").strip(),
                    "tip_organizatie": sub if sub in ("srl", "pfa", "ong", "af") else "ong",
                })
            login(request, user)
            messages.success(request, "Cont creat. Bine ați venit!")
            return redirect("home")
    else:
        form = UserRegistrationForm()
    return render(request, "registration/signup.html", {"form": form})


def signup_verificare_telefon_view(request):
    """Pagina de introducere cod SMS pentru validare telefon. (Implementare completă: trimitere SMS și validare.)"""
    phone_masked = request.session.get("signup_phone_masked", "***")
    if request.method == "POST":
        # TODO: validare cod SMS și activare cont
        messages.info(request, "Funcția de validare SMS va fi activată în curând.")
        return redirect("home")
    return render(
        request,
        "registration/signup_verificare_telefon.html",
        {"phone_masked": phone_masked},
    )


def register_choose_type(request):
    """Pasul 1: Alege tipul contului (PF, SRL, ONG)."""
    if request.user.is_authenticated:
        return redirect("cont")
    return render(request, "registration/register_choose_type.html")


def register_pf(request):
    """Înregistrare Persoană Fizică."""
    if request.user.is_authenticated:
        return redirect("cont")
    if request.method == "POST":
        form = RegisterPFForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cont creat. Bine ați venit!")
            return redirect("cont")
    else:
        form = RegisterPFForm()
    return render(request, "registration/register_pf.html", {"form": form})


def register_srl(request):
    """Înregistrare SRL / Firmă."""
    if request.user.is_authenticated:
        return redirect("cont")
    if request.method == "POST":
        form = RegisterSRLForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cont firmă creat. Bine ați venit!")
            return redirect("cont")
    else:
        form = RegisterSRLForm()
    return render(request, "registration/register_srl.html", {"form": form})


def register_ong(request):
    """Înregistrare ONG / Asociație / Fundație."""
    if request.user.is_authenticated:
        return redirect("cont")
    if request.method == "POST":
        form = RegisterONGForm(request.POST)
        if form.is_valid():
            user = form.save()
            login(request, user)
            messages.success(request, "Cont organizație creat. Bine ați venit!")
            return redirect("cont")
    else:
        form = RegisterONGForm()
    return render(request, "registration/register_ong.html", {"form": form})


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


def cont_profil_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    profile, _ = UserProfile.objects.get_or_create(user=request.user)
    if request.method == "POST":
        form = UserProfileForm(request.POST, request.FILES, instance=profile)
        if form.is_valid():
            form.save()
            messages.success(request, "Profil actualizat.")
            return redirect("cont_profil")
    else:
        form = UserProfileForm(instance=profile)
    return render(request, "anunturi/cont-profil.html", {"form": form})


def cont_ong_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    profile = getattr(request.user, "ong_profile", None)
    pets = Pet.objects.filter(ong_email=profile.email) if profile and profile.email else Pet.objects.none()
    return render(request, "anunturi/cont-ong.html", {"profile": profile, "pets": pets})


def cont_adauga_animal_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin:anunturi_pet_add")
    return redirect("cont_profil")


def cont_ong_adauga_view(request):
    if not request.user.is_authenticated:
        return redirect("login")
    if request.user.is_staff:
        return redirect("admin:anunturi_pet_add")
    return redirect("cont_ong")


contact_view = TemplateView.as_view(template_name="anunturi/contact.html")
termeni_view = TemplateView.as_view(template_name="anunturi/termeni.html")
schema_site_view = TemplateView.as_view(template_name="anunturi/schema-site.html")