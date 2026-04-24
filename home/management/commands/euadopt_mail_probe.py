"""
Trimite emailuri de probă pentru verificare SMTP reală (inbox).

Exemple (din rădăcina proiectului):
  python manage.py euadopt_mail_probe
  python manage.py euadopt_mail_probe --usernames dpf,dg1,dm
  python manage.py euadopt_mail_probe --to rarespepsi@gmail.com

Necesită în .env: EMAIL_HOST_PASSWORD (parolă aplicație Gmail pentru contul din EMAIL_HOST_USER).
Fără parolă, Django folosește backend-ul consolă — vezi mesajul la rulare.
"""

from __future__ import annotations

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.mail import send_mail
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.mail_helpers import email_subject_for_user


class Command(BaseCommand):
    help = "Trimite un email de probă per destinatar (verificare trimitere SMTP reală)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--usernames",
            default="dpf,dg1,dm",
            help="Lista de username-uri (virgulă). Se trimite la User.email al fiecăruia.",
        )
        parser.add_argument(
            "--to",
            default="",
            help="Dacă e setat, trimite un singur mesaj la această adresă (ignoră --usernames).",
        )
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează doar backend-ul și destinatarii, fără trimitere.",
        )

    def handle(self, *args, **options):
        backend = getattr(settings, "EMAIL_BACKEND", "")
        self.stdout.write(f"EMAIL_BACKEND = {backend}")
        self.stdout.write(f"EMAIL_HOST_USER = {getattr(settings, 'EMAIL_HOST_USER', '')}")
        self.stdout.write(f"SITE_BASE_URL = {getattr(settings, 'SITE_BASE_URL', '')}")

        if "console" in backend:
            self.stdout.write(
                self.style.WARNING(
                    "Lipsește EMAIL_HOST_PASSWORD în mediu → mesajele nu pleacă pe SMTP; "
                    "apar în consola serverului Django."
                )
            )

        to_single = (options.get("to") or "").strip()
        dry = bool(options.get("dry_run"))

        if to_single:
            recipients = [("probe", to_single)]
        else:
            raw = (options.get("usernames") or "").strip()
            names = [x.strip() for x in raw.split(",") if x.strip()]
            User = get_user_model()
            recipients = []
            for name in names:
                u = User.objects.filter(username__iexact=name).first()
                if not u:
                    self.stdout.write(self.style.WARNING(f"Lipsește user: {name!r}"))
                    continue
                em = (u.email or "").strip()
                if not em:
                    self.stdout.write(self.style.WARNING(f"{u.username}: fără email în cont"))
                    continue
                if not u.is_active:
                    self.stdout.write(self.style.WARNING(f"{u.username}: is_active=False (login blocat)"))
                recipients.append((u.username, em))

        if not recipients:
            self.stdout.write(self.style.ERROR("Niciun destinatar."))
            return

        for uname, em in recipients:
            self.stdout.write(f"Destinatar: {uname!r} -> {em!r}")

        if dry:
            self.stdout.write(self.style.NOTICE("--dry-run: nu s-a trimis nimic."))
            return

        when = timezone.now().isoformat(timespec="seconds")
        for uname, em in recipients:
            # Subiect unic per rulare: Gmail grupeaza altfel mesaje identice catre acelasi inbox.
            subj = email_subject_for_user(
                uname,
                f"EU-Adopt SMTP probe run={when}",
            )
            body = (
                "Hello,\n\n"
                "This message confirms the EU-Adopt server can send mail via SMTP.\n"
                f"Server time: {when}\n"
                f"EMAIL_BACKEND: {backend}\n"
                f"Probe account username: {uname}\n\n"
                "If the subject starts with [username], one inbox can tell accounts apart.\n"
            )
            try:
                send_mail(subj, body, settings.DEFAULT_FROM_EMAIL, [em], fail_silently=False)
                self.stdout.write(self.style.SUCCESS(f"OK sent -> {em}"))
            except Exception as exc:
                err = str(exc).encode("ascii", "backslashreplace").decode("ascii")
                self.stdout.write(self.style.ERROR(f"ERR {em}: {err}"))
