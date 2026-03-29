from django import template

from home.pet_traits import trait_label

register = template.Library()


@register.simple_tag
def animal_trait_label(species, field_name):
    """Text afișat pentru o trăsătură (câmp DB), în funcție de specie (dog/cat)."""
    return trait_label(species, field_name)