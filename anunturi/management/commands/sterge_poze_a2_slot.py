"""Sterge pozele pentru un slot A2 (1-12). Ex: python manage.py sterge_poze_a2_slot 6"""
from django.core.management.base import BaseCommand
from anunturi.models import Pet

def clear_pet_images(pet):
    for field_name in ("imagine", "imagine_2", "imagine_3"):
        field = getattr(pet, field_name, None)
        if field and getattr(field, "name", None):
            try:
                field.delete(save=False)
            except Exception:
                pass
    pet.imagine_fallback = ""
    pet.save()

class Command(BaseCommand):
    help = "Sterge pozele pentru un slot A2 (1-12)."

    def add_arguments(self, parser):
        parser.add_argument("slot", type=int, help="Slot A2 (1-12)")

    def handle(self, *args, **options):
        slot = options["slot"]
        if slot < 1 or slot > 12:
            self.stdout.write(self.style.ERROR("Slot trebuie 1-12."))
            return
        qs = list(Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:12])
        if slot > len(qs):
            self.stdout.write(self.style.ERROR("Nu exista atatia caini."))
            return
        pet = qs[slot - 1]
        self.stdout.write("A2.{}: {} (pk={}) – sterg pozele...".format(slot, pet.nume, pet.pk))
        clear_pet_images(pet)
        self.stdout.write(self.style.SUCCESS("Gata."))
