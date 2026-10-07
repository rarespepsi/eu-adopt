"""Thumbnails JPEG pentru poze animale — smart crop (subiect centrat) + cache pe disc."""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.http import FileResponse, Http404
from django.urls import reverse

ALLOWED_PREFIX = "animals/"
VALID_SIZES = frozenset({320, 400, 600, 1200})
# v6 = smart cover + tăiere benzi negre/letterbox din sursă (înainte de crop)
THUMB_VERSION = "v6"
# păstrat pentru helper/teste (letterbox_square rămâne disponibil, nefolosit în v6)
EXTREME_ASPECT_RATIO = 1.45
LETTERBOX_FILL = (245, 245, 245)
# margini aproape negre (pillar/letterbox din surse FB/phone)
DARK_BORDER_LUMA_MAX = 28
DARK_BORDER_FRAC = 0.90


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
    # ?v= bustă cache browser (thumb URL e immutable pe disc)
    return reverse("pet_media_thumb", kwargs={"size": size, "relpath": rel}) + f"?v={THUMB_VERSION}"


def _thumb_cache_path(media_root: Path, size: int, rel: str) -> Path:
    safe_name = rel.replace("/", "__")
    return media_root / ".thumbs" / THUMB_VERSION / str(size) / f"{safe_name}.jpg"


def trim_dark_letterbox(
    im,
    *,
    luma_max: int = DARK_BORDER_LUMA_MAX,
    frac: float = DARK_BORDER_FRAC,
):
    """
    Taie benzi aproape negre de pe margini (letterbox/pillarbox în fișierul sursă).
    Fără schimbare dacă nu există benzi clare.
    """
    g = im.convert("L")
    w, h = g.size
    if w < 16 or h < 16:
        return im
    px = g.load()

    def col_dark(x: int) -> bool:
        dark = sum(1 for y in range(h) if px[x, y] <= luma_max)
        return (dark / float(h)) >= frac

    def row_dark(y: int) -> bool:
        dark = sum(1 for x in range(w) if px[x, y] <= luma_max)
        return (dark / float(w)) >= frac

    left = 0
    while left < w - 1 and col_dark(left):
        left += 1
    right = w - 1
    while right > left and col_dark(right):
        right -= 1
    top = 0
    while top < h - 1 and row_dark(top):
        top += 1
    bottom = h - 1
    while bottom > top and row_dark(bottom):
        bottom -= 1

    cw, ch = right - left + 1, bottom - top + 1
    if cw < 12 or ch < 12:
        return im
    if left == 0 and top == 0 and right == w - 1 and bottom == h - 1:
        return im
    removed = (w * h) - (cw * ch)
    if removed < max(24, int(0.02 * w * h)):
        return im
    return im.crop((left, top, right + 1, bottom + 1))


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


def is_extreme_aspect(w: int, h: int, threshold: float = EXTREME_ASPECT_RATIO) -> bool:
    """True dacă poza e foarte lată sau foarte înaltă (cover ar tăia subiectul)."""
    if w <= 0 or h <= 0:
        return False
    return (max(w, h) / float(min(w, h))) >= float(threshold)


def letterbox_square(im, fill=LETTERBOX_FILL):
    """Pătrat cu imaginea întreagă centrată + benzi (fără crop)."""
    from PIL import Image

    w, h = im.size
    side = max(w, h)
    if side <= 0:
        return im
    out = Image.new("RGB", (side, side), fill)
    out.paste(im, ((side - w) // 2, (side - h) // 2))
    return out


def square_for_thumb(im, focus_x: float | None = None, focus_y: float | None = None):
    """
    Pătrat pentru thumb: mereu smart cover (umple caseta, fără benzi albe).
    """
    if focus_x is None or focus_y is None:
        focus_x, focus_y = estimate_subject_focus(im)
    return smart_cover_square(im, focus_x, focus_y)


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
        im = trim_dark_letterbox(im)
        im = square_for_thumb(im)
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
