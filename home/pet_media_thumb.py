"""Thumbnails JPEG pentru poze animale — smart crop (subiect centrat) + cache pe disc."""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import reverse

ALLOWED_PREFIX = "animals/"
VALID_SIZES = frozenset({320, 400, 600, 1200})
# v2 = smart cover crop (înlocuiește thumbnail-ul vechi care doar micșora imaginea)
THUMB_VERSION = "v2"


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
    return media_root / ".thumbs" / THUMB_VERSION / str(size) / f"{safe_name}.jpg"


def estimate_subject_focus(im) -> tuple[float, float]:
    """
    Estimează centrul de interes (0..1, 0..1) din energia de contur.
    Fără ML: sobel aproximativ pe o grilă mică — animalul are de obicei mai multe muchii.
    """
    from PIL import Image

    small = im.copy()
    small.thumbnail((72, 72), Image.Resampling.BILINEAR)
    g = small.convert("L")
    w, h = g.size
    if w < 3 or h < 3:
        return 0.5, 0.42
    px = g.load()
    samples: list[tuple[float, float, float]] = []
    for y in range(1, h - 1):
        for x in range(1, w - 1):
            gx = abs(px[x + 1, y] - px[x - 1, y])
            gy = abs(px[x, y + 1] - px[x, y - 1])
            e = float(gx + gy)
            if e >= 24.0:
                samples.append((e, float(x), float(y)))
    if not samples:
        # Preferă ușor partea de sus (capul animalului)
        return 0.5, 0.38
    samples.sort(key=lambda t: t[0], reverse=True)
    top_n = max(8, len(samples) // 5)
    top = samples[:top_n]
    tw = sum(e for e, _, _ in top) or 1.0
    cx = sum(e * x for e, x, _ in top) / tw
    cy = sum(e * y for e, _, y in top) / tw
    fx = cx / float(max(w - 1, 1))
    fy = cy / float(max(h - 1, 1))
    # Bias ușor în sus (bot/cap), clamp
    fy = max(0.22, min(0.62, fy * 0.82 + 0.08))
    fx = max(0.18, min(0.82, fx))
    return fx, fy


def smart_cover_square(im, focus_x: float, focus_y: float):
    """Crop pătrat cover, cu centrul pe focus (clampat în imagine)."""
    w, h = im.size
    side = min(w, h)
    if side <= 0:
        return im
    fx = max(0.0, min(1.0, focus_x)) * w
    fy = max(0.0, min(1.0, focus_y)) * h
    left = int(round(fx - side / 2.0))
    top = int(round(fy - side / 2.0))
    left = max(0, min(left, w - side))
    top = max(0, min(top, h - side))
    return im.crop((left, top, left + side, top + side))


def _build_thumb(source: Path, dest: Path, max_side: int) -> None:
    from PIL import Image, ImageOps

    dest.parent.mkdir(parents=True, exist_ok=True)
    with Image.open(source) as raw:
        im = ImageOps.exif_transpose(raw)
        if im.mode in ("RGBA", "P", "LA"):
            background = Image.new("RGB", im.size, (255, 255, 255))
            if im.mode == "P":
                im = im.convert("RGBA")
            background.paste(im, mask=im.split()[-1] if im.mode in ("RGBA", "LA") else None)
            im = background
        elif im.mode != "RGB":
            im = im.convert("RGB")
        fx, fy = estimate_subject_focus(im)
        im = smart_cover_square(im, fx, fy)
        # Pătrat exact max_side (sau mai mic dacă sursa e mică)
        out_side = min(max_side, im.size[0])
        im = im.resize((out_side, out_side), Image.Resampling.LANCZOS)
        im.save(dest, format="JPEG", quality=85, optimize=True)


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


def clear_pet_thumb_cache(media_root: Path | None = None, *, version: str | None = None) -> int:
    """Șterge cache thumbs (implicit doar THUMB_VERSION curent). Returnează fișiere șterse."""
    root = Path(media_root or settings.MEDIA_ROOT) / ".thumbs"
    if version:
        root = root / version
    if not root.exists():
        return 0
    n = 0
    for p in root.rglob("*"):
        if p.is_file():
            try:
                p.unlink()
                n += 1
            except OSError:
                pass
    return n
