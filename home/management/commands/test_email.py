"""

Trimite un email de test SMTP (Zoho) către rarespepsi@yahoo.com.



Rulare (din rădăcina proiectului):

  python manage.py test_email



Parola: EMAIL_HOST_PASSWORD în `.env` (App Password Zoho).

"""



from django.conf import settings

from django.core.management.base import BaseCommand, CommandError





class Command(BaseCommand):

    help = "Trimite email de test SMTP Zoho (EU-Adopt) — template HTML + text."



    def handle(self, *args, **options):

        to = "rarespepsi@yahoo.com"



        self.stdout.write(f"EMAIL_BACKEND = {settings.EMAIL_BACKEND}")

        self.stdout.write(f"EMAIL_HOST = {settings.EMAIL_HOST}")

        self.stdout.write(f"EMAIL_PORT = {settings.EMAIL_PORT}")

        self.stdout.write(f"EMAIL_USE_SSL = {getattr(settings, 'EMAIL_USE_SSL', False)}")

        self.stdout.write(f"EMAIL_HOST_USER = {settings.EMAIL_HOST_USER}")

        self.stdout.write(f"DEFAULT_FROM_EMAIL = {settings.DEFAULT_FROM_EMAIL}")

        self.stdout.write(f"Destinatar test: {to}")



        pwd = (settings.EMAIL_HOST_PASSWORD or "").strip()

        if not pwd or pwd == "PAROLA_ZOHO_TEMP":

            raise CommandError(

                "EMAIL_HOST_PASSWORD lipsește sau e încă placeholder PAROLA_ZOHO_TEMP în .env. "

                "Pune parola reală Zoho (App Password) și rulează din nou."

            )



        try:

            from home.euadopt_email import send_test_email



            ok = send_test_email(to)

        except Exception as exc:

            self.stderr.write(self.style.ERROR("EROARE la trimitere:"))

            self.stderr.write(str(exc))

            raise CommandError(str(exc)) from exc



        if not ok:

            raise CommandError("send_test_email a returnat False.")



        self.stdout.write(self.style.SUCCESS("SUCCESS: test email sent to rarespepsi@yahoo.com"))


