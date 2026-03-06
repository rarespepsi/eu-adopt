"""
Retrimite emailurile de bun venit către utilizatori care au adresă de email.
Rulează: python manage.py resend_welcome_emails
         python manage.py resend_welcome_emails --send
"""
from django.core.management.base import BaseCommand
from django.contrib.auth import get_user_model

User = get_user_model()


class Command(BaseCommand):
    help = "Listează sau retrimite emailurile de bun venit către utilizatori cu email."

    def add_arguments(self, parser):
        parser.add_argument(
            "--send",
            action="store_true",
            help="Efectiv trimite emailurile. Fără --send doar afișează lista.",
        )

    def handle(self, *args, **options):
        from anunturi.welcome_email import send_welcome_email

        qs = User.objects.filter(is_active=True).exclude(email__isnull=True).exclude(email="")
        users = list(qs.order_by("date_joined"))
        count = len(users)

        if count == 0:
            self.stdout.write("Niciun utilizator activ cu email setat.")
            return

        if not options["send"]:
            self.stdout.write(f"S-ar trimite {count} email(uri) de bun venit la:")
            for u in users:
                self.stdout.write(f"  {u.email} ({u.username})")
            self.stdout.write(self.style.WARNING("\nPentru a trimite efectiv: python manage.py resend_welcome_emails --send"))
            return

        sent = 0
        for user in users:
            if send_welcome_email(user, request=None):
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"Trimis: {user.email}"))
            else:
                self.stdout.write(self.style.WARNING(f"Eroare/skip: {user.email}"))
        self.stdout.write(self.style.SUCCESS(f"\nTotal trimise: {sent} / {count}"))
