"""
Hard-delete anunțuri pierdut/găsit soft-șterse de peste 45 zile.

  python manage.py cleanup_lost_found_deleted
  python manage.py cleanup_lost_found_deleted --days 45 --dry-run
"""
from __future__ import annotations

from datetime import timedelta

from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import LostFoundAnimal


class Command(BaseCommand):
    help = "Șterge definitiv LostFoundAnimal cu deleted_at mai vechi de N zile (implicit 45)."

    def add_arguments(self, parser):
        parser.add_argument("--days", type=int, default=45)
        parser.add_argument("--dry-run", action="store_true")

    def handle(self, *args, **options):
        days = max(1, int(options["days"] or 45))
        dry = bool(options["dry_run"])
        cutoff = timezone.now() - timedelta(days=days)
        qs = LostFoundAnimal.objects.filter(deleted_at__isnull=False, deleted_at__lt=cutoff)
        n = qs.count()
        self.stdout.write(f"candidates={n} cutoff={cutoff.isoformat()} dry_run={dry}")
        if dry or n == 0:
            return
        # Șterge și fișierele foto
        for row in qs.iterator():
            try:
                if row.photo:
                    row.photo.delete(save=False)
            except Exception:
                pass
            row.delete()
        self.stdout.write(self.style.SUCCESS(f"deleted={n}"))
