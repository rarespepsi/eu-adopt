from django import template

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