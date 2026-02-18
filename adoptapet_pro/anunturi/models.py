"""
Modele pentru platforma Adopt a Pet.
Reconstruite din migrații pentru pets_single și adopții.
"""
import os
from django.db import models
from django.conf import settings

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


class Pet(models.Model):
    TIP_CHOICES = [("dog", "Câine"), ("cat", "Pisică"), ("other", "Altele")]
    VARSTA_CHOICES = [("baby", "Baby"), ("young", "Young"), ("adult", "Adult")]
    SEX_CHOICES = [("male", "Male"), ("female", "Female")]
    MARIME_CHOICES = [("small", "Small"), ("medium", "Medium"), ("large", "Large"), ("xlarge", "Extra Large")]
    STATUS_CHOICES = [
        ("adoptable", "Adoptable"), 
        ("pending", "Adoption Pending"), 
        ("adopted", "Adopted"),
        ("showcase_archive", "Showcase Archive")  # Visual buffer, not adoptable, not searchable
    ]
    JUDET_CHOICES = JUDET_CHOICES

    nume = models.CharField(max_length=100)
    slug = models.SlugField(max_length=120, unique=True)
    rasa = models.CharField(max_length=100)
    tip = models.CharField(choices=TIP_CHOICES, default="dog", max_length=10)
    tip_altele = models.CharField(blank=True, max_length=20, choices=[
        ("bird", "Pasăre"), ("donkey", "Magar"), ("rabbit", "Iepure"),
        ("hamster", "Hamster"), ("guinea_pig", "Cobai"), ("other", "Altul (completați mai jos)"),
    ])
    tip_altele_altul = models.CharField(blank=True, max_length=80)
    varsta = models.CharField(choices=VARSTA_CHOICES, max_length=10)
    sex = models.CharField(choices=SEX_CHOICES, max_length=10)
    marime = models.CharField(blank=True, choices=MARIME_CHOICES, max_length=10)
    descriere = models.TextField(blank=True)
    imagine = models.ImageField(blank=True, null=True, upload_to="pets/")
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
    featured = models.BooleanField(default=False, verbose_name="Animale lunii / VIP")
    added_by_user = models.ForeignKey(
        settings.AUTH_USER_MODEL, blank=True, null=True, on_delete=models.SET_NULL,
        related_name="pets_added", help_text="Setat când anunțul e adăugat de o persoană fizică."
    )

    class Meta:
        verbose_name = "Animal"
        verbose_name_plural = "Animale"
        ordering = ["-data_adaugare"]


class AdoptionRequest(models.Model):
    STATUS_CHOICES = [
        ("new", "Nouă"),
        ("approved_platform", "Aprobată de platformă (trimisă la ONG)"),
        ("approved_ong", "Validată de ONG"),
        ("rejected", "Refuzată"),
    ]

    pet = models.ForeignKey(Pet, on_delete=models.CASCADE, related_name="adoption_requests")
    nume_complet = models.CharField(max_length=200, verbose_name="Nume complet")
    email = models.EmailField(max_length=254)
    telefon = models.CharField(max_length=30)
    adresa = models.CharField(blank=True, max_length=300)
    mesaj = models.TextField(blank=True, verbose_name="Motivație / alte detalii")
    status = models.CharField(choices=STATUS_CHOICES, default="new", max_length=30)
    data_cerere = models.DateTimeField(auto_now_add=True)
    validation_token = models.CharField(blank=True, null=True, unique=True, max_length=64)
    ridicare_personala = models.BooleanField(default=False, verbose_name="Ridicare personală, mă deplasez eu la locație")
    doreste_transport = models.BooleanField(default=False, verbose_name="Ridicăm noi și transportăm contra cost la client")
    doreste_cazare_medicala_toiletare = models.BooleanField(
        default=False, verbose_name="Dorește servicii medicale și toaletare (serviciu platformă)"
    )
    post_adoption_followup_sent_at = models.DateTimeField(blank=True, null=True)
    post_adoption_verification_token = models.CharField(blank=True, null=True, unique=True, max_length=64)

    class Meta:
        verbose_name = "Cerere adopție"
        verbose_name_plural = "Cereri adopție"
        ordering = ["-data_cerere"]


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
    email = models.EmailField(blank=True, max_length=254, verbose_name="Email")
    poza_1 = models.ImageField(blank=True, null=True, upload_to=user_photo_upload_to, verbose_name="Poza 1")
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
