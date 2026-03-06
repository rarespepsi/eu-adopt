"""
Adaugă 20 de animale pe contul rarespepsi pentru testare MyPets (grid 4 coloane).

Rulează: python manage.py add_20_pets_rarespepsi
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model
from anunturi.models import Pet

User = get_user_model()

NUME_RASE = [
    ("Rex", "German Shepherd"), ("Max", "Labrador"), ("Bella", "Golden Retriever"),
    ("Lucky", "Husky"), ("Daisy", "Beagle"), ("Bruno", "Rottweiler"),
    ("Mia", "Poodle"), ("Rocky", "Boxer"), ("Lola", "Corgi"),
    ("Zeus", "Doberman"), ("Nala", "Pisică Europeană"), ("Oscar", "Bulldog"),
    ("Luna", "Pisică British"), ("Thor", "Ciobănesc"), ("Coco", "Chihuahua"),
    ("Charlie", "Labrador"), ("Milo", "Pisică"), ("Buddy", "Beagle"),
    ("Lucy", "Câine mix"), ("Jack", "Ciobănesc german"),
]


class Command(BaseCommand):
    help = "Adaugă 20 animale pe contul rarespepsi pentru test MyPets."

    def handle(self, *args, **options):
        user = User.objects.filter(username="rarespepsi").first()
        if not user:
            self.stdout.write(self.style.ERROR("User rarespepsi not found."))
            return
        created = 0
        for i, (nume, rasa) in enumerate(NUME_RASE):
            slug = f"rarespepsi-demo-{i+1}"
            if Pet.objects.filter(slug=slug).exists():
                continue
            tip = "cat" if "Pisică" in rasa or "pisică" in rasa else "dog"
            Pet.objects.create(
                nume=nume,
                slug=slug,
                rasa=rasa,
                tip=tip,
                varsta_aproximativa=[1, 2, 5][i % 3],
                sex=["male", "female"][i % 2],
                marime=["small", "medium", "large"][i % 3],
                descriere=f"Animal demo {i+1} pe contul rarespepsi.",
                status="adoptable",
                judet="bucuresti",
                ong_email=user.email or "rarespepsi@yahoo.com",
                ong_contact_person=user.get_username(),
                ong_phone="0700000000",
                imagine_fallback="images/pets/charlie-275x275.jpg",
                added_by_user=user,
            )
            created += 1
            self.stdout.write(f"  + {nume} ({slug})")
        self.stdout.write(self.style.SUCCESS(f"Total: {created} animale pe rarespepsi. MyPets = grid 4 coloane."))
