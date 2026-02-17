from django import forms
from django.core.exceptions import ValidationError
from django.contrib.auth import get_user_model
from django.contrib.auth.forms import UserCreationForm
from .models import (
    AdoptionRequest,
    Pet,
    Profile,
    UserProfile,
    OngProfile,
    PostAdoptionVerificationResponse,
    USER_PHOTO_MAX_SIZE_BYTES,
)

User = get_user_model()


# 3 categorii la înregistrare: 1 PF, 2 SRL/PFA, 3 ONG/Asociație/Fundație
TIP_CONT_CHOICES = [
    ("pf", "1. Persoană fizică"),
    ("srl_pfa_af", "2. SRL / PFA"),
    ("ong", "3. ONG / Asociație / Fundație"),
]

# Subtip pentru categoria 2 (doar SRL și PFA)
TIP_ORG_SRL_PFA_CHOICES = [
    ("srl", "SRL"),
    ("pfa", "PFA"),
]

# Subtip pentru categoria 3 (ONG / Asociație / Fundație)
TIP_ORG_ONG_CHOICES = [
    ("ong", "ONG"),
    ("af", "Asociație / Fundație"),
]

# Tipuri care folosesc OngProfile (în backend: ong, srl, pfa, af)
TIPURI_ORGANIZATII = ("ong", "srl", "pfa", "af")


class UserRegistrationForm(UserCreationForm):
    """
    Înregistrare: la selectarea categoriei apar câmpurile de identificare corespunzătoare.
    PF: nume, prenume, telefon, oraș. ONG/SRL/PFA/AF: denumire, CUI/CIF, nr. registru, etc.
    """
    email = forms.EmailField(
        label="Email",
        required=True,
        widget=forms.EmailInput(attrs={"placeholder": "Adresa de email"}),
    )
    tip_cont = forms.ChoiceField(
        label="Tip cont",
        choices=TIP_CONT_CHOICES,
        required=True,
        widget=forms.RadioSelect(),
        initial="pf",
    )
    # Când tip_cont = srl_pfa_af, se alege SRL sau PFA
    tip_org_organizatie = forms.ChoiceField(
        label="Tip (categoria 2)",
        choices=[("", "---------")] + list(TIP_ORG_SRL_PFA_CHOICES),
        required=False,
        widget=forms.RadioSelect(),
    )
    # Când tip_cont = ong, se alege ONG sau Asociație/Fundație
    tip_org_ong = forms.ChoiceField(
        label="Tip (categoria 3)",
        choices=[("", "---------")] + list(TIP_ORG_ONG_CHOICES),
        required=False,
        widget=forms.RadioSelect(),
    )
    # --- Persoană fizică ---
    nume = forms.CharField(label="Nume", max_length=80, required=False)
    prenume = forms.CharField(label="Prenume", max_length=80, required=False)
    telefon = forms.CharField(label="Telefon", max_length=30, required=False)
    oras = forms.CharField(label="Oraș / Localitate", max_length=120, required=False)
    # --- ONG / SRL / PFA / AF (identificare) ---
    denumire_legala = forms.CharField(
        label="Denumire (firmă / asociație / PFA)",
        max_length=200,
        required=False,
        help_text="Denumire legală (SRL/ONG) sau nume activitate (PFA)",
    )
    cui = forms.CharField(
        label="CUI / CIF",
        max_length=20,
        required=False,
        help_text="CUI (SRL/PFA) sau CIF (ONG/Asociație/Fundație)",
    )
    numar_registru = forms.CharField(
        label="Nr. registru",
        max_length=80,
        required=False,
        help_text="Nr. Registrul Comerțului (SRL) sau nr. registru asociații/fundații (ONG/AF)",
    )
    judet = forms.ChoiceField(
        label="Județ",
        choices=[("", "---------")] + list(Pet.JUDET_CHOICES),
        required=False,
    )
    oras_org = forms.CharField(
        label="Oraș / Localitate (sediu)",
        max_length=100,
        required=False,
    )
    email_contact = forms.EmailField(label="Email contact", required=False)
    telefon_org = forms.CharField(label="Telefon", max_length=30, required=False)
    reprezentant_legal = forms.CharField(
        label="Persoană de contact (SRL/PFA)",
        max_length=120,
        required=False,
        help_text="Persoana la care apelăm / cu care comunicăm la telefon.",
    )
    persoana_responsabila_adoptii = forms.CharField(
        label="Persoană de contact (ONG / Asociație / Fundație)",
        max_length=120,
        required=False,
        help_text="Persoana la care apelăm pentru adopții / comunicare.",
    )

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Utilizator"}

    def clean(self):
        data = super().clean()
        tip = data.get("tip_cont")
        if tip == "pf":
            for f in ("nume", "prenume", "telefon", "oras"):
                if not (data.get(f) or (data.get(f) or "").strip()):
                    self.add_error(f, "Obligatoriu pentru persoană fizică.")
        elif tip == "srl_pfa_af":
            sub = (data.get("tip_org_organizatie") or "").strip()
            if not sub or sub not in ("srl", "pfa"):
                self.add_error("tip_org_organizatie", "Alegeți SRL sau PFA.")
            if not (data.get("denumire_legala") or not data.get("denumire_legala").strip()):
                self.add_error("denumire_legala", "Obligatoriu.")
            if not (data.get("cui") or not data.get("cui").strip()):
                self.add_error("cui", "CUI/CIF obligatoriu (date verificabile).")
            if not (data.get("judet") or not data.get("judet").strip()):
                self.add_error("judet", "Obligatoriu.")
            if not ((data.get("reprezentant_legal") or "").strip()):
                self.add_error("reprezentant_legal", "Obligatoriu: persoană de contact.")
        elif tip == "ong":
            sub_ong = (data.get("tip_org_ong") or "").strip()
            if not sub_ong or sub_ong not in ("ong", "af"):
                self.add_error("tip_org_ong", "Alegeți ONG sau Asociație/Fundație.")
            if not (data.get("denumire_legala") or not data.get("denumire_legala").strip()):
                self.add_error("denumire_legala", "Obligatoriu.")
            if not (data.get("cui") or not data.get("cui").strip()):
                self.add_error("cui", "CUI/CIF obligatoriu (date verificabile).")
            if not (data.get("judet") or not data.get("judet").strip()):
                self.add_error("judet", "Obligatoriu.")
            if not ((data.get("persoana_responsabila_adoptii") or "").strip()):
                self.add_error("persoana_responsabila_adoptii", "Obligatoriu: persoană de contact.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


# ----- Noul flux de înregistrare: PF / SRL / ONG -----

class RegisterPFForm(UserCreationForm):
    """Persoană fizică: first_name, last_name, email, phone, password."""
    email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="Prenume", max_length=150, required=True)
    last_name = forms.CharField(label="Nume", max_length=150, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        labels = {"username": "Utilizator (pentru autentificare)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].help_text = "Folosiți email sau un nume de utilizator unic."

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        if commit:
            user.save()
            Profile.objects.get_or_create(user=user, defaults={"account_type": "individual", "phone": self.cleaned_data.get("phone", "")})
            UserProfile.objects.get_or_create(user=user, defaults={
                "nume": self.cleaned_data.get("last_name", ""),
                "prenume": self.cleaned_data.get("first_name", ""),
                "telefon": self.cleaned_data.get("phone", ""),
                "email": user.email,
            })
        return user


class RegisterSRLForm(UserCreationForm):
    """SRL / Firmă: company_name, CUI, registration_number, contact_person, email, phone, password."""
    email = forms.EmailField(label="Email", required=True)
    company_name = forms.CharField(label="Denumire firmă", max_length=200, required=True)
    cui = forms.CharField(label="CUI", max_length=20, required=True)
    registration_number = forms.CharField(label="Nr. registru", max_length=80, required=False)
    contact_person = forms.CharField(label="Persoană de contact", max_length=120, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Utilizator (pentru autentificare)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        user.first_name = self.cleaned_data.get("contact_person", "")[:150]
        if commit:
            user.save()
            Profile.objects.get_or_create(user=user, defaults={
                "account_type": "company",
                "phone": self.cleaned_data.get("phone", ""),
                "company_name": self.cleaned_data.get("company_name", ""),
                "cui": self.cleaned_data.get("cui", ""),
                "registration_number": self.cleaned_data.get("registration_number", ""),
                "contact_person": self.cleaned_data.get("contact_person", ""),
            })
            OngProfile.objects.get_or_create(user=user, defaults={
                "denumire_legala": self.cleaned_data.get("company_name", ""),
                "cui": self.cleaned_data.get("cui", ""),
                "numar_registru": self.cleaned_data.get("registration_number", ""),
                "reprezentant_legal": self.cleaned_data.get("contact_person", ""),
                "email": user.email,
                "telefon": self.cleaned_data.get("phone", ""),
                "tip_organizatie": "srl",
            })
        return user


class RegisterONGForm(UserCreationForm):
    """ONG: organization_name, legal_registration_number, representative_name, email, phone, password."""
    email = forms.EmailField(label="Email", required=True)
    organization_name = forms.CharField(label="Denumire organizație", max_length=200, required=True)
    legal_registration_number = forms.CharField(label="Nr. înregistrare", max_length=80, required=True)
    representative_name = forms.CharField(label="Reprezentant legal", max_length=120, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Utilizator (pentru autentificare)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        user.first_name = self.cleaned_data.get("representative_name", "")[:150]
        if commit:
            user.save()
            Profile.objects.get_or_create(user=user, defaults={
                "account_type": "ngo",
                "phone": self.cleaned_data.get("phone", ""),
                "organization_name": self.cleaned_data.get("organization_name", ""),
                "legal_registration_number": self.cleaned_data.get("legal_registration_number", ""),
                "representative_name": self.cleaned_data.get("representative_name", ""),
            })
            OngProfile.objects.get_or_create(user=user, defaults={
                "denumire_legala": self.cleaned_data.get("organization_name", ""),
                "numar_registru": self.cleaned_data.get("legal_registration_number", ""),
                "persoana_responsabila_adoptii": self.cleaned_data.get("representative_name", ""),
                "reprezentant_legal": self.cleaned_data.get("representative_name", ""),
                "email": user.email,
                "telefon": self.cleaned_data.get("phone", ""),
                "tip_organizatie": "ong",
            })
        return user


class AdoptionRequestForm(forms.ModelForm):
    class Meta:
        model = AdoptionRequest
        fields = (
            "nume_complet",
            "email",
            "telefon",
            "adresa",
            "mesaj",
            "ridicare_personala",
            "doreste_transport",
            "doreste_cazare_medicala_toiletare",
        )
        widgets = {
            "nume_complet": forms.TextInput(attrs={"placeholder": "Numele și prenumele", "required": True}),
            "email": forms.EmailInput(attrs={"placeholder": "Email", "required": True}),
            "telefon": forms.TextInput(attrs={"placeholder": "Telefon", "required": True}),
            "adresa": forms.TextInput(attrs={"placeholder": "Adresă (opțional)"}),
            "mesaj": forms.Textarea(attrs={"placeholder": "De ce doriți să adoptați? Experiență cu animale? (opțional)", "rows": 4}),
            "ridicare_personala": forms.CheckboxInput(),
            "doreste_transport": forms.CheckboxInput(),
            "doreste_cazare_medicala_toiletare": forms.CheckboxInput(),
        }
        labels = {
            "nume_complet": "Nume complet",
            "email": "Email",
            "telefon": "Telefon",
            "adresa": "Adresă",
            "mesaj": "Motivație / alte detalii",
            "ridicare_personala": "Ridicare personală (vin eu la adăpost)",
            "doreste_transport": "Doresc transport la domiciliu (serviciu Adopt a Pet)",
            "doreste_cazare_medicala_toiletare": "Doresc cazare medicală și toiletare (serviciu Adopt a Pet)",
        }


class PetAddForm(forms.ModelForm):
    """Formular pentru ONG: adăugare animal; ong_email se setează în view."""
    class Meta:
        model = Pet
        fields = (
            "nume",
            "rasa",
            "tip",
            "tip_altele",
            "tip_altele_altul",
            "varsta",
            "sex",
            "marime",
            "status",
            "judet",
            "descriere",
        )
        widgets = {
            "nume": forms.TextInput(attrs={"placeholder": "Numele animalului"}),
            "rasa": forms.TextInput(attrs={"placeholder": "Rasa"}),
            "descriere": forms.Textarea(attrs={"rows": 4, "placeholder": "Descriere (opțional)"}),
        }
        labels = {
            "nume": "Nume",
            "rasa": "Rasă",
            "tip": "Tip animal",
            "tip_altele": "Categorie (dacă Tip = Altele)",
            "tip_altele_altul": "Altul (dacă ați ales Altul)",
            "varsta": "Vârstă",
            "sex": "Sex",
            "marime": "Mărime",
            "status": "Status",
            "judet": "Județ",
            "descriere": "Descriere",
        }

    def clean(self):
        data = super().clean()
        if data.get("tip") == "other":
            if not data.get("tip_altele"):
                raise ValidationError(
                    {"tip_altele": "Dacă Tip = Altele, alegeți o categorie (Pasăre, Magar, etc.) sau „Altul”."}
                )
            if data.get("tip_altele") == "other":
                altul = (data.get("tip_altele_altul") or "").strip()
                if not altul:
                    raise ValidationError(
                        {"tip_altele_altul": "Dacă ați ales „Altul”, completați aici (ex: Șopârlă)."}
                    )
        return data


def _validate_photo_size(file, field_name):
    """Verifică că fișierul are maxim USER_PHOTO_MAX_SIZE_BYTES (2 MB)."""
    if file and file.size > USER_PHOTO_MAX_SIZE_BYTES:
        max_mb = USER_PHOTO_MAX_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(
            f"Poza este prea mare. Maxim {max_mb} MB per poză (pentru a nu încărca serverul)."
        )


class UserProfileForm(forms.ModelForm):
    """Profil persoană fizică: nume, prenume, telefon, oraș, email, max 3 poze (max 2 MB fiecare)."""

    class Meta:
        model = UserProfile
        fields = ("nume", "prenume", "telefon", "oras", "email", "poza_1", "poza_2", "poza_3")
        labels = {
            "nume": "Nume",
            "prenume": "Prenume",
            "telefon": "Telefon",
            "oras": "Oraș / Localitate",
            "email": "Email",
            "poza_1": "Poza 1 (max 2 MB)",
            "poza_2": "Poza 2 (max 2 MB)",
            "poza_3": "Poza 3 (max 2 MB)",
        }
        widgets = {
            "nume": forms.TextInput(attrs={"placeholder": "Nume"}),
            "prenume": forms.TextInput(attrs={"placeholder": "Prenume"}),
            "telefon": forms.TextInput(attrs={"placeholder": "Telefon"}),
            "oras": forms.TextInput(attrs={"placeholder": "Oraș / Localitate"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email"}),
        }

    def clean_poza_1(self):
        if self.files.get("poza_1") and hasattr(self.files["poza_1"], "size"):
            _validate_photo_size(self.files["poza_1"], "poza_1")
        return self.cleaned_data.get("poza_1")

    def clean_poza_2(self):
        if self.files.get("poza_2") and hasattr(self.files["poza_2"], "size"):
            _validate_photo_size(self.files["poza_2"], "poza_2")
        return self.cleaned_data.get("poza_2")

    def clean_poza_3(self):
        if self.files.get("poza_3") and hasattr(self.files["poza_3"], "size"):
            _validate_photo_size(self.files["poza_3"], "poza_3")
        return self.cleaned_data.get("poza_3")


class PostAdoptionVerificationForm(forms.ModelForm):
    """Formular verificare post-adopție: mesaj + opțional până la 3 poze (max 2 MB fiecare)."""

    class Meta:
        model = PostAdoptionVerificationResponse
        fields = ("mesaj", "poza_1", "poza_2", "poza_3")
        labels = {
            "mesaj": "Cum se simte animalul? (stare, comportament, orice detalii)",
            "poza_1": "Poza 1 (max 2 MB)",
            "poza_2": "Poza 2 (max 2 MB)",
            "poza_3": "Poza 3 (max 2 MB)",
        }
        widgets = {
            "mesaj": forms.Textarea(attrs={"rows": 5, "placeholder": "Scrieți câteva cuvinte despre cum se simte animalul..."}),
        }

    def clean_poza_1(self):
        if self.files.get("poza_1") and hasattr(self.files["poza_1"], "size"):
            _validate_photo_size(self.files["poza_1"], "poza_1")
        return self.cleaned_data.get("poza_1")

    def clean_poza_2(self):
        if self.files.get("poza_2") and hasattr(self.files["poza_2"], "size"):
            _validate_photo_size(self.files["poza_2"], "poza_2")
        return self.cleaned_data.get("poza_2")

    def clean_poza_3(self):
        if self.files.get("poza_3") and hasattr(self.files["poza_3"], "size"):
            _validate_photo_size(self.files["poza_3"], "poza_3")
        return self.cleaned_data.get("poza_3")
