from .models import WishlistItem
from .data import DEMO_DOGS


def wishlist_counts(request):
    """
    Injectează wishlist_count și nav_avatar_url în toate paginile (pentru navbar).
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

    return {
        "wishlist_count": wishlist_count,
        "nav_avatar_url": nav_avatar_url,
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
    }

