"""
Adaugă parteneri demo pentru pagina Beneficii după adopție.

Rulează: python manage.py seed_beneficiary_partners
"""
from django.core.management.base import BaseCommand
from anunturi.models import BeneficiaryPartner, BENEFICIARY_CATEGORY_VET, BENEFICIARY_CATEGORY_GROOMING, BENEFICIARY_CATEGORY_SHOP


DEMO_PARTNERS = [
    {"name": "VetCare Plus", "category": BENEFICIARY_CATEGORY_VET, "county": "bucuresti", "city": "București", "offer_text": "-15% la prima consultație + vaccinare", "email": "", "url": "https://example.com/vet1", "order": 1},
    {"name": "Clinica Dr. Patru", "category": BENEFICIARY_CATEGORY_VET, "county": "cluj", "city": "Cluj-Napoca", "offer_text": "-10% la pachet sterilizare", "email": "", "url": "", "order": 2},
    {"name": "ToaletarePet Studio", "category": BENEFICIARY_CATEGORY_GROOMING, "county": "iasi", "city": "Iași", "offer_text": "-10% la prima toaletare", "email": "", "url": "", "order": 1},
    {"name": "Salon Canin Elegance", "category": BENEFICIARY_CATEGORY_GROOMING, "county": "bucuresti", "city": "București", "offer_text": "1 băi gratuită la al 2-lea vizită", "email": "", "url": "", "order": 2},
    {"name": "Pet Shop Maxi", "category": BENEFICIARY_CATEGORY_SHOP, "county": "bucuresti", "city": "București", "offer_text": "-10% la mâncare și accesorii (valabil 30 zile)", "email": "", "url": "", "order": 1},
    {"name": "Animal House", "category": BENEFICIARY_CATEGORY_SHOP, "county": "cluj", "city": "Cluj-Napoca", "offer_text": "Reducere 5% la prima cumpărătură peste 100 RON", "email": "", "url": "", "order": 2},
]


class Command(BaseCommand):
    help = "Adaugă parteneri demo pentru Beneficii după adopție."

    def handle(self, *args, **options):
        created = 0
        for data in DEMO_PARTNERS:
            _, c = BeneficiaryPartner.objects.get_or_create(
                name=data["name"],
                category=data["category"],
                defaults={
                    "county": data.get("county", ""),
                    "city": data.get("city", ""),
                    "offer_text": data.get("offer_text", ""),
                    "email": data.get("email", ""),
                    "url": data.get("url", ""),
                    "order": data.get("order", 0),
                    "is_active": True,
                },
            )
            if c:
                created += 1
        self.stdout.write(self.style.SUCCESS(f"Parteneri beneficii: {created} creați, {len(DEMO_PARTNERS) - created} existau deja."))
