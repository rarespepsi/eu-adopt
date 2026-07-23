from django import template

from home.pet_card_display import pet_card_meta_context
from home.pet_media_thumb import pet_thumb_url_for
from home.pet_traits import trait_label

register = template.Library()


@register.simple_tag
def animal_trait_label(species, field_name):
    """Text afișat pentru o trăsătură (câmp DB), în funcție de specie (dog/cat)."""
    return trait_label(species, field_name)


@register.simple_tag
def pet_thumb_url(image_field, size=400):
    """URL thumbnail JPEG (max latura = size px) pentru poze din MEDIA animals/."""
    return pet_thumb_url_for(image_field, size)


@register.inclusion_tag("anunturi/includes/pet_card_meta_footer.html")
def pet_card_meta_footer(pet):
    """Localitate + M/F + vârstă (rânduri sub nume pe card)."""
    return pet_card_meta_context(pet)


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


@register.simple_tag(takes_context=True)
def eu_t(context, key, ro_fallback=""):
    """
    Text UI: pe site EU → engleză din eu_ui / eu_ui_labels;
    pe .ro → ro_fallback (sau cheia).
    """
    request = context.get("request")
    eu_active = bool(context.get("eu_site_active"))
    if request is not None and getattr(request, "eu_site_active", False):
        eu_active = True
    if eu_active:
        pack = context.get("eu_ui") or {}
        if key in pack and pack[key]:
            return pack[key]
        from home.eu_ui_labels import eu_ui_label

        return eu_ui_label(key) or ro_fallback or key
    return ro_fallback or key
