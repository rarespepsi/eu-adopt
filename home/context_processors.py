from .models import WishlistItem


def wishlist_counts(request):
    """
    Injectează wishlist_count și nav_avatar_url în toate paginile (pentru navbar).
    La orice eroare (DB, migrații) returnăm 0 / None ca să nu 500 întreaga pagină.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"wishlist_count": 0, "nav_avatar_url": None}
    try:
        count = WishlistItem.objects.filter(user=request.user).count()
        avatar_url = None
        profile = getattr(request.user, "profile", None)
        if profile and profile.poza_1:
            try:
                avatar_url = profile.poza_1.url
            except Exception:
                pass
        return {"wishlist_count": count, "nav_avatar_url": avatar_url}
    except Exception:
        return {"wishlist_count": 0, "nav_avatar_url": None}

