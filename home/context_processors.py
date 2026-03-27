from .models import WishlistItem, PetMessage, CollabServiceMessage
from .data import DEMO_DOGS
from django.utils import timezone


def _collaborator_tip_partener_for_nav(request):
    """
    cabinet | servicii | magazin — aliniat cu views._collaborator_tip_partener
    (inclus staff „Vezi ca colaborator” + view_as_collab_tip în sesiune).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return "servicii"
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        if request.session.get("view_as_role") == "collaborator":
            st = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
            if st in ("cabinet", "servicii", "magazin"):
                return st
            return "servicii"
    try:
        prof = getattr(user, "profile", None)
        tip = (getattr(prof, "collaborator_type", None) or "").strip().lower()
    except Exception:
        tip = ""
    if tip in ("cabinet", "servicii", "magazin"):
        return tip
    return "servicii"


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
    # MyPet → PF / ONG. Magazinul meu → colaborator. Staff: după „Vezi ca …”.
    if not user or not user.is_authenticated:
        show_mypet_nav = False
        show_magazinul_meu_nav = False
    elif user.is_staff or getattr(user, "is_superuser", False):
        va = request.session.get("view_as_role")
        if va == "collaborator":
            show_mypet_nav = False
            show_magazinul_meu_nav = True
        elif va in ("pf", "org"):
            show_mypet_nav = True
            show_magazinul_meu_nav = False
        else:
            show_mypet_nav = True
            show_magazinul_meu_nav = False
    else:
        show_mypet_nav = display_role in ("pf", "org")
        show_magazinul_meu_nav = display_role == "collaborator"
    # True doar când admin/staff folosește „Vezi ca Colaborator” (nu pentru colaboratori reali)
    is_viewing_as_collaborator = (
        user
        and user.is_authenticated
        and (getattr(user, "is_staff", False) or getattr(user, "is_superuser", False))
        and request.session.get("view_as_role") == "collaborator"
    )

    # Mesaje necitite: PetMessage (animale) + CollabServiceMessage (servicii/produse).
    pet_message_unread_count = 0
    collab_business_unread_count = 0
    collab_client_unread_count = 0
    message_unread_count = 0
    if user and user.is_authenticated:
        try:
            active_since = timezone.now() - timezone.timedelta(days=30)
            pet_message_unread_count = PetMessage.objects.filter(
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            ).count()
            collab_business_unread_count = CollabServiceMessage.objects.filter(
                receiver=user,
                collaborator=user,
                is_read=False,
                created_at__gte=active_since,
            ).count()
            collab_client_unread_count = (
                CollabServiceMessage.objects.filter(
                    receiver=user,
                    is_read=False,
                    created_at__gte=active_since,
                )
                .exclude(collaborator=user)
                .count()
            )
            if show_magazinul_meu_nav:
                message_unread_count = collab_business_unread_count
            elif show_mypet_nav:
                # MyPet (PF/ONG) rămâne strict pe fluxul de pet.
                message_unread_count = pet_message_unread_count
            else:
                message_unread_count = (
                    pet_message_unread_count
                    + collab_business_unread_count
                    + collab_client_unread_count
                )
        except Exception:
            pet_message_unread_count = 0
            collab_business_unread_count = 0
            collab_client_unread_count = 0
            message_unread_count = 0

    # Formă restrânsă în navbar: MyListVet (cabinet veterinar), MyListServicii (grooming), Magazinul meu
    nav_magazinul_meu_label = "Magazinul meu"
    if show_magazinul_meu_nav:
        tip_nav = _collaborator_tip_partener_for_nav(request)
        if tip_nav == "magazin":
            nav_magazinul_meu_label = "Magazinul meu"
        elif tip_nav == "cabinet":
            nav_magazinul_meu_label = "MyListVet"
        else:
            nav_magazinul_meu_label = "MyListServicii"

    return {
        "wishlist_count": wishlist_count,
        "nav_avatar_url": nav_avatar_url,
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
        "display_role": display_role,
        "show_mypet_nav": show_mypet_nav,
        "show_magazinul_meu_nav": show_magazinul_meu_nav,
        "is_viewing_as_collaborator": is_viewing_as_collaborator,
        "message_unread_count": message_unread_count,
        "pet_message_unread_count": pet_message_unread_count,
        "collab_business_unread_count": collab_business_unread_count,
        "collab_client_unread_count": collab_client_unread_count,
        "nav_magazinul_meu_label": nav_magazinul_meu_label,
    }

