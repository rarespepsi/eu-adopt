"""
Regenerează / curăță thumbnails poze animale (smart crop + letterbox v3).

  python manage.py rebuild_pet_thumbs --clear-only
  python manage.py rebuild_pet_thumbs --warm --limit 200
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.core.management.base import BaseCommand

from home.models import AnimalListing
from home.pet_media_thumb import (
    THUMB_VERSION,
    VALID_SIZES,
    _build_thumb,
    _safe_media_relpath,
    _thumb_cache_path,
    clear_pet_thumb_cache,
)


class Command(BaseCommand):
    help = "Curăță și/sau regenerează thumbnails smart-crop pentru poze animale."

    def add_arguments(self, parser):
        parser.add_argument(
            "--clear-only",
            action="store_true",
            help="Șterge doar cache-ul .thumbs (versiunea curentă + optional legacy).",
        )
        parser.add_argument(
            "--clear-legacy",
            action="store_true",
            help="Șterge și .thumbs/<size>/ vechi (fără v2/).",
        )
        parser.add_argument(
            "--warm",
            action="store_true",
            help="Regenerează thumbs pentru photo_1/2/3 (size 400 + 320).",
        )
        parser.add_argument("--limit", type=int, default=0, help="Max animale (0 = toate).")
        parser.add_argument(
            "--sizes",
            default="320,400",
            help="Mărimi de regenerat, ex. 320,400,1200",
        )

    def handle(self, *args, **options):
        media = Path(settings.MEDIA_ROOT)
        cleared = clear_pet_thumb_cache(media, version=THUMB_VERSION)
        self.stdout.write(f"cleared {THUMB_VERSION} files={cleared}")
        if options.get("clear_legacy"):
            # legacy: .thumbs/400/ fără v2
            legacy_n = 0
            for size in VALID_SIZES:
                d = media / ".thumbs" / str(size)
                if d.is_dir():
                    for p in d.rglob("*.jpg"):
                        try:
                            p.unlink()
                            legacy_n += 1
                        except OSError:
                            pass
            self.stdout.write(f"cleared legacy size-dirs files={legacy_n}")

        if options.get("clear_only") and not options.get("warm"):
            return

        if not options.get("warm"):
            self.stdout.write("Done (no --warm). New thumbs build on first request.")
            return

        sizes = []
        for part in str(options.get("sizes") or "320,400").split(","):
            part = part.strip()
            if not part:
                continue
            try:
                s = int(part)
            except ValueError:
                continue
            if s in VALID_SIZES:
                sizes.append(s)
        if not sizes:
            sizes = [320, 400]

        qs = AnimalListing.objects.all().order_by("-id")
        lim = int(options.get("limit") or 0)
        if lim > 0:
            qs = qs[:lim]

        built = 0
        missing = 0
        for listing in qs.iterator(chunk_size=100):
            for field_name in ("photo_1", "photo_2", "photo_3"):
                field = getattr(listing, field_name, None)
                if not field:
                    continue
                rel = _safe_media_relpath(getattr(field, "name", "") or "")
                if not rel:
                    continue
                src = media / rel
                if not src.is_file():
                    missing += 1
                    continue
                for size in sizes:
                    dest = _thumb_cache_path(media, size, rel)
                    try:
                        _build_thumb(src, dest, size)
                        built += 1
                    except Exception as exc:
                        self.stderr.write(f"fail pk={listing.pk} {rel} size={size}: {exc}")
        self.stdout.write(self.style.SUCCESS(f"warm built={built} missing_files={missing}"))
