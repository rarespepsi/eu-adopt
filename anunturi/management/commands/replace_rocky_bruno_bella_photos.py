"""
Șterge pozele actuale pentru Rocky, Bruno și Bella și le înlocuiește cu imagini noi de pe internet (Dog CEO API).

Rulează: python manage.py replace_rocky_bruno_bella_photos
"""
import json
import urllib.request
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile

from anunturi.models import Pet
from anunturi.image_utils import crop_white_margins

DOG_CEO_RANDOM_3 = "https://dog.ceo/api/breeds/image/random/3"
NUME_INLOCUIRE = ("Rocky", "Bruno", "Bella")


def fetch_image_urls(count=3):
    """Returnează o listă de URL-uri de imagini câini de pe Dog CEO API."""
    req = urllib.request.Request(
        DOG_CEO_RANDOM_3,
        headers={"User-Agent": "EU-Adopt-Bot/1.0"},
    )
    with urllib.request.urlopen(req, timeout=15) as resp:
        data = json.loads(resp.read().decode())
    if data.get("status") != "success" or "message" not in data:
        return []
    urls = data["message"]
    return urls[:count] if isinstance(urls, list) else [urls]


def download_image(url):
    """Descarcă imaginea de la URL; returnează bytes sau None."""
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EU-Adopt-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


def clear_pet_images(pet):
    """Șterge fișierele pozelor existente și golește câmpurile."""
    for field_name in ("imagine", "imagine_2", "imagine_3"):
        field = getattr(pet, field_name, None)
        if field and getattr(field, "name", None):
            try:
                field.delete(save=False)
            except Exception:
                pass
    pet.imagine_fallback = ""
    pet.save()


def set_pet_images_from_urls(pet, urls, base_name):
    """Descarcă imaginile de la URL-uri, taie marginile albe, salvează pe pet."""
    for i, url in enumerate(urls[:3]):
        content = download_image(url)
        if not content:
            continue
        content = crop_white_margins(content, threshold=245, format_out="JPEG")
        ext = ".jpg"
        filename = f"{base_name}_{i + 1}{ext}"
        field_name = ["imagine", "imagine_2", "imagine_3"][i]
        field_file = getattr(pet, field_name)
        field_file.save(filename, ContentFile(content), save=True)
    pet.imagine_fallback = ""
    pet.save()


class Command(BaseCommand):
    help = "Înlocuiește pozele pentru Rocky, Bruno și Bella cu imagini noi de pe internet."

    def handle(self, *args, **options):
        pets = Pet.objects.filter(nume__in=NUME_INLOCUIRE)
        if not pets.exists():
            self.stdout.write(self.style.WARNING("Nu s-au găsit animale cu numele Rocky, Bruno sau Bella."))
            return

        for pet in pets:
            self.stdout.write(f"Procesez: {pet.nume} (pk={pet.pk}) ...")
            clear_pet_images(pet)
            urls = fetch_image_urls(3)
            if not urls:
                self.stdout.write(self.style.ERROR(f"  Nu s-au putut obține URL-uri pentru {pet.nume}. Sari peste."))
                continue
            base_name = pet.slug or pet.nume.lower().replace(" ", "-")
            set_pet_images_from_urls(pet, urls, base_name)
            self.stdout.write(self.style.SUCCESS(f"  Ok: {pet.nume} – 3 poze înlocuite."))

        self.stdout.write(self.style.SUCCESS("Gata."))
