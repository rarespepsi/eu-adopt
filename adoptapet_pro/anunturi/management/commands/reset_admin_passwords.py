"""
Resetează parola pentru toți utilizatorii admin (superuser).

Rulează:
  python manage.py reset_admin_passwords NOUA_PAROLA

Sau cu DATABASE_URL pentru baza de pe Render:
  $env:DATABASE_URL="postgresql://..."; python manage.py reset_admin_passwords NOUA_PAROLA
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Reseteaza parola tuturor utilizatorilor admin (is_superuser=True)."

    def add_arguments(self, parser):
        parser.add_argument(
            "password",
            type=str,
            help="Noua parola pentru toti adminii.",
        )

    def handle(self, *args, **options):
        password = options["password"]
        if len(password) < 8:
            self.stderr.write("Parola trebuie sa aiba minim 8 caractere.")
            return
        admins = User.objects.filter(is_superuser=True)
        count = admins.count()
        if count == 0:
            self.stdout.write("Nu exista niciun admin. Ruleaza: python manage.py createsuperuser")
            return
        for user in admins:
            user.set_password(password)
            user.save()
            self.stdout.write("Resetat parola pentru: %s" % user.username)
        self.stdout.write(self.style.SUCCESS("Gata. %d admin(i) au parola noua." % count))
