from .models import WishlistItem


def wishlist_counts(request):
    """
    Injectează wishlist_count în toate paginile (pentru navbar).
    La orice eroare (DB, migrații) returnăm 0 ca să nu 500 întreaga pagină.
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"wishlist_count": 0}
    try:
        return {"wishlist_count": WishlistItem.objects.filter(user=request.user).count()}
    except Exception:
        return {"wishlist_count": 0}

