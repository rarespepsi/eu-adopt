from .models import WishlistItem
from .data import DEMO_DOGS


def _get_display_role(request):
    """
    Rol folosit pentru afișare („Vezi ca”): dacă userul e staff și a ales view_as în sesiune,
    returnăm acel rol; altfel rolul real din account_profile.
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    if user.is_staff or getattr(user, "is_superuser", False):
        view_as = request.session.get("view_as_role")
        if view_as in ("pf", "org", "collaborator"):
            return view_as
    try:
        profile = getattr(user, "account_profile", None)
        if profile:
            return profile.role
    except Exception:
        pass
    return None


def wishlist_counts(request):
    """
    Injectează wishlist_count, nav_avatar_url și display_role în toate paginile.
    La orice eroare (DB, migrații) returnăm 0 / None ca să nu 500 întreaga pagină.
    """
    user = getattr(request, "user", None)
    wishlist_count = 0
    nav_avatar_url = None
    if user and user.is_authenticated:
        try:
            wishlist_count = WishlistItem.objects.filter(user=user).count()
            profile = getattr(user, "profile", None)
            if profile and profile.poza_1:
                try:
                    nav_avatar_url = profile.poza_1.url
                except Exception:
                    nav_avatar_url = None
        except Exception:
            wishlist_count = 0
            nav_avatar_url = None

    # Contoare animale – demo global (aceleași cifre ca pe Home, bazate pe DEMO_DOGS)
    active_animals = len(DEMO_DOGS)
    adopted_animals = 0

    display_role = _get_display_role(request)
    # True doar când admin/staff folosește „Vezi ca Colaborator” (nu pentru colaboratori reali)
    is_viewing_as_collaborator = (
        user
        and user.is_authenticated
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        and request.session.get("view_as_role") == "collaborator"
    )

    return {
        "wishlist_count": wishlist_count,
        "nav_avatar_url": nav_avatar_url,
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
        "display_role": display_role,
        "is_viewing_as_collaborator": is_viewing_as_collaborator,
    }

