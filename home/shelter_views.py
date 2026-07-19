"""Views: director Adăpost/ONG + fișă animal pe slug public."""

from __future__ import annotations

from django.contrib.auth.models import User
from django.http import Http404
from django.shortcuts import get_object_or_404, redirect, render
from django.urls import reverse

from home.models import AnimalListing
from home.shelter_directory import (
    animal_public_url,
    directory_org_queryset,
    ensure_animal_slug,
    ensure_org_slug,
    get_org_by_public_slug,
    org_about_text,
    org_address_line,
    org_contact_person,
    org_county,
    org_display_name,
    org_external_link,
    org_google_embed_url,
    org_locality,
    org_logo_url,
    org_maps_url,
    org_phone,
    org_promo_links,
    org_public_url,
    published_animals_for_org,
)
from home.ro_location import all_counties

# TEMP: casete demo pentru layout director — scoate la lansare / când user cere
_SHELTER_DIR_DEMO_COUNT = 30


def _shelter_directory_demo_rows(n: int = _SHELTER_DIR_DEMO_COUNT) -> list[dict]:
    counties = all_counties() or ["Cluj"]
    rows = []
    for i in range(1, n + 1):
        jud = counties[(i - 1) % len(counties)]
        rows.append(
            {
                "name": f"Adăpost Demo {i}",
                "locality": f"Localitate {i}, {jud}",
                "county": jud,
                "logo_url": "",
                "url": "#",
                "count": (i % 12) + 1,
                "is_public_shelter": i % 2 == 0,
                "is_demo": True,
            }
        )
    return rows


def shelter_directory_view(request):
    rows = []
    for user in directory_org_queryset():
        ensure_org_slug(user)
        rows.append(
            {
                "user": user,
                "name": org_display_name(user),
                "locality": org_locality(user),
                "county": org_county(user),
                "logo_url": org_logo_url(user),
                "url": org_public_url(user),
                "count": getattr(user, "pub_animal_count", 0) or 0,
                "is_public_shelter": bool(getattr(user.account_profile, "is_public_shelter", False)),
                "is_demo": False,
            }
        )
    # TEMP layout: +30 casete demo (filtre județ vizibile pe grilă)
    rows.extend(_shelter_directory_demo_rows())
    return render(
        request,
        "anunturi/adaposturi_directory.html",
        {
            "shelter_rows": rows,
            "shelter_count": len(rows),
            "shelter_counties": all_counties(),
            "shelter_demo_layout": True,
        },
    )


def shelter_detail_view(request, slug: str):
    user = get_org_by_public_slug(slug)
    if user is None:
        raise Http404("Adăpostul / ONG-ul nu a fost găsit.")
    ensure_org_slug(user)
    animals = list(published_animals_for_org(user)[:120])

    from home.models import WishlistItem
    from home.population_onboarding import user_may_adopt_animals

    wishlist_ids = set()
    if request.user.is_authenticated:
        wishlist_ids = set(
            WishlistItem.objects.filter(user=request.user).values_list("animal_id", flat=True)
        )

    can_ask = bool(
        request.user.is_authenticated
        and user_may_adopt_animals(request.user)
    )
    viewer_id = int(request.user.pk) if request.user.is_authenticated else None

    for a in animals:
        ensure_animal_slug(a, save=True)
        a.public_url = animal_public_url(a)
        a.show_ask_plic = False
        if can_ask and viewer_id is not None and int(a.owner_id) != viewer_id:
            if (a.adoption_state or "").strip() != AnimalListing.ADOPTION_STATE_ADOPTED:
                a.show_ask_plic = True

    maps_url = org_maps_url(user)
    embed_url = org_google_embed_url(user)
    share_url = request.build_absolute_uri(org_public_url(user))
    org_back_path = org_public_url(user)
    return render(
        request,
        "anunturi/adapost_detail.html",
        {
            "org_user": user,
            "org_name": org_display_name(user),
            "org_locality": org_locality(user),
            "org_logo_url": org_logo_url(user),
            "org_about": org_about_text(user),
            "org_external_link": org_external_link(user),
            "org_promo": org_promo_links(user),
            "org_address": org_address_line(user),
            "org_phone": org_phone(user),
            "org_contact": org_contact_person(user),
            "org_maps_url": maps_url,
            "org_map_embed_url": embed_url,
            "org_share_url": share_url,
            "org_back_path": org_back_path,
            "org_animals": animals,
            "org_animal_count": len(animals),
            "org_is_public_shelter": bool(getattr(user.account_profile, "is_public_shelter", False)),
            "wishlist_ids": wishlist_ids,
        },
    )


def animal_public_by_slug_view(request, slug: str, species: str):
    """Fișa animalului pe URL frumos: /caini/rex-bucuresti/ etc."""
    from home import views as home_views

    listing = get_object_or_404(
        AnimalListing,
        slug=slug,
        species=species,
        is_published=True,
    )
    return home_views.render_dog_profile(request, listing)


def dog_profile_pk_redirect(request, pk: int):
    """Compat: /pets/<pk>/ → /caini|pisici|altele/<slug>/."""
    listing = get_object_or_404(AnimalListing, pk=pk, is_published=True)
    ensure_animal_slug(listing, save=True)
    target = animal_public_url(listing)
    qs = request.GET.urlencode()
    if qs:
        target = f"{target}?{qs}"
    return redirect(target)
