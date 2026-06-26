"""Thumbnails JPEG pentru poze animale (PT grid, fișă) — cache pe disc sub MEDIA_ROOT/.thumbs/."""
from __future__ import annotations

import os
from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import reverse

ALLOWED_PREFIX = "animals/"
VALID_SIZES = frozenset({320, 400, 600, 1200})


def _safe_media_relpath(rel: str) -> str | None:
    rel = (rel or "").replace("\\", "/").lstrip("/")
    if not rel.startswith(ALLOWED_PREFIX):
        return None
    parts = rel.split("/")
    if ".." in parts or not parts[-1]:
        return None
    return rel


def pet_thumb_url_for(image_field, size: int = 400) -> str:
    if not image_field:
        return ""
    try:
        name = image_field.name
    except Exception:
        return ""
    rel = _safe_media_relpath(name)
    if not rel:
        return ""
    try:
        size = int(size)
    except (TypeError, ValueError):
        size = 400
    if size not in VALID_SIZES:
        size = 400
    return reverse("pet_media_thumb", kwargs={"size": size, "relpath": rel})


def _thumb_cache_path(media_root: Path, size: int, rel: str) -> Path:
    safe_name = rel.replace("/", "__")
    return media_root / ".thumbs" / str(size) / f"{safe_name}.jpg"


def _build_thumb(source: Path, dest: Path, max_side: int) -> None:
    from PIL import Image

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as im:
        if im.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "P":
                im = im.convert("RGBA")
            background.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
            im = background
        elif im.mode != "RGB":
            im = im.convert("RGB")
        im.thumbnail((max_side, max_side), Image.Resampling.LANCZOS)
        im.save(dest, format="JPEG", quality=84, optimize=True)


def pet_media_thumb_view(request, size, relpath):
    rel = _safe_media_relpath(relpath)
    if not rel:
        raise Http404
    try:
        size = int(size)
    except (TypeError, ValueError):
        raise Http404
    if size not in VALID_SIZES:
        raise Http404

    media_root = Path(settings.MEDIA_ROOT)
    source = media_root / rel
    if not source.is_file():
        raise Http404

    thumb_path = _thumb_cache_path(media_root, size, rel)
    try:
        src_mtime = source.stat().st_mtime
        if not thumb_path.is_file() or thumb_path.stat().st_mtime < src_mtime:
            _build_thumb(source, thumb_path, size)
    except OSError as exc:
        raise Http404 from exc

    try:
        fh = thumb_path.open("rb")
    except OSError as exc:
        raise Http404 from exc

    resp = FileResponse(fh, content_type="image/jpeg")
    resp["Cache-Control"] = "public, max-age=31536000, immutable"
    return resp
