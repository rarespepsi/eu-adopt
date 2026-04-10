"""
Populează DB cu date de test „realiste” pentru ~10 useri aliniați în scripts/_align_user_roles.py:

- PF + ONG: 15 anunțuri animal / user (5 câini, 5 pisici, 5 alte specii) — nume prefix [seed]
- Colaboratori: 15 oferte / user (5 țintă câine, 5 pisică, 5 oricare/altele) — titlu prefix [seed]
- Pe fiecare imagine generată de script apare vizibil textul **PRODUS DEMO** (Pillow); nu se modifică casete sau setări UI în site.

Anunțurile PF folosesc bulk_create (nu apelează AnimalListing.save() → nu se aplică limita 3/lună).

Rulare (din rădăcina proiectului):
  python scripts/seed_portfolio.py
  python scripts/seed_portfolio.py --clear   # șterge doar rândurile [seed] apoi re-populează

Pentru QA adopție (inimioare pe Servicii + transport în aceeași zonă), după `_align_user_roles.py` rulează:
  python scripts/qa_adoption_transport_setup.py
  (vezi `QA_REGISTRU_CONSTATARI.md` — Lot **AD**).
"""
from __future__ import annotations

import argparse
import base64
import os
import sys
from io import BytesIO

_ROOT = os.path.dirname(os.path.dirname(os.path.abspath(__file__)))
sys.path.insert(0, _ROOT)
os.environ.setdefault("DJANGO_SETTINGS_MODULE", "euadopt_final.settings")

import django

django.setup()

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.uploadedfile import SimpleUploadedFile
from django.utils import timezone

from home.models import AnimalListing, CollaboratorServiceOffer

User = get_user_model()

# Aliniat cu scripts/_align_user_roles.py
PF_USERS = ["dpf", "e2e_pf", "e2e_staff"]
ORG_USERS = ["rarespepsi", "radu"]
COLLAB_OFFERS = [
    ("nccristescu", CollaboratorServiceOffer.PARTNER_KIND_CABINET, "Cabinet"),
    ("dg1", CollaboratorServiceOffer.PARTNER_KIND_SERVICII, "Servicii"),
    ("dg2", CollaboratorServiceOffer.PARTNER_KIND_SERVICII, "Servicii"),
    ("dm", CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN, "Magazin"),
    ("rares", CollaboratorServiceOffer.PARTNER_KIND_SERVICII, "Transport"),
]

SEED_NAME_PREFIX = "[seed] "
SEED_TITLE_PREFIX = "[seed] "

# Text vizibil pe fiecare imagine generată de acest script (nu modifică casete / UI site).
DEMO_IMAGE_LABEL = "PRODUS DEMO"
# Fișier partajat pentru photo_1 la anunțuri seed (scriere directă în MEDIA_ROOT).
SEED_ANIMAL_PHOTO_REL = "animals/seed_produs_demo.jpg"


def _demo_jpeg_bytes() -> bytes:
    """JPEG cu text PRODUS DEMO vizibil (necesită Pillow)."""
    from PIL import Image, ImageDraw, ImageFont

    w, h = 520, 340
    img = Image.new("RGB", (w, h), (88, 96, 108))
    draw = ImageDraw.Draw(img)
    banner_h = 78
    draw.rectangle([0, h - banner_h, w, h], fill=(198, 52, 42))
    font = None
    for fp in (
        os.path.join(os.environ.get("WINDIR", r"C:\Windows"), "Fonts", "arialbd.ttf"),
        "/usr/share/fonts/truetype/dejavu/DejaVuSans-Bold.ttf",
    ):
        if os.path.isfile(fp):
            try:
                font = ImageFont.truetype(fp, 34)
                break
            except OSError:
                continue
    if font is None:
        font = ImageFont.load_default()
    bbox = draw.textbbox((0, 0), DEMO_IMAGE_LABEL, font=font)
    tw, th = bbox[2] - bbox[0], bbox[3] - bbox[1]
    tx = (w - tw) // 2
    ty = h - banner_h + (banner_h - th) // 2 - 2
    draw.text((tx, ty), DEMO_IMAGE_LABEL, fill=(255, 255, 255), font=font)
    buf = BytesIO()
    img.save(buf, format="JPEG", quality=90)
    buf.seek(0)
    return buf.read()


def _tiny_jpeg_upload(filename: str = "offer.jpg") -> SimpleUploadedFile:
    try:
        data = _demo_jpeg_bytes()
    except Exception:
        # Fără Pillow: imagine minimală (fără text — instală Pillow pentru PRODUS DEMO).
        raw = base64.b64decode(
            "/9j/4AAQSkZJRgABAQEASABIAAD/2wBDAAgGBgcGBQgHBwcJCQgKDBQNDAsLDBkSEw8UHRofHh0aHBwgJC4nICIsIxwcKDcpLDAxNDQ0Hyc5PTgyPC4zNDL/2wBDAQkJCQwLDBgNDRgyIRwhMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjIyMjL/wAARCAABAAEDASIAAhEBAxEB/8QAFQABAQAAAAAAAAAAAAAAAAAAAAX/xAAUEAEAAAAAAAAAAAAAAAAAAAAA/8QAFQEBAQAAAAAAAAAAAAAAAAAAAAX/xAAUEQEAAAAAAAAAAAAAAAAAAAAA/9oADAMBAAIRAxEAPwCwAA8A/9k="
        )
        data = raw
    return SimpleUploadedFile(filename, data, content_type="image/jpeg")


_SEED_ANIMAL_PHOTO_CACHED: str | None = None


def _seed_animal_photo_1_rel() -> str:
    """Cale relativă media pentru photo_1 (PRODUS DEMO) sau '' dacă nu s-a putut genera."""
    global _SEED_ANIMAL_PHOTO_CACHED
    if _SEED_ANIMAL_PHOTO_CACHED is not None:
        return _SEED_ANIMAL_PHOTO_CACHED
    try:
        data = _demo_jpeg_bytes()
    except Exception:
        _SEED_ANIMAL_PHOTO_CACHED = ""
        return ""
    dest = settings.MEDIA_ROOT / SEED_ANIMAL_PHOTO_REL
    dest.parent.mkdir(parents=True, exist_ok=True)
    dest.write_bytes(data)
    _SEED_ANIMAL_PHOTO_CACHED = SEED_ANIMAL_PHOTO_REL
    return _SEED_ANIMAL_PHOTO_CACHED


def _get_user(username: str):
    return User.objects.filter(username__iexact=username.strip()).first()


def clear_seed_rows() -> None:
    """Șterge doar înregistrările create de acest script (prefix [seed])."""
    n_anim = AnimalListing.objects.filter(name__startswith=SEED_NAME_PREFIX).delete()[0]
    n_off = CollaboratorServiceOffer.objects.filter(title__startswith=SEED_TITLE_PREFIX).delete()[0]
    print(f"Cleared: {n_anim} animals, {n_off} offers (matching prefix).")


def seed_animals_for_owner(user: User, uname: str) -> int:
    """15 animale: 5 dog, 5 cat, 5 other — bulk_create (fără AnimalListing.save)."""
    order = [("dog", "Câine")] * 5 + [("cat", "Pisică")] * 5 + [("other", "Alt")] * 5
    existing = AnimalListing.objects.filter(
        owner=user, name__startswith=SEED_NAME_PREFIX
    ).count()
    needed = 15 - existing
    if needed <= 0:
        print(f"  Skip animals for {uname}: already have {existing} seed rows.")
        return 0

    now = timezone.now()
    photo_1 = _seed_animal_photo_1_rel()
    rows: list[AnimalListing] = []
    for j in range(existing, 15):
        sp, label = order[j]
        i = j + 1
        name = f"{SEED_NAME_PREFIX}{uname}-{sp}-{i:02d}"
        kw = dict(
            owner_id=user.id,
            name=name,
            species=sp,
            size="medie" if sp == "dog" else ("mica" if sp == "cat" else "—"),
            age_label="adult" if i % 2 else "tânăr",
            city="București",
            county="București",
            color="mixt",
            cine_sunt=f"Proprietar {uname} — anunț seed #{i}.",
            detalii_animal=f"Animal {label} pentru umplere casete (seed).",
            is_published=True,
            adoption_state=AnimalListing.ADOPTION_STATE_OPEN,
            created_at=now,
            updated_at=now,
        )
        if photo_1:
            kw["photo_1"] = photo_1
        rows.append(AnimalListing(**kw))
    AnimalListing.objects.bulk_create(rows, batch_size=50)
    print(f"  Created {len(rows)} animals for {uname} (had {existing}, target 15).")
    return len(rows)


def seed_offers_for_collab(
    username: str, partner_kind: str, kind_label: str
) -> int:
    u = _get_user(username)
    if not u:
        print(f"  Skip offers: user missing {username!r}")
        return 0
    existing = CollaboratorServiceOffer.objects.filter(
        collaborator=u, title__startswith=SEED_TITLE_PREFIX
    ).count()
    needed = 15 - existing
    if needed <= 0:
        print(f"  Skip offers for {username}: already have {existing} seed rows.")
        return 0

    # 5 dog, 5 cat, 5 „oricare” (altele / mix) — aliniat la model (target_species fără „hamster”)
    triplets = (
        [(CollaboratorServiceOffer.TARGET_SPECIES_DOG, "câine")] * 5
        + [(CollaboratorServiceOffer.TARGET_SPECIES_CAT, "pisică")] * 5
        + [(CollaboratorServiceOffer.TARGET_SPECIES_ALL, "altele")] * 5
    )
    n = 0
    for idx in range(existing, 15):
        ts, tag = triplets[idx]
        i = idx + 1
        title = f"{SEED_TITLE_PREFIX}{kind_label} {username} — {tag} #{i}"
        desc = f"Ofertă seed {kind_label.lower()} pentru {tag} (umplere Servicii / oferte)."
        img = _tiny_jpeg_upload(f"seed_{username}_{i}.jpg")
        extra: dict = {}
        if partner_kind == CollaboratorServiceOffer.PARTNER_KIND_MAGAZIN:
            if ts == CollaboratorServiceOffer.TARGET_SPECIES_DOG:
                extra = {
                    "species_dog": True,
                    "species_cat": False,
                    "species_other": False,
                }
            elif ts == CollaboratorServiceOffer.TARGET_SPECIES_CAT:
                extra = {
                    "species_dog": False,
                    "species_cat": True,
                    "species_other": False,
                }
            else:
                extra = {
                    "species_dog": False,
                    "species_cat": False,
                    "species_other": True,
                }
        CollaboratorServiceOffer.objects.create(
            collaborator=u,
            partner_kind=partner_kind,
            title=title[:160],
            description=desc[:500],
            image=img,
            target_species=ts,
            is_active=True,
            price_hint=f"{10 + i * 3} lei",
            **extra,
        )
        n += 1
    print(f"  Created {n} offers for {username} ({kind_label}).")
    return n


def main() -> None:
    parser = argparse.ArgumentParser(description="Seed portfolio data for aligned test users.")
    parser.add_argument(
        "--clear",
        action="store_true",
        help="Remove existing [seed] rows before inserting.",
    )
    args = parser.parse_args()

    if args.clear:
        clear_seed_rows()

    total_a = 0
    total_o = 0

    for uname in PF_USERS + ORG_USERS:
        u = _get_user(uname)
        if not u:
            print(f"MISSING USER: {uname!r} — run scripts/_align_user_roles.py first.")
            continue
        total_a += seed_animals_for_owner(u, uname)

    for username, pkind, label in COLLAB_OFFERS:
        total_o += seed_offers_for_collab(username, pkind, label)

    print(f"Done. New animals this run: {total_a}, new offers this run: {total_o}.")


if __name__ == "__main__":
    main()
