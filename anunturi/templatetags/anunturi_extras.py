from django import template
from django.contrib.auth.models import AbstractBaseUser

register = template.Library()


@register.simple_tag(takes_context=True)
def user_is_authenticated(context):
    """Reusable check: True dacă utilizatorul este autentificat, altfel False. Folosește: {% user_is_authenticated as is_auth %}."""
    request = context.get("request")
    return bool(request and getattr(request.user, "is_authenticated", False) and request.user.is_authenticated)


@register.filter
def in_group(user: AbstractBaseUser, group_name: str) -> bool:
    """Returnează True dacă utilizatorul face parte din grupul cu numele dat (categoria de client)."""
    if not user or not user.is_authenticated:
        return False
    return user.groups.filter(name=group_name).exists()


@register.filter
def get_item(d, key):
    """Acces dict după cheie în template: {{ mydict|get_item:key }}."""
    if d is None:
        return None
    return d.get(key)


@register.filter
def get_at_index(seq, index):
    """Acces element din listă după index: {{ list|get_at_index:0 }}. Dacă index invalid, returnează dict gol."""
    if seq is None:
        return {}
    try:
        i = int(index)
        if 0 <= i < len(seq):
            return seq[i]
    except (TypeError, ValueError):
        pass
    return {}
