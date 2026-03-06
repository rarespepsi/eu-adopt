"""
La 30 zile: utilizatori cu wishlist (prima adăugare >= 30 zile) și opt-in primesc email
„Încă îți cauți prietenul perfect?” cu 4–6 animale recomandate. Max 1 email la 7 zile.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.urls import reverse
from django.db.models import Min
from datetime import timedelta

from anunturi.models import Profile, PetFavorite, Pet
from anunturi.wishlist_emails import send_wishlist_email, can_send_wishlist_email


class Command(BaseCommand):
    help = "Trimite email „Încă îți cauți prietenul perfect?” la 30 zile (wishlist + opt-in)."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar afișează căror utilizatori s-ar trimite email.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
        site_url = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")

        cutoff_30 = timezone.now() - timedelta(days=30)
        # Utilizatori care au cel puțin un PetFavorite adăugat acum 30+ zile
        first_add = (
            PetFavorite.objects.filter(user__is_active=True)
            .values("user_id")
            .annotate(first_created=Min("created_at"))
            .filter(first_created__lte=cutoff_30)
        )
        user_ids_30 = [x["user_id"] for x in first_add]
        profiles = list(
            Profile.objects.filter(
                user_id__in=user_ids_30,
                email_opt_in_wishlist=True,
                last_followup_30d_at__isnull=True,
            ).select_related("user")
        )
        to_send = [p for p in profiles if can_send_wishlist_email(p) and (p.user.email or "").strip()]

        if not to_send:
            self.stdout.write("Niciun utilizator eligibil pentru emailul 30 zile (wishlist 30d+, opt-in, fara follow-up trimis, 7z).")
            return

        if dry_run:
            self.stdout.write(f"[DRY-RUN] S-ar trimite {len(to_send)} emailuri (30z Încă îți cauți...).")
            for p in to_send[:10]:
                self.stdout.write(f"  - {p.user.email}")
            if len(to_send) > 10:
                self.stdout.write(f"  ... si inca {len(to_send) - 10}")
            return

        recommended = list(Pet.objects.filter(status="adoptable").order_by("-data_adaugare")[:6])
        rec_lines = []
        for p in recommended:
            path = reverse("pets_single", kwargs={"pk": p.pk})
            rec_lines.append(f"  • {p.nume} – {p.get_tip_display}, {p.rasa}: {site_url}{path}")
        rec_block = "\n".join(rec_lines) if rec_lines else ""

        subject = "[EU Adopt] Încă îți cauți prietenul perfect?"
        body = (
            "Bună ziua,\n\n"
            "Încă îți cauți prietenul perfect? Am selectat câteva animale care își caută familie:\n\n"
            f"{rec_block}\n\n"
            f"Vezi toate animalele: {site_url}{reverse('pets_all')}\n\n"
            f"Site: {site_url}\n\n"
            "Cu drag,\nEchipa EU Adopt"
        )
        html_li = []
        for p in recommended:
            path = reverse("pets_single", kwargs={"pk": p.pk})
            html_li.append(f'<li><a href="{site_url}{path}">{p.nume}</a> – {p.get_tip_display}, {p.rasa}</li>')
        html_body = (
            "<p>Bună ziua,</p>"
            "<p>Încă îți cauți prietenul perfect? Am selectat câteva animale care își caută familie:</p>"
            "<ul>" + "".join(html_li) + "</ul>"
            f'<p><a href="{site_url}{reverse("pets_all")}">Vezi toate animalele</a></p>'
            f"<p>Site: {site_url}</p>"
            "<p>Cu drag,<br>Echipa EU Adopt</p>"
        )

        sent = 0
        now = timezone.now()
        for p in to_send:
            email = (p.user.email or "").strip()
            if not email:
                continue
            try:
                send_wishlist_email(subject, body, email, from_email=from_email, html_body=html_body, user_for_unsubscribe=p.user)
                p.last_followup_30d_at = now
                p.last_wishlist_email_at = now
                p.save(update_fields=["last_followup_30d_at", "last_wishlist_email_at"])
                sent += 1
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Eroare la {email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Total trimise: {sent} emailuri (30z Încă îți cauți...)."))
