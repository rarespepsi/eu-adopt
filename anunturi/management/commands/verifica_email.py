"""
Verificare configurare email în Django.
Rulează: python manage.py verifica_email
"""
from django.core.management.base import BaseCommand
from django.conf import settings
from django.core.mail import send_mail


class Command(BaseCommand):
    help = "Verifică setările de email și trimite un mesaj de test (opțional)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--test",
            action="store_true",
            help="Trimite un email de test la adresa indicată (necesită --to=email@exemplu.ro)",
        )
        parser.add_argument("--to", type=str, default="", help="Adresa la care se trimite emailul de test")

    def handle(self, *args, **options):
        self.stdout.write("=== Verificare email Django ===\n")

        backend = getattr(settings, "EMAIL_BACKEND", "?")
        self.stdout.write(f"EMAIL_BACKEND: {backend}")

        if "console" in str(backend):
            self.stdout.write(self.style.WARNING("  => Emailurile se afiseaza in CONSOLA (nu se trimit pe internet)."))
            self.stdout.write("  => Pentru trimitere reala, adauga in .env: EMAIL_HOST, EMAIL_HOST_USER, EMAIL_HOST_PASSWORD")
        else:
            self.stdout.write(self.style.SUCCESS("  => SMTP activ - emailurile se trimit efectiv."))

        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "?")
        self.stdout.write(f"\nDEFAULT_FROM_EMAIL: {from_email}")

        if getattr(settings, "EMAIL_HOST", None):
            self.stdout.write(f"EMAIL_HOST: {settings.EMAIL_HOST}")
            self.stdout.write(f"EMAIL_HOST_USER: {getattr(settings, 'EMAIL_HOST_USER', '') or '(gol)'}")
        else:
            self.stdout.write("EMAIL_HOST: (nesetat)")

        site_url = getattr(settings, "SITE_URL", "?")
        self.stdout.write(f"SITE_URL: {site_url}\n")

        if options["test"] and options["to"]:
            to = options["to"].strip()
            if not to or "@" not in to:
                self.stdout.write(self.style.ERROR("Pentru --test da si --to=adresa@exemplu.ro"))
                return
            self.stdout.write(f"Trimit email de test la {to}...")
            try:
                send_mail(
                    "Test EU-Adopt – verificare email",
                    "Acesta este un mesaj de test. Dacă l-ai primit, configurarea email funcționează.",
                    from_email,
                    [to],
                    fail_silently=False,
                )
                self.stdout.write(self.style.SUCCESS("Trimis. Verifica inbox (si spam) la " + to))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Eroare la trimitere: {e}"))
        elif options["test"]:
            self.stdout.write(self.style.WARNING("Pentru email de test foloseste: --test --to=email@exemplu.ro"))
