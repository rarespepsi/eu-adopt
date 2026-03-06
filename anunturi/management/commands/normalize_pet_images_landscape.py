from django.core.management.base import BaseCommand


class Command(BaseCommand):
    help = (
        "Normalizează pozele animalelor la format landscape standard (ex. 1200x900) "
        "folosind logica _ensure_landscape_image din modelul Pet."
    )

    def handle(self, *args, **options):
        from anunturi.models import Pet

        total = 0
        self.stdout.write("Pornesc normalizarea pozelor la format landscape...")
        for pet in Pet.objects.all().iterator():
            for field_name in ("imagine", "imagine_2", "imagine_3"):
                pet._ensure_landscape_image(field_name)
            total += 1
            if total % 50 == 0:
                self.stdout.write(f"Procesate {total} animale...")
        # Evităm diacriticele, ca să nu dea eroare în consola Windows
        self.stdout.write(self.style.SUCCESS(f"Normalizare terminata pentru {total} animale."))

