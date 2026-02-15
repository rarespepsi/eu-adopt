from django import template
from django.contrib.auth.models import AbstractBaseUser

register = template.Library()


@register.filter
def in_group(user: AbstractBaseUser, group_name: str) -> bool:
    """Returnează True dacă utilizatorul face parte din grupul cu numele dat (categoria de client)."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()
