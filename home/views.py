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
from .data import DEMO_DOGS, DEMO_DOG_IMAGE, A2_QUOTE_POOL, HERO_SLIDER_IMAGES

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
        return render(request, "anunturi/pt.html", {
            "p2_pets": p2_pets,
            "p2_pets_rest": p2_pets_rest,
            "strip_pets": strip_pets,
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
    return render(request, "anunturi/home_v2.html", {
        "a2_pets": a2_pets,
        "a2_quote_pool": A2_QUOTE_POOL,
        "a2_compact": is_home,
        "left_sidebar_partners": [None, None, None],
        "right_sidebar_partners": [None, None, None],
        "hero_slider_images": hero_slider_images,
        "adopted_animals": 0,
        "active_animals": len(DEMO_DOGS),
    })

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


def dog_profile_view(request, pk):
    dog = next((d for d in DEMO_DOGS if d["id"] == pk), None)
    if not dog:
        dog = {"id": pk, "nume": "—", "varsta": "—", "descriere": ""}
    ctx = {"pet": {"pk": dog["id"], "nume": dog["nume"], "varsta": dog["varsta"], "descriere": dog["descriere"], "imagine_fallback": dog.get("imagine_fallback", DEMO_DOG_IMAGE)}}
    return render(request, "anunturi/pets-single.html", ctx)