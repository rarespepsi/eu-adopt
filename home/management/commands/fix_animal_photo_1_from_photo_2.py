"""
Copiază photo_2 → photo_1 pentru animale unde poza 1 lipsește sau e placeholder seed/demo.

Folosit după migrare media incompletă sau seed cu animals/seed_produs_demo.jpg partajat.

Rulare:
  python manage.py fix_animal_photo_1_from_photo_2 --dry-run
  python manage.py fix_animal_photo_1_from_photo_2
"""
from __future__ import annotations

from pathlib import Path

from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand
from django.utils import timezone

from home.models import AnimalListing

SEED_PLACEHOLDER_FRAGMENT = "seed_produs_demo"


def _field_name(field) -> str:
    if not field or not getattr(field, "name", None):
        return ""
    return str(field.name).replace("\\", "/")


def _file_on_disk(field) -> bool:
    if not _field_name(field):
        return False
    try:
        return Path(field.path).is_file()
    except Exception:
        return False


def _photo_1_needs_fix(listing: AnimalListing) -> bool:
    p1 = listing.photo_1
    name = _field_name(p1)
    if not name:
        return True
    if SEED_PLACEHOLDER_FRAGMENT in name:
        return True
    return not _file_on_disk(p1)


def _copy_photo_2_to_photo_1(listing: AnimalListing) -> bool:
    p2 = listing.photo_2
    if not _file_on_disk(p2):
        return False
    src_path = Path(p2.path)
    ext = src_path.suffix or ".jpg"
    data = src_path.read_bytes()
    new_filename = f"p1_from_p2_{listing.pk}{ext}"
    listing.photo_1.save(new_filename, ContentFile(data), save=False)
    listing.updated_at = timezone.now()
    listing.save(update_fields=["photo_1", "updated_at"])
    return True


class Command(BaseCommand):
    help = "Copiază fișierul photo_2 în photo_1 când photo_1 lipsește sau e placeholder demo."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Afișează ce s-ar actualiza, fără scriere.",
        )
        parser.add_argument(
            "--include-unpublished",
            action="store_true",
            help="Include și animale nepublicate (implicit: doar is_published=True).",
        )

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        qs = AnimalListing.objects.all().order_by("pk")
        if not options["include_unpublished"]:
            qs = qs.filter(is_published=True)

        scanned = 0
        skipped_ok = 0
        skipped_no_source = 0
        updated = 0

        for listing in qs.iterator():
            scanned += 1
            if not _photo_1_needs_fix(listing):
                skipped_ok += 1
                continue
            if not _file_on_disk(listing.photo_2):
                skipped_no_source += 1
                self.stdout.write(
                    f"  skip pk={listing.pk}: photo_2 missing on disk"
                )
                continue
            if dry_run:
                self.stdout.write(
                    f"  would fix pk={listing.pk} "
                    f"photo_2={_field_name(listing.photo_2)!r}"
                )
                updated += 1
                continue
            if _copy_photo_2_to_photo_1(listing):
                updated += 1
                self.stdout.write(
                    f"  fixed pk={listing.pk} -> {_field_name(listing.photo_1)!r}"
                )

        mode = "DRY-RUN" if dry_run else "DONE"
        self.stdout.write(
            f"{mode}: scanned={scanned} updated={updated} "
            f"already_ok={skipped_ok} no_photo_2={skipped_no_source}"
        )
