"""
Modele pentru platforma Adopt a Pet.
Reconstruite din migrații pentru pets_single și adopții.
"""
import os
from django.db import models
from django.conf import settings
from django.db.models import Q, Min
from django.core.exceptions import ValidationError
from django.core.validators import MinValueValidator, MaxValueValidator

try:
    from PIL import Image, ImageOps
except Exception:  # pragma: no cover
    Image = None
    ImageOps = None

USER_PHOTO_MAX_SIZE_BYTES = 2 * 1024 * 1024  # 2 MB


def user_photo_upload_to(instance, filename):
    return f"profiles/{instance.user_id}/{filename}"


def post_adoption_photo_upload_to(instance, filename):
    return f"post_adoption/{instance.adoption_request_id}/{filename}"


JUDET_CHOICES = [
    ("alba", "Alba"), ("arad", "Arad"), ("arges", "Argeș"), ("bacau", "Bacău"),
    ("bihor", "Bihor"), ("bistrita-nasaud", "Bistrița-Năsăud"), ("botosani", "Botoșani"),
    ("brasov", "Brașov"), ("braila", "Brăila"), ("buzau", "Buzău"), ("calarasi", "Călărași"),
    ("caras-severin", "Caraș-Severin"), ("cluj", "Cluj"), ("constanta", "Constanța"),
    ("covasna", "Covasna"), ("dambovita", "Dâmbovița"), ("dolj", "Dolj"), ("galati", "Galați"),
    ("giurgiu", "Giurgiu"), ("gorj", "Gorj"), ("harghita", "Harghita"), ("hunedoara", "Hunedoara"),
    ("ialomita", "Ialomița"), ("iasi", "Iași"), ("ilfov", "Ilfov"), ("maramures", "Maramureș"),
    ("mehedinti", "Mehedinți"), ("mures", "Mureș"), ("neamt", "Neamț"), ("olt", "Olt"),
    ("prahova", "Prahova"), ("salaj", "Sălaj"), ("satu-mare", "Satu Mare"), ("sibiu", "Sibiu"),
    ("suceava", "Suceava"), ("teleorman", "Teleorman"), ("timis", "Timiș"), ("tulcea", "Tulcea"),
    ("valcea", "Vâlcea"), ("vaslui", "Vaslui"), ("vrancea", "Vrancea"), ("bucuresti", "București"),
]


def _varsta_aproximativa_choices():
    """Opțiuni vârstă aproximativă: < 1 an, 1 an .. 15 ani, > 15 ani (unghi/simbol, nu scris)."""
    choices = [(0, "< 1 an"), (1, "1 an")]
    for i in range(2, 16):
        choices.append((i, f"{i} ani"))
    choices.append((16, "> 15 ani"))
    return choices


class Pet(models.Model):
    TIP_CHOICES = [("dog", "Câine"), ("cat", "Pisică"), ("other", "Altele")]
    VARSTA_APROX_CHOICES = _varsta_aproximativa_choices()
    SEX_CHOICES = [("male", "Male"), ("female", "Female")]
    MARIME_CHOICES = [("small", "Small"), ("medium", "Medium"), ("large", "Large"), ("xlarge", "Extra Large")]
    STATUS_CHOICES = [
        ("adoptable", "Adoptable"), 
        ("pending", "În curs de adoptare!"), 
        ("adopted", "Adopted"),
        ("showcase_archive", "Showcase Archive")  # Visual buffer, not adoptable, not searchable
    ]
    JUDET_CHOICES = JUDET_CHOICES

    nume = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    rasa = models.CharField(max_length=100)
    tip = models.CharField(choices=TIP_CHOICES, default="dog", max_length=10)
    tip_altele = models.CharField(
        blank=True,
        max_length=80,
        verbose_name="Tip animal (Altele)",
        help_text="Completați liber dacă Tip = Altele (ex: Pasăre, Iepure, Șopârlă). În liste apare la categoria Altele.",
    )
    varsta_aproximativa = models.PositiveSmallIntegerField(
        choices=VARSTA_APROX_CHOICES,
        null=True,
        blank=True,
        verbose_name="Vârstă aproximativă (ani)",
    )
    age_years = models.PositiveSmallIntegerField(
        null=True,
        blank=True,
        validators=[MinValueValidator(0), MaxValueValidator(20)],
        verbose_name="Vârsta (ani)",
        help_text="Vârstă în ani (0–20). Obligatoriu la postare.",
    )
    sex = models.CharField(choices=SEX_CHOICES, max_length=10)
    marime = models.CharField(blank=True, choices=MARIME_CHOICES, max_length=10, verbose_name="Talie")
    descriere = models.TextField(blank=True)
    imagine = models.ImageField(blank=True, null=True, upload_to="pets/", verbose_name="Poză 1 (principală)")
    imagine_2 = models.ImageField(blank=True, null=True, upload_to="pets/", verbose_name="Poză 2")
    imagine_3 = models.ImageField(blank=True, null=True, upload_to="pets/", verbose_name="Poză 3")
    imagine_fallback = models.CharField(
        blank=True, max_length=200,
        help_text="Path static ex: images/pets/charlie-275x275.jpg dacă nu e upload"
    )
    status = models.CharField(choices=STATUS_CHOICES, default="adoptable", max_length=20)
    tags = models.TextField(blank=True, help_text="Separate prin virgulă: Adoptable, Spayed/Neutered, House trained")
    data_adaugare = models.DateTimeField(auto_now_add=True)
    judet = models.CharField(blank=True, choices=JUDET_CHOICES, max_length=30, help_text="Județul unde se află animalul / adăpostul.")
    ong_email = models.EmailField(blank=True, max_length=254, help_text="Emailul asociației. Primește cererea.")
    ong_address = models.CharField(blank=True, max_length=300, verbose_name="Adresă ONG")
    ong_contact_person = models.CharField(blank=True, max_length=120, verbose_name="Persoană de contact")
    ong_phone = models.CharField(blank=True, max_length=30, verbose_name="Telefon ONG")
    ong_visiting_hours = models.CharField(blank=True, max_length=200, verbose_name="Program vizită")
    ong_pickup_address = models.CharField(
        blank=True, max_length=300,
        verbose_name="Locație ridicare câine / locație fizică",
        help_text="Adresă separată unde se ridică animalul (dacă e diferită de sediul legal).",
    )
    featured = models.BooleanField(default=False, verbose_name="Animale lunii / VIP")
    # Adăpost public = obligație legală să completeze sterilizat, CIP, carnet sănătate. PF și ONG pot completa și ei casutele sanitar.
    adapost_public = models.BooleanField(
        default=False,
        verbose_name="Adăpost public",
        help_text="Bifat doar pentru adăposturi publice. Pentru adăpost public, sterilizat, CIP și carnet sănătate sunt obligatorii. Casutele de mai jos (vaccin, carnet, etc.) pot fi completate de oricine (PF, ONG, adăpost)."
    )
    # Sanitar: obligatoriu pentru adăpost public; opțional pentru PF și ONG
    sterilizat = models.BooleanField(null=True, blank=True, verbose_name="Sterilizat/Castrat")
    cip = models.CharField(max_length=50, blank=True, verbose_name="Număr CIP")
    carnet_sanatate = models.CharField(
        max_length=200, blank=True,
        verbose_name="Carnet de sănătate",
        help_text="Obligatoriu pentru adăposturi publice."
    )
    vaccin = models.CharField(max_length=200, blank=True, verbose_name="Vaccin (da/nu/detalii)")
    # Status sanitar standard (dropdown) pentru formular uniform
    YES_NO_PROGRESS_UNKNOWN = [
        ("yes", "Da"),
        ("no", "Nu"),
        ("in_progress", "În curs"),
        ("unknown", "Necunoscut"),
    ]
    sterilized_status = models.CharField(
        max_length=20, blank=True, choices=YES_NO_PROGRESS_UNKNOWN,
        verbose_name="Sterilizat/Castrat",
    )
    vaccinated_status = models.CharField(
        max_length=20, blank=True, choices=YES_NO_PROGRESS_UNKNOWN,
        verbose_name="Vaccinat",
    )
    dewormed_status = models.CharField(
        max_length=20, blank=True, choices=YES_NO_PROGRESS_UNKNOWN,
        verbose_name="Deparazitat",
    )
    microchipped_status = models.CharField(
        max_length=20, blank=True, choices=YES_NO_PROGRESS_UNKNOWN,
        verbose_name="Microcipat",
    )
    video_url = models.URLField(
        max_length=500, blank=True,
        verbose_name="Link video (opțional)",
        help_text="URL către un video (YouTube, etc.). Opțional.",
    )
    # --- Descriere structurată (bife + recomandare automată) ---
    # Temperament
    prietenos_cu_oamenii = models.BooleanField(default=False, blank=True, verbose_name="Prietenos cu oamenii")
    prietenos_cu_copiii = models.BooleanField(default=False, blank=True, verbose_name="Prietenos cu copiii")
    timid = models.BooleanField(default=False, blank=True, verbose_name="Timid")
    protector = models.BooleanField(default=False, blank=True, verbose_name="Protector")
    energic_jucaus = models.BooleanField(default=False, blank=True, verbose_name="Energic, jucăuș")
    linistit = models.BooleanField(default=False, blank=True, verbose_name="Liniștit")
    independent = models.BooleanField(default=False, blank=True, verbose_name="Independent")
    cauta_atentie = models.BooleanField(default=False, blank=True, verbose_name="Caută atenție")
    latra_des = models.BooleanField(default=False, blank=True, verbose_name="Lată des")
    calm_in_casa = models.BooleanField(default=False, blank=True, verbose_name="Calm în casă")
    # Stil de viață
    potrivit_apartament = models.BooleanField(default=False, blank=True, verbose_name="Potrivit apartament")
    prefera_curte = models.BooleanField(default=False, blank=True, verbose_name="Preferă curte")
    poate_sta_afara = models.BooleanField(default=False, blank=True, verbose_name="Poate sta afară")
    poate_sta_interior = models.BooleanField(default=False, blank=True, verbose_name="Poate sta în interior")
    obisnuit_in_lesa = models.BooleanField(default=False, blank=True, verbose_name="Obisnuit în lesă")
    merge_bine_la_plimbare = models.BooleanField(default=False, blank=True, verbose_name="Merge bine la plimbare")
    necesita_miscare_multa = models.BooleanField(default=False, blank=True, verbose_name="Necesită mișcare multă")
    potrivit_persoane_varstnice = models.BooleanField(default=False, blank=True, verbose_name="Potrivit persoane vârstnice")
    potrivit_familie_activa = models.BooleanField(default=False, blank=True, verbose_name="Potrivit familie activă")
    # Compatibilitate
    ok_cu_alti_caini = models.BooleanField(default=False, blank=True, verbose_name="OK cu alți câini")
    ok_cu_pisici = models.BooleanField(default=False, blank=True, verbose_name="OK cu pisici")
    prefera_singurul_animal = models.BooleanField(default=False, blank=True, verbose_name="Preferă singurul animal")
    accepta_vizitatori = models.BooleanField(default=False, blank=True, verbose_name="Acceptă vizitatori")
    necesita_socializare = models.BooleanField(default=False, blank=True, verbose_name="Necesită socializare")
    # Status medical (bife suplimentare față de câmpurile existente)
    vaccinat = models.BooleanField(default=False, blank=True, verbose_name="Vaccinat")
    deparazitat = models.BooleanField(default=False, blank=True, verbose_name="Deparazitat")
    microcipat = models.BooleanField(default=False, blank=True, verbose_name="Microcipat")
    are_pasaport = models.BooleanField(default=False, blank=True, verbose_name="Are pașaport")
    necesita_tratament = models.BooleanField(default=False, blank=True, verbose_name="Necesită tratament")
    sensibil_zgomote = models.BooleanField(default=False, blank=True, verbose_name="Sensibil la zgomote")
    # Educație
    stie_comenzi_baza = models.BooleanField(default=False, blank=True, verbose_name="Știe comenzi de bază")
    face_nevoile_afara = models.BooleanField(default=False, blank=True, verbose_name="Face nevoile afară")
    invata_repede = models.BooleanField(default=False, blank=True, verbose_name="Învață repede")
    necesita_dresaj = models.BooleanField(default=False, blank=True, verbose_name="Necesită dresaj")
    nu_roade = models.BooleanField(default=False, blank=True, verbose_name="Nu roade")
    obisnuit_masina = models.BooleanField(default=False, blank=True, verbose_name="Obisnuit mașină")
    # Recomandare specială
    recomandat_prima_adoptie = models.BooleanField(default=False, blank=True, verbose_name="Recomandat pentru prima adopție")
    # Descriere liberă personalitate (max 500 caractere)
    descriere_personalitate = models.CharField(
        max_length=500, blank=True,
        verbose_name="Descriere personalitate",
        help_text="Max 500 caractere. Completare liberă.",
    )
    # Câmpuri pentru algoritm matching (Găsește-mi prietenul ideal)
    ENERGY_LEVEL_CHOICES = [("low", "Scăzut"), ("medium", "Mediu"), ("high", "Ridicat")]
    SIZE_CATEGORY_CHOICES = [("small", "Mic"), ("medium", "Mediu"), ("large", "Mare")]
    AGE_CATEGORY_CHOICES = [("puppy", "Pui"), ("young", "Tânăr"), ("adult", "Adult"), ("senior", "Senior")]
    GOOD_WITH_CHOICES = [("yes", "Da"), ("no", "Nu"), ("unknown", "Necunoscut")]
    HOUSING_FIT_CHOICES = [("apartment", "Apartament"), ("house", "Casă"), ("both", "Ambele")]
    EXPERIENCE_REQUIRED_CHOICES = [("beginner", "Începător"), ("medium", "Mediu"), ("experienced", "Experimentat")]
    ATTENTION_NEED_CHOICES = [("low", "Scăzut"), ("medium", "Mediu"), ("high", "Ridicat")]
    energy_level = models.CharField(
        max_length=20, blank=True, choices=ENERGY_LEVEL_CHOICES,
        verbose_name="Nivel energie",
    )
    size_category = models.CharField(
        max_length=20, blank=True, choices=SIZE_CATEGORY_CHOICES,
        verbose_name="Categorie talie (matching)",
    )
    age_category = models.CharField(
        max_length=20, blank=True, choices=AGE_CATEGORY_CHOICES,
        verbose_name="Categorie vârstă (matching)",
    )
    good_with_children = models.CharField(
        max_length=20, blank=True, choices=GOOD_WITH_CHOICES,
        verbose_name="Ok cu copii",
    )
    good_with_dogs = models.CharField(
        max_length=20, blank=True, choices=GOOD_WITH_CHOICES,
        verbose_name="Ok cu câini",
    )
    good_with_cats = models.CharField(
        max_length=20, blank=True, choices=GOOD_WITH_CHOICES,
        verbose_name="Ok cu pisici",
    )
    housing_fit = models.CharField(
        max_length=20, blank=True, choices=HOUSING_FIT_CHOICES,
        verbose_name="Potrivit locuință",
    )
    experience_required = models.CharField(
        max_length=20, blank=True, choices=EXPERIENCE_REQUIRED_CHOICES,
        verbose_name="Experiență necesară",
    )
    attention_need = models.CharField(
        max_length=20, blank=True, choices=ATTENTION_NEED_CHOICES,
        verbose_name="Nevoie de atenție",
    )
    added_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL,
        related_name="pets_added", help_text="Setat când anunțul e adăugat de o persoană fizică."
    )
    ADOPTION_STATUS_CHOICES = [
        ("available", "Disponibil"),
        ("reserved", "În curs de adopție"),
        ("adopted", "Adoptat"),
        ("unavailable", "Indisponibil"),
    ]
    adoption_status = models.CharField(
        max_length=20,
        choices=ADOPTION_STATUS_CHOICES,
        default="available",
        verbose_name="Status adopție",
    )
    reserved_for_request = models.ForeignKey(
        "anunturi.AdoptionRequest",
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="reserved_pet",
        verbose_name="Rezervat pentru cererea",
    )

    def _ensure_landscape_image(self, field_name: str, target_size=(1200, 900)):
        """
        Transformă imaginea asociată câmpului într-un canvas landscape fix (ex. 1200x900),
        păstrând întreaga poză (fără crop agresiv): imaginea este încadrată cu 'letterbox'
        dacă raportul nu este landscape. Nu face nimic dacă Pillow nu este disponibil.
        """
        if Image is None or ImageOps is None:
            return
        image_field = getattr(self, field_name, None)
        if not image_field or not getattr(image_field, "path", None):
            return
        try:
            img = Image.open(image_field.path)
        except Exception:
            return
        try:
            # Normalizăm orientarea după EXIF (dacă există) ca să nu fie întoarse
            img = ImageOps.exif_transpose(img)
        except Exception:
            pass
        try:
            # Construim un canvas landscape cu raport fix (ex. 4:3) și încadrăm poza complet în el
            canvas_w, canvas_h = target_size
            img = ImageOps.contain(img, target_size)  # micșorăm dacă e foarte mare, păstrăm raportul
            background = Image.new("RGB", target_size, (245, 245, 245))
            offset = ((canvas_w - img.width) // 2, (canvas_h - img.height) // 2)
            background.paste(img, offset)
            background.save(image_field.path, optimize=True, quality=85)
        except Exception:
            # Dacă ceva eșuează, nu stricăm upload-ul
            return

    def has_active_requests(self):
        """True dacă există cereri cu status activ (Nouă, Validată ONG, Aprobată platformă)."""
        return self.adoption_requests.filter(
            status__in=ACTIVE_DUPLICATE_CHECK_STATUSES
        ).exists()

    def is_reserved(self):
        """True dacă există o cerere cu status REZERVAT pentru acest animal."""
        return self.adoption_requests.filter(status=REZERVAT_STATUS).exists()

    def generate_recommendation_text(self):
        """Generează text de recomandare din bifele structurate (pentru afișare pe fișa animalului)."""
        parts = []
        if getattr(self, "potrivit_apartament", False):
            parts.append("potrivit pentru apartament")
        if getattr(self, "prietenos_cu_copiii", False):
            parts.append("bun pentru familii cu copii")
        if getattr(self, "necesita_miscare_multa", False):
            parts.append("ideal pentru persoane active")
        if getattr(self, "linistit", False):
            parts.append("temperament calm")
        if getattr(self, "recomandat_prima_adoptie", False):
            parts.append("potrivit pentru prima adopție")
        if not parts:
            return ""
        return ", ".join(parts)

    def cereri_summary(self):
        total = self.adoption_requests.count()
        pending = self.adoption_requests.filter(status__in=["pending", "new", "approved_platform"]).count()
        approved = self.adoption_requests.filter(status__in=["approved", "approved_ong"]).count()
        return f"Total: {total}, Pending: {pending}, Approved: {approved}"

    cereri_summary.short_description = "Cereri adopție"

    def save(self, *args, **kwargs):
        """
        La salvare, standardizăm pozele la un format landscape (ex. 1200x900) cu letterbox,
        astfel încât toate imaginile de animale să aibă același raport de aspect pe site.
        """
        super().save(*args, **kwargs)
        # Aplicăm transformarea doar dacă imaginile există; nu ridicăm erori dacă Pillow lipsește.
        for field_name in ("imagine", "imagine_2", "imagine_3"):
            self._ensure_landscape_image(field_name)

    class Meta:
        verbose_name = "Animal"
        verbose_name_plural = "Animale"
        ordering = ["-data_adaugare"]


class PetFavorite(models.Model):
    """Câini marcați de utilizator ca „Îmi plac” (wishlist). Persistă în cont; la adopție utilizatorul primește email."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="pet_favorites"
    )
    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="favorited_by")
    created_at = models.DateTimeField(auto_now_add=True)
    notified_adopted = models.BooleanField(
        default=False,
        help_text="Setat după ce am trimis email că animalul a fost adoptat.",
    )
    reminder_72h_sent_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Dacă e setat, am trimis deja reminderul „câinii încă disponibili” după 72h.",
    )

    class Meta:
        verbose_name = "Animal preferat"
        verbose_name_plural = "Animale preferate"
        constraints = [
            models.UniqueConstraint(fields=["user", "pet"], name="unique_user_pet_favorite"),
        ]
        ordering = ["-created_at"]


ACTIVE_ADOPTION_REQUEST_STATUSES = ["pending", "approved", "new", "approved_platform", "approved_ong"]

# Statusuri care = „cerere activă” pentru verificarea duplicatului (același animal + același adoptator)
ACTIVE_DUPLICATE_CHECK_STATUSES = ["new", "approved_ong", "approved_platform"]

# Status unic: o cerere REZERVAT = animalul este rezervat; nu se mai acceptă cereri noi
REZERVAT_STATUS = "rezervat"

# Statusuri considerate „rezervare activă” (pentru butoane Adopție finalizată / Anulează)
APPROVED_RESERVATION_STATUSES = ["approved", "approved_ong"]

# Statusuri care blochează o nouă cerere de la același user pe același pet
BLOCK_DUPLICATE_REQUEST_STATUSES = ["pending", "approved", "approved_ong", "approved_platform", "new", "waitlist"]


class AdoptionRequest(models.Model):
    STATUS_CHOICES = [
        ("pending", "În așteptare"),
        ("approved", "Aprobat (așteaptă vizita)"),
        ("finalized", "Adopție finalizată"),
        ("rejected", "Respins"),
        ("cancelled", "Anulat de adoptator"),
        ("no_show", "Nu s-a prezentat"),
        ("waitlist", "În așteptare (listă)"),
        ("rezervat", "REZERVAT"),
        # Compatibilitate cu fluxul existent (platformă / ONG)
        ("new", "Nouă"),
        ("approved_platform", "Aprobată de platformă (trimisă la ONG)"),
        ("approved_ong", "Validată de ONG"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="adoption_requests", verbose_name="Animal")
    adopter = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="adoption_requests_made",
        verbose_name="Adoptator (cont)",
    )
    owner = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="adoption_requests_received",
        verbose_name="Proprietar (cine a postat animalul)",
    )
    nume_complet = models.CharField(max_length=200, verbose_name="Nume complet")
    email = models.EmailField(max_length=254)
    telefon = models.CharField(max_length=30)
    adresa = models.CharField(blank=True, max_length=300)
    mesaj = models.TextField(blank=True, verbose_name="Motivație / alte detalii")
    status = models.CharField(choices=STATUS_CHOICES, default="pending", max_length=30)
    data_cerere = models.DateTimeField(auto_now_add=True, verbose_name="Data cerere")
    approved_at = models.DateTimeField(blank=True, null=True, verbose_name="Data aprobare")
    finalized_at = models.DateTimeField(blank=True, null=True, verbose_name="Data finalizare")
    cancelled_at = models.DateTimeField(blank=True, null=True, verbose_name="Data anulare")
    finalized_by = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        null=True,
        blank=True,
        on_delete=models.SET_NULL,
        related_name="adoption_requests_finalized",
        verbose_name="Finalizat de (adăpost)",
    )
    validation_token = models.CharField(blank=True, null=True, unique=True, max_length=64)
    ridicare_personala = models.BooleanField(default=False, verbose_name="Ridicare personală, mă deplasez eu la locație")
    doreste_transport = models.BooleanField(default=False, verbose_name="Ridicăm noi și transportăm contra cost la client")
    doreste_cazare_medicala_toiletare = models.BooleanField(
        default=False, verbose_name="Dorește servicii medicale și toaletare (serviciu platformă)"
    )
    post_adoption_followup_sent_at = models.DateTimeField(blank=True, null=True)
    post_adoption_verification_token = models.CharField(blank=True, null=True, unique=True, max_length=64)
    queue_position = models.PositiveIntegerField(
        default=0,
        verbose_name="Poziție în coadă (1 = primul)",
        help_text="Setat la creare; 1 = primul venit.",
    )

    class Meta:
        verbose_name = "Cerere adopție"
        verbose_name_plural = "Cereri adopție"
        ordering = ["data_cerere"]
        constraints = [
            models.UniqueConstraint(
                fields=["pet", "adopter"],
                condition=Q(adopter__isnull=False) & Q(status__in=ACTIVE_DUPLICATE_CHECK_STATUSES),
                name="unique_active_adoption_request_per_pet_adopter",
            ),
            # PF: maxim o cerere per (pet, user) indiferent de status
            models.UniqueConstraint(
                fields=["pet", "adopter"],
                condition=Q(adopter__isnull=False),
                name="unique_pet_adopter_one_per_user",
            ),
        ]

    def clean(self):
        super().clean()
        if self.pet_id and self.status == REZERVAT_STATUS:
            min_pos = AdoptionRequest.objects.filter(pet_id=self.pet_id).aggregate(
                min_pos=Min("queue_position")
            )["min_pos"]
            if min_pos is not None and (self.queue_position or 0) != min_pos:
                raise ValidationError(
                    {"__all__": "Doar prima cerere poate fi rezervată."}
                )
        if not self.adopter_id or not self.pet_id:
            return
        qs = AdoptionRequest.objects.filter(
            pet_id=self.pet_id,
            adopter_id=self.adopter_id,
            status__in=ACTIVE_DUPLICATE_CHECK_STATUSES,
        )
        if self.pk:
            qs = qs.exclude(pk=self.pk)
        if qs.exists():
            raise ValidationError({"__all__": "Ai deja o cerere activă pentru acest animal."})


class PostAdoptionVerificationResponse(models.Model):
    adoption_request = models.ForeignKey(
        AdoptionRequest, on_delete=models.CASCADE, related_name="verification_responses"
    )
    data_raspuns = models.DateTimeField(auto_now_add=True, verbose_name="Data răspuns")
    mesaj = models.TextField(blank=True, verbose_name="Cum se simte animalul? Stare, comportament, orice detalii.")
    poza_1 = models.ImageField(blank=True, null=True, upload_to=post_adoption_photo_upload_to, verbose_name="Poza 1")
    poza_2 = models.ImageField(blank=True, null=True, upload_to=post_adoption_photo_upload_to, verbose_name="Poza 2")
    poza_3 = models.ImageField(blank=True, null=True, upload_to=post_adoption_photo_upload_to, verbose_name="Poza 3")

    class Meta:
        verbose_name = "Răspuns verificare post-adopție"
        verbose_name_plural = "Răspunsuri verificare post-adopție"
        ordering = ["-data_raspuns"]


class OngProfile(models.Model):
    TIP_ORGANIZATIE_CHOICES = [
        ("srl", "SRL"), ("ong", "ONG / Asociație"),
        ("pfa", "PFA (persoană fizică autorizată)"), ("af", "Asociație / Fundație"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="ong_profile"
    )
    cui = models.CharField(blank=True, max_length=20, verbose_name="CUI / CIF")
    denumire_legala = models.CharField(blank=True, max_length=200, verbose_name="Denumire")
    numar_registru = models.CharField(blank=True, max_length=80, verbose_name="Nr. registru")
    alte_date_identificare = models.CharField(blank=True, max_length=200, verbose_name="Alte date de identificare")
    email = models.EmailField(blank=True, max_length=254, verbose_name="Email contact")
    judet = models.CharField(blank=True, choices=JUDET_CHOICES, max_length=30, verbose_name="Județ")
    oras = models.CharField(blank=True, max_length=100, verbose_name="Oraș / Localitate")
    persoana_responsabila_adoptii = models.CharField(blank=True, max_length=120, verbose_name="Persoană de contact")
    reprezentant_legal = models.CharField(blank=True, max_length=120, verbose_name="Persoană de contact")
    telefon = models.CharField(blank=True, max_length=30, verbose_name="Telefon")
    tip_organizatie = models.CharField(
        choices=TIP_ORGANIZATIE_CHOICES, default="ong", max_length=10, verbose_name="Tip organizație"
    )
    # Adresă legală (sediu) – obligatorie la pagina 2 pentru categoria 2
    legal_street = models.CharField(blank=True, max_length=200, verbose_name="Stradă (sediu)")
    legal_number = models.CharField(blank=True, max_length=30, verbose_name="Nr. (sediu)")
    legal_locality = models.CharField(blank=True, max_length=120, verbose_name="Localitate (sediu)")
    legal_judet = models.CharField(blank=True, choices=JUDET_CHOICES, max_length=30, verbose_name="Județ (sediu)")
    legal_country = models.CharField(blank=True, max_length=100, default="România", verbose_name="Țară (sediu)")
    legal_postal_code = models.CharField(blank=True, max_length=20, verbose_name="Cod poștal (sediu)")
    # Adresă locație animale (pickup)
    pickup_street = models.CharField(blank=True, max_length=200, verbose_name="Stradă (locație animale)")
    pickup_number = models.CharField(blank=True, max_length=30, verbose_name="Nr. (locație animale)")
    pickup_locality = models.CharField(blank=True, max_length=120, verbose_name="Localitate (locație animale)")
    pickup_judet = models.CharField(blank=True, choices=JUDET_CHOICES, max_length=30, verbose_name="Județ (locație animale)")
    pickup_country = models.CharField(blank=True, max_length=100, default="România", verbose_name="Țară (locație animale)")
    pickup_postal_code = models.CharField(blank=True, max_length=20, verbose_name="Cod poștal (locație animale, opțional)")
    # Adăpost public – obligatoriu bifă la pagina 2 (categoria 2)
    adapost_public = models.BooleanField(
        default=False,
        verbose_name="Sunteți adăpost public?",
        help_text="Bifă obligatorie pentru organizații.",
    )

    class Meta:
        verbose_name = "Profil ONG / Adăpost"
        verbose_name_plural = "Profili ONG / Adăposturi"


ACCOUNT_TYPE_CHOICES = [
    ("individual", "Persoană fizică"),
    ("company", "Persoană juridică (SRL / Firmă)"),
    ("ngo", "Asociație / Fundație"),
]


class Profile(models.Model):
    """
    Profil unificat OneToOne cu User. account_type determină tipul contului.
    Date suplimentare în funcție de tip.
    """
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="profile"
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="individual",
    )
    # Comune / individual
    phone = models.CharField(blank=True, max_length=30, verbose_name="Telefon")
    # Company (SRL)
    company_name = models.CharField(blank=True, max_length=200, verbose_name="Denumire firmă")
    cui = models.CharField(blank=True, max_length=20, verbose_name="CUI")
    registration_number = models.CharField(blank=True, max_length=80, verbose_name="Nr. registru")
    contact_person = models.CharField(blank=True, max_length=120, verbose_name="Persoană de contact")
    # ONG
    organization_name = models.CharField(blank=True, max_length=200, verbose_name="Denumire organizație")
    legal_registration_number = models.CharField(blank=True, max_length=80, verbose_name="Nr. înregistrare")
    representative_name = models.CharField(blank=True, max_length=120, verbose_name="Reprezentant legal")
    last_informal_email_sent_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Ultima dată când am trimis emailul informal de mulțumire (la 30 zile).",
    )
    # Notificări wishlist (opt-in, anti-spam)
    email_opt_in_wishlist = models.BooleanField(
        default=False,
        verbose_name="Accept notificări email wishlist",
        help_text="Utilizatorul primește emailuri despre animalele din lista „Te plac” (reminder 72h, adopție, follow-up 30z).",
    )
    last_wishlist_email_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Ultima dată trimiterii unui email wishlist (limită 1 la 7 zile, excepție: email adopție).",
    )
    last_followup_30d_at = models.DateTimeField(
        blank=True, null=True,
        help_text="Data trimiterii emailului „Încă îți cauți prietenul perfect?” (o singură dată / per 30z).",
    )

    class Meta:
        verbose_name = "Profil"
        verbose_name_plural = "Profili"

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_account_type_display()})"


class UserProfile(models.Model):
    user = models.OneToOneField(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="user_profile"
    )
    nume = models.CharField(blank=True, max_length=80, verbose_name="Nume")
    prenume = models.CharField(blank=True, max_length=80, verbose_name="Prenume")
    telefon = models.CharField(blank=True, max_length=30, verbose_name="Telefon")
    oras = models.CharField(blank=True, max_length=120, verbose_name="Oraș / Localitate")
    judet = models.CharField(blank=True, max_length=30, choices=JUDET_CHOICES, verbose_name="Județ")
    email = models.EmailField(blank=True, max_length=254, verbose_name="Email")
    poza_1 = models.ImageField(blank=True, null=True, upload_to=user_photo_upload_to, verbose_name="Poza (opțional)")
    poza_2 = models.ImageField(blank=True, null=True, upload_to=user_photo_upload_to, verbose_name="Poza 2")
    poza_3 = models.ImageField(blank=True, null=True, upload_to=user_photo_upload_to, verbose_name="Poza 3")
    phone_verified = models.BooleanField(default=False, verbose_name="Telefon verificat prin SMS")

    class Meta:
        verbose_name = "Profil persoană fizică"
        verbose_name_plural = "Profili persoane fizice"


def contest_prize_upload_to(instance, filename):
    return f"contest_prizes/{filename}"


class Contest(models.Model):
    name = models.CharField(max_length=200, verbose_name="Nume concurs")
    start_date = models.DateTimeField(verbose_name="Data început")
    end_date = models.DateTimeField(verbose_name="Data sfârșit")
    prize_title = models.CharField(max_length=200, blank=True, verbose_name="Titlu premiu")
    prize_image = models.ImageField(blank=True, null=True, upload_to=contest_prize_upload_to, verbose_name="Imagine premiu")
    is_active = models.BooleanField(default=True, verbose_name="Activ")

    class Meta:
        verbose_name = "Concurs"
        verbose_name_plural = "Concursuri"
        ordering = ["-start_date"]

    def __str__(self):
        return self.name


class ReferralVisit(models.Model):
    ref_code = models.CharField(max_length=100, db_index=True, verbose_name="Cod referral")
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL, on_delete=models.CASCADE, related_name="referral_visits",
        verbose_name="Utilizator"
    )
    timestamp = models.DateTimeField(auto_now_add=True, db_index=True, verbose_name="Data vizită")
    ip_hash = models.CharField(max_length=64, db_index=True, verbose_name="Hash IP")
    counted = models.BooleanField(default=False, db_index=True, verbose_name="Contorizat")

    class Meta:
        verbose_name = "Vizită referral"
        verbose_name_plural = "Vizite referral"
        ordering = ["-timestamp"]
        indexes = [
            models.Index(fields=["ref_code", "ip_hash", "timestamp"]),
            models.Index(fields=["user", "counted"]),
        ]

    def __str__(self):
        return f"{self.ref_code} - {self.user.username} - {self.timestamp}"


def beneficiary_partner_logo_upload_to(instance, filename):
    return f"beneficiary_partners/{instance.id or 'new'}/{filename}"


BENEFICIARY_CATEGORY_VET = "vet"
BENEFICIARY_CATEGORY_GROOMING = "grooming"
BENEFICIARY_CATEGORY_SHOP = "shop"
BENEFICIARY_CATEGORY_CHOICES = [
    (BENEFICIARY_CATEGORY_VET, "Cabinet veterinar"),
    (BENEFICIARY_CATEGORY_GROOMING, "Grooming / frizerie"),
    (BENEFICIARY_CATEGORY_SHOP, "Magazin animale"),
]


class BeneficiaryPartner(models.Model):
    """Colaborator care oferă cupoane/reduceri adoptatorilor (după adopție finalizată)."""
    name = models.CharField(max_length=200, verbose_name="Nume colaborator")
    category = models.CharField(
        max_length=20,
        choices=BENEFICIARY_CATEGORY_CHOICES,
        db_index=True,
        verbose_name="Categorie",
    )
    county = models.CharField(max_length=30, blank=True, choices=JUDET_CHOICES, verbose_name="Județ")
    city = models.CharField(max_length=120, blank=True, verbose_name="Localitate")
    offer_text = models.CharField(
        max_length=300,
        blank=True,
        verbose_name="Text ofertă",
        help_text="Ex: -10% la pachet starter",
    )
    logo = models.ImageField(
        blank=True,
        null=True,
        upload_to=beneficiary_partner_logo_upload_to,
        verbose_name="Logo / poză",
    )
    email = models.EmailField(blank=True, max_length=254, verbose_name="Email (notificări cupon)")
    url = models.URLField(blank=True, max_length=500, verbose_name="Link site / pagină")
    is_active = models.BooleanField(default=True, verbose_name="Activ")
    order = models.PositiveSmallIntegerField(default=0, verbose_name="Ordine afișare")

    class Meta:
        verbose_name = "Partener beneficii"
        verbose_name_plural = "Parteneri beneficii"
        ordering = ["category", "order", "name"]

    def __str__(self):
        return f"{self.get_category_display()}: {self.name}"


COUPON_CLAIM_STATUS_SELECTED = "SELECTED"
COUPON_CLAIM_STATUS_CHOICES = [
    (COUPON_CLAIM_STATUS_SELECTED, "Selectat"),
]


class CouponClaim(models.Model):
    """Alegere cupon de către adoptator (max 1 per categorie)."""
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="coupon_claims",
        verbose_name="Adoptator",
    )
    partner = models.ForeignKey(
        BeneficiaryPartner,
        on_delete=models.CASCADE,
        related_name="claims",
        verbose_name="Partener",
    )
    category = models.CharField(
        max_length=20,
        choices=BENEFICIARY_CATEGORY_CHOICES,
        db_index=True,
        verbose_name="Categorie",
    )
    status = models.CharField(
        max_length=20,
        choices=COUPON_CLAIM_STATUS_CHOICES,
        default=COUPON_CLAIM_STATUS_SELECTED,
    )
    created_at = models.DateTimeField(auto_now_add=True, verbose_name="Data alegere")
    # Opțional: legătură la cererea de adopție finalizată (dacă există)
    adoption_request = models.ForeignKey(
        AdoptionRequest,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="coupon_claims",
        verbose_name="Cerere adopție (opțional)",
    )

    class Meta:
        verbose_name = "Alegere cupon"
        verbose_name_plural = "Alegeri cupoane"
        ordering = ["-created_at"]
        constraints = [
            models.UniqueConstraint(
                fields=["user", "category"],
                name="unique_coupon_claim_per_user_category",
            ),
        ]

    def __str__(self):
        return f"{self.user_id} - {self.get_category_display()} - {self.partner.name}"
