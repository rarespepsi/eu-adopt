"""
Sterge definitiv pozele (imagine, imagine_2, imagine_3, imagine_fallback) pentru cainii
din sloturile A2.10 si A2.12. Foloseste ordinea fixa: adoptable, -data_adaugare, primele 12;
pozitiile 10 si 12 (1-based) = index 9 si 11.

Ruleaza: python manage.py sterge_poze_a2_10_12
"""
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
    help = "Sterge definitiv pozele pentru A2.10 si A2.12 (ordine fixa: pozitiile 10 si 12 din primele 12)."

    def handle(self, *args, **options):
        qs = Pet.objects.filter(status="adoptable").exclude(adoption_status="adopted").order_by("-data_adaugare")[:12]
        pets = list(qs)
        if len(pets) < 12:
            self.stdout.write(self.style.WARNING("Mai putin de 12 caini adoptabili. Folosesc ce exista."))
        # A2.10 = index 9, A2.12 = index 11 (1-based)
        indices = [9, 11]
        for i in indices:
            if i >= len(pets):
                continue
            pet = pets[i]
            self.stdout.write("A2.{}: {} (pk={}) – sterg pozele...".format(i + 1, pet.nume, pet.pk))
            clear_pet_images(pet)
            self.stdout.write(self.style.SUCCESS("  Gata."))
        self.stdout.write(self.style.SUCCESS("Operatie terminata."))
