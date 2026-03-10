from django.db import models
from django.contrib.auth.models import User


class UserProfile(models.Model):
    """
    Profil extensie pentru User (persoană fizică).
    Datele din formularul de înregistrare PF: telefon, oraș, poză, acorduri.
    """
    user = models.OneToOneField(User, on_delete=models.CASCADE, related_name="profile")
    phone = models.CharField("Telefon", max_length=20, blank=True)
    oras = models.CharField("Oraș / Localitate", max_length=120, blank=True)
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

