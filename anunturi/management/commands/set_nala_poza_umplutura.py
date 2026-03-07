"""Pune o poza de umplutura (Dog CEO API) la Nala; taie marginile albe din imagine. Ruleaza: python manage.py set_nala_poza_umplutura"""
import json
import urllib.request
from django.core.management.base import BaseCommand
from django.core.files.base import ContentFile
from anunturi.models import Pet
from anunturi.image_utils import crop_white_margins


def download_image(url):
    try:
        req = urllib.request.Request(url, headers={"User-Agent": "EU-Adopt-Bot/1.0"})
        with urllib.request.urlopen(req, timeout=15) as resp:
            return resp.read()
    except Exception:
        return None


class Command(BaseCommand):
    help = "Pune o poza de umplutura la Nala (Dog CEO API)."

    def handle(self, *args, **options):
        pet = Pet.objects.filter(nume="Nala").first()
        if not pet:
            self.stdout.write(self.style.ERROR("Nala nu a fost gasit."))
            return
        req = urllib.request.Request(
            "https://dog.ceo/api/breeds/image/random",
            headers={"User-Agent": "EU-Adopt-Bot/1.0"},
        )
        with urllib.request.urlopen(req, timeout=15) as resp:
            data = json.loads(resp.read().decode())
        url = data.get("message") if data.get("status") == "success" else None
        if not url:
            self.stdout.write(self.style.ERROR("Nu s-a putut obtine URL imagine."))
            return
        content = download_image(url)
        if not content:
            self.stdout.write(self.style.ERROR("Nu s-a putut descarca imaginea."))
            return
        content = crop_white_margins(content, threshold=245, format_out="JPEG")
        ext = ".jpg"
        filename = "nala_umplutura_1" + ext
        if pet.imagine and getattr(pet.imagine, "name", None):
            try:
                pet.imagine.delete(save=False)
            except Exception:
                pass
        pet.imagine.save(filename, ContentFile(content), save=True)
        pet.imagine_fallback = ""
        pet.save()
        self.stdout.write(self.style.SUCCESS("Nala (pk=%s): poza de umplutura setata." % pet.pk))
