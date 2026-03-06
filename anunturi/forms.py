import re
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
    JUDET_CHOICES,
)
from accounts.models import UserMatchProfile

User = get_user_model()


def _normalize_phone(phone):
    """Returnează doar cifrele din telefon pentru comparație (evită dubluri 0751 vs 075 1)."""
    if not phone:
        return ""
    return re.sub(r"\D", "", str(phone).strip())


def _phone_already_used(normalized_phone, exclude_user=None):
    """Verifică dacă numărul (normalizat) există deja la UserProfile, Profile sau OngProfile."""
    if not normalized_phone or len(normalized_phone) < 6:
        return False
    qs_up = UserProfile.objects.all()
    qs_pr = Profile.objects.all()
    qs_ong = OngProfile.objects.all()
    if exclude_user:
        qs_up = qs_up.exclude(user=exclude_user)
        qs_pr = qs_pr.exclude(user=exclude_user)
        qs_ong = qs_ong.exclude(user=exclude_user)
    for up in qs_up.only("telefon"):
        if _normalize_phone(up.telefon) == normalized_phone:
            return True
    for pr in qs_pr.only("phone"):
        if _normalize_phone(pr.phone) == normalized_phone:
            return True
    for og in qs_ong.only("telefon"):
        if _normalize_phone(og.telefon) == normalized_phone:
            return True
    return False


def _normalize_cui(cui):
    """Returnează doar cifrele din CUI/CIF pentru comparație."""
    if not cui:
        return ""
    return re.sub(r"\D", "", str(cui).strip())


def _cui_already_used(normalized_cui, exclude_user=None):
    """Verifică dacă CUI-ul (normalizat) există deja la OngProfile sau Profile."""
    if not normalized_cui or len(normalized_cui) < 5:
        return False
    qs_ong = OngProfile.objects.all()
    qs_pr = Profile.objects.exclude(cui="").exclude(cui__isnull=True)
    if exclude_user:
        qs_ong = qs_ong.exclude(user=exclude_user)
        qs_pr = qs_pr.exclude(user=exclude_user)
    for og in qs_ong.only("cui"):
        if _normalize_cui(og.cui) == normalized_cui:
            return True
    for pr in qs_pr.only("cui"):
        if _normalize_cui(pr.cui) == normalized_cui:
            return True
    return False


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
        # CUI duplicat (pentru SRL/PFA/ONG)
        if (tip in ("srl_pfa_af", "ong")) and (data.get("cui") or "").strip():
            norm = _normalize_cui(data.get("cui"))
            if norm and _cui_already_used(norm):
                self.add_error("cui", "Acest CUI/CIF este deja înregistrat. Folosiți alt CUI sau recuperați contul.")
        return data

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if commit:
            user.save()
        return user


# ----- Noul flux de înregistrare: PF / SRL / ONG -----

class RegisterPFForm(UserCreationForm):
    """Persoană fizică: email (unic), phone (unic), password, first_name, last_name, judet, oras + accept termeni + GDPR."""
    email = forms.EmailField(label="Email", required=True)
    first_name = forms.CharField(label="Prenume", max_length=150, required=True)
    last_name = forms.CharField(label="Nume", max_length=150, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)
    judet = forms.ChoiceField(
        label="Județ",
        choices=[("", "---------")] + list(JUDET_CHOICES),
        required=True,
        error_messages={"required": "Județul este obligatoriu."},
    )
    oras = forms.CharField(label="Oraș / Localitate (comună)", max_length=120, required=True)
    accept_termeni = forms.BooleanField(
        required=True,
        label="Accept termenii și condițiile",
        error_messages={"required": "Trebuie să accepți termenii și condițiile pentru a crea cont."},
    )
    accept_gdpr = forms.BooleanField(
        required=True,
        label="Accept prelucrarea datelor conform GDPR",
        error_messages={"required": "Trebuie să accepți prelucrarea datelor conform GDPR."},
    )
    email_opt_in_wishlist = forms.BooleanField(
        required=False,
        initial=True,
        label="Accept notificări email EU-Adopt (wishlist)",
        help_text="Poți dezactiva oricând din setări.",
    )
    poza_1 = forms.ImageField(label="Poză profil (opțional)", required=False)

    class Meta:
        model = User
        fields = ("username", "email", "first_name", "last_name", "password1", "password2")
        labels = {"username": "Utilizator (opțional, se folosește emailul dacă e gol)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False
        self.fields["username"].help_text = "Opțional. Dacă îl lași gol, vom folosi emailul."

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Acest nume de utilizator este deja folosit. Alegeți altul sau folosiți emailul.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Acest email este deja folosit. Folosiți alt email sau recuperați contul.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone
        norm = _normalize_phone(phone)
        if _phone_already_used(norm):
            raise ValidationError("Acest număr de telefon este deja asociat unui cont. Folosiți alt număr sau recuperați contul.")
        return phone

    def clean_judet(self):
        judet = (self.cleaned_data.get("judet") or "").strip()
        if not judet:
            raise ValidationError("Județul este obligatoriu.")
        return judet

    def clean_oras(self):
        oras = (self.cleaned_data.get("oras") or "").strip()
        if not oras:
            raise ValidationError("Orașul / localitatea este obligatoriu.")
        return oras

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        opt_in = self.cleaned_data.get("email_opt_in_wishlist", True)
        if commit:
            user.save()
            prof, _ = Profile.objects.get_or_create(user=user, defaults={
                "account_type": "individual",
                "phone": self.cleaned_data.get("phone", ""),
                "email_opt_in_wishlist": opt_in,
            })
            if not _:
                prof.email_opt_in_wishlist = opt_in
                prof.save(update_fields=["email_opt_in_wishlist"])
            up_defaults = {
                "nume": self.cleaned_data.get("last_name", ""),
                "prenume": self.cleaned_data.get("first_name", ""),
                "telefon": self.cleaned_data.get("phone", ""),
                "email": user.email,
                "judet": self.cleaned_data.get("judet", ""),
                "oras": self.cleaned_data.get("oras", ""),
            }
            if self.cleaned_data.get("poza_1"):
                up_defaults["poza_1"] = self.cleaned_data["poza_1"]
            UserProfile.objects.get_or_create(user=user, defaults=up_defaults)
            up = UserProfile.objects.get(user=user)
            up.judet = self.cleaned_data.get("judet", "")
            up.oras = self.cleaned_data.get("oras", "")
            fields = ["judet", "oras"]
            if self.cleaned_data.get("poza_1"):
                up.poza_1 = self.cleaned_data["poza_1"]
                fields.append("poza_1")
            up.save(update_fields=fields)
        return user


class RegisterSRLForm(UserCreationForm):
    """SRL / Firmă: company_name, CUI, contact_person, email, phone, password + accept termeni."""
    email = forms.EmailField(label="Email", required=True)
    company_name = forms.CharField(label="Denumire firmă", max_length=200, required=True)
    accept_termeni = forms.BooleanField(
        required=True,
        label="Accept termenii și condițiile",
        error_messages={"required": "Trebuie să accepți termenii și condițiile pentru a crea cont."},
    )
    email_opt_in_wishlist = forms.BooleanField(
        required=False,
        initial=False,
        label="Accept notificări email EU-Adopt (wishlist)",
    )
    cui = forms.CharField(label="CUI", max_length=20, required=True)
    contact_person = forms.CharField(label="Persoană de contact", max_length=120, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Utilizator (pentru autentificare)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Acest nume de utilizator este deja folosit.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Acest email este deja folosit. Folosiți alt email sau recuperați contul.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone
        norm = _normalize_phone(phone)
        if _phone_already_used(norm):
            raise ValidationError("Acest număr de telefon este deja asociat unui cont.")
        return phone

    def clean_cui(self):
        cui = (self.cleaned_data.get("cui") or "").strip()
        if not cui:
            return cui
        norm = _normalize_cui(cui)
        if _cui_already_used(norm):
            raise ValidationError("Acest CUI este deja înregistrat. Folosiți alt CUI sau recuperați contul.")
        return cui

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        user.first_name = self.cleaned_data.get("contact_person", "")[:150]
        opt_in = self.cleaned_data.get("email_opt_in_wishlist", False)
        if commit:
            user.save()
            prof, _ = Profile.objects.get_or_create(user=user, defaults={
                "account_type": "company",
                "phone": self.cleaned_data.get("phone", ""),
                "company_name": self.cleaned_data.get("company_name", ""),
                "cui": self.cleaned_data.get("cui", ""),
                "contact_person": self.cleaned_data.get("contact_person", ""),
                "email_opt_in_wishlist": opt_in,
            })
            if not _:
                prof.email_opt_in_wishlist = opt_in
                prof.save(update_fields=["email_opt_in_wishlist"])
            OngProfile.objects.get_or_create(user=user, defaults={
                "denumire_legala": self.cleaned_data.get("company_name", ""),
                "cui": self.cleaned_data.get("cui", ""),
                "reprezentant_legal": self.cleaned_data.get("contact_person", ""),
                "email": user.email,
                "telefon": self.cleaned_data.get("phone", ""),
                "tip_organizatie": "srl",
            })
        return user


class RegisterONGForm(UserCreationForm):
    """ONG: organization_name, representative_name, email, phone, password + accept termeni."""
    email = forms.EmailField(label="Email", required=True)
    organization_name = forms.CharField(label="Denumire organizație", max_length=200, required=True)
    accept_termeni = forms.BooleanField(
        required=True,
        label="Accept termenii și condițiile",
        error_messages={"required": "Trebuie să accepți termenii și condițiile pentru a crea cont."},
    )
    email_opt_in_wishlist = forms.BooleanField(
        required=False,
        initial=False,
        label="Accept notificări email EU-Adopt (wishlist)",
    )
    representative_name = forms.CharField(label="Reprezentant legal", max_length=120, required=True)
    phone = forms.CharField(label="Telefon", max_length=30, required=True)

    class Meta:
        model = User
        fields = ("username", "email", "password1", "password2")
        labels = {"username": "Utilizator (pentru autentificare)"}

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["username"].required = False

    def clean_username(self):
        username = (self.cleaned_data.get("username") or "").strip()
        if username and User.objects.filter(username__iexact=username).exists():
            raise ValidationError("Acest nume de utilizator este deja folosit.")
        return username

    def clean_email(self):
        email = (self.cleaned_data.get("email") or "").strip().lower()
        if not email:
            return email
        if User.objects.filter(email__iexact=email).exists():
            raise ValidationError("Acest email este deja folosit. Folosiți alt email sau recuperați contul.")
        return email

    def clean_phone(self):
        phone = (self.cleaned_data.get("phone") or "").strip()
        if not phone:
            return phone
        norm = _normalize_phone(phone)
        if _phone_already_used(norm):
            raise ValidationError("Acest număr de telefon este deja asociat unui cont.")
        return phone

    def save(self, commit=True):
        user = super().save(commit=False)
        user.email = self.cleaned_data["email"].strip().lower()
        if not user.username:
            user.username = user.email
        user.first_name = self.cleaned_data.get("representative_name", "")[:150]
        opt_in = self.cleaned_data.get("email_opt_in_wishlist", False)
        if commit:
            user.save()
            prof, _ = Profile.objects.get_or_create(user=user, defaults={
                "account_type": "ngo",
                "phone": self.cleaned_data.get("phone", ""),
                "organization_name": self.cleaned_data.get("organization_name", ""),
                "representative_name": self.cleaned_data.get("representative_name", ""),
                "email_opt_in_wishlist": opt_in,
            })
            if not _:
                prof.email_opt_in_wishlist = opt_in
                prof.save(update_fields=["email_opt_in_wishlist"])
            OngProfile.objects.get_or_create(user=user, defaults={
                "denumire_legala": self.cleaned_data.get("organization_name", ""),
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
            "varsta_aproximativa",
            "sex",
            "marime",
            "status",
            "prietenos_cu_oamenii", "prietenos_cu_copiii", "timid", "protector", "energic_jucaus",
            "linistit", "independent", "cauta_atentie", "latra_des", "calm_in_casa",
            "potrivit_apartament", "prefera_curte", "poate_sta_afara", "poate_sta_interior",
            "obisnuit_in_lesa", "merge_bine_la_plimbare", "necesita_miscare_multa",
            "potrivit_persoane_varstnice", "potrivit_familie_activa",
            "ok_cu_alti_caini", "ok_cu_pisici", "prefera_singurul_animal", "accepta_vizitatori", "necesita_socializare",
            "vaccinat", "sterilizat", "deparazitat", "microcipat", "are_pasaport", "necesita_tratament", "sensibil_zgomote",
            "stie_comenzi_baza", "face_nevoile_afara", "invata_repede", "necesita_dresaj", "nu_roade", "obisnuit_masina",
            "recomandat_prima_adoptie",
            "descriere_personalitate",
        )
        widgets = {
            "nume": forms.TextInput(attrs={"placeholder": "Numele animalului"}),
            "rasa": forms.TextInput(attrs={"placeholder": "Ex: Metis, maidanez – completați liber"}),
            "tip_altele": forms.TextInput(attrs={"placeholder": "Ex: Pasăre, Iepure, Șopârlă, Hamster..."}),
            "descriere_personalitate": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "Max 500 caractere."}),
        }
        labels = {
            "nume": "Nume",
            "rasa": "Rasă",
            "tip": "Tip animal",
            "tip_altele": "Tip animal (dacă e altul decât câine/pisică)",
            "varsta_aproximativa": "Vârstă aproximativă (ani) *",
            "sex": "Sex",
            "marime": "Talie",
            "status": "Status",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.initial.setdefault("rasa", "Metis")
        self.fields["varsta_aproximativa"].required = True

    def clean(self):
        data = super().clean()
        if data.get("tip") == "other":
            val = (data.get("tip_altele") or "").strip()
            if not val:
                raise ValidationError(
                    {"tip_altele": "Dacă Tip = Altele, completați tipul de animal (ex: Pasăre, Iepure, Șopârlă)."}
                )
            data["tip_altele"] = val
        if data.get("varsta_aproximativa") is None:
            raise ValidationError(
                {"varsta_aproximativa": "Vârsta aproximativă este obligatorie. Alegeți de la „< 1 an” până la „> 15 ani”."}
            )
        dp = (data.get("descriere_personalitate") or "").strip()
        if len(dp) > 500:
            raise ValidationError({"descriere_personalitate": "Maxim 500 caractere."})
        return data


def _validate_photo_size(file, field_name):
    """Verifică că fișierul are maxim USER_PHOTO_MAX_SIZE_BYTES (2 MB)."""
    if file and file.size > USER_PHOTO_MAX_SIZE_BYTES:
        max_mb = USER_PHOTO_MAX_SIZE_BYTES // (1024 * 1024)
        raise ValidationError(
            f"Poza este prea mare. Maxim {max_mb} MB per poză (pentru a nu încărca serverul)."
        )


class UserProfileForm(forms.ModelForm):
    """Profil (PF/SRL/ONG): nume, prenume, telefon, oraș, județ obligatoriu, email, poză opțional. Județul folosește la filtrarea câinilor."""

    class Meta:
        model = UserProfile
        fields = ("nume", "prenume", "telefon", "oras", "judet", "email", "poza_1")
        labels = {
            "nume": "Nume",
            "prenume": "Prenume",
            "telefon": "Telefon",
            "oras": "Oraș / Localitate",
            "judet": "Județ *",
            "email": "Email",
            "poza_1": "Poza (opțional, max 2 MB)",
        }
        widgets = {
            "nume": forms.TextInput(attrs={"placeholder": "Nume"}),
            "prenume": forms.TextInput(attrs={"placeholder": "Prenume"}),
            "telefon": forms.TextInput(attrs={"placeholder": "Telefon"}),
            "oras": forms.TextInput(attrs={"placeholder": "Oraș / Localitate"}),
            "judet": forms.Select(attrs={"class": "judet-select"}),
            "email": forms.EmailInput(attrs={"placeholder": "Email"}),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["judet"].required = True

    def clean_judet(self):
        judet = (self.cleaned_data.get("judet") or "").strip()
        if not judet:
            raise ValidationError("Județul este obligatoriu. Ne ajută la filtrarea animalelor după județ.")
        return judet

    def clean_telefon(self):
        phone = (self.cleaned_data.get("telefon") or "").strip()
        if not phone:
            return phone
        norm = _normalize_phone(phone)
        exclude_user = getattr(self.instance, "user", None)
        if _phone_already_used(norm, exclude_user=exclude_user):
            raise ValidationError("Acest număr de telefon este deja folosit de alt cont. Folosiți alt număr.")
        return phone

    def clean_poza_1(self):
        if self.files.get("poza_1") and hasattr(self.files["poza_1"], "size"):
            _validate_photo_size(self.files["poza_1"], "poza_1")
        return self.cleaned_data.get("poza_1")


class OrgRequiredPage2Form(forms.ModelForm):
    """Categoria 2 (SRL/ONG): câmpuri obligatorii pe pagina 2 – adresă legală, locație animale, CUI, adăpost public."""

    class Meta:
        model = OngProfile
        fields = (
            "legal_street", "legal_number", "legal_locality", "legal_judet", "legal_country", "legal_postal_code",
            "pickup_street", "pickup_number", "pickup_locality", "pickup_judet", "pickup_country", "pickup_postal_code",
            "cui", "adapost_public",
        )
        labels = {
            "legal_street": "Stradă (sediu) *",
            "legal_number": "Nr. (sediu) *",
            "legal_locality": "Localitate (sediu) *",
            "legal_judet": "Județ (sediu) *",
            "legal_country": "Țară (sediu) *",
            "legal_postal_code": "Cod poștal (sediu) *",
            "pickup_street": "Stradă (locație animale) *",
            "pickup_number": "Nr. (locație animale) *",
            "pickup_locality": "Localitate (locație animale) *",
            "pickup_judet": "Județ (locație animale) *",
            "pickup_country": "Țară (locație animale) *",
            "pickup_postal_code": "Cod poștal (locație animale, opțional)",
            "cui": "CUI / CIF *",
            "adapost_public": "Sunteți adăpost public? *",
        }
        widgets = {
            "legal_judet": forms.Select(choices=[("", "---------")] + list(JUDET_CHOICES)),
            "pickup_judet": forms.Select(choices=[("", "---------")] + list(JUDET_CHOICES)),
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        for f in (
            "legal_street", "legal_number", "legal_locality", "legal_judet", "legal_country", "legal_postal_code",
            "pickup_street", "pickup_number", "pickup_locality", "pickup_judet", "pickup_country",
            "cui", "adapost_public",
        ):
            if f in self.fields:
                self.fields[f].required = True
        self.fields["adapost_public"].error_messages = {"required": "Trebuie să indicați dacă sunteți adăpost public (Da/Nu)."}

    def clean_cui(self):
        raw = (self.cleaned_data.get("cui") or "").strip()
        if not raw:
            raise ValidationError("CUI/CIF este obligatoriu.")
        norm = _normalize_cui(raw)
        if len(norm) < 5:
            raise ValidationError("Introduceți un CUI valid (cifre, cu sau fără prefix RO).")
        return norm  # salvăm normalizat (doar cifre)

    def clean_legal_judet(self):
        v = (self.cleaned_data.get("legal_judet") or "").strip()
        if not v:
            raise ValidationError("Județul (sediu) este obligatoriu.")
        return v

    def clean_pickup_judet(self):
        v = (self.cleaned_data.get("pickup_judet") or "").strip()
        if not v:
            raise ValidationError("Județul (locație animale) este obligatoriu.")
        return v


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


# Secțiuni pentru formularul standard „Postează câine pentru adopție”
PET_ADAUGA_SECTIONS = [
    ("Identitate", [
        "nume", "rasa", "tip", "tip_altele", "sex", "age_years", "age_category", "size_category",
    ]),
    ("Locație & status", [
        "judet", "status", "adoption_status",
        "ong_email", "ong_contact_person", "ong_phone", "ong_address", "ong_visiting_hours",
    ]),
    ("Sănătate", [
        "sterilized_status", "vaccinated_status", "dewormed_status", "microchipped_status",
        "cip", "carnet_sanatate",
    ]),
    ("Comportament & potrivire", [
        "energy_level", "good_with_children", "good_with_dogs", "good_with_cats",
        "housing_fit", "experience_required", "attention_need",
    ]),
    ("Poveste (scurt)", [
        "descriere_personalitate",
    ]),
    ("Media", [
        "imagine", "imagine_2", "imagine_3", "video_url",
    ]),
]


class PetAdaugaForm(forms.ModelForm):
    """Formular standard adăugare animal (PF/ONG). Secțiuni cu titluri, dropdown-uri, min 3 poze."""

    SECTIONS = PET_ADAUGA_SECTIONS

    class Meta:
        model = Pet
        fields = [
            "nume", "rasa", "tip", "tip_altele", "sex", "age_years", "age_category", "size_category",
            "judet", "status", "adoption_status",
            "ong_email", "ong_contact_person", "ong_phone", "ong_address", "ong_visiting_hours",
            "sterilized_status", "vaccinated_status", "dewormed_status", "microchipped_status",
            "cip", "carnet_sanatate",
            "energy_level", "good_with_children", "good_with_dogs", "good_with_cats",
            "housing_fit", "experience_required", "attention_need",
            "descriere_personalitate",
            "imagine", "imagine_2", "imagine_3", "video_url",
        ]
        widgets = {
            "age_years": forms.NumberInput(attrs={"min": 0, "max": 20, "step": 1}),
            "rasa": forms.TextInput(attrs={"placeholder": "Ex: Metis, maidanez"}),
            "tip_altele": forms.TextInput(attrs={"placeholder": "Ex: Pasăre, Iepure..."}),
            "descriere_personalitate": forms.Textarea(attrs={"rows": 3, "maxlength": 500, "placeholder": "Max 500 caractere. Poveste scurtă despre animal."}),
            "video_url": forms.URLInput(attrs={"placeholder": "https://..."}),
        }
        labels = {
            "age_years": "Vârsta (ani)",
            "age_category": "Categorie vârstă",
            "size_category": "Categorie talie",
            "sterilized_status": "Sterilizat/Castrat",
            "vaccinated_status": "Vaccinat",
            "dewormed_status": "Deparazitat",
            "microchipped_status": "Microcipat",
            "good_with_children": "Ok cu copii",
            "good_with_dogs": "Ok cu câini",
            "good_with_cats": "Ok cu pisici",
            "housing_fit": "Potrivit locuință",
            "experience_required": "Experiență necesară",
            "attention_need": "Nevoie de atenție",
            "video_url": "Link video (opțional)",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        if not self.instance or not self.instance.pk:
            self.initial.setdefault("rasa", "Metis")
        empty = [("", "— Alegeți —")]
        choice_fields = [
            "sex", "age_category", "size_category", "status", "adoption_status",
            "sterilized_status", "vaccinated_status", "dewormed_status", "microchipped_status",
            "energy_level", "good_with_children", "good_with_dogs", "good_with_cats",
            "housing_fit", "experience_required", "attention_need",
        ]
        for name in choice_fields:
            if name in self.fields and hasattr(self.fields[name], "choices"):
                choices = list(self.fields[name].choices)
                if choices and (not choices[0][0] == ""):
                    self.fields[name].choices = empty + choices
        self.fields["age_category"].help_text = "Dacă nu știi exact, alege categoria."
        self.fields["good_with_children"].help_text = "Dacă nu e testat, alege „Necunoscut”."
        self.fields["good_with_dogs"].help_text = "Dacă nu e testat, alege „Necunoscut”."
        self.fields["good_with_cats"].help_text = "Dacă nu e testat, alege „Necunoscut”."
        self.fields["energy_level"].help_text = "Scăzut = calm, Ridicat = nevoie mare de mișcare."
        self.fields["age_years"].required = True
        self.fields["imagine"].label = "Poză 1 *"
        self.fields["imagine_2"].label = "Poză 2 *"
        self.fields["imagine_3"].label = "Poză 3 *"

    def clean(self):
        data = super().clean()
        if data.get("tip") == "other":
            val = (data.get("tip_altele") or "").strip()
            if not val:
                self.add_error("tip_altele", "Dacă Tip = Altele, completați tipul de animal.")
            else:
                data["tip_altele"] = val
        ay = data.get("age_years")
        if ay is None or ay == "":
            self.add_error("age_years", "Completează vârsta.")
        else:
            try:
                ay = int(ay)
                if not (0 <= ay <= 20):
                    self.add_error("age_years", "Vârsta trebuie să fie între 0 și 20.")
                else:
                    data["age_years"] = ay
            except (TypeError, ValueError):
                self.add_error("age_years", "Vârsta trebuie să fie un număr întreg (0–20).")
        dp = (data.get("descriere_personalitate") or "").strip()
        if len(dp) > 500:
            self.add_error("descriere_personalitate", "Maxim 500 caractere.")
        # Min 3 poze: la creare toate 3 obligatorii; la edit fie 3 uploaduri fie 3 deja pe instanță
        has_1 = data.get("imagine") or (self.instance and self.instance.pk and getattr(self.instance, "imagine", None))
        has_2 = data.get("imagine_2") or (self.instance and self.instance.pk and getattr(self.instance, "imagine_2", None))
        has_3 = data.get("imagine_3") or (self.instance and self.instance.pk and getattr(self.instance, "imagine_3", None))
        if not (has_1 and has_2 and has_3):
            self.add_error("imagine", "Sunt necesare minim 3 poze pentru publicare.")
        return data


class MatchQuizForm(forms.ModelForm):
    """
    Formular chestionar „Potrivirea perfectă”.
    Câmpuri: housing, experience, activity_level, time_available, has_kids, has_cat, has_dog, size_preference, age_preference.
    """
    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        empty_label = ("", "— Alegeți —")
        for name in ("housing", "experience", "activity_level", "time_available", "size_preference", "age_preference"):
            if name in self.fields and hasattr(self.fields[name], "choices"):
                choices = list(self.fields[name].choices)
                if choices and choices[0][0] != "":
                    self.fields[name].choices = [empty_label] + choices

    class Meta:
        model = UserMatchProfile
        fields = [
            "housing", "experience", "activity_level", "time_available",
            "has_kids", "has_cat", "has_dog",
            "size_preference", "age_preference",
        ]
        widgets = {
            "housing": forms.Select(attrs={"class": "match-quiz-select"}),
            "experience": forms.Select(attrs={"class": "match-quiz-select"}),
            "activity_level": forms.Select(attrs={"class": "match-quiz-select"}),
            "time_available": forms.Select(attrs={"class": "match-quiz-select"}),
            "has_kids": forms.CheckboxInput(attrs={"class": "match-quiz-check"}),
            "has_cat": forms.CheckboxInput(attrs={"class": "match-quiz-check"}),
            "has_dog": forms.CheckboxInput(attrs={"class": "match-quiz-check"}),
            "size_preference": forms.Select(attrs={"class": "match-quiz-select"}),
            "age_preference": forms.Select(attrs={"class": "match-quiz-select"}),
        }
        labels = {
            "housing": "Locuință",
            "experience": "Experiență cu animale",
            "activity_level": "Nivel activitate",
            "time_available": "Timp disponibil",
            "has_kids": "Am copii",
            "has_cat": "Am pisică(e)",
            "has_dog": "Am câine(ți)",
            "size_preference": "Preferință talie",
            "age_preference": "Preferință vârstă",
        }
