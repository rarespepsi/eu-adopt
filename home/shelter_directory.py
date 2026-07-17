"""
Director Adăpost/ONG + slug-uri publice (animale și organizații).
"""

from __future__ import annotations

import re
import unicodedata

from django.contrib.auth.models import User
from django.db.models import Count, Prefetch, Q
from django.urls import reverse
from django.utils.text import slugify

from home.models import AccountProfile, AnimalListing, PartnerLocation
from home.partner_locations import (
    google_maps_url,
    maps_query_for_location,
    primary_location_for_user,
    sediu_social_for_user,
)

SPECIES_URL_PREFIX = {
    "dog": "caini",
    "cat": "pisici",
    "other": "altele",
}

SPECIES_URL_NAME = {
    "dog": "animal_public_dog",
    "cat": "animal_public_cat",
    "other": "animal_public_other",
}


def strip_diacritics(s: str) -> str:
    s = unicodedata.normalize("NFD", s or "")
    return "".join(c for c in s if unicodedata.category(c) != "Mn")


def make_base_slug(*parts: str, max_len: int = 72) -> str:
    raw = " ".join((p or "").strip() for p in parts if (p or "").strip())
    raw = strip_diacritics(raw)
    s = slugify(raw, allow_unicode=False) or "entitate"
    s = re.sub(r"-{2,}", "-", s).strip("-")
    return s[:max_len] or "entitate"


def unique_animal_slug(listing: AnimalListing, base: str | None = None) -> str:
    base = (base or "").strip("-") or make_base_slug(listing.name, listing.city) or f"animal-{listing.pk or 'nou'}"
    if listing.pk:
        # Prefer stable slug without pk when free; otherwise name-city-pk
        candidates = [base, f"{base}-{listing.pk}"]
    else:
        candidates = [base]
    for cand in candidates:
        qs = AnimalListing.objects.filter(slug=cand)
        if listing.pk:
            qs = qs.exclude(pk=listing.pk)
        if not qs.exists():
            return cand[:90]
    # Fallback rare collisions
    n = 2
    while n < 1000:
        cand = f"{base}-{n}"[:90]
        qs = AnimalListing.objects.filter(slug=cand)
        if listing.pk:
            qs = qs.exclude(pk=listing.pk)
        if not qs.exists():
            return cand
        n += 1
    return f"animal-{listing.pk or 'x'}"


def unique_org_slug(user: User, base: str | None = None) -> str:
    profile = getattr(user, "profile", None)
    display = ""
    if profile:
        display = (profile.company_display_name or profile.company_legal_name or "").strip()
    base = (base or "").strip("-") or make_base_slug(display or user.username) or f"org-{user.pk}"
    candidates = [base, f"{base}-{user.pk}"]
    for cand in candidates:
        qs = AccountProfile.objects.filter(public_slug=cand)
        if user.pk:
            qs = qs.exclude(user_id=user.pk)
        if not qs.exists():
            return cand[:90]
    return f"org-{user.pk}"


def ensure_animal_slug(listing: AnimalListing, *, save: bool = False) -> str:
    if (listing.slug or "").strip():
        return listing.slug
    listing.slug = unique_animal_slug(listing)
    if save and listing.pk:
        AnimalListing.objects.filter(pk=listing.pk).update(slug=listing.slug)
    return listing.slug


def ensure_org_slug(user: User, *, save: bool = True) -> str:
    ap = getattr(user, "account_profile", None)
    if not ap:
        return ""
    if (ap.public_slug or "").strip():
        return ap.public_slug
    ap.public_slug = unique_org_slug(user)
    if save:
        AccountProfile.objects.filter(pk=ap.pk).update(public_slug=ap.public_slug)
    return ap.public_slug


def animal_public_url(listing: AnimalListing) -> str:
    ensure_animal_slug(listing, save=bool(listing.pk))
    species = (listing.species or "dog").strip().lower()
    if species not in SPECIES_URL_NAME:
        species = "dog"
    return reverse(SPECIES_URL_NAME[species], kwargs={"slug": listing.slug})


def org_public_url(user: User) -> str:
    slug = ensure_org_slug(user)
    if not slug:
        return reverse("shelter_directory")
    return reverse("shelter_detail", kwargs={"slug": slug})


def org_display_name(user: User) -> str:
    profile = getattr(user, "profile", None)
    if profile:
        name = (profile.company_display_name or profile.company_legal_name or "").strip()
        if name:
            return name
    full = (user.get_full_name() or "").strip()
    return full or user.username


def org_locality(user: User) -> str:
    loc = primary_location_for_user(user) or sediu_social_for_user(user)
    if loc:
        bits = [b for b in ((loc.oras or "").strip(), (loc.judet or "").strip()) if b]
        if bits:
            return ", ".join(bits)
    profile = getattr(user, "profile", None)
    if profile:
        bits = [
            b
            for b in (
                (profile.company_oras or profile.oras or "").strip(),
                (profile.company_judet or profile.judet or "").strip(),
            )
            if b
        ]
        if bits:
            return ", ".join(bits)
    return ""


def org_address_line(user: User) -> str:
    loc = sediu_social_for_user(user) or primary_location_for_user(user)
    if loc:
        bits = [b for b in ((loc.adresa or "").strip(), (loc.oras or "").strip(), (loc.judet or "").strip()) if b]
        if bits:
            return ", ".join(bits)
    profile = getattr(user, "profile", None)
    if profile:
        bits = [
            b
            for b in (
                (profile.company_address or "").strip(),
                (profile.company_oras or profile.oras or "").strip(),
                (profile.company_judet or profile.judet or "").strip(),
            )
            if b
        ]
        if bits:
            return ", ".join(bits)
    return ""


def org_phone(user: User) -> str:
    loc = primary_location_for_user(user)
    if loc and (loc.phone or "").strip():
        return loc.phone.strip()
    profile = getattr(user, "profile", None)
    if profile and (profile.phone or "").strip():
        return profile.phone.strip()
    return ""


def org_contact_person(user: User) -> str:
    """Persoană de contact publică. Adăpost demo (rarespepsi): fără username pe pagină."""
    uname = (user.username or "").strip()
    uname_l = uname.lower()
    profile = getattr(user, "profile", None)
    slug = ""
    if profile:
        slug = (getattr(profile, "public_slug", None) or "").strip().lower()
    is_adapost_demo = uname_l == "rarespepsi" or slug == "adapost-demo"

    if profile and (profile.company_representative or "").strip():
        rep = profile.company_representative.strip()
        if is_adapost_demo and rep.lower() == uname_l:
            return ""
        return rep
    full = (user.get_full_name() or "").strip()
    if full:
        if is_adapost_demo and full.lower() == uname_l:
            return ""
        return full
    if is_adapost_demo:
        return ""
    return uname


def org_logo_url(user: User) -> str:
    profile = getattr(user, "profile", None)
    if profile and profile.poza_1:
        try:
            return profile.poza_1.url
        except Exception:
            return ""
    return ""


def org_maps_query(user: User) -> str:
    loc = sediu_social_for_user(user) or primary_location_for_user(user)
    if loc:
        q = maps_query_for_location(loc)
        if q:
            return q
    addr = org_address_line(user)
    if addr:
        blob = addr.lower()
        if "românia" not in blob and "romania" not in blob:
            return f"{addr}, România"
        return addr
    return ""


def org_maps_url(user: User) -> str:
    return google_maps_url(org_maps_query(user))


def org_osm_embed_url(user: User) -> str:
    """Păstrat pentru compatibilitate — preferă Google embed pe adresă (ca Transport)."""
    return org_google_embed_url(user)


def org_google_embed_url(user: User) -> str:
    q = org_maps_query(user)
    if not q:
        return ""
    from urllib.parse import quote

    return f"https://maps.google.com/maps?q={quote(q)}&z=14&output=embed"


def org_about_text(user: User) -> str:
    """
    Text „Despre noi” pe pagina publică adăpost.
    Implicit: doar denumirea afișată. Dacă e completat despre_noi → acel text (scurt).
    """
    display = org_display_name(user)
    profile = getattr(user, "profile", None)
    custom = (getattr(profile, "despre_noi", None) or "").strip() if profile else ""
    if custom:
        custom = " ".join(custom.split())
        return custom[:360]
    return display


def normalize_external_link(raw: str) -> str:
    """Normalizează URL-ul introdus de user (adaugă https:// dacă lipsește schema)."""
    s = (raw or "").strip()
    if not s:
        return ""
    if len(s) > 500:
        s = s[:500]
    low = s.lower()
    if not (
        low.startswith("http://")
        or low.startswith("https://")
        or low.startswith("mailto:")
    ):
        s = "https://" + s
    return s


def org_external_link(user: User) -> str:
    """Link site/pagină din profil (gol dacă lipsește)."""
    profile = getattr(user, "profile", None)
    raw = (getattr(profile, "link_extern", None) or "").strip() if profile else ""
    return normalize_external_link(raw) if raw else ""


def org_promo_links(user: User) -> dict:
    """
    Cele 3 sloturi promo pe pagina publică adăpost.
    Slot 3: dacă lipsește link_propriu → Suflet și Caracter.
    """
    from home.donatii_constants import EUADOPT_PARTNER_NGO

    profile = getattr(user, "profile", None)
    social = normalize_external_link(getattr(profile, "link_social", "") or "") if profile else ""
    mancare = normalize_external_link(getattr(profile, "link_mancare", "") or "") if profile else ""
    propriu_raw = (getattr(profile, "link_propriu", None) or "").strip() if profile else ""
    propriu = normalize_external_link(propriu_raw) if propriu_raw else ""
    default_own = (EUADOPT_PARTNER_NGO.get("url") or "").strip() or "https://eu-adopt.ro/donatii/"
    if not propriu:
        propriu = default_own
        propriu_is_default = True
    else:
        propriu_is_default = False
    return {
        "social": social,
        "mancare": mancare,
        "propriu": propriu,
        "propriu_is_default": propriu_is_default,
        "propriu_label": (
            (EUADOPT_PARTNER_NGO.get("name") or "Suflet și Caracter")
            if propriu_is_default
            else "Link propriu"
        ),
    }


def directory_org_queryset():
    """ORG cu cel puțin un animal publicat."""
    return (
        User.objects.filter(
            is_active=True,
            account_profile__role=AccountProfile.ROLE_ORG,
            animal_listings__is_published=True,
        )
        .annotate(pub_animal_count=Count("animal_listings", filter=Q(animal_listings__is_published=True), distinct=True))
        .filter(pub_animal_count__gt=0)
        .select_related("account_profile", "profile")
        .prefetch_related(
            Prefetch(
                "partner_locations",
                queryset=PartnerLocation.objects.filter(is_active=True).order_by(
                    "-is_primary", "-is_sediu_social", "pk"
                ),
            )
        )
        .distinct()
        .order_by("profile__company_display_name", "username")
    )


def get_org_by_public_slug(slug: str) -> User | None:
    slug = (slug or "").strip()
    if not slug:
        return None
    return (
        User.objects.filter(account_profile__public_slug=slug, account_profile__role=AccountProfile.ROLE_ORG, is_active=True)
        .select_related("account_profile", "profile")
        .first()
    )


def published_animals_for_org(user: User):
    return (
        AnimalListing.objects.filter(owner=user, is_published=True)
        .exclude(adoption_state=AnimalListing.ADOPTION_STATE_ADOPTED)
        .order_by("-created_at")
    )
