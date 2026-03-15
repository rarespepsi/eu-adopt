"""
Home views. Layout HOME înghețat: v. HOME_SLOTS.md
A0=navbar, A1=hero, A2=grid 4×3, A3=mission bar, A4=footer, A5=left sidebar (3), A6=right sidebar (3).
REGULĂ: Orice modificare în home (punct, virgulă, orice) doar cu aprobarea titularului, cu parolă.
"""
import random
from copy import deepcopy
from itertools import cycle
from django.shortcuts import render, redirect
from django.urls import reverse
from django.utils import timezone
from django.http import JsonResponse
from django.views.decorators.http import require_POST
from django.contrib.auth.decorators import login_required
from django.views.decorators.csrf import csrf_protect
from .data import DEMO_DOGS, DEMO_DOG_IMAGE, A2_QUOTE_POOL, HERO_SLIDER_IMAGES
from .models import WishlistItem, AnimalListing, UserAdoption, AccountProfile, UserProfile
from django.contrib.auth import get_user_model


def _phone_digits(phone_str):
    """Returnează doar cifrele din număr (pentru comparatie unicitate)."""
    if not phone_str:
        return ""
    return "".join(c for c in str(phone_str) if c.isdigit())


def _phone_already_used(phone_input):
    """True dacă există deja un UserProfile cu același număr (comparat doar pe cifre)."""
    norm = _phone_digits(phone_input)
    if not norm:
        return False
    for p in UserProfile.objects.exclude(phone="").exclude(phone__isnull=True):
        if _phone_digits(p.phone) == norm:
            return True
    return False

# A2 selection: 12 dogs. New (added in last 24h) first, then fill randomly from PT. Never empty if any available.
A2_SLOT_COUNT = 12
A2_NEW_HOURS = 24


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
        # P2: toți câinii activi; rândurile în funcție de număr; ultimul rând complet (4) prin repetare
        p2_list = []
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
        # Demo: ~10 rânduri în scroll (40 celule); când vine DB, lista vine de acolo
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
            try:
                wishlist_ids = set(WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True))
            except Exception:
                pass
        return render(request, "anunturi/pt.html", {
            "p2_pets": p2_pets,
            "p2_pets_rest": p2_pets_rest,
            "strip_pets": strip_pets,
            "wishlist_ids": wishlist_ids,
        })

    is_home = request.resolver_match.url_name == "home"

    # Available dogs for PT (Prietenul tău); demo: use DEMO_DOGS with default added_at so all are "old"
    available_for_pt = []
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
            "imagine_fallback": d.get("imagine_fallback", DEMO_DOG_IMAGE),
        }
        if is_home:
            pet["quote"] = random.choice(A2_QUOTE_POOL)
        a2_pets.append(pet)

    hero_slider_images = HERO_SLIDER_IMAGES[:5]
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
    return render(request, "anunturi/login.html", {"error": error, "login_value": login_value})


def forgot_password_view(request):
    """Pagina de resetare parolă (placeholder simplu)."""
    return render(request, "anunturi/forgot_password.html", {})


def signup_choose_type_view(request):
    """Pagina de alegere tip cont (persoană fizică / firmă / ONG / colaborator)."""
    return render(request, "anunturi/signup_choose_type.html", {})


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
            ctx["form_prefill"] = data
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
    poza_1 = request.FILES.get("poza_1")

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


def signup_verificare_sms_view(request):
    """Pas SMS comun pentru PF, ONG, Colaborator: cod 111111, creare user (inactiv), email cu link, redirect verifică email."""
    data = _get_signup_pending(request)
    if not data:
        return redirect(reverse("signup_choose_type"))

    role = data.get("role", "pf")
    email = (data.get("email") or "").strip().lower()

    if request.method != "POST":
        back_url = _redirect_for_role(role, "")
        return render(request, "anunturi/signup_pf_sms.html", {"email": email, "back_url": back_url})

    sms_code = (request.POST.get("sms_code") or "").strip()
    if sms_code != "111111":
        back_url = _redirect_for_role(role, "")
        return render(
            request,
            "anunturi/signup_pf_sms.html",
            {"email": email, "sms_error": "Cod invalid. Folosește 111111 pentru verificare.", "back_url": back_url},
        )

    if role == "pf":
        full_phone = f"{data.get('phone_country', '')} {data.get('phone', '')}".strip()
    else:
        full_phone = (data.get("telefon") or "").strip()

    if _phone_already_used(full_phone):
        request.session.pop("signup_pending", None)
        request.session.pop("signup_pf_pending", None)
        return redirect(_redirect_for_role(role, "phone") + "?phone_taken=1")

    User = get_user_model()
    if User.objects.filter(email=email).exists():
        request.session.pop("signup_pending", None)
        request.session.pop("signup_pf_pending", None)
        return redirect(_redirect_for_role(role, "email") + "?email_taken=1")

    username = email
    if User.objects.filter(username=username).exists():
        base = email.split("@")[0]
        for i in range(1, 100):
            username = f"{base}{i}"
            if not User.objects.filter(username=username).exists():
                break

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
        profile.accept_termeni = data.get("accept_termeni", False)
        profile.accept_gdpr = data.get("accept_gdpr", False)
        profile.email_opt_in_wishlist = data.get("email_opt_in", False)
        profile.save()

    from django.core.signing import Signer
    from django.core.mail import send_mail
    from urllib.parse import quote

    signer = Signer()
    token = signer.sign(user.pk)
    verify_url = request.build_absolute_uri(reverse("signup_verify_email")) + "?token=" + quote(token)
    try:
        send_mail(
            subject="Verificare email – EU-Adopt",
            message=f"Bună ziua,\n\nApasă pe link pentru a-ți activa contul:\n{verify_url}\n\nDacă nu ai creat cont, poți ignora acest email.",
            from_email=None,
            recipient_list=[email],
            fail_silently=False,
        )
    except Exception:
        pass

    request.session.pop("signup_pending", None)
    request.session.pop("signup_pf_pending", None)
    return redirect(reverse("signup_pf_check_email") + f"?email={email}")


def signup_pf_sms_view(request):
    """Redirect către pasul comun de verificare SMS (compatibilitate link vechi)."""
    return signup_verificare_sms_view(request)


def signup_pf_check_email_view(request):
    """Pagina 'Verifică email-ul – am trimis un link la ...'."""
    email = request.GET.get("email", "")
    return render(request, "anunturi/signup_pf_check_email.html", {"email": email, "back_url": reverse("signup_choose_type")})


def signup_verify_email_view(request):
    """Link din email: verifică token, activează user, login, redirect home cu welcome."""
    from django.core.signing import Signer
    from django.contrib.auth import login as auth_login

    token = request.GET.get("token", "")
    if not token:
        return redirect(reverse("signup_pf"))
    signer = Signer()
    try:
        user_pk = signer.unsign(token)
    except Exception:
        return redirect(reverse("signup_pf"))

    User = get_user_model()
    try:
        user = User.objects.get(pk=user_pk)
    except User.DoesNotExist:
        return redirect(reverse("signup_pf"))

    user.is_active = True
    user.save()
    auth_login(request, user)
    return redirect(reverse("home") + "?welcome=1")


def signup_organizatie_view(request):
    """Formular înregistrare – Adăpost / ONG / Firmă. La POST: validează, salvează în sesiune, redirect SMS. La GET: prefill din sesiune dacă user a dat Back din SMS."""
    if request.method != "POST":
        ctx = {}
        if request.GET.get("phone_taken"):
            ctx["signup_errors"] = ["Acest număr de telefon este deja folosit. Te rugăm folosește alt număr."]
        if request.GET.get("email_taken"):
            ctx["signup_errors"] = ["Acest email este deja folosit. Te rugăm folosește alt email."]
        data = _get_signup_pending(request)
        if data and data.get("role") == "org":
            if "cui_cu_ro" not in data and data.get("cui") and (data.get("cui") or "").upper().startswith("RO"):
                data = dict(data)
                data["cui_cu_ro"] = "da"
            elif "cui_cu_ro" not in data:
                data = dict(data)
                data["cui_cu_ro"] = "nu"
            ctx["form_prefill"] = data
        return render(request, "anunturi/signup_organizatie.html", ctx)

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

    errors = []
    if is_public_shelter_val not in ("yes", "no"):
        errors.append("Trebuie să alegi una dintre variante: Sunt adăpost public / Nu sunt adăpost public.")
    if not email:
        errors.append("Email obligatoriu.")
    if User.objects.filter(email=email).exists():
        errors.append("Acest email este deja folosit.")
    if not denumire:
        errors.append("Denumirea organizației este obligatorie.")
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
            "email": email,
            "telefon": telefon,
            "judet": judet,
            "oras": oras,
            "accept_termeni": accept_termeni,
            "accept_gdpr": accept_gdpr,
            "email_opt_in": email_opt_in,
            "is_public_shelter": is_public_shelter if is_public_shelter_val in ("yes", "no") else None,
        }
        return render(request, "anunturi/signup_organizatie.html", {"signup_errors": errors, "form_prefill": prefill})

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


def dog_profile_view(request, pk):
    dog = next((d for d in DEMO_DOGS if d["id"] == pk), None)
    if not dog:
        dog = {"id": pk, "nume": "—", "varsta": "—", "descriere": ""}
    ctx = {"pet": {"pk": dog["id"], "nume": dog["nume"], "varsta": dog["varsta"], "descriere": dog["descriere"], "imagine_fallback": dog.get("imagine_fallback", DEMO_DOG_IMAGE)}}
    return render(request, "anunturi/pets-single.html", ctx)


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
    Pagina MyPet – listă animale ale userului (un rând per câine).
    """
    user = request.user
    pets = list(
        AnimalListing.objects.filter(owner=user)
        .order_by("-id")[:50]
    )
    # Minim 20 rânduri pentru a vedea scroll-ul
    while len(pets) < 20:
        pets.append(None)
    active_animals = AnimalListing.objects.filter(owner=user, is_published=True).count()
    adopted_animals = UserAdoption.objects.filter(user=user, status="completed").count()
    return render(request, "anunturi/mypet.html", {
        "pets": pets,
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
    })


@login_required
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
        if not name:
            error = "Te rugăm să completezi numele câinelui."
        if not age_label:
            error = "Te rugăm să alegi vârsta estimată."
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
                return redirect("mypet_edit", pk=listing.pk)
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
    }
    return render(request, "anunturi/mypet_add.html", ctx)


@login_required
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
        if not name:
            error = "Te rugăm să completezi numele câinelui."
        if not age_label:
            error = "Te rugăm să alegi vârsta estimată."
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