import re
from typing import Optional

from django.db import models
from django.contrib.auth.models import User
from django.core.exceptions import ValidationError
from django.core.validators import FileExtensionValidator
from django.db.models.signals import post_save
from django.dispatch import receiver
from django.utils import timezone


class UserProfile(models.Model):
    """
    Profil extensie pentru User (persoană fizică).
    Datele din formularul de înregistrare PF: telefon, oraș, poză, acorduri.
    Poză: salvată permanent în profiles/ (MEDIA_ROOT).
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Telefon", max_length=20, blank=True)
    judet = models.CharField("Județ", max_length=120, blank=True)
    oras = models.CharField("Oraș / Localitate", max_length=120, blank=True)
    # Date firmă / colaborator (ONG / SRL / Colaborator servicii-produse)
    company_display_name = models.CharField("Denumire afișată", max_length=255, blank=True)
    company_legal_name = models.CharField("Denumire societate", max_length=255, blank=True)
    company_cui = models.CharField("CUI/CIF", max_length=32, blank=True)
    company_cui_has_ro = models.BooleanField("CUI cu RO", default=False)
    company_address = models.CharField("Adresă firmă", max_length=255, blank=True)
    company_judet = models.CharField("Județ firmă", max_length=120, blank=True)
    company_oras = models.CharField("Oraș firmă", max_length=120, blank=True)
    collaborator_type = models.CharField("Tip colaborator", max_length=20, blank=True)  # cabinet/servicii/magazin
    poza_1 = models.ImageField(
        "Poză profil",
        upload_to="profiles/",
        blank=True,
        null=True,
    )
    accept_termeni = models.BooleanField(
        "Accept termenii și condițiile",
        default=False,
    )
    accept_gdpr = models.BooleanField("Accept GDPR", default=False)
    email_opt_in_wishlist = models.BooleanField(
        "Notificări email wishlist",
        default=False,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil utilizator"
        verbose_name_plural = "Profile utilizatori"

    def __str__(self):
        return self.user.get_full_name() or self.user.username


class UserLegalConsent(models.Model):
    """Audit trail pentru accepturile legale (T&C, GDPR, marketing)."""

    CONSENT_TERMS = "terms"
    CONSENT_PRIVACY = "privacy"
    CONSENT_MARKETING = "marketing"
    CONSENT_CHOICES = [
        (CONSENT_TERMS, "Termeni și condiții"),
        (CONSENT_PRIVACY, "Politica de confidențialitate"),
        (CONSENT_MARKETING, "Marketing / noutăți"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="legal_consents")
    consent_type = models.CharField("Tip consimțământ", max_length=20, choices=CONSENT_CHOICES)
    accepted = models.BooleanField("Acceptat", default=False)
    version = models.CharField("Versiune document", max_length=20, default="1.0")
    source = models.CharField("Sursă acțiune", max_length=50, blank=True, default="")
    ip_address = models.CharField("IP", max_length=64, blank=True, default="")
    user_agent = models.CharField("User-Agent", max_length=500, blank=True, default="")
    created_at = models.DateTimeField("Înregistrat la", auto_now_add=True)

    class Meta:
        verbose_name = "Consimțământ legal utilizator"
        verbose_name_plural = "Consimțăminte legale utilizatori"
        indexes = [
            models.Index(fields=["user", "consent_type", "created_at"]),
            models.Index(fields=["created_at"]),
        ]

    def __str__(self):
        state = "da" if self.accepted else "nu"
        return f"{self.user_id}:{self.consent_type}:{state}@{self.version}"


class ContactMessage(models.Model):
    """Mesaj trimis din pagina Contact."""

    TOPIC_GENERAL = "general"
    TOPIC_GDPR = "gdpr"
    TOPIC_COMMERCIAL = "commercial"
    TOPIC_MODERATION = "moderation"
    TOPIC_CHOICES = [
        (TOPIC_GENERAL, "Suport general"),
        (TOPIC_GDPR, "Date personale (GDPR)"),
        (TOPIC_COMMERCIAL, "Publicitate / servicii plătite"),
        (TOPIC_MODERATION, "Moderare / raportări"),
    ]

    user = models.ForeignKey(User, on_delete=models.SET_NULL, null=True, blank=True, related_name="contact_messages")
    full_name = models.CharField("Nume", max_length=120)
    email = models.EmailField("E-mail")
    phone = models.CharField("Telefon", max_length=40, blank=True, default="")
    topic = models.CharField("Tip solicitare", max_length=20, choices=TOPIC_CHOICES, default=TOPIC_GENERAL)
    subject = models.CharField("Subiect", max_length=180)
    message = models.TextField("Mesaj", max_length=3000)
    attachment = models.FileField("Fișier atașat", upload_to="contact_attachments/", blank=True, null=True)
    accepted_privacy = models.BooleanField("Acord confidențialitate", default=False)
    ip_address = models.CharField("IP", max_length=64, blank=True, default="")
    user_agent = models.CharField("User-Agent", max_length=500, blank=True, default="")
    created_at = models.DateTimeField("Trimis la", auto_now_add=True)

    class Meta:
        verbose_name = "Mesaj Contact"
        verbose_name_plural = "Mesaje Contact"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["topic", "created_at"]),
            models.Index(fields=["email", "created_at"]),
        ]

    def __str__(self):
        return f"{self.email} [{self.topic}] {self.subject[:40]}"


class AccountProfile(models.Model):
    """
    Profil comun pentru toți userii (PF / ONG+SRL / Colaborator).
    Folosit pentru roluri + reguli UI.
    """

    ROLE_PF = "pf"
    ROLE_ORG = "org"
    ROLE_COLLAB = "collaborator"

    ROLE_CHOICES = [
        (ROLE_PF, "Persoană fizică"),
        (ROLE_ORG, "ONG / Adăpost / Firmă"),
        (ROLE_COLLAB, "Colaborator (servicii / produse)"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="account_profile",
    )
    role = models.CharField("Rol cont", max_length=20, choices=ROLE_CHOICES, default=ROLE_PF)
    is_public_shelter = models.BooleanField("Adăpost public", default=False)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil cont (rol)"
        verbose_name_plural = "Profile cont (roluri)"

    def __str__(self):
        return f"{self.user.username} ({self.role})"

    @property
    def can_post_animals(self) -> bool:
        return self.role in {self.ROLE_PF, self.ROLE_ORG}

    @property
    def can_adopt_animals(self) -> bool:
        if self.role == self.ROLE_PF:
            return True
        if self.role == self.ROLE_ORG:
            # Adăpost public: poate publica spre adopție, nu poate adopta.
            return not bool(self.is_public_shelter)
        return False

    @property
    def can_post_services(self) -> bool:
        return self.role == self.ROLE_COLLAB


class AnimalListing(models.Model):
    """
    Anunț/postare animal (bază pentru MyPet).

    Regula PF: max 3 animale postate pe lună calendaristică.
    (ONG/Org nu are limită aici; limitele se pot adăuga ulterior.)
    """

    SPECIES_CHOICES = [
        ("dog", "Câine"),
        ("cat", "Pisică"),
        ("other", "Alt"),
    ]
    ADOPTION_STATE_FREE = "liber"
    ADOPTION_STATE_OPEN = "spre_adoptie"
    ADOPTION_STATE_IN_PROGRESS = "in_curs_adoptie"
    ADOPTION_STATE_ADOPTED = "adoptat"
    ADOPTION_STATE_CHOICES = [
        (ADOPTION_STATE_FREE, "Liber"),
        (ADOPTION_STATE_OPEN, "Spre adopție"),
        (ADOPTION_STATE_IN_PROGRESS, "În curs de adopție"),
        (ADOPTION_STATE_ADOPTED, "Adoptat"),
    ]

    owner = models.ForeignKey(User, on_delete=models.CASCADE, related_name="animal_listings")
    name = models.CharField("Nume", max_length=120, blank=True)
    species = models.CharField("Specie", max_length=20, choices=SPECIES_CHOICES, default="dog")
    size = models.CharField("Talie", max_length=20, blank=True)
    age_label = models.CharField("Vârstă (eticheta)", max_length=20, blank=True)
    city = models.CharField("Oraș / Localitate", max_length=120, blank=True)
    county = models.CharField("Județ", max_length=120, blank=True)

    # Poze (cale în DB, fișierul în MEDIA; la lansare putem folosi Cloudinary)
    photo_1 = models.ImageField("Poza 1", upload_to="animals/", blank=True, null=True)
    photo_2 = models.ImageField("Poza 2", upload_to="animals/", blank=True, null=True)
    photo_3 = models.ImageField("Poza 3", upload_to="animals/", blank=True, null=True)
    video = models.FileField("Video", upload_to="animals/videos/", blank=True, null=True)

    # Date suplimentare din fișă
    color = models.CharField("Culoare", max_length=80, blank=True)
    sterilizat = models.CharField("Sterilizat", max_length=10, blank=True)
    vaccinat = models.CharField("Vaccinat", max_length=10, blank=True)
    carnet_sanatate = models.CharField("Carnet sănătate", max_length=10, blank=True)
    cip = models.CharField("CIP", max_length=10, blank=True)
    sex = models.CharField("Sex", max_length=10, blank=True)
    greutate_aprox = models.CharField("Greutate (aprox.)", max_length=30, blank=True)
    probleme_medicale = models.TextField("Probleme medicale", blank=True)
    cine_sunt = models.TextField("Cine sunt și de unde sunt", blank=True)
    detalii_animal = models.TextField(
        "Detalii despre animal",
        blank=True,
        default="",
        help_text="Comportament, obiceiuri, ce îi place — vizibil adoptatorilor pe fișă.",
    )

    # Trăsături potrivire adoptator (15 bife)
    trait_jucaus = models.BooleanField("Jucăuș", default=False)
    trait_iubitor = models.BooleanField("Iubitor", default=False)
    trait_protector = models.BooleanField("Protector", default=False)
    trait_energic = models.BooleanField("Energetic", default=False)
    trait_linistit = models.BooleanField("Liniștit", default=False)
    trait_bun_copii = models.BooleanField("Bun cu copii", default=False)
    trait_bun_caini = models.BooleanField("Bun cu alți câini", default=False)
    trait_bun_pisici = models.BooleanField("Bun cu pisici", default=False)
    trait_obisnuit_casa = models.BooleanField("Obișnuit în casă", default=False)
    trait_obisnuit_lesa = models.BooleanField("Obișnuit cu lesa", default=False)
    trait_nu_latla = models.BooleanField("Nu latră excesiv", default=False)
    trait_apartament = models.BooleanField("Potrivit pentru apartament", default=False)
    trait_se_adapteaza = models.BooleanField("Se adaptează ușor", default=False)
    trait_tolereaza_singur = models.BooleanField("Tolerează să stea singur", default=False)
    trait_necesita_experienta = models.BooleanField("Necesită experiență cu câini", default=False)

    is_published = models.BooleanField("Publicat", default=True)
    adoption_state = models.CharField(
        "Stare adopție",
        max_length=20,
        choices=ADOPTION_STATE_CHOICES,
        default=ADOPTION_STATE_FREE,
        db_index=True,
    )
    media_views = models.IntegerField("Vizualizări media (click pe poză/video)", default=0)
    share_clicks = models.IntegerField("Distribuiri (click pe buton)", default=0)
    observatii = models.TextField("Observații (MyPet)", blank=True, default="")
    created_at = models.DateTimeField("Creat la", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)

    class Meta:
        verbose_name = "Anunț animal"
        verbose_name_plural = "Anunțuri animale"
        ordering = ["-created_at"]

    def __str__(self):
        return self.name or f"Animal #{self.pk}"

    @staticmethod
    def _month_bounds(dt):
        start = dt.replace(day=1, hour=0, minute=0, second=0, microsecond=0)
        if start.month == 12:
            end = start.replace(year=start.year + 1, month=1)
        else:
            end = start.replace(month=start.month + 1)
        return start, end

    def clean(self):
        super().clean()
        # Aplicăm limita doar la crearea unui anunț nou.
        if self.pk:
            return

        role = None
        try:
            role = self.owner.account_profile.role
        except Exception:
            role = None

        if role != AccountProfile.ROLE_PF:
            return

        now = timezone.now()
        start, end = self._month_bounds(now)
        posted_this_month = AnimalListing.objects.filter(owner=self.owner, created_at__gte=start, created_at__lt=end).count()
        limit = 3
        if posted_this_month >= limit:
            raise ValidationError(f"Limită PF: maxim {limit} animale postate pe lună.")

    def save(self, *args, **kwargs):
        # Asigurăm că regula se aplică și dacă cineva salvează din cod/admin fără form validation.
        self.full_clean()
        return super().save(*args, **kwargs)


class WishlistItem(models.Model):
    """
    Wishlist / I Love: inimioara pentru un animal.
    Pentru moment folosim animal_id (ID-ul demo) – ulterior se poate lega direct la AnimalListing.
    """

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="wishlist_items")
    animal_id = models.IntegerField("ID animal")
    created_at = models.DateTimeField("Adăugat la", auto_now_add=True)

    class Meta:
        verbose_name = "Wishlist item"
        verbose_name_plural = "Wishlist items"
        unique_together = [("user", "animal_id")]
        indexes = [
            models.Index(fields=["animal_id"]),
            models.Index(fields=["user", "created_at"]),
        ]

    def __str__(self):
        return f"{self.user} ♥ {self.animal_id}"


@receiver(post_save, sender=User)
def ensure_account_profile(sender, instance: User, created: bool, **kwargs):
    """
    Creează automat un AccountProfile pentru orice user.
    Default: PF (până când signup ONG/Colaborator devine backend real și setează rolul).
    """
    if created:
        AccountProfile.objects.get_or_create(user=instance)


class UserAdoption(models.Model):
    """
    Înregistrare adopție făcută de un utilizator.
    Deocamdată legăm de un ID numeric de animal (din sistemul existent).
    """
    STATUS_CHOICES = [
        ("pending", "În așteptare"),
        ("approved", "Aprobată"),
        ("completed", "Finalizată"),
        ("cancelled", "Anulată"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="adoptii")
    animal_id = models.IntegerField("ID animal", blank=True, null=True)
    animal_name = models.CharField("Nume animal", max_length=120, blank=True)
    animal_type = models.CharField("Tip animal", max_length=40, blank=True)
    source = models.CharField(
        "Sursă",
        max_length=40,
        blank=True,
        help_text="Ex: PT, CUSTI, SHOP, alte surse interne",
    )
    status = models.CharField(
        "Stare adopție",
        max_length=20,
        choices=STATUS_CHOICES,
        default="pending",
    )
    requested_at = models.DateTimeField("Cerere făcută la", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)

    class Meta:
        verbose_name = "Adopție utilizator"
        verbose_name_plural = "Adopții utilizatori"
        ordering = ["-requested_at"]

    def __str__(self):
        if self.animal_name:
            return f"{self.user} → {self.animal_name} ({self.status})"
        return f"{self.user} → adopție ({self.status})"


class UserPost(models.Model):
    """
    Postare creată de utilizator: anunț, cerere adopție, donație, servicii etc.
    UI se va decide mai târziu; modelul e gata.
    """
    POST_TYPES = [
        ("adoption_request", "Cerere adopție"),
        ("adoption_story", "Poveste adopție"),
        ("donation", "Donație / campanie"),
        ("service", "Serviciu / colaborator"),
        ("other", "Alt tip"),
    ]

    user = models.ForeignKey(User, on_delete=models.CASCADE, related_name="postari")
    post_type = models.CharField(
        "Tip postare",
        max_length=40,
        choices=POST_TYPES,
        default="other",
    )
    title = models.CharField("Titlu", max_length=200)
    body = models.TextField("Conținut", blank=True)
    is_published = models.BooleanField("Publicat", default=False)
    created_at = models.DateTimeField("Creat la", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)

    class Meta:
        verbose_name = "Postare utilizator"
        verbose_name_plural = "Postări utilizatori"
        ordering = ["-created_at"]

    def __str__(self):
        return self.title


class PetMessage(models.Model):
    """
    Mesaje despre **animal / adopție** (MyPet, fișă publică).

    Folosit de **PF** și **ONG/SRL** (proprietar anunț sau adoptator).
    Nu folosi acest model pentru discuții despre servicii sau produse colaborator —
    pentru acelea vezi `CollabServiceMessage`.
    """
    animal = models.ForeignKey(AnimalListing, on_delete=models.CASCADE, related_name="messages")
    sender = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pet_messages_sent")
    receiver = models.ForeignKey(User, on_delete=models.CASCADE, related_name="pet_messages_received")
    body = models.TextField("Mesaj", max_length=2000)
    is_read = models.BooleanField("Citit", default=False)
    created_at = models.DateTimeField("Creat la", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)

    class Meta:
        verbose_name = "Mesaj pet"
        verbose_name_plural = "Mesaje pet"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["animal", "created_at"]),
            models.Index(fields=["receiver", "is_read", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender} -> {self.receiver} ({self.animal_id})"


class CollabServiceMessage(models.Model):
    """
    Mesaje despre **servicii / produse / magazin colaborator** (nu despre animale).

    Colaboratorul este partea care oferă serviciul sau produsul; celălalt user
    (PF, ONG sau orice client) poartă discuția în acest flux.
    Pentru adopție și fișă animal folosește `PetMessage`.
    """

    CONTEXT_SERVICII = "servicii"
    CONTEXT_SHOP = "shop"
    CONTEXT_MAGAZIN = "magazin"
    CONTEXT_CABINET = "cabinet"
    CONTEXT_GENERAL = "general"

    CONTEXT_CHOICES = [
        (CONTEXT_SERVICII, "Servicii"),
        (CONTEXT_SHOP, "Shop"),
        (CONTEXT_MAGAZIN, "Magazin colaborator"),
        (CONTEXT_CABINET, "Cabinet"),
        (CONTEXT_GENERAL, "General"),
    ]

    collaborator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="collab_service_messages_as_collaborator",
        help_text="Colaboratorul (ofertant).",
    )
    context_type = models.CharField(
        "Context",
        max_length=24,
        choices=CONTEXT_CHOICES,
        default=CONTEXT_GENERAL,
    )
    context_ref = models.CharField(
        "Referință ofertă",
        max_length=120,
        blank=True,
        help_text="Opțional: ID/slug când există anunț de serviciu sau produs.",
    )
    sender = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="collab_service_messages_sent",
    )
    receiver = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="collab_service_messages_received",
    )
    body = models.TextField("Mesaj", max_length=2000)
    is_read = models.BooleanField("Citit", default=False)
    created_at = models.DateTimeField("Creat la", auto_now_add=True)
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)

    class Meta:
        verbose_name = "Mesaj servicii / produs"
        verbose_name_plural = "Mesaje servicii / produse"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["collaborator", "created_at"]),
            models.Index(fields=["collaborator", "context_type", "context_ref", "created_at"]),
            models.Index(fields=["receiver", "is_read", "created_at"]),
            models.Index(fields=["sender", "created_at"]),
        ]

    def __str__(self):
        return f"{self.sender_id} → {self.receiver_id} (collab={self.collaborator_id}, {self.context_type})"


class AdoptionRequest(models.Model):
    """
    Cerere de adopție: PF apasă „Vreau să adopt”; owner acceptă în MyPet.
    Datele de contact (PII) se trimit pe email doar după accept.
    """

    STATUS_PENDING = "in_asteptare"
    STATUS_ACCEPTED = "acceptata"
    STATUS_REJECTED = "respinsa"
    STATUS_EXPIRED = "expirata_neconfirmata"
    STATUS_FINALIZED = "finalizata"

    STATUS_CHOICES = [
        (STATUS_PENDING, "În așteptare (owner)"),
        (STATUS_ACCEPTED, "Acceptată"),
        (STATUS_REJECTED, "Respinsă"),
        (STATUS_EXPIRED, "Expirată neconfirmată"),
        (STATUS_FINALIZED, "Adopție finalizată"),
    ]

    animal = models.ForeignKey(
        AnimalListing,
        on_delete=models.CASCADE,
        related_name="adoption_requests",
    )
    adopter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="adoption_requests_sent",
    )
    status = models.CharField(
        "Stare",
        max_length=32,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
    )
    accepted_at = models.DateTimeField("Acceptată la", null=True, blank=True)
    accepted_expires_at = models.DateTimeField("Acceptare valabilă până la", null=True, blank=True)
    extension_count = models.PositiveSmallIntegerField("Număr prelungiri", default=0)
    finalized_at = models.DateTimeField("Adopție finalizată la", null=True, blank=True)
    goodwill_email_sent_at = models.DateTimeField("Mail bun venit +15 zile trimis la", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Cerere adopție"
        verbose_name_plural = "Cereri adopție"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["animal", "status"]),
            models.Index(fields=["adopter", "status"]),
            models.Index(fields=["status", "goodwill_email_sent_at"]),
            models.Index(fields=["status", "finalized_at"]),
        ]

    def __str__(self):
        return f"Adopt #{self.pk} pet={self.animal_id} de {self.adopter_id} → {self.status}"


class CollaboratorServiceOffer(models.Model):
    """
    Ofertă simplă postată de colaborator (cabinet / servicii): imagine, titlu, scurtă descriere,
    preț opțional și/sau discount %. Publică pe /oferte-parteneri/; vizitatorul poate
    cere pe email datele de contact ale cabinetului (fără programări în platformă).

    partner_kind = canal la creare (snapshot): S3 cabinet / S5 servicii / S4 magazin în pagina Servicii.
    Nu depinde de bifa curentă din profil după salvare — ofertele nu se amestecă între canale.
    """

    PARTNER_KIND_CABINET = "cabinet"
    PARTNER_KIND_SERVICII = "servicii"
    PARTNER_KIND_MAGAZIN = "magazin"
    PARTNER_KIND_CHOICES = [
        (PARTNER_KIND_CABINET, "Cabinet / clinică veterinară"),
        (PARTNER_KIND_SERVICII, "Servicii / grooming / dresaj"),
        (PARTNER_KIND_MAGAZIN, "Magazin / pet-shop"),
    ]

    # Filtrare țintă (setată de furnizor; recomandări orientative pentru adoptatori)
    TARGET_SPECIES_ALL = "all"
    TARGET_SPECIES_DOG = "dog"
    TARGET_SPECIES_CAT = "cat"
    TARGET_SPECIES_CHOICES = [
        (TARGET_SPECIES_ALL, "Câine sau pisică (oricare)"),
        (TARGET_SPECIES_DOG, "Câine"),
        (TARGET_SPECIES_CAT, "Pisică"),
    ]
    TARGET_SIZE_ALL = "all"
    TARGET_SIZE_SMALL = "small"
    TARGET_SIZE_MEDIUM = "medium"
    TARGET_SIZE_LARGE = "large"
    TARGET_SIZE_CHOICES = [
        (TARGET_SIZE_ALL, "Oricare talie"),
        (TARGET_SIZE_SMALL, "Talie mică"),
        (TARGET_SIZE_MEDIUM, "Talie medie"),
        (TARGET_SIZE_LARGE, "Talie mare"),
    ]
    TARGET_SEX_ALL = "all"
    TARGET_SEX_MALE = "male"
    TARGET_SEX_FEMALE = "female"
    TARGET_SEX_CHOICES = [
        (TARGET_SEX_ALL, "Oricare sex"),
        (TARGET_SEX_MALE, "Mascul"),
        (TARGET_SEX_FEMALE, "Femelă"),
    ]
    TARGET_AGE_ALL = "all"
    TARGET_AGE_PUPPY = "puppy"
    TARGET_AGE_YOUNG = "young"
    TARGET_AGE_ADULT = "adult"
    TARGET_AGE_SENIOR = "senior"
    TARGET_AGE_CHOICES = [
        (TARGET_AGE_ALL, "Oricare vârstă"),
        (TARGET_AGE_PUPPY, "Pui"),
        (TARGET_AGE_YOUNG, "Tânăr"),
        (TARGET_AGE_ADULT, "Adult"),
        (TARGET_AGE_SENIOR, "Senior"),
    ]
    TARGET_STERIL_ALL = "all"
    TARGET_STERIL_YES = "yes"
    TARGET_STERIL_NO = "no"
    TARGET_STERIL_CHOICES = [
        (TARGET_STERIL_ALL, "Oricare"),
        (TARGET_STERIL_YES, "Sterilizat / castrat"),
        (TARGET_STERIL_NO, "Nesterilizat"),
    ]

    collaborator = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="service_offers",
    )
    partner_kind = models.CharField(
        "Canal partener (la creare)",
        max_length=20,
        choices=PARTNER_KIND_CHOICES,
        default=PARTNER_KIND_CABINET,
        db_index=True,
        help_text="Setat la publicare; determină zona Servicii. Nu se schimbă cu bifa din cont.",
    )
    title = models.CharField("Titlu serviciu", max_length=160)
    description = models.CharField("Scurtă descriere produs", max_length=500, blank=True)
    image = models.ImageField("Imagine", upload_to="collab_offers/")
    external_url = models.URLField(
        "Link produs (extern)",
        max_length=500,
        blank=True,
        help_text="Opțional pentru servicii/cabinet; recomandat/obligatoriu la magazin (http/https).",
    )
    product_sheet = models.FileField(
        "Fișă tehnică produs",
        upload_to="collab_offer_sheets/",
        blank=True,
        validators=[FileExtensionValidator(allowed_extensions=["pdf", "doc", "docx"])],
        help_text="Opțional, recomandat la magazin (PDF/DOC/DOCX).",
    )
    target_species = models.CharField(
        "Țintă: specie",
        max_length=12,
        choices=TARGET_SPECIES_CHOICES,
        default=TARGET_SPECIES_ALL,
        db_index=True,
    )
    target_size = models.CharField(
        "Țintă: talie (în special câine)",
        max_length=12,
        choices=TARGET_SIZE_CHOICES,
        default=TARGET_SIZE_ALL,
    )
    target_sex = models.CharField(
        "Țintă: sex",
        max_length=12,
        choices=TARGET_SEX_CHOICES,
        default=TARGET_SEX_ALL,
    )
    target_age_band = models.CharField(
        "Țintă: categorie vârstă",
        max_length=12,
        choices=TARGET_AGE_CHOICES,
        default=TARGET_AGE_ALL,
    )
    target_sterilized = models.CharField(
        "Țintă: sterilizare",
        max_length=12,
        choices=TARGET_STERIL_CHOICES,
        default=TARGET_STERIL_ALL,
    )
    species_dog = models.BooleanField("Specie: câine", default=True)
    species_cat = models.BooleanField("Specie: pisică", default=True)
    species_other = models.BooleanField("Specie: altele", default=True)
    price_hint = models.CharField("Preț (text scurt)", max_length=80, blank=True)
    discount_percent = models.PositiveSmallIntegerField(
        "Reducere %",
        null=True,
        blank=True,
        help_text="Opțional, 1–100 (ex. 25 pentru 25%).",
    )
    quantity_available = models.PositiveIntegerField(
        "Număr oferte valabile",
        null=True,
        blank=True,
        help_text="Opțional: câte oferte/locuri sunt disponibile (ex. 10).",
    )
    valid_from = models.DateField(
        "Valabilă de la",
        null=True,
        blank=True,
        help_text="Prima zi în care oferta e valabilă (calendar România).",
    )
    valid_until = models.DateField(
        "Valabilă până la",
        null=True,
        blank=True,
        help_text="Ultima zi de valabilitate (inclusiv).",
    )
    is_active = models.BooleanField("Activă pe site", default=True)
    # Notificări email (max. 1 / tip / perioadă stoc sau / perioadă valabilitate; se resetează la edit)
    expiry_notice_sent_for_valid_until = models.DateField(
        "Reminder expirare trimis pentru data sfârșit",
        null=True,
        blank=True,
        help_text="Dacă e setat la aceeași valoare ca valid_until, nu mai trimitem iar mailul T−5 zile.",
    )
    low_stock_notice_sent = models.BooleanField(
        "Reminder stoc 1 rămas trimis",
        default=False,
        help_text="True după mailul „mai ai 1 ofertă”; se resetează la creșterea stocului în fișă.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Ofertă colaborator"
        verbose_name_plural = "Oferte colaboratori"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["collaborator", "is_active", "created_at"]),
            models.Index(fields=["is_active", "valid_until"]),
            models.Index(fields=["partner_kind", "is_active", "created_at"]),
        ]

    def __str__(self):
        return f"{self.title} ({self.collaborator_id})"

    def partner_display_name(self) -> str:
        try:
            p = self.collaborator.profile
            return (p.company_display_name or "").strip() or self.collaborator.username
        except UserProfile.DoesNotExist:
            return self.collaborator.username

    @property
    def shows_product_targeting(self) -> bool:
        """Potrivire animal / link produs relevante doar pentru canalul magazin."""
        return self.partner_kind == self.PARTNER_KIND_MAGAZIN

    @property
    def has_any_species_selected(self) -> bool:
        return bool(self.species_dog or self.species_cat or self.species_other)

    @property
    def target_filters_are_defaults(self) -> bool:
        return (
            self.target_species == self.TARGET_SPECIES_ALL
            and self.target_size == self.TARGET_SIZE_ALL
            and self.target_sex == self.TARGET_SEX_ALL
            and self.target_age_band == self.TARGET_AGE_ALL
            and self.target_sterilized == self.TARGET_STERIL_ALL
        )

    @property
    def target_filter_tag_list(self) -> list[str]:
        """Etichete scurte pentru listă/tabel (doar criterii nerestânse la „oricare”)."""
        if not self.shows_product_targeting:
            return []
        tags: list[str] = []
        if self.target_species != self.TARGET_SPECIES_ALL:
            tags.append(self.get_target_species_display())
        if self.target_size != self.TARGET_SIZE_ALL:
            tags.append(self.get_target_size_display())
        if self.target_sex != self.TARGET_SEX_ALL:
            tags.append(self.get_target_sex_display())
        if self.target_age_band != self.TARGET_AGE_ALL:
            tags.append(self.get_target_age_band_display())
        if self.target_sterilized != self.TARGET_STERIL_ALL:
            tags.append(self.get_target_sterilized_display())
        return tags

    def price_numeric_from_hint(self) -> float | None:
        """Extrage primul număr din `price_hint` (ex. «100 lei», «350,50»)."""
        if not (self.price_hint or "").strip():
            return None
        t = self.price_hint.strip().replace("\u00a0", " ").replace(" ", "")
        m = re.search(r"(\d+(?:[.,]\d+)?)", t)
        if not m:
            return None
        raw = m.group(1)
        if raw.count(".") > 1:
            raw = raw.replace(".", "")
        raw = raw.replace(",", ".")
        try:
            v = float(raw)
            return v if v >= 0 else None
        except ValueError:
            return None

    @property
    def price_after_discount_display(self) -> str | None:
        """Preț final estimativ (text), dacă există preț numeric și discount 1–100%."""
        base = self.price_numeric_from_hint()
        if base is None:
            return None
        d = self.discount_percent
        if d is None or d < 1 or d > 100:
            return None
        final = base * (1.0 - float(d) / 100.0)
        if final < 0:
            return None
        if abs(final - round(final)) < 1e-6:
            return f"{int(round(final))} lei"
        s = f"{final:.2f}".replace(".", ",").rstrip("0").rstrip(",")
        return f"{s} lei"


class AdoptionBonusSelection(models.Model):
    """
    Oferte partener alese cu inimioara în timpul unui demers de adopție (max 1 / partner_kind).
    La adopție finalizată: cod comun + mail adoptator + mail colaborator.
    """

    adoption_request = models.ForeignKey(
        AdoptionRequest,
        on_delete=models.CASCADE,
        related_name="bonus_selections",
    )
    offer = models.ForeignKey(
        CollaboratorServiceOffer,
        on_delete=models.CASCADE,
        related_name="adoption_bonus_selections",
    )
    partner_kind = models.CharField(
        "Canal ofertă (snapshot)",
        max_length=20,
        choices=CollaboratorServiceOffer.PARTNER_KIND_CHOICES,
    )
    redemption_code = models.CharField("Cod identificare", max_length=40, blank=True, default="")
    bonus_emails_sent_at = models.DateTimeField("Mailuri bonus trimise la", null=True, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Selecție bonus adopție (ofertă)"
        verbose_name_plural = "Selecții bonus adopție"
        constraints = [
            models.UniqueConstraint(
                fields=["adoption_request", "partner_kind"],
                name="uniq_adoption_bonus_per_kind",
            ),
        ]
        indexes = [
            models.Index(fields=["adoption_request"]),
            models.Index(fields=["redemption_code"]),
        ]

    def __str__(self):
        return f"Bonus AR{self.adoption_request_id} {self.partner_kind} → ofertă {self.offer_id}"


class CollaboratorOfferClaim(models.Model):
    """
    O „acceptare” a ofertei de către un utilizator: generează cod unic,
    trimite emailuri cumpărător + colaborator, consumă din stoc.
    """

    offer = models.ForeignKey(
        CollaboratorServiceOffer,
        on_delete=models.CASCADE,
        related_name="claims",
    )
    code = models.CharField("Cod ofertă", max_length=20, unique=True, db_index=True)
    buyer_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="collab_offer_claims",
    )
    buyer_email = models.EmailField("Email cumpărător")
    buyer_name_snapshot = models.CharField("Nume (snapshot)", max_length=200, blank=True)
    buyer_phone_snapshot = models.CharField("Telefon (snapshot)", max_length=40, blank=True)
    buyer_locality_snapshot = models.CharField("Localitate (snapshot)", max_length=200, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Acceptare ofertă colaborator"
        verbose_name_plural = "Acceptări oferte colaboratori"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["offer", "created_at"]),
        ]

    def __str__(self):
        return f"{self.code} → ofertă {self.offer_id}"


class PromoA2Order(models.Model):
    """
    Comandă promovare A2 (flux curent demo/plată).
    Rezumatul final se trimite plătitorului după expirarea perioadei cumpărate.
    """

    STATUS_DRAFT = "draft"
    STATUS_CHECKOUT_PENDING = "checkout_pending"
    STATUS_PAID = "paid"
    STATUS_FAILED = "failed"
    STATUS_CANCELLED = "cancelled"
    STATUS_CHOICES = [
        (STATUS_DRAFT, "Draft"),
        (STATUS_CHECKOUT_PENDING, "Checkout pending"),
        (STATUS_PAID, "Paid"),
        (STATUS_FAILED, "Failed"),
        (STATUS_CANCELLED, "Cancelled"),
    ]

    PACKAGE_6H = "6h"
    PACKAGE_12H = "12h"
    PACKAGE_CHOICES = [
        (PACKAGE_6H, "6h"),
        (PACKAGE_12H, "12h"),
    ]
    SLOT_A2 = "A2"

    pet = models.ForeignKey(
        AnimalListing,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_a2_orders",
    )
    payer_user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="promo_a2_orders",
    )
    payer_email = models.EmailField("Email plătitor")
    payer_name_snapshot = models.CharField("Nume plătitor (snapshot)", max_length=200, blank=True)

    package = models.CharField("Pachet", max_length=8, choices=PACKAGE_CHOICES, default=PACKAGE_6H)
    quantity = models.PositiveIntegerField("Cantitate", default=1)
    unit_price = models.PositiveIntegerField("Preț unitar (lei)", default=10)
    total_price = models.PositiveIntegerField("Total (lei)", default=10)
    payment_method = models.CharField("Metodă plată", max_length=20, default="card")
    schedule = models.CharField("Programare", max_length=20, default="intercalat")
    slot_code = models.CharField("Caseta promovare", max_length=20, default=SLOT_A2, db_index=True)

    start_date = models.DateField("Data start")
    starts_at = models.DateTimeField("Pornire promovare", null=True, blank=True)
    ends_at = models.DateTimeField("Final promovare", null=True, blank=True)

    status = models.CharField("Status", max_length=24, choices=STATUS_CHOICES, default=STATUS_DRAFT, db_index=True)
    payment_provider = models.CharField("Procesator", max_length=40, blank=True, default="demo")
    payment_ref = models.CharField("Referință plată", max_length=120, blank=True)

    summary_sent_at = models.DateTimeField("Rezumat final trimis la", null=True, blank=True)
    summary_manual_sent_at = models.DateTimeField("Rezumat trimis manual la", null=True, blank=True)

    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Comandă promovare A2"
        verbose_name_plural = "Comenzi promovare A2"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["status", "ends_at"]),
            models.Index(fields=["payer_email", "created_at"]),
        ]

    def __str__(self):
        return f"A2#{self.pk} pet={self.pet_id} {self.status}"


class ReclamaSlotNote(models.Model):
    """Notiță editabilă pentru sloturile din pagina Reclama (ex. Burtieră HOME)."""

    section = models.CharField("Secțiune", max_length=30, db_index=True)
    slot_code = models.CharField("Slot", max_length=30, db_index=True)
    text = models.TextField("Text notiță", blank=True, default="")
    updated_by = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="reclama_slot_notes_updated",
    )
    updated_at = models.DateTimeField("Actualizat la", auto_now=True)
    created_at = models.DateTimeField("Creat la", auto_now_add=True)

    class Meta:
        verbose_name = "Notiță slot Reclama"
        verbose_name_plural = "Notițe sloturi Reclama"
        unique_together = [("section", "slot_code")]
        ordering = ["section", "slot_code"]

    def __str__(self):
        return f"{self.section}:{self.slot_code}"


class TransportOperatorProfile(models.Model):
    """
    Profil transportator (colaborator cu tip_partener=transport).
    Aprobare admin; capacitate câini/pisici; bifă național / internațional.
    """

    APPROVAL_PENDING = "pending"
    APPROVAL_APPROVED = "approved"
    APPROVAL_INACTIVE = "inactive"
    APPROVAL_CHOICES = [
        (APPROVAL_PENDING, "În așteptare aprobare"),
        (APPROVAL_APPROVED, "Aprobat"),
        (APPROVAL_INACTIVE, "Inactiv"),
    ]

    user = models.OneToOneField(
        User,
        on_delete=models.CASCADE,
        related_name="transport_operator_profile",
    )
    approval_status = models.CharField(
        "Status aprobare",
        max_length=20,
        choices=APPROVAL_CHOICES,
        default=APPROVAL_PENDING,
        db_index=True,
    )
    transport_national = models.BooleanField("TRANSPORT NAȚIONAL", default=False)
    transport_international = models.BooleanField("TRANSPORT INTERNATIONAL", default=False)
    max_caini = models.PositiveSmallIntegerField("Capacitate max. câini / cursă", default=1)
    max_pisici = models.PositiveSmallIntegerField("Capacitate max. pisici / cursă", default=1)
    block_count = models.PositiveSmallIntegerField("Număr blocări", default=0)
    blocked_until = models.DateTimeField("Blocat până la", null=True, blank=True)
    removed_after_third_block = models.BooleanField("Eliminat după a 3-a blocare", default=False)
    # Medie note user → transportator (agregat simplu; evaluările detaliate pot veni într-un model separat)
    rating_sum = models.IntegerField("Sumă stele (user→transportator)", default=0)
    rating_count = models.PositiveIntegerField("Număr evaluări (user→transportator)", default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil transportator"
        verbose_name_plural = "Profile transportatori"

    def __str__(self):
        return f"Transport {self.user_id} ({self.approval_status})"

    @property
    def average_rating_public(self) -> Optional[float]:
        if not self.rating_count:
            return None
        return round(self.rating_sum / self.rating_count, 2)


class TransportVeterinaryRequest(models.Model):
    """
    Cerere completată pe pagina Transport (formular veterinar).
    Opțional legată de o fișă animal când fluxul vine din adopție.
    """

    user = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_veterinary_requests",
    )
    judet = models.CharField("Județ", max_length=120)
    oras = models.CharField("Oraș / localitate", max_length=120)
    plecare = models.CharField("Punct plecare", max_length=500)
    sosire = models.CharField("Punct sosire", max_length=500)
    plecare_lat = models.CharField("Plecare lat", max_length=32, blank=True, default="")
    plecare_lng = models.CharField("Plecare lng", max_length=32, blank=True, default="")
    sosire_lat = models.CharField("Sosire lat", max_length=32, blank=True, default="")
    sosire_lng = models.CharField("Sosire lng", max_length=32, blank=True, default="")
    data_raw = models.CharField("Data (text formular)", max_length=40, blank=True, default="")
    ora_raw = models.CharField("Ora (text formular)", max_length=20, blank=True, default="")
    nr_caini = models.PositiveSmallIntegerField("Nr. animale", default=1)
    ROUTE_NATIONAL = "national"
    ROUTE_INTERNATIONAL = "international"
    ROUTE_SCOPE_CHOICES = [
        (ROUTE_NATIONAL, "Național"),
        (ROUTE_INTERNATIONAL, "Internațional"),
    ]
    route_scope = models.CharField(
        "Tip traseu",
        max_length=20,
        choices=ROUTE_SCOPE_CHOICES,
        default=ROUTE_NATIONAL,
    )
    URGENCY_FLEX = "flex"
    URGENCY_TODAY = "today"
    URGENCY_24H = "h24"
    URGENCY_CHOICES = [
        (URGENCY_FLEX, "Fără fereastră strictă"),
        (URGENCY_TODAY, "Transport azi"),
        (URGENCY_24H, "24 ore"),
    ]
    urgency_window = models.CharField(
        "Fereastră timp",
        max_length=12,
        choices=URGENCY_CHOICES,
        default=URGENCY_FLEX,
    )
    related_animal = models.ForeignKey(
        "AnimalListing",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_requests",
        verbose_name="Anunț asociat (adopție)",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Cerere transport veterinar"
        verbose_name_plural = "Cereri transport veterinar"
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["-created_at"]),
            models.Index(fields=["user", "-created_at"]),
            models.Index(fields=["route_scope", "-created_at"]),
        ]

    def __str__(self):
        return f"Transport #{self.pk} {self.judet}/{self.oras}"


class TransportDispatchJob(models.Model):
    """Flux: broadcast către transportatori, primul accept, anulare, re-ofertă."""

    STATUS_OPEN = "open"
    STATUS_ASSIGNED = "assigned"
    STATUS_CANCELLED = "cancelled"
    STATUS_COMPLETED = "completed"
    STATUS_EXPIRED = "expired"
    STATUS_EXHAUSTED = "exhausted"
    STATUS_CHOICES = [
        (STATUS_OPEN, "Deschisă (ofertă)"),
        (STATUS_ASSIGNED, "Asignată"),
        (STATUS_CANCELLED, "Anulată"),
        (STATUS_COMPLETED, "Finalizată"),
        (STATUS_EXPIRED, "Expirată"),
        (STATUS_EXHAUSTED, "Fără transportatori disponibili"),
    ]

    tvr = models.OneToOneField(
        TransportVeterinaryRequest,
        on_delete=models.CASCADE,
        related_name="dispatch_job",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=STATUS_OPEN, db_index=True)
    expires_at = models.DateTimeField(null=True, blank=True)
    assigned_transporter = models.ForeignKey(
        User,
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="transport_dispatch_jobs_assigned",
    )
    assigned_at = models.DateTimeField(null=True, blank=True)
    reopen_count = models.PositiveSmallIntegerField(default=0)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Job dispatch transport"
        verbose_name_plural = "Joburi dispatch transport"

    def __str__(self):
        return f"Dispatch #{self.pk} TVR={self.tvr_id} {self.status}"


class TransportDispatchRecipient(models.Model):
    """Transportator invitat la o cerere; primul accept câștigă."""

    ST_PENDING = "pending"
    ST_ACCEPTED = "accepted"
    ST_SUPERSEDED = "superseded"
    ST_DECLINED = "declined"
    STATUS_CHOICES = [
        (ST_PENDING, "În așteptare"),
        (ST_ACCEPTED, "Acceptat"),
        (ST_SUPERSEDED, "Luat de altcineva"),
        (ST_DECLINED, "Refuzat"),
    ]

    job = models.ForeignKey(
        TransportDispatchJob,
        on_delete=models.CASCADE,
        related_name="recipients",
    )
    transporter = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transport_dispatch_recipients",
    )
    status = models.CharField(max_length=20, choices=STATUS_CHOICES, default=ST_PENDING, db_index=True)
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Destinatar dispatch transport"
        verbose_name_plural = "Destinatari dispatch transport"
        unique_together = [("job", "transporter")]
        indexes = [
            models.Index(fields=["job", "status"]),
            models.Index(fields=["transporter", "status"]),
        ]

    def __str__(self):
        return f"R{self.pk} job={self.job_id} t={self.transporter_id} {self.status}"


class TransportTripRating(models.Model):
    """Evaluare după cursă; reciprocă — vizibilitate diferită după direcție."""

    DIR_USER_TO_OP = "user_to_op"
    DIR_OP_TO_USER = "op_to_user"
    DIR_CHOICES = [
        (DIR_USER_TO_OP, "Utilizator → transportator"),
        (DIR_OP_TO_USER, "Transportator → utilizator"),
    ]

    job = models.ForeignKey(
        TransportDispatchJob,
        on_delete=models.CASCADE,
        related_name="ratings",
    )
    from_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transport_ratings_given",
    )
    to_user = models.ForeignKey(
        User,
        on_delete=models.CASCADE,
        related_name="transport_ratings_received",
    )
    direction = models.CharField(max_length=20, choices=DIR_CHOICES)
    stars = models.PositiveSmallIntegerField()
    comment = models.TextField(blank=True, default="")
    # user→op: inclus în medie publică; op→user: doar admin + părți (nu agregat public)
    visible_to_public_profile = models.BooleanField(default=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        verbose_name = "Evaluare cursă transport"
        verbose_name_plural = "Evaluări cursă transport"
        indexes = [
            models.Index(fields=["job", "direction"]),
            models.Index(fields=["to_user", "-created_at"]),
        ]

    def __str__(self):
        return f"Rating #{self.pk} job={self.job_id} {self.stars}*"

