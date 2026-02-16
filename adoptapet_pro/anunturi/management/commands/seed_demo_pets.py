"""
Adaugă animale demo în baza de date pentru ca site-ul să nu fie gol.

Rulează:
  python manage.py seed_demo_pets

Rulează automat la deploy pe Render (build.sh).
"""
from django.core.management.base import BaseCommand
from django.core.management import call_command
from pathlib import Path

from anunturi.models import Pet


# Animale demo: nume, slug, imagine_fallback, etc.
DEMO_PETS = [
    {
        "nume": "Charlie",
        "slug": "charlie",
        "rasa": "Labrador",
        "varsta": "young",
        "sex": "male",
        "marime": "large",
        "descriere": "Charlie este un câine prietenos și plin de energie. Iubește plimbările și jocurile.",
        "imagine_fallback": "images/pets/charlie-275x275.jpg",
        "status": "adoptable",
        "featured": True,
        "judet": "bucuresti",
    },
    {
        "nume": "Shorty",
        "slug": "shorty",
        "rasa": "Beagle",
        "varsta": "adult",
        "sex": "male",
        "marime": "medium",
        "descriere": "Shorty este calm și se adaptează ușor. Ideal pentru apartament.",
        "imagine_fallback": "images/pets/shorty1-180x180.jpg",
        "status": "adoptable",
        "featured": True,
        "judet": "cluj",
    },
    {
        "nume": "Cindy",
        "slug": "cindy",
        "rasa": "Corgi",
        "varsta": "young",
        "sex": "female",
        "marime": "medium",
        "descriere": "Cindy este veselă și inteligentă. Îi place compania oamenilor.",
        "imagine_fallback": "images/pets/cindy1-275x275.jpg",
        "status": "adoptable",
        "featured": False,
        "judet": "brasov",
    },
    {
        "nume": "Chester",
        "slug": "chester",
        "rasa": "Golden Retriever",
        "varsta": "adult",
        "sex": "male",
        "marime": "large",
        "descriere": "Chester este foarte blând, ideal pentru familii cu copii.",
        "imagine_fallback": "images/pets/chester1-275x275.jpg",
        "status": "adoptable",
        "featured": False,
        "judet": "iasi",
    },
    {
        "nume": "Luna",
        "slug": "luna",
        "rasa": "Pisică Europeană",
        "tip": "cat",
        "varsta": "young",
        "sex": "female",
        "marime": "small",
        "descriere": "Luna este o pisică afectuoasă care caută o casă caldă.",
        "imagine_fallback": "images/pets/charlie-275x275.jpg",
        "status": "adoptable",
        "featured": True,
        "judet": "timis",
    },
]


def create_placeholder_images(static_root: Path) -> None:
    """Creează imagini placeholder în static/images/pets/ dacă nu există."""
    try:
        from PIL import Image
    except ImportError:
        return
    images_dir = static_root / "images"
    images_dir.mkdir(parents=True, exist_ok=True)
    pets_dir = images_dir / "pets"
    pets_dir.mkdir(parents=True, exist_ok=True)
    needed_pets = [
        "charlie-275x275.jpg",
        "charlie-400x200.jpg",
        "charlie-180x180.jpg",
        "charlie-600x240.jpg",
        "cindy1-275x110.jpg",
        "chester1-275x110.jpg",
    ]
    needed_slides = ["slide1.jpg", "slide2.jpg", "slide3.jpg"]

    def ensure_image(dir_path: Path, name: str, default_size=(275, 275)) -> None:
        fpath = dir_path / name
        if fpath.exists():
            return
        w, h = default_size
        if "400x200" in name:
            w, h = 400, 200
        elif "180x180" in name:
            w, h = 180, 180
        elif "600x240" in name:
            w, h = 600, 240
        elif "275x110" in name:
            w, h = 275, 110
        elif "slide" in name:
            w, h = 800, 400  # slide mai mic decât 2880x1000 pentru placeholder
        img = Image.new("RGB", (w, h), color=(210, 180, 140))
        img.save(fpath, "JPEG", quality=85)
        print(f"  Creat placeholder: {name}")

    for name in needed_pets:
        ensure_image(pets_dir, name)
    for name in needed_slides:
        ensure_image(images_dir, name)


class Command(BaseCommand):
    help = "Adaugă animale demo (Charlie, Shorty, Cindy, Chester, Luna) dacă baza e goală."

    def add_arguments(self, parser):
        parser.add_argument(
            "--force",
            action="store_true",
            help="Adaugă animale chiar dacă există deja (va actualiza doar cele cu slug-ul dat).",
        )
        parser.add_argument(
            "--no-images",
            action="store_true",
            help="Nu crea imagini placeholder.",
        )

    def handle(self, *args, **options):
        from django.conf import settings
        static_root = Path(settings.BASE_DIR) / "static"
        if not options.get("no_images") and static_root.exists():
            self.stdout.write("Verific imagini placeholder...")
            create_placeholder_images(static_root)

        count = 0
        for data in DEMO_PETS:
            defaults = {k: v for k, v in data.items() if k != "slug"}
            defaults.setdefault("tip", "dog")
            pet, created = Pet.objects.get_or_create(
                slug=data["slug"],
                defaults=defaults,
            )
            if created:
                count += 1
                self.stdout.write(self.style.SUCCESS("  Adaugat: %s" % pet.nume))
            elif options.get("force"):
                for k, v in defaults.items():
                    setattr(pet, k, v)
                pet.save()
                self.stdout.write(self.style.WARNING("  Actualizat: %s" % pet.nume))

        if count:
            self.stdout.write(self.style.SUCCESS("Gata. Adaugate %d animale demo." % count))
        else:
            self.stdout.write("Animale demo exista deja. Foloseste --force pentru actualizare.")
