"""
După 72 de ore, dacă câinii din wishlist nu sunt adoptați, doritorul primește un email
cu toți câinii bifați. Doar utilizatori cu email_opt_in_wishlist=True; max 1 email la 7 zile.
"""
from django.core.management.base import BaseCommand
from django.utils import timezone
from django.conf import settings
from django.urls import reverse

from datetime import timedelta
from collections import defaultdict

from anunturi.models import PetFavorite, Pet, Profile
from anunturi.wishlist_emails import send_wishlist_email, can_send_wishlist_email


class Command(BaseCommand):
    help = "Trimite email doritorilor: după 72h, lista câinilor din wishlist încă disponibili."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Doar afișează ce emailuri s-ar trimite, fără a trimite.",
        )

    def handle(self, *args, **options):
        dry_run = options["dry_run"]
        from_email = getattr(settings, "DEFAULT_FROM_EMAIL", "contact.euadopt@gmail.com")
        site_url = getattr(settings, "SITE_URL", "https://eu-adopt.ro").rstrip("/")

        # Favorituri unde: animalul e încă adoptable, adăugat acum 72+ ore, reminder nes trimis
        cutoff = timezone.now() - timedelta(hours=72)
        qs = (
            PetFavorite.objects.filter(
                pet__status="adoptable",
                created_at__lte=cutoff,
                reminder_72h_sent_at__isnull=True,
                notified_adopted=False,
            )
            .select_related("user", "pet")
            .order_by("user_id", "created_at")
        )

        # Grupare per user: toți câinii care îi qualifies pentru acest user
        by_user = defaultdict(list)
        for fav in qs:
            by_user[fav.user_id].append(fav)

        if not by_user:
            self.stdout.write("Niciun doritor cu animale in wishlist de 72+ ore (neadoptate) fara reminder trimis.")
            return

        # Filtrare: doar useri cu opt-in și care respectă limita 7 zile
        to_send = []
        for user_id, favs in by_user.items():
            user = favs[0].user
            profile = getattr(user, "profile", None)
            if not profile or not profile.email_opt_in_wishlist:
                continue
            if not can_send_wishlist_email(profile):
                continue
            to_send.append((user, profile, favs))

        if dry_run:
            self.stdout.write(f"[DRY-RUN] S-ar trimite {len(to_send)} emailuri (reminder 72h wishlist, cu opt-in si 7z).")
            for user, profile, favs in to_send[:5]:
                names = [f.pet.nume for f in favs]
                self.stdout.write(f"  - {user.email}: {', '.join(names)}")
            if len(to_send) > 5:
                self.stdout.write(f"  ... si inca {len(to_send) - 5} utilizatori")
            return

        sent = 0
        now = timezone.now()
        for user, profile, favs in to_send:
            email = (user.email or "").strip()
            if not email:
                continue
            lines = []
            for fav in favs:
                pet = fav.pet
                path = reverse("pets_single", kwargs={"pk": pet.pk})
                link = f"{site_url}{path}"
                lines.append(f"  • {pet.nume} – {pet.get_tip_display}, {pet.rasa}: {link}")
            pets_block = "\n".join(lines)
            list_url = f"{site_url}{reverse('wishlist')}"

            subject = "[EU Adopt] Câinele din wishlist încă te așteaptă ❤️"
            body = (
                "Bună ziua,\n\n"
                "Acum mai bine de 72 de ore ai marcat cu „Te plac” următoarele animale. "
                "Încă sunt disponibile pentru adopție:\n\n"
                f"{pets_block}\n\n"
                f"Vezi lista ta: {list_url}\n\n"
                "Dacă vrei să faci un pas înainte, completează cererea de adopție pentru animalul care ți se potrivește.\n\n"
                f"Site: {site_url}\n\n"
                "Cu drag,\nEchipa EU Adopt"
            )
            html_li = []
            for f in favs:
                path = reverse("pets_single", kwargs={"pk": f.pet.pk})
                html_li.append(f'<li><a href="{site_url}{path}">{f.pet.nume}</a> – {f.pet.get_tip_display}, {f.pet.rasa}</li>')
            html_body = (
                "<p>Bună ziua,</p>"
                "<p>Acum mai bine de 72 de ore ai marcat cu „Te plac” următoarele animale. Încă sunt disponibile:</p>"
                "<ul>" + "".join(html_li) + "</ul>"
                f'<p><a href="{list_url}">Vezi lista mea</a></p>'
                f"<p>Site: {site_url}</p>"
                "<p>Cu drag,<br>Echipa EU Adopt</p>"
            )
            try:
                send_wishlist_email(subject, body, email, from_email=from_email, html_body=html_body, user_for_unsubscribe=user)
                profile.last_wishlist_email_at = now
                profile.save(update_fields=["last_wishlist_email_at"])
                for fav in favs:
                    fav.reminder_72h_sent_at = now
                    fav.save(update_fields=["reminder_72h_sent_at"])
                sent += 1
                self.stdout.write(self.style.SUCCESS(f"Trimis: {email} – {len(favs)} animale"))
            except Exception as e:
                self.stdout.write(self.style.ERROR(f"Eroare la {email}: {e}"))

        self.stdout.write(self.style.SUCCESS(f"Total trimise: {sent} emailuri (reminder 72h wishlist)."))
