"""
Seed 4 anunțuri demo pierdut/găsit (2+2) pe Neamț și Cluj.
Idempotent: șterge mai întâi rândurile cu marker [DEMO-AP] în description.
Rulează pe H: sudo -u euadopt bash -c 'cd /opt/eu-adopt && source venv/bin/activate && python manage.py shell < scripts/_seed_pierdute_demo.py'
"""
from pathlib import Path

from django.conf import settings
from django.contrib.auth import get_user_model
from django.core.files.base import ContentFile

from home.models import LostFoundAnimal

User = get_user_model()
u = User.objects.filter(is_superuser=True).order_by("id").first()
if u is None:
    u = User.objects.order_by("id").first()
print("USER", getattr(u, "id", None), getattr(u, "username", None))
if not u:
    raise SystemExit("no user")

MARKER = "[DEMO-AP]"
deleted, _ = LostFoundAnimal.objects.filter(description__contains=MARKER).delete()
print("DELETED_OLD", deleted)

base = Path(settings.BASE_DIR) / "static" / "images" / "a2_demo"
photos = {
    "dog1": base / "a2_demo_01_caine.jpg",
    "dog2": base / "a2_demo_02_caine.jpg",
    "cat1": base / "a2_demo_05_pisica.jpg",
    "cat2": base / "a2_demo_06_pisica.jpg",
}
for key, path in photos.items():
    if not path.is_file():
        raise SystemExit(f"missing photo {path}")

demos = [
    {
        "kind": LostFoundAnimal.KIND_LOST,
        "species": "dog",
        "name": "Rex",
        "judet": "Neamț",
        "judet_slug": "neamt",
        "localitate": "Piatra Neamț",
        "phone": "0722000111",
        "photo_key": "dog1",
        "description": (
            f"{MARKER} Câine de talie medie, blana maro-deschis, cu zgarda albastră. "
            "Pierdut lângă Parcul Central din Piatra Neamț, seara. "
            "Răspunde la numele Rex. Mulțumim pentru orice informație!"
        ),
    },
    {
        "kind": LostFoundAnimal.KIND_FOUND,
        "species": "cat",
        "name": "Miau",
        "judet": "Neamț",
        "judet_slug": "neamt",
        "localitate": "Roman",
        "phone": "0722000222",
        "photo_key": "cat1",
        "description": (
            f"{MARKER} Pisică găsită pe Str. Ștefan cel Mare, Roman. "
            "Blana gri, ochi verzi, foarte blândă. Are un clopoțel la gât. "
            "O țin temporar — stăpânul o poate contacta la telefon."
        ),
    },
    {
        "kind": LostFoundAnimal.KIND_LOST,
        "species": "dog",
        "name": "Bruno",
        "judet": "Cluj",
        "judet_slug": "cluj",
        "localitate": "Cluj-Napoca",
        "phone": "0744000333",
        "photo_key": "dog2",
        "description": (
            f"{MARKER} Labrador negru, ~3 ani, pierdut în zona Mărăști. "
            "Poartă ham roșu. Timid cu străinii, dar vine dacă aude „Bruno”. "
            "Recompensă pentru găsire."
        ),
    },
    {
        "kind": LostFoundAnimal.KIND_FOUND,
        "species": "cat",
        "name": "Luna",
        "judet": "Cluj",
        "judet_slug": "cluj",
        "localitate": "Turda",
        "phone": "0744000444",
        "photo_key": "cat2",
        "description": (
            f"{MARKER} Pisică alb-negru găsită lângă piața din Turda. "
            "Pare îngrijită, posibil microcip. Stă într-o cutie încălzită "
            "până apare stăpânul. Vă rugăm să distribuiți anunțul."
        ),
    },
]

created = []
for i, d in enumerate(demos, 1):
    raw = photos[d["photo_key"]].read_bytes()
    obj = LostFoundAnimal(
        user=u,
        kind=d["kind"],
        species=d["species"],
        name=d["name"],
        judet=d["judet"],
        judet_slug=d["judet_slug"],
        localitate=d["localitate"],
        description=d["description"],
        phone=d["phone"],
        is_active=True,
    )
    obj.photo.save(f"demo_ap_{i}_{d['photo_key']}.jpg", ContentFile(raw), save=True)
    created.append((obj.pk, obj.kind, obj.name, obj.judet_slug))
    print("CREATED", obj.pk, obj.kind, obj.name, obj.judet_slug, obj.localitate)

print("OK", created)
print(
    "counts",
    {
        "neamt": LostFoundAnimal.objects.filter(judet_slug="neamt", is_active=True).count(),
        "cluj": LostFoundAnimal.objects.filter(judet_slug="cluj", is_active=True).count(),
    },
)
