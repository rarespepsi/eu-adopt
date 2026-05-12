"""
Finalizează conturile pentru care a expirat perioada de grație după cererea de ștergere.
Rulează periodic (ex. zilnic pe Render): python manage.py finalize_pending_account_deletions
"""
from django.contrib.auth import get_user_model
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.account_deletion import account_deletion_grace_expired, finalize_pending_account
from home.models import AccountProfile

User = get_user_model()


class Command(BaseCommand):
    help = "Dezactivează și anonimizează conturile la expirarea grației după cererea de ștergere."

    def handle(self, *args, **options):
        now = timezone.now()
        qs = (
            AccountProfile.objects.filter(
                pending_deletion_grace_until__isnull=False,
                pending_deletion_finalized_at__isnull=True,
                pending_deletion_grace_until__lte=now,
            )
            .select_related("user")
        )
        n = 0
        for ap in qs:
            if not account_deletion_grace_expired(ap):
                continue
            user = ap.user
            if user.is_superuser and User.objects.filter(is_superuser=True).count() <= 1:
                self.stdout.write(self.style.WARNING(f"Skip sole superuser pk={user.pk}"))
                continue
            finalize_pending_account(user)
            n += 1
            self.stdout.write(self.style.SUCCESS(f"Finalizat cont pk={user.pk}"))
        if not n:
            self.stdout.write("Nicio cerere expirată de procesat.")
        else:
            self.stdout.write(self.style.SUCCESS(f"Procesate {n} cont(uri)."))
