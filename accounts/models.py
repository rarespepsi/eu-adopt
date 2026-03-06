"""
accounts.Profile: extensie OneToOne la User pentru tip cont.
Tracking trimitere emailuri (bun venit etc.) pentru admin.
"""
from django.conf import settings
from django.db import models


class Profile(models.Model):
    """
    Profil utilizator legat OneToOne de User.
    Tipul contului: Adoptator (PF), Adăpost (SRL), ONG.
    """
    ACCOUNT_TYPE_CHOICES = [
        ("adopter", "ADOPTER (PF)"),
        ("shelter", "SHELTER (SRL / Adapost)"),
        ("ong", "ONG"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="accounts_profile",
    )
    account_type = models.CharField(
        max_length=20,
        choices=ACCOUNT_TYPE_CHOICES,
        default="adopter",
    )

    class Meta:
        verbose_name = "Profil (accounts)"
        verbose_name_plural = "Profili (accounts)"

    def __str__(self):
        return f"{self.user.get_username()} ({self.get_account_type_display()})"


class EmailDeliveryLog(models.Model):
    """
    Jurnal trimiteri email (bun venit etc.) pentru vizibilitate în admin: SENT / FAILED.
    """
    STATUS_CHOICES = [
        ("sent", "SENT"),
        ("failed", "FAILED"),
    ]
    EMAIL_TYPE_CHOICES = [
        ("welcome", "Welcome (bun venit)"),
        ("adoption_request_new", "Cerere nouă adopție"),
        ("other", "Other"),
    ]

    subject = models.CharField(
        max_length=255,
        blank=True,
        help_text="Subiectul emailului (opțional).",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="email_delivery_logs",
        null=True,
        blank=True,
        help_text="Utilizatorul căruia i s-a trimis (sau a eșuat) emailul.",
    )
    email_type = models.CharField(
        max_length=20,
        choices=EMAIL_TYPE_CHOICES,
        default="welcome",
    )
    status = models.CharField(
        max_length=10,
        choices=STATUS_CHOICES,
    )
    to_email = models.EmailField(
        max_length=254,
        help_text="Adresa la care s-a trimis / a eșuat trimiterea.",
    )
    sent_at = models.DateTimeField(auto_now_add=True)
    error_message = models.TextField(
        blank=True,
        help_text="Mesaj eroare dacă status=FAILED.",
    )

    class Meta:
        verbose_name = "Email delivery log"
        verbose_name_plural = "Email delivery logs"
        ordering = ["-sent_at"]

    def __str__(self):
        return f"{self.email_type} → {self.to_email} ({self.status}) @ {self.sent_at}"


class UserMatchProfile(models.Model):
    """
    Profil de potrivire (chestionar „Găsește-mi prietenul ideal”).
    OneToOne cu User. Salvat după completare chestionar de utilizator autentificat.
    """
    HOUSING_CHOICES = [
        ("apartment", "Apartament"),
        ("house_no_yard", "Casă fără curte"),
        ("house_yard", "Casă cu curte"),
    ]
    EXPERIENCE_CHOICES = [
        ("first_dog", "Primul meu animal"),
        ("some", "Am avut în trecut"),
        ("advanced", "Experiență multă"),
    ]
    ACTIVITY_LEVEL_CHOICES = [
        ("low", "Liniștit"),
        ("medium", "Moderat"),
        ("high", "Activ"),
    ]
    TIME_AVAILABLE_CHOICES = [
        ("low", "Puțin"),
        ("normal", "Moderat"),
        ("high", "Mult"),
    ]
    SIZE_PREFERENCE_CHOICES = [
        ("small", "Mic"),
        ("medium", "Mediu"),
        ("large", "Mare"),
        ("any", "Oricare"),
    ]
    AGE_PREFERENCE_CHOICES = [
        ("puppy", "Pui"),
        ("adult", "Adult"),
        ("senior", "Senior"),
        ("any", "Oricare"),
    ]

    user = models.OneToOneField(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="match_profile",
    )
    housing = models.CharField(max_length=20, blank=True, choices=HOUSING_CHOICES)
    experience = models.CharField(max_length=20, blank=True, choices=EXPERIENCE_CHOICES)
    activity_level = models.CharField(max_length=20, blank=True, choices=ACTIVITY_LEVEL_CHOICES)
    time_available = models.CharField(max_length=20, blank=True, choices=TIME_AVAILABLE_CHOICES)
    has_kids = models.BooleanField(blank=True, null=True)
    has_cat = models.BooleanField(blank=True, null=True)
    has_dog = models.BooleanField(blank=True, null=True)
    size_preference = models.CharField(max_length=20, blank=True, choices=SIZE_PREFERENCE_CHOICES)
    age_preference = models.CharField(max_length=20, blank=True, choices=AGE_PREFERENCE_CHOICES)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        verbose_name = "Profil potrivire (match)"
        verbose_name_plural = "Profili potrivire (match)"

    def __str__(self):
        return f"Match profile: {self.user.get_username()}"
