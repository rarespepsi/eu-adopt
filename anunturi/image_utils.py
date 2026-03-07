"""
Utilitare pentru imagini: crop margini albe la poze descarcate (ex. Dog CEO),
ca fișierul salvat sa contina doar chenarul cu animalul, fara laterale albe.
"""
import io


def crop_white_margins(image_bytes, threshold=245, format_out="JPEG", quality=90):
    """
    Taie marginile (aproape) albe din imagine; returneaza bytes pentru salvare.

    - image_bytes: bytes ai imaginii (JPEG/PNG etc.)
    - threshold: pixel cu R,G,B >= threshold se considera alb (default 245)
    - format_out: 'JPEG' sau 'PNG'
    - quality: pentru JPEG, 1-100
    """
    try:
        from PIL import Image
    except ImportError:
        return image_bytes

    try:
        img = Image.open(io.BytesIO(image_bytes)).convert("RGB")
    except Exception:
        return image_bytes

    w, h = img.size
    # Mask: 255 unde e continut (pixel nu e alb), 0 unde e alb
    # Alb = toate canalele >= threshold
    data = list(img.getdata())
    mask_data = [
        255 if (r < threshold or g < threshold or b < threshold) else 0
        for (r, g, b) in data
    ]
    mask = Image.new("L", (w, h))
    mask.putdata(mask_data)

    bbox = mask.getbbox()
    if not bbox:
        return image_bytes

    img_cropped = img.crop(bbox)
    buf = io.BytesIO()
    if format_out.upper() == "PNG":
        img_cropped.save(buf, format="PNG")
    else:
        img_cropped.save(buf, format="JPEG", quality=quality)
    buf.seek(0)
    return buf.getvalue()
