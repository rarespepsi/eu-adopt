"""
Context processors for global sidebar boxes.
"""
from django.conf import settings


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
