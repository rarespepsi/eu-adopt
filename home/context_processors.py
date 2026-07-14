from django.conf import settings

from .models import (
    AccountProfile,
    WishlistItem,
    SiteCartItem,
    PetMessage,
    CollabServiceMessage,
    UserInboxNotification,
)
from .data import DEMO_DOGS
from django.urls import reverse
from django.utils import timezone

# Aliniat cu home.views.MESSAGE_ARCHIVE_DAYS (fereastra „mesaje active”).
_NAVBAR_UNREAD_DAYS = 30

_MYPET_PUB_SLOT_CODES = ("MP.L1", "MP.L2", "MP.L3")


def _mypet_pub_slots_for_request(request):
    """Sloturi live MP.L1–L3 pentru sidebar MyPet (/mypet/, adopțiile mele)."""
    try:
        rm = getattr(request, "resolver_match", None)
        if not rm or rm.url_name not in ("mypet", "mypet_adopter_adoptions"):
            return []
        from .pub_slot_defaults import pub_slots_ordered

        return pub_slots_ordered("mypet", _MYPET_PUB_SLOT_CODES)
    except Exception:
        return []


def get_navbar_unread_counts(user):
    """
    Contoare pentru plicul din navbar (aceeași logică ca în wishlist_counts).
    Folosit în JSON-uri thread ca `navbar_unread_total` să coincidă cu HTML-ul inițial.
    """
    empty = {
        "pet_message": 0,
        "collab_business": 0,
        "collab_client": 0,
        "inbox_notification": 0,
        "total": 0,
    }
    if not user or not user.is_authenticated:
        return empty
    try:
        active_since = timezone.now() - timezone.timedelta(days=_NAVBAR_UNREAD_DAYS)
        pet_message = PetMessage.objects.filter(
            receiver=user,
            is_read=False,
            created_at__gte=active_since,
        ).count()
        collab_business = CollabServiceMessage.objects.filter(
            receiver=user,
            collaborator=user,
            is_read=False,
            created_at__gte=active_since,
        ).count()
        collab_client = (
            CollabServiceMessage.objects.filter(
                receiver=user,
                is_read=False,
                created_at__gte=active_since,
            )
            .exclude(collaborator=user)
            .count()
        )
        inbox_notification = UserInboxNotification.objects.filter(
            user=user,
            is_read=False,
            created_at__gte=active_since,
        ).count()
        total = pet_message + collab_business + collab_client + inbox_notification
        return {
            "pet_message": pet_message,
            "collab_business": collab_business,
            "collab_client": collab_client,
            "inbox_notification": inbox_notification,
            "total": total,
        }
    except Exception:
        return {**empty}


def _collaborator_tip_partener_for_nav(request):
    """
    cabinet | servicii | magazin | transport — aliniat cu views._collaborator_tip_partener
    (inclus staff „Vezi ca colaborator” + view_as_collab_tip în sesiune).
    """
    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return "servicii"
    if getattr(user, "is_staff", False) or getattr(user, "is_superuser", False):
        if request.session.get("view_as_role") == "collaborator":
            st = (request.session.get("view_as_collab_tip") or "servicii").strip().lower()
            if st in ("cabinet", "servicii", "magazin", "transport"):
                return st
            return "servicii"
    try:
        prof = getattr(user, "profile", None)
        tip = (getattr(prof, "collaborator_type", None) or "").strip().lower()
    except Exception:
        tip = ""
    if tip in ("cabinet", "servicii", "magazin", "transport"):
        return tip
    return "servicii"


def _get_display_role(request):
    """
    Rol folosit pentru afișare („Vezi ca”): dacă userul e staff și a ales view_as în sesiune,
    returnăm acel rol; altfel rolul real din account_profile.
    Superuser: fără rol afișat (excepție — acces complet în UI).
    """
    from home.population_onboarding import is_superuser_full_access

    user = getattr(request, "user", None)
    if not user or not user.is_authenticated:
        return None
    if is_superuser_full_access(user):
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


def prelaunch_mode(request):
    """True când modul PRE-LAUNCH este activ (EUADOPT_PRELAUNCH_MODE=1)."""
    from home.prelaunch_soft_lock import (
        PRELAUNCH_SOFT_LOCK_BANNER,
        prelaunch_first_hint_for_url_name,
        prelaunch_monetization_soft_lock_enabled,
        prelaunch_soft_lock_active_for_user,
    )

    rm = getattr(request, "resolver_match", None)
    url_name = getattr(rm, "url_name", None) if rm else None
    return {
        "prelaunch_mode": bool(getattr(settings, "PRELAUNCH_MODE", False)),
        "prelaunch_soft_lock": prelaunch_soft_lock_active_for_user(getattr(request, "user", None)),
        "prelaunch_soft_lock_banner": PRELAUNCH_SOFT_LOCK_BANNER,
        "prelaunch_first_hint": prelaunch_first_hint_for_url_name(url_name or ""),
        "prelaunch_monetization_soft_lock": prelaunch_monetization_soft_lock_enabled(),
    }


def population_org(request):
    """Context populare adăpost/ONG: min/max animale, meniu redus, banner."""
    from home.population_onboarding import population_context_for_request

    return population_context_for_request(request)


def sms_otp(request):
    """Cod SMS dev (populare) sau flag live — disponibil în toate template-urile."""
    from home.sms_otp import sms_otp_template_context

    return sms_otp_template_context()


def site_guide(request):
    """Context: widget Ghid EU-Adopt pe paginile principale selectate."""
    from django.urls import reverse

    from home.site_guide import is_site_guide_enabled, is_site_guide_path

    path = getattr(request, "path", "/") or "/"
    enabled = is_site_guide_enabled() and is_site_guide_path(path)
    ask_url = ""
    if enabled:
        try:
            ask_url = reverse("site_guide_ask")
        except Exception:
            ask_url = ""
    return {
        "show_site_guide": enabled,
        "site_guide_ask_url": ask_url,
    }


def user_onboarding(request):
    """Context: banner + tur scurt la prima vizită (user nou)."""
    from home.user_onboarding import onboarding_payload_for_request

    payload = onboarding_payload_for_request(request)
    return {
        "user_onboarding_payload": payload,
    }


def wishlist_counts(request):
    """
    Injectează wishlist_count, nav_avatar_url și display_role în toate paginile.
    La orice eroare (DB, migrații) returnăm 0 / None ca să nu 500 întreaga pagină.
    """
    user = getattr(request, "user", None)
    wishlist_count = 0
    site_cart_count = 0
    site_cart_ref_keys = frozenset()
    nav_avatar_url = None
    if user and user.is_authenticated:
        try:
            wishlist_count = WishlistItem.objects.filter(user=user).count()
            site_cart_ref_keys = frozenset(
                SiteCartItem.objects.filter(user=user).values_list("ref_key", flat=True)
            )
            site_cart_count = len(site_cart_ref_keys)
            profile = getattr(user, "profile", None)
            if profile and profile.poza_1:
                try:
                    nav_avatar_url = profile.poza_1.url
                except Exception:
                    nav_avatar_url = None
        except Exception:
            wishlist_count = 0
            site_cart_count = 0
            site_cart_ref_keys = frozenset()
            nav_avatar_url = None

    # Contoare animale – demo global (aceleași cifre ca pe Home, bazate pe DEMO_DOGS)
    active_animals = len(DEMO_DOGS)
    adopted_animals = 0

    from home.population_onboarding import is_superuser_full_access

    display_role = _get_display_role(request)
    superuser_full_access = is_superuser_full_access(user)
    # MyPet → PF / ONG. Magazinul meu → colaborator. Staff: după „Vezi ca …”.
    if not user or not user.is_authenticated:
        show_mypet_nav = False
        show_magazinul_meu_nav = False
    elif superuser_full_access:
        show_mypet_nav = True
        show_magazinul_meu_nav = True
    elif user.is_staff or getattr(user, "is_superuser", False):
        try:
            real_role = user.account_profile.role
        except Exception:
            real_role = None
        # Cont real colaborator: link My transport / Magazin (nu MyPet), chiar dacă sesiunea are „Vezi ca PF”.
        if real_role == AccountProfile.ROLE_COLLAB:
            show_mypet_nav = False
            show_magazinul_meu_nav = True
        else:
            va = request.session.get("view_as_role")
            if va == "collaborator":
                show_mypet_nav = False
                show_magazinul_meu_nav = True
            elif va in ("pf", "org"):
                show_mypet_nav = True
                show_magazinul_meu_nav = False
            else:
                if real_role in (AccountProfile.ROLE_PF, AccountProfile.ROLE_ORG):
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

    # Mesaje necitite: PetMessage (animale) + CollabServiceMessage (servicii/produse) + inbox.
    pet_message_unread_count = 0
    collab_business_unread_count = 0
    collab_client_unread_count = 0
    inbox_notification_unread_count = 0
    message_unread_count = 0
    if user and user.is_authenticated:
        nav_u = get_navbar_unread_counts(user)
        pet_message_unread_count = nav_u["pet_message"]
        collab_business_unread_count = nav_u["collab_business"]
        collab_client_unread_count = nav_u["collab_client"]
        inbox_notification_unread_count = nav_u["inbox_notification"]
        message_unread_count = nav_u["total"]

    # Link unic mesaje → inbox unificat (toate tipurile de cont)
    navbar_messages_url = ""
    if user and user.is_authenticated:
        try:
            navbar_messages_url = reverse("unified_inbox")
        except Exception:
            navbar_messages_url = ""

    # Formă restrânsă în navbar: MyListVet (cabinet veterinar), MyListServicii (grooming), Magazinul meu
    nav_magazinul_meu_label = "Magazinul meu"
    if show_magazinul_meu_nav:
        tip_nav = _collaborator_tip_partener_for_nav(request)
        if tip_nav == "magazin":
            nav_magazinul_meu_label = "Magazinul meu"
        elif tip_nav == "cabinet":
            nav_magazinul_meu_label = "MyListVet"
        elif tip_nav == "transport":
            nav_magazinul_meu_label = "My transport"
        else:
            nav_magazinul_meu_label = "MyListServicii"

    return {
        "wishlist_count": wishlist_count,
        "site_cart_count": site_cart_count,
        "site_cart_ref_keys": site_cart_ref_keys,
        "site_cart_toggle_url": reverse("site_cart_toggle"),
        "adoption_bonus_cart_unlock_url": reverse("adoption_bonus_cart_unlock"),
        "nav_avatar_url": nav_avatar_url,
        "active_animals": active_animals,
        "adopted_animals": adopted_animals,
        "display_role": display_role,
        "superuser_full_access": superuser_full_access,
        "show_mypet_nav": show_mypet_nav,
        "show_magazinul_meu_nav": show_magazinul_meu_nav,
        "is_viewing_as_collaborator": is_viewing_as_collaborator,
        "message_unread_count": message_unread_count,
        "pet_message_unread_count": pet_message_unread_count,
        "collab_business_unread_count": collab_business_unread_count,
        "collab_client_unread_count": collab_client_unread_count,
        "inbox_notification_unread_count": inbox_notification_unread_count,
        "nav_magazinul_meu_label": nav_magazinul_meu_label,
        "navbar_messages_url": navbar_messages_url,
        "mypet_pub_slots": _mypet_pub_slots_for_request(request),
    }

