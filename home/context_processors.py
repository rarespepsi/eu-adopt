from .models import WishlistItem


def wishlist_counts(request):
    """
    Injectează wishlist_count în toate paginile (pentru navbar).
    """
    if not getattr(request, "user", None) or not request.user.is_authenticated:
        return {"wishlist_count": 0}
    return {"wishlist_count": WishlistItem.objects.filter(user=request.user).count()}

