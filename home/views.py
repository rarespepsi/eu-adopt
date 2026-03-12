"""
Home views. Layout HOME înghețat: v. HOME_SLOTS.md
A0=navbar, A1=hero, A2=grid 4×3, A3=mission bar, A4=footer, A5=left sidebar (3), A6=right sidebar (3).
REGULĂ: Orice modificare în home (punct, virgulă, orice) doar cu aprobarea titularului, cu parolă.
"""
import random
from copy import deepcopy
from itertools import cycle
from django.shortcuts import render, redirect, get_object_or_404
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .data import DEMO_DOGS, DEMO_DOG_IMAGE, A2_QUOTE_POOL, HERO_SLIDER_IMAGES
from .models import WishlistItem, AnimalListing, UserAdoption

# A2 selection: 12 câini.
# Regula nouă: NEW = câini adăugați în ultimele 7 zile (din MyPet/AnimalListing),
# apoi completăm aleator din rest (inclusiv câini mai vechi) dacă nu avem suficienți.
A2_SLOT_COUNT = 12
A2_NEW_HOURS = 24 * 7


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
    if request.resolver_match.url_name == "pets_all":
        # P2: toți câinii activi; rândurile în funcție de număr; ultimul rând complet (4) prin repetare
        qs = AnimalListing.objects.filter(is_published=True).order_by("-created_at")
        p2_list = []
        if qs.exists():
            base_items = []
            for a in qs:
                base_items.append({
                    "pk": a.pk,
                    "nume": a.name or f"Pet #{a.pk}",
                    "imagine": a.photo_1,
                })
            # pornim de la lista de bază
            p2_list = list(base_items)
            n = len(p2_list)
            need = (4 - n % 4) % 4  # completează ultimul rând la 4 (repetă câini din listă)
            if need and p2_list:
                for i, item in enumerate(cycle(base_items)):
                    if i >= need:
                        break
                    p2_list.append(item)
            # ~10 rânduri în scroll (40 celule) – repetăm câinii existenți
            if p2_list and len(p2_list) <= 12:
                extra = 40
                for i, item in enumerate(cycle(base_items)):
                    if i >= extra:
                        break
                    p2_list.append(item)
        else:
            # Fallback demo (vechiul comportament) dacă nu avem încă animale reale
            for d in DEMO_DOGS:
                p2_list.append({
                    "pk": d["id"],
                    "nume": d["nume"],
                    "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
                    "traits": (d.get("traits") or [])[:2],
                })
            n = len(p2_list)
            need = (4 - n % 4) % 4  # completează ultimul rând la 4 (repetă câini din listă)
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
            wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
        return render(request, "anunturi/pt.html", {
            "p2_pets": p2_pets,
            "p2_pets_rest": p2_pets_rest,
            "strip_pets": strip_pets,
            "wishlist_ids": wishlist_ids,
        })

    is_home = request.resolver_match.url_name == "home"

    # Available dogs pentru PT (Prietenul tău) + A2.
    # 1) Preferăm animale reale din AnimalListing (is_published=True).
    # 2) Dacă nu există încă, folosim fallback DEMO_DOGS (comportament vechi).
    available_for_pt = []
    now = timezone.now()
    real_qs = AnimalListing.objects.filter(is_published=True).order_by("-created_at")
    if real_qs.exists():
        for a in real_qs:
            row = {
                "id": a.pk,
                "nume": a.name or f"Pet #{a.pk}",
                "varsta": a.age_label or "",
                "descriere": "",
                "imagine": a.photo_1,
                "added_at": a.created_at,
            }
            available_for_pt.append(row)
    else:
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
            "varsta": d.get("varsta", ""),
            "descriere": d.get("descriere", ""),
            "imagine": d.get("imagine"),
            "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
        }
        if is_home:
            pet["quote"] = random.choice(A2_QUOTE_POOL)
        a2_pets.append(pet)

    hero_slider_images = HERO_SLIDER_IMAGES[:5]
    show_welcome_demo = request.GET.get("welcome_demo") == "1"
    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
    # Pentru A3: număr animale active – dacă avem reale, le numărăm din AnimalListing.
    active_animals_count = real_qs.count() if real_qs.exists() else len(DEMO_DOGS)

    return render(request, "anunturi/home_v2.html", {
        "a2_pets": a2_pets,
        "a2_quote_pool": A2_QUOTE_POOL,
        "a2_compact": is_home,
        "left_sidebar_partners": [None, None, None],
        "right_sidebar_partners": [None, None, None],
        "hero_slider_images": hero_slider_images,
        "adopted_animals": 0,
        "active_animals": active_animals_count,
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
    return render(request, "anunturi/login.html", {"error": error, "login_value": login_value})


def forgot_password_view(request):
    """Pagina de resetare parolă (placeholder simplu)."""
    return render(request, "anunturi/forgot_password.html", {})


def signup_choose_type_view(request):
    """Pagina de alegere tip cont (persoană fizică / firmă / ONG / colaborator)."""
    return render(request, "anunturi/signup_choose_type.html", {})


def signup_pf_view(request):
    """Formular înregistrare – Persoană fizică (UI simplu, fără logică încă)."""
    return render(request, "anunturi/signup_pf.html", {})


def signup_organizatie_view(request):
    """Formular înregistrare – Adăpost / ONG / Firmă (UI simplu, fără logică încă)."""
    return render(request, "anunturi/signup_organizatie.html", {})


def signup_colaborator_view(request):
    """Formular înregistrare – Cabinet / Magazin / Servicii (UI simplu, fără logică încă)."""
    return render(request, "anunturi/signup_colaborator.html", {})


def servicii_view(request):
    """Pagina Servicii – S1/S3 benzi ca PT, strip_pets pentru poze."""
    strip_pets = []
    for i, d in enumerate(cycle(DEMO_DOGS)):
        if i >= 20:
            break
        strip_pets.append({"imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE)})
    return render(request, "anunturi/servicii.html", {"strip_pets": strip_pets})


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

def account_view(request):
    """Pagina cont utilizator: date completate la înscriere + rol."""
    if not request.user.is_authenticated:
        return redirect(f"{reverse('login')}?next={reverse('account')}")

    user = request.user
    account_profile = getattr(user, "account_profile", None)
    user_profile = getattr(user, "profile", None)
    return render(request, "anunturi/account.html", {
        "account_profile": account_profile,
        "user_profile": user_profile,
    })


@login_required
def mypet_view(request):
    """
    Pagina MyPet – deocamdată doar un wrapper gol MW,
    sub navbar, fără alte benzi sau layout-uri speciale.
    """
    user = request.user
    qs = AnimalListing.objects.filter(owner=user).order_by("-created_at")
    pets = []
    for a in qs:
        love_count = WishlistItem.objects.filter(animal_id=a.pk).count()
        pets.append({
            "pk": a.pk,
            "name": a.name or f"Pet #{a.pk}",
            "species": a.get_species_display(),
            "age_label": a.age_label,
            "city": a.city,
            "is_published": a.is_published,
            "photo_1": a.photo_1,
            "love_count": love_count,
        })
    active_animals = qs.filter(is_published=True).count()
    adopted_animals = UserAdoption.objects.filter(user=user, status="completed").count()
    return render(request, "anunturi/mypet.html", {
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
        "pets": pets,
    })


@login_required
def mypet_add_view(request):
    """
    Formular simplu pentru a adăuga un pet nou.
    În pasul următor vom rafina câmpurile și layout-ul fișei.
    """
    user = request.user
    profile = getattr(user, "profile", None)
    default_city = getattr(profile, "oras", "") if profile else ""
    default_county = ""

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
        color = (request.POST.get("color") or "").strip()
        age_label = (request.POST.get("age_label") or "").strip()
        city = (request.POST.get("city") or "").strip()
        county = (request.POST.get("county") or "").strip()
        sex = (request.POST.get("sex") or "").strip()
        weight = (request.POST.get("weight") or "").strip()
        medical_issues = (request.POST.get("medical_issues") or "").strip()
        about_pet = (request.POST.get("about_pet") or "").strip()
        sterilized_choice = (request.POST.get("sterilized") or "").strip()
        vaccinated_choice = (request.POST.get("vaccinated") or "").strip()
        health_book_choice = (request.POST.get("health_book") or "").strip()
        chip_choice = (request.POST.get("chip") or "").strip()
        trait_playful = bool(request.POST.get("trait_playful"))
        trait_affectionate = bool(request.POST.get("trait_affectionate"))
        trait_protective = bool(request.POST.get("trait_protective"))
        trait_energetic = bool(request.POST.get("trait_energetic"))
        trait_calm = bool(request.POST.get("trait_calm"))
        trait_good_with_kids = bool(request.POST.get("trait_good_with_kids"))
        trait_good_with_dogs = bool(request.POST.get("trait_good_with_dogs"))
        trait_good_with_cats = bool(request.POST.get("trait_good_with_cats"))
        trait_house_trained = bool(request.POST.get("trait_house_trained"))
        trait_leash_trained = bool(request.POST.get("trait_leash_trained"))
        trait_low_barker = bool(request.POST.get("trait_low_barker"))
        trait_apartment_ok = bool(request.POST.get("trait_apartment_ok"))
        trait_adapts_easily = bool(request.POST.get("trait_adapts_easily"))
        trait_ok_left_alone = bool(request.POST.get("trait_ok_left_alone"))
        trait_needs_experienced_owner = bool(request.POST.get("trait_needs_experienced_owner"))
        trait_good_for_yard = bool(request.POST.get("trait_good_for_yard"))
        photo_1 = request.FILES.get("photo_1")
        photo_2 = request.FILES.get("photo_2")
        photo_3 = request.FILES.get("photo_3")
        error = None
        if not name:
            error = "Te rugăm să completezi numele câinelui."
        elif not size:
            error = "Te rugăm să completezi talia (mică/medie/mare)."
        elif not age_label:
            error = "Te rugăm să alegi vârsta estimată."
        if not error:
            try:
                sterilized = sterilized_choice == "yes"
                vaccinated = vaccinated_choice == "yes"
                has_health_book = health_book_choice == "yes"
                has_chip = chip_choice == "yes"
                listing = AnimalListing.objects.create(
                    owner=user,
                    name=name,
                    species=species,
                    size=size,
                    color=color,
                    age_label=age_label,
                    city=city,
                    county=county,
                    sterilized=sterilized,
                    vaccinated=vaccinated,
                    has_health_book=has_health_book,
                    has_chip=has_chip,
                    trait_playful=trait_playful,
                    trait_affectionate=trait_affectionate,
                    trait_protective=trait_protective,
                    trait_energetic=trait_energetic,
                    trait_calm=trait_calm,
                    trait_good_with_kids=trait_good_with_kids,
                    trait_good_with_dogs=trait_good_with_dogs,
                    trait_good_with_cats=trait_good_with_cats,
                    trait_house_trained=trait_house_trained,
                    trait_leash_trained=trait_leash_trained,
                    trait_low_barker=trait_low_barker,
                    trait_apartment_ok=trait_apartment_ok,
                    trait_adapts_easily=trait_adapts_easily,
                    trait_ok_left_alone=trait_ok_left_alone,
                    trait_needs_experienced_owner=trait_needs_experienced_owner,
                    trait_good_for_yard=trait_good_for_yard,
                    medical_issues=medical_issues,
                    about_pet=about_pet,
                    is_published=True,
                )
                # Atașăm pozele dacă există (maxim 3)
                if photo_1:
                    listing.photo_1 = photo_1
                if photo_2:
                    listing.photo_2 = photo_2
                if photo_3:
                    listing.photo_3 = photo_3
                if photo_1 or photo_2 or photo_3:
                    listing.save()
                return redirect("mypet")
            except Exception as exc:
                error = str(exc)
        ctx = {
            "error": error,
            "name": name,
            "species": species,
            "size": size,
            "color": color,
            "sex": sex,
            "weight": weight,
            "medical_issues": medical_issues,
            "about_pet": about_pet,
            "age_label": age_label,
            "city": city or default_city,
            "county": county or default_county,
            "age_choices": age_choices,
            "sterilized_choice": sterilized_choice,
            "vaccinated_choice": vaccinated_choice,
            "health_book_choice": health_book_choice,
            "chip_choice": chip_choice,
            "trait_playful": trait_playful,
            "trait_affectionate": trait_affectionate,
            "trait_protective": trait_protective,
            "trait_energetic": trait_energetic,
            "trait_calm": trait_calm,
            "trait_good_with_kids": trait_good_with_kids,
            "trait_good_with_dogs": trait_good_with_dogs,
            "trait_good_with_cats": trait_good_with_cats,
            "trait_house_trained": trait_house_trained,
            "trait_leash_trained": trait_leash_trained,
            "trait_low_barker": trait_low_barker,
            "trait_apartment_ok": trait_apartment_ok,
            "trait_adapts_easily": trait_adapts_easily,
            "trait_ok_left_alone": trait_ok_left_alone,
            "trait_needs_experienced_owner": trait_needs_experienced_owner,
            "trait_good_for_yard": trait_good_for_yard,
        }
        return render(request, "anunturi/mypet_add.html", ctx)

    ctx = {
        "error": None,
        "name": "",
        "species": "dog",
        "size": "",
        "color": "",
        "sex": "",
        "weight": "",
        "medical_issues": "",
        "about_pet": "",
        "age_label": "",
        "city": default_city,
        "county": default_county,
        "age_choices": age_choices,
        "sterilized_choice": "",
        "vaccinated_choice": "",
        "health_book_choice": "",
        "chip_choice": "",
        "trait_playful": False,
        "trait_affectionate": False,
        "trait_protective": False,
        "trait_energetic": False,
        "trait_calm": False,
        "trait_good_with_kids": False,
        "trait_good_with_dogs": False,
        "trait_good_with_cats": False,
        "trait_house_trained": False,
        "trait_leash_trained": False,
        "trait_low_barker": False,
        "trait_apartment_ok": False,
        "trait_adapts_easily": False,
        "trait_ok_left_alone": False,
        "trait_needs_experienced_owner": False,
        "trait_good_for_yard": False,
    }
    return render(request, "anunturi/mypet_add.html", ctx)


@login_required
def mypet_edit_view(request, pk: int):
    """
    Editare fișă existentă pentru un pet din MyPet.
    Refolosim același template ca la adăugare, cu câmpurile precompletate.
    """
    user = request.user
    listing = get_object_or_404(AnimalListing, pk=pk, owner=user)

    profile = getattr(user, "profile", None)
    default_city = getattr(profile, "oras", "") if profile else ""
    default_county = ""

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
        color = (request.POST.get("color") or "").strip()
        age_label = (request.POST.get("age_label") or "").strip()
        city = (request.POST.get("city") or "").strip()
        county = (request.POST.get("county") or "").strip()
        sex = (request.POST.get("sex") or "").strip()
        weight = (request.POST.get("weight") or "").strip()
        medical_issues = (request.POST.get("medical_issues") or "").strip()
        about_pet = (request.POST.get("about_pet") or "").strip()
        sterilized_choice = (request.POST.get("sterilized") or "").strip()
        vaccinated_choice = (request.POST.get("vaccinated") or "").strip()
        health_book_choice = (request.POST.get("health_book") or "").strip()
        chip_choice = (request.POST.get("chip") or "").strip()
        trait_playful = bool(request.POST.get("trait_playful"))
        trait_affectionate = bool(request.POST.get("trait_affectionate"))
        trait_protective = bool(request.POST.get("trait_protective"))
        trait_energetic = bool(request.POST.get("trait_energetic"))
        trait_calm = bool(request.POST.get("trait_calm"))
        trait_good_with_kids = bool(request.POST.get("trait_good_with_kids"))
        trait_good_with_dogs = bool(request.POST.get("trait_good_with_dogs"))
        trait_good_with_cats = bool(request.POST.get("trait_good_with_cats"))
        trait_house_trained = bool(request.POST.get("trait_house_trained"))
        trait_leash_trained = bool(request.POST.get("trait_leash_trained"))
        trait_low_barker = bool(request.POST.get("trait_low_barker"))
        trait_apartment_ok = bool(request.POST.get("trait_apartment_ok"))
        trait_adapts_easily = bool(request.POST.get("trait_adapts_easily"))
        trait_ok_left_alone = bool(request.POST.get("trait_ok_left_alone"))
        trait_needs_experienced_owner = bool(request.POST.get("trait_needs_experienced_owner"))
        trait_good_for_yard = bool(request.POST.get("trait_good_for_yard"))
        photo_1 = request.FILES.get("photo_1")
        photo_2 = request.FILES.get("photo_2")
        photo_3 = request.FILES.get("photo_3")

        error = None
        if not name:
            error = "Te rugăm să completezi numele câinelui."
        elif not size:
            error = "Te rugăm să completezi talia (mică/medie/mare)."
        elif not age_label:
            error = "Te rugăm să alegi vârsta estimată."

        if not error:
            try:
                listing.name = name
                listing.species = species
                listing.size = size
                listing.color = color
                listing.age_label = age_label
                listing.city = city
                listing.county = county
                listing.medical_issues = medical_issues
                listing.about_pet = about_pet

                listing.sterilized = (sterilized_choice == "yes")
                listing.vaccinated = (vaccinated_choice == "yes")
                listing.has_health_book = (health_book_choice == "yes")
                listing.has_chip = (chip_choice == "yes")

                listing.trait_playful = trait_playful
                listing.trait_affectionate = trait_affectionate
                listing.trait_protective = trait_protective
                listing.trait_energetic = trait_energetic
                listing.trait_calm = trait_calm
                listing.trait_good_with_kids = trait_good_with_kids
                listing.trait_good_with_dogs = trait_good_with_dogs
                listing.trait_good_with_cats = trait_good_with_cats
                listing.trait_house_trained = trait_house_trained
                listing.trait_leash_trained = trait_leash_trained
                listing.trait_low_barker = trait_low_barker
                listing.trait_apartment_ok = trait_apartment_ok
                listing.trait_adapts_easily = trait_adapts_easily
                listing.trait_ok_left_alone = trait_ok_left_alone
                listing.trait_needs_experienced_owner = trait_needs_experienced_owner
                listing.trait_good_for_yard = trait_good_for_yard

                # Poze: dacă userul încarcă ceva nou, înlocuim; altfel păstrăm
                if photo_1:
                    listing.photo_1 = photo_1
                if photo_2:
                    listing.photo_2 = photo_2
                if photo_3:
                    listing.photo_3 = photo_3

                listing.save()
                return redirect("mypet")
            except Exception as exc:
                error = str(exc)

        ctx = {
            "error": error,
            "name": name,
            "species": species,
            "size": size,
            "color": color,
            "sex": sex,
            "weight": weight,
            "medical_issues": medical_issues,
            "about_pet": about_pet,
            "age_label": age_label,
            "city": city or default_city,
            "county": county or default_county,
            "age_choices": age_choices,
            "sterilized_choice": sterilized_choice,
            "vaccinated_choice": vaccinated_choice,
            "health_book_choice": health_book_choice,
            "chip_choice": chip_choice,
            "trait_playful": trait_playful,
            "trait_affectionate": trait_affectionate,
            "trait_protective": trait_protective,
            "trait_energetic": trait_energetic,
            "trait_calm": trait_calm,
            "trait_good_with_kids": trait_good_with_kids,
            "trait_good_with_dogs": trait_good_with_dogs,
            "trait_good_with_cats": trait_good_with_cats,
            "trait_house_trained": trait_house_trained,
            "trait_leash_trained": trait_leash_trained,
            "trait_low_barker": trait_low_barker,
            "trait_apartment_ok": trait_apartment_ok,
            "trait_adapts_easily": trait_adapts_easily,
            "trait_ok_left_alone": trait_ok_left_alone,
            "trait_needs_experienced_owner": trait_needs_experienced_owner,
            "trait_good_for_yard": trait_good_for_yard,
        }
        return render(request, "anunturi/mypet_add.html", ctx)

    # GET: precompletăm din listing
    ctx = {
        "error": None,
        "name": listing.name,
        "species": listing.species or "dog",
        "size": listing.size,
        "color": listing.color,
        "sex": "",
        "weight": "",
        "medical_issues": listing.medical_issues,
        "about_pet": listing.about_pet,
        "age_label": listing.age_label,
        "city": listing.city or default_city,
        "county": listing.county or default_county,
        "age_choices": age_choices,
        "sterilized_choice": "yes" if listing.sterilized else "no" if listing.sterilized is not None else "",
        "vaccinated_choice": "yes" if listing.vaccinated else "no" if listing.vaccinated is not None else "",
        "health_book_choice": "yes" if listing.has_health_book else "no" if listing.has_health_book is not None else "",
        "chip_choice": "yes" if listing.has_chip else "no" if listing.has_chip is not None else "",
        "trait_playful": listing.trait_playful,
        "trait_affectionate": listing.trait_affectionate,
        "trait_protective": listing.trait_protective,
        "trait_energetic": listing.trait_energetic,
        "trait_calm": listing.trait_calm,
        "trait_good_with_kids": listing.trait_good_with_kids,
        "trait_good_with_dogs": listing.trait_good_with_dogs,
        "trait_good_with_cats": listing.trait_good_with_cats,
        "trait_house_trained": listing.trait_house_trained,
        "trait_leash_trained": listing.trait_leash_trained,
        "trait_low_barker": listing.trait_low_barker,
        "trait_apartment_ok": listing.trait_apartment_ok,
        "trait_adapts_easily": listing.trait_adapts_easily,
        "trait_ok_left_alone": listing.trait_ok_left_alone,
        "trait_needs_experienced_owner": listing.trait_needs_experienced_owner,
        "trait_good_for_yard": listing.trait_good_for_yard,
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