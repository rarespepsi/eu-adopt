from django import template

from home.org_trust_badge import pet_shows_org_trust_badge
from home.pet_card_display import pet_card_meta_context
from home.pet_media_thumb import pet_thumb_url_for
from home.pet_traits import trait_label

register = template.Library()


@register.simple_tag(takes_context=True)
def animal_trait_label(context, species, field_name):
    """Text afișat pentru o trăsătură (câmp DB), în funcție de specie (dog/cat)."""
    return trait_label(species, field_name, english=bool(context.get("eu_site_active")))


@register.simple_tag(takes_context=True)
def eu_pet_val(context, raw, default=""):
    """Valoare câmp fișă: limba EU (EN/DE/FR/ES), altfel textul din DB."""
    if raw is None or str(raw).strip() == "":
        return default
    if not context.get("eu_site_active"):
        return str(raw)
    from home.pet_ui_display import pet_field_value

    lang = (context.get("eu_site_lang") or "en").split("-")[0].lower()
    return pet_field_value(raw, lang) or default


@register.simple_tag
def pet_thumb_url(image_field, size=400):
    """URL thumbnail JPEG (max latura = size px) pentru poze din MEDIA animals/."""
    return pet_thumb_url_for(image_field, size)


@register.inclusion_tag("anunturi/includes/eu_org_trust_badge.html")
def eu_org_trust_badge(pet=None, show=None, size="", overlay=False):
    """Badge verde thumbs-up: adăpost / ONG înregistrat."""
    if show is None:
        show = pet_shows_org_trust_badge(pet)
    return {
        "show": bool(show),
        "size": (size or "").strip(),
        "overlay": bool(overlay),
    }


@register.inclusion_tag("anunturi/includes/pet_card_meta_footer.html", takes_context=True)
def pet_card_meta_footer(context, pet):
    """Localitate + M/F + vârstă (rânduri sub nume pe card). Vârstă i18n pe site EU."""
    meta = pet_card_meta_context(pet)
    if context.get("eu_site_active") and meta.get("age_text"):
        from home.pet_ui_display import pet_field_value

        lang = (context.get("eu_site_lang") or "en").split("-")[0].lower()
        meta["age_text"] = pet_field_value(meta["age_text"], lang) or meta["age_text"]
    return meta


@register.simple_tag
def animal_public_href(pet_or_listing):
    """
    URL frumos pentru fișa animalului (/caini/rex-bucuresti/).
    Acceptă AnimalListing sau dict/obj cu pk (+ optional slug/species/name/city).
    """
    from home.models import AnimalListing
    from home.shelter_directory import animal_public_url

    if pet_or_listing is None:
        return ""
    if isinstance(pet_or_listing, AnimalListing):
        return animal_public_url(pet_or_listing)
    pk = getattr(pet_or_listing, "pk", None)
    if pk is None and isinstance(pet_or_listing, dict):
        pk = pet_or_listing.get("pk")
    if not pk:
        return ""
    listing = AnimalListing.objects.filter(pk=pk).first()
    if not listing:
        from django.urls import reverse

        return reverse("pets_single", args=[pk])
    return animal_public_url(listing)
