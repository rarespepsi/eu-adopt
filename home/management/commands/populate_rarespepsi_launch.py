"""
Populează vitrina lansare pe contul ORG rarespepsi: +57 animale (total 65 = 25 câini, 25 pisici, 15 alte).

- Nume reale, fără prefix [seed]
- Fișă completă (vârstă, talie, sex, culoare, steril/vaccin/CIP/carnet, texte, trăsături)
- 3 poze / animal (copiate din static/images/pets/ → media/animals/)
- Județe: tur 1 = câte un animal / județ (42); tur 2 = oraș secundar pe primele 23 județe

Folosește bulk_create pentru animale noi (ocolire limită populare 5 animale / ORG).

Rulare:
  python manage.py populate_rarespepsi_launch --dry-run
  python manage.py populate_rarespepsi_launch
"""
from __future__ import annotations

from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile
from django.core.management.base import BaseCommand, CommandError
from django.utils import timezone

from home.management.commands.import_grooming_ddg_by_judet import JUDETE_RO, ORASE_EXTRA
from home.models import AnimalListing

User = get_user_model()

OWNER_USERNAME = "rarespepsi"
TARGET_BY_SPECIES = {"dog": 25, "cat": 25, "other": 15}
NUM_JUDETE = len(JUDETE_RO)  # 42 (41 județe + București)


def _location_for_slot(slot: int) -> tuple[str, str]:
    """
    Tur 1 (slot 0..41): reședința fiecărui județ, câte un animal / județ.
    Tur 2+ (slot >= 42): același județ, oraș secundar din ORASE_EXTRA când există.
    """
    county_idx = slot % NUM_JUDETE
    code, county, capital = JUDETE_RO[county_idx]
    tour = slot // NUM_JUDETE
    if tour == 0:
        return county, capital
    extras = ORASE_EXTRA.get(code, [])
    if extras:
        return county, extras[(tour - 1) % len(extras)]
    return county, capital

AGE_LABELS = (
    "<1 an",
    "1 an",
    "2 ani",
    "3 ani",
    "4 ani",
    "5 ani",
    "6 ani",
    "7 ani",
    "8 ani",
    "9 ani",
    "10+ ani",
)

COLORS = (
    "Negru",
    "Alb",
    "Maro",
    "Bej",
    "Cafeniu",
    "Roșcat",
    "Gri",
    "Tigrat",
    "Pătat",
    "Negru cu alb",
    "Maro cu alb",
    "Tricolor",
)

DOG_NAMES = [
    "Charlie",
    "Bella",
    "Daisy",
    "Bruno",
    "Mia",
    "Rocky",
    "Zara",
    "Archie",
    "Buddy",
    "Cooper",
    "Duke",
    "Finn",
    "Hugo",
    "Jasper",
    "Leo",
    "Milo",
    "Nora",
    "Odin",
    "Poppy",
    "Sam",
    "Toby",
    "Zeus",
    "Rex",
    "Luna",
    "Max",
    "Bailey",
    "Cody",
    "Ace",
]

CAT_NAMES = [
    "Simba",
    "Tiger",
    "Whiskers",
    "Cleo",
    "Felix",
    "Ginger",
    "Misty",
    "Pepper",
    "Shadow",
    "Smokey",
    "Tigger",
    "Willow",
    "Amber",
    "Coco",
    "Dotty",
    "Ivy",
    "Kira",
    "Loki",
    "Misha",
    "Pixel",
    "Ruby",
    "Sassy",
    "Mitzi",
    "Oscar",
    "Nala",
    "Oreo",
    "Pumpkin",
    "Binx",
]

OTHER_NAMES = [
    "Albă",
    "Cappuccino",
    "Alpi",
    "Verde",
    "Nimbus",
    "Patch",
    "Chinchilla Alba",
    "Chinchilla Gri",
    "Pixi",
    "Pufi",
    "Tudi",
    "Dolly",
    "Tris",
    "Mimi",
    "Nori",
    "Zori",
    "Bibi",
]

OTHER_SPECIES_LABEL = [
    "iepure",
    "iepure",
    "papagal",
    "papagal",
    "porcușor de Guineea",
    "porcușor de Guineea",
    "chinchilla",
    "chinchilla",
    "ferică",
    "șopârlă",
    "broască țestoasă",
    "rată",
    "veveriță",
    "hamster",
    "porcupine",
    "gecko",
]

TRAIT_FIELDS = (
    "trait_jucaus",
    "trait_iubitor",
    "trait_protector",
    "trait_energic",
    "trait_linistit",
    "trait_bun_copii",
    "trait_bun_caini",
    "trait_bun_pisici",
    "trait_obisnuit_casa",
    "trait_obisnuit_lesa",
    "trait_nu_latla",
    "trait_apartament",
    "trait_se_adapteaza",
    "trait_tolereaza_singur",
    "trait_necesita_experienta",
)

DOG_TRAIT_PRESETS = [
    ("trait_jucaus", "trait_iubitor", "trait_bun_copii", "trait_se_adapteaza"),
    ("trait_energic", "trait_obisnuit_lesa", "trait_bun_caini", "trait_iubitor"),
    ("trait_linistit", "trait_apartament", "trait_tolereaza_singur", "trait_iubitor"),
    ("trait_protector", "trait_bun_copii", "trait_nu_latla", "trait_obisnuit_casa"),
    ("trait_jucaus", "trait_energic", "trait_bun_copii", "trait_obisnuit_lesa"),
]

CAT_TRAIT_PRESETS = [
    ("trait_linistit", "trait_iubitor", "trait_apartament", "trait_se_adapteaza"),
    ("trait_jucaus", "trait_bun_copii", "trait_bun_pisici", "trait_tolereaza_singur"),
    ("trait_iubitor", "trait_obisnuit_casa", "trait_apartament", "trait_se_adapteaza"),
    ("trait_energic", "trait_jucaus", "trait_bun_copii", "trait_iubitor"),
]

OTHER_TRAIT_PRESETS = [
    ("trait_linistit", "trait_obisnuit_casa", "trait_se_adapteaza", "trait_iubitor"),
    ("trait_jucaus", "trait_tolereaza_singur", "trait_apartament", "trait_iubitor"),
]


def _pet_image_paths() -> list[Path]:
    root = Path(settings.BASE_DIR) / "static" / "images" / "pets"
    if not root.is_dir():
        return []
    files = sorted(
        p
        for p in root.iterdir()
        if p.is_file()
        and p.suffix.lower() in (".jpg", ".jpeg", ".png", ".webp")
        and not p.name.startswith("hero_")
    )
    # Preferă variante 275×275 / 400×200 față de miniaturi 180×180
    preferred = [p for p in files if "275" in p.name or "400" in p.name or "600" in p.name]
    return preferred or files


def _size_for(species: str, idx: int) -> str:
    if species == "cat":
        return ("mica", "medie", "mica")[idx % 3]
    if species == "other":
        return "mica"
    return ("medie", "mare", "mica", "medie")[idx % 4]


def _weight_for(species: str, size: str) -> str:
    if species == "cat":
        return {"mica": "3.5 kg", "medie": "4.8 kg", "mare": "5.5 kg"}.get(size, "4 kg")
    if species == "other":
        return "0.4 kg"
    return {"mica": "8 kg", "medie": "18 kg", "mare": "32 kg"}.get(size, "15 kg")


def _traits_for(species: str, idx: int) -> dict[str, bool]:
    presets = {
        "dog": DOG_TRAIT_PRESETS,
        "cat": CAT_TRAIT_PRESETS,
        "other": OTHER_TRAIT_PRESETS,
    }[species]
    chosen = presets[idx % len(presets)]
    out = {f: False for f in TRAIT_FIELDS}
    for f in chosen:
        out[f] = True
    return out


def _texts_for(species: str, name: str, county: str, city: str, other_label: str = "") -> tuple[str, str, str]:
    if species == "dog":
        cine = (
            f"Sunt {name}, un câine prietenos din zona {city}, județul {county}. "
            f"Am fost preluat de echipa adăpostului și aștept o familie responsabilă."
        )
        detalii = (
            f"{name} este sociabil, obișnuiește cu plimbările zilnice și răspunde bine la comenzi de bază. "
            "Se înțelege bine cu oamenii blânzi și se adaptează treptat la mediul nou."
        )
        probleme = "Nu sunt cunoscute probleme medicale majore la momentul evaluării."
    elif species == "cat":
        cine = (
            f"Sunt {name}, o pisică blândă din {city} ({county}). "
            "Caut o casă liniștită unde să pot avea timp să mă obișnuiesc."
        )
        detalii = (
            f"{name} folosește litiera, este curată și preferă colțuri liniștite pentru odihnă. "
            "Se apropie ușor de persoanele care vorbesc calm și oferă mângâieri."
        )
        probleme = "Nu sunt raportate afecțiuni cronice; a primit evaluare veterinară de rutină."
    else:
        label = other_label or "animal mic"
        cine = (
            f"Sunt {name}, un {label} găsit în {city}, județul {county}. "
            "Am nevoie de îngrijire adaptată speciei mele și de o familie informată."
        )
        detalii = (
            f"{name} ({label}) are rutină stabilă de hrană și adapost. "
            "Viitorul adoptator primește recomandări clare de îngrijire de la echipa adăpostului."
        )
        probleme = "Fără probleme medicale evidente; consult veterinar la preluare."
    return cine, detalii, probleme


def _build_row(
    owner_id: int,
    species: str,
    name: str,
    slot: int,
    other_label: str = "",
) -> AnimalListing:
    county, city = _location_for_slot(slot)
    size = _size_for(species, slot)
    age = AGE_LABELS[slot % len(AGE_LABELS)]
    color = COLORS[slot % len(COLORS)]
    sex = "m" if slot % 2 == 0 else "f"
    cine, detalii, probleme = _texts_for(species, name, county, city, other_label)
    traits = _traits_for(species, slot)
    now = timezone.now()
    return AnimalListing(
        owner_id=owner_id,
        name=name,
        species=species,
        size=size,
        age_label=age,
        city=city,
        county=county,
        color=color,
        sterilizat="da" if slot % 5 else "nu",
        vaccinat="da",
        carnet_sanatate="da" if species != "other" or slot % 2 == 0 else "nu",
        cip="da" if species != "other" else "nu",
        sex=sex,
        greutate_aprox=_weight_for(species, size),
        probleme_medicale=probleme,
        cine_sunt=cine,
        detalii_animal=detalii,
        is_published=True,
        adoption_state=AnimalListing.ADOPTION_STATE_OPEN,
        created_at=now,
        updated_at=now,
        **traits,
    )


def _photo_on_disk(field) -> bool:
    if not field or not getattr(field, "name", None):
        return False
    try:
        return Path(field.path).is_file()
    except Exception:
        return False


def _attach_three_photos(listing: AnimalListing, images: list[Path], slot: int) -> list[str]:
    """Returnează lista câmpurilor photo actualizate."""
    updated: list[str] = []
    if not images:
        return updated
    for pi, field_name in enumerate(("photo_1", "photo_2", "photo_3")):
        field = getattr(listing, field_name)
        if _photo_on_disk(field):
            continue
        src = images[(slot * 3 + pi) % len(images)]
        data = src.read_bytes()
        ext = src.suffix.lower() or ".jpg"
        fname = f"launch_{listing.pk}_{field_name}{ext}"
        field.save(fname, ContentFile(data), save=False)
        updated.append(field_name)
    return updated


def _apply_location(listing: AnimalListing, slot: int, other_label: str = "") -> list[str]:
    """Setează județ/oraș (tur 1 sau 2) și regenerează textele din fișă."""
    county, city = _location_for_slot(slot)
    listing.county = county
    listing.city = city
    cine, detalii, probleme = _texts_for(
        listing.species,
        listing.name or "Animal",
        county,
        city,
        other_label,
    )
    listing.cine_sunt = cine
    listing.detalii_animal = detalii
    listing.probleme_medicale = probleme
    return ["county", "city", "cine_sunt", "detalii_animal", "probleme_medicale"]


def _fill_missing_text(listing: AnimalListing, slot: int, other_label: str = "") -> list[str]:
    """Completează câmpuri goale pe animale existente."""
    changed: list[str] = []
    county, city = _location_for_slot(slot)
    if not (listing.county or "").strip():
        listing.county = county
        changed.append("county")
    if not (listing.city or "").strip():
        listing.city = city
        changed.append("city")
    for attr, default in (
        ("vaccinat", "da"),
        ("carnet_sanatate", "da"),
        ("cip", "da" if listing.species != "other" else "nu"),
        ("sex", "m" if slot % 2 == 0 else "f"),
    ):
        if not (getattr(listing, attr) or "").strip():
            setattr(listing, attr, default)
            changed.append(attr)
    if not (listing.color or "").strip():
        listing.color = COLORS[slot % len(COLORS)]
        changed.append("color")
    if not (listing.greutate_aprox or "").strip():
        listing.greutate_aprox = _weight_for(listing.species, listing.size or "medie")
        changed.append("greutate_aprox")
    if not (listing.probleme_medicale or "").strip():
        _, _, listing.probleme_medicale = _texts_for(
            listing.species,
            listing.name or "Animal",
            listing.county,
            listing.city,
            other_label,
        )
        changed.append("probleme_medicale")
    if not (listing.detalii_animal or "").strip():
        _, listing.detalii_animal, _ = _texts_for(
            listing.species,
            listing.name or "Animal",
            listing.county,
            listing.city,
            other_label,
        )
        changed.append("detalii_animal")
    if not (listing.cine_sunt or "").strip():
        listing.cine_sunt, _, _ = _texts_for(
            listing.species,
            listing.name or "Animal",
            listing.county,
            listing.city,
            other_label,
        )
        changed.append("cine_sunt")
    traits = _traits_for(listing.species, slot)
    for f, val in traits.items():
        if getattr(listing, f) != val and not any(getattr(listing, t) for t in TRAIT_FIELDS):
            setattr(listing, f, val)
            changed.append(f)
    return changed


class Command(BaseCommand):
    help = "Adaugă +57 animale vitrină pe rarespepsi (65 total) + fișă full + 3 poze."

    def add_arguments(self, parser):
        parser.add_argument(
            "--dry-run",
            action="store_true",
            help="Simulare, fără scriere în DB/media.",
        )
        parser.add_argument(
            "--username",
            default=OWNER_USERNAME,
            help=f"Cont ORG (implicit {OWNER_USERNAME}).",
        )
        parser.add_argument(
            "--vary-counties-existing",
            action="store_true",
            help="Rescrie județ/oraș și pe animalele existente (implicit: da, prin rotație).",
        )
        parser.set_defaults(vary_counties_existing=True)

    def handle(self, *args, **options):
        dry_run: bool = options["dry_run"]
        username: str = options["username"]
        vary_existing: bool = options["vary_counties_existing"]

        user = User.objects.filter(username__iexact=username).first()
        if not user:
            raise CommandError(f"User {username!r} lipsește.")

        images = _pet_image_paths()
        if not images:
            raise CommandError("Nu găsesc imagini în static/images/pets/.")

        base_qs = AnimalListing.objects.filter(owner=user).exclude(name__startswith="[seed]")
        counts = {sp: base_qs.filter(species=sp).count() for sp in TARGET_BY_SPECIES}
        to_create: list[AnimalListing] = []
        slot = base_qs.count()

        name_pools = {
            "dog": DOG_NAMES,
            "cat": CAT_NAMES,
            "other": OTHER_NAMES,
        }
        used_names = set(base_qs.values_list("name", flat=True))

        for species, target in TARGET_BY_SPECIES.items():
            have = counts.get(species, 0)
            need = max(0, target - have)
            pool = name_pools[species]
            added = 0
            pi = 0
            while added < need and pi < len(pool) * 3:
                candidate = pool[pi % len(pool)]
                pi += 1
                if candidate in used_names:
                    continue
                other_label = ""
                if species == "other":
                    other_label = OTHER_SPECIES_LABEL[added % len(OTHER_SPECIES_LABEL)]
                to_create.append(_build_row(user.id, species, candidate, slot, other_label))
                used_names.add(candidate)
                slot += 1
                added += 1
            if added < need:
                raise CommandError(
                    f"Nu am destule nume pentru {species}: lipsesc {need - added}."
                )

        self.stdout.write(
            f"Owner={username} existente={dict(counts)} de_creat={len(to_create)} "
            f"imagini={len(images)}"
        )

        if dry_run:
            preview = list(
                AnimalListing.objects.filter(owner=user)
                .exclude(name__startswith="[seed]")
                .order_by("pk")
            )
            for row in to_create[:5]:
                self.stdout.write(
                    f"  + {row.species} {row.name} @ {row.county}/{row.city}"
                )
            for idx, listing in enumerate(preview[:8]):
                county, city = _location_for_slot(idx)
                tour = idx // NUM_JUDETE + 1
                self.stdout.write(
                    f"  loc pk={listing.pk} -> {county}/{city} (tur {tour})"
                )
            if len(preview) > 8:
                self.stdout.write(f"  ... și încă {len(preview) - 8} locații")
            self.stdout.write(self.style.WARNING("DRY-RUN — nimic scris."))
            return

        if to_create:
            AnimalListing.objects.bulk_create(to_create, batch_size=50)
            self.stdout.write(self.style.SUCCESS(f"Create {len(to_create)} animale noi."))

        all_listings = list(
            AnimalListing.objects.filter(owner=user)
            .exclude(name__startswith="[seed]")
            .order_by("pk")
        )

        enriched = 0
        photos_fixed = 0
        for idx, listing in enumerate(all_listings):
            other_label = ""
            if listing.species == "other":
                other_label = OTHER_SPECIES_LABEL[idx % len(OTHER_SPECIES_LABEL)]

            if vary_existing:
                loc_fields = _apply_location(listing, idx, other_label)
            else:
                loc_fields = []

            text_fields = _fill_missing_text(listing, idx, other_label)
            photo_fields = _attach_three_photos(listing, images, idx)
            update_fields = list(
                dict.fromkeys(loc_fields + text_fields + photo_fields + ["updated_at"])
            )
            if update_fields:
                listing.updated_at = timezone.now()
                if "updated_at" not in update_fields:
                    update_fields.append("updated_at")
                listing.save(update_fields=update_fields)
                enriched += 1
                photos_fixed += len(photo_fields)

        final_counts = {
            sp: AnimalListing.objects.filter(owner=user, species=sp)
            .exclude(name__startswith="[seed]")
            .count()
            for sp in TARGET_BY_SPECIES
        }
        total = sum(final_counts.values())
        counties_used = (
            AnimalListing.objects.filter(owner=user)
            .exclude(name__startswith="[seed]")
            .values_list("county", flat=True)
            .distinct()
            .count()
        )
        second_tour = max(0, total - NUM_JUDETE)
        self.stdout.write(
            self.style.SUCCESS(
                f"Gata: total={total} ({final_counts}), "
                f"judete_distincte={counties_used}/{NUM_JUDETE}, "
                f"tur2={second_tour}, "
                f"actualizate={enriched}, poze_noí={photos_fixed}"
            )
        )
