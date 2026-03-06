"""
Context processors for global sidebar boxes, wishlist count, and navbar counters.
"""
from django.conf import settings


def navbar_counters_context(request):
    """Furnizează active_animals și adopted_animals pentru navbar pe toate paginile (aceeași așezare ca pe home)."""
    from anunturi.models import Pet
    return {
        "active_animals": Pet.objects.filter(status="adoptable").count(),
        "adopted_animals": Pet.objects.filter(status="adopted").count(),
    }


def wishlist_context(request):
    """Furnizează wishlist_count și wishlist_pet_ids pentru navbar (A0) și pentru butonul Te plac (toate favoritele, inclusiv adoptate)."""
    if request.user.is_authenticated:
        from anunturi.models import PetFavorite
        pet_ids = list(PetFavorite.objects.filter(user=request.user).values_list("pet_id", flat=True))
        return {
            "wishlist_count": len(pet_ids),
            "wishlist_pet_ids": pet_ids,
        }
    return {"wishlist_count": 0, "wishlist_pet_ids": []}


def sidebar_boxes(request):
    """
    Provides sidebar boxes data for all pages.
    Hardcoded sample content for now - will be replaced with database later.
    """
    # Left sidebar boxes
    left_boxes = [
        {
            'title': '💝 Donează',
            'text': 'Ajută-ne să continuăm salvarea animalelor. Orice donație contează!',
            'image': 'images/donation-placeholder.jpg',
            'link_url': '/contact/',
            'button_text': 'Donează acum',
            'animation_class': 'box-pulse',
        },
        {
            'title': '🏥 Servicii Veterinare',
            'text': 'Găsește clinici veterinare de încredere pentru animalele tale.',
            'image': 'images/vet-placeholder.jpg',
            'link_url': '/contact/',
            'button_text': 'Vezi servicii',
            'animation_class': '',
        },
    ]
    
    # Right sidebar boxes
    right_boxes = [
        {
            'title': '🤝 Cazuri Sociale',
            'text': 'Ajută animalele care au nevoie de ajutor urgent. Fiecare contribuție face diferența.',
            'image': 'images/social-case-placeholder.jpg',
            'link_url': '/contact/',
            'button_text': 'Află mai mult',
            'animation_class': 'box-fade',
        },
        {
            'title': '📢 Promoție',
            'text': 'Spațiu pentru promovare. Contactează-ne pentru detalii.',
            'image': 'images/promo-placeholder.jpg',
            'link_url': '/contact/',
            'button_text': 'Contact',
            'animation_class': '',
        },
    ]
    
    return {
        'sidebar_boxes_left': left_boxes,
        'sidebar_boxes_right': right_boxes,
    }
