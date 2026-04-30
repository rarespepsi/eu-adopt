import re

from django import forms

_IN = {"class": "donatii-input"}
_TA = {"class": "donatii-input", "rows": 3}


def _validate_cnp_ro(value: str) -> str:
    s = (value or "").strip()
    if not s:
        raise forms.ValidationError("CNP este obligatoriu pentru formularul 230.")
    if not re.fullmatch(r"\d{13}", s):
        raise forms.ValidationError("CNP trebuie să aibă exact 13 cifre.")
    return s


class Formular230Form(forms.Form):
    """Date pentru generare PDF orientativ formular 230 (3,5%)."""

    prenume = forms.CharField(
        label="Prenume", max_length=80, required=True, widget=forms.TextInput(attrs=_IN)
    )
    nume = forms.CharField(
        label="Nume", max_length=80, required=True, widget=forms.TextInput(attrs=_IN)
    )
    cnp = forms.CharField(
        label="CNP",
        max_length=13,
        required=True,
        validators=[_validate_cnp_ro],
        widget=forms.TextInput(attrs=_IN),
    )
    adresa = forms.CharField(
        label="Adresă (str., nr., bl., sc., et., ap.)",
        max_length=500,
        required=True,
        widget=forms.Textarea(attrs=_TA),
    )
    judet = forms.CharField(
        label="Județ", max_length=120, required=True, widget=forms.TextInput(attrs=_IN)
    )
    localitate = forms.CharField(
        label="Localitate", max_length=120, required=True, widget=forms.TextInput(attrs=_IN)
    )
    email = forms.EmailField(label="E-mail", required=True, widget=forms.EmailInput(attrs=_IN))
    telefon = forms.CharField(
        label="Telefon", max_length=40, required=False, widget=forms.TextInput(attrs=_IN)
    )
    memoreaza_in_profil = forms.BooleanField(
        label="Memorează CNP și adresa în profilul meu (opțional)",
        required=False,
        help_text="Doar dacă ești autentificat. Poți actualiza sau goli câmpurile din pagina de editare cont.",
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not user or not getattr(user, "is_authenticated", False):
            self.fields.pop("memoreaza_in_profil", None)


class ContractSponsorizareForm(forms.Form):
    denumire_firma = forms.CharField(
        label="Denumire firmă", max_length=255, required=True, widget=forms.TextInput(attrs=_IN)
    )
    cui = forms.CharField(
        label="CUI / CIF", max_length=32, required=True, widget=forms.TextInput(attrs=_IN)
    )
    nr_reg_com = forms.CharField(
        label="Nr. Reg. Com. / J", max_length=64, required=True, widget=forms.TextInput(attrs=_IN)
    )
    adresa_firma = forms.CharField(
        label="Adresă sediu social",
        max_length=500,
        required=True,
        widget=forms.Textarea(attrs=_TA),
    )
    reprezentant = forms.CharField(
        label="Reprezentant legal", max_length=255, required=True, widget=forms.TextInput(attrs=_IN)
    )
    suma = forms.CharField(
        label="Valoare sponsorizare (RON, text)",
        max_length=32,
        required=True,
        widget=forms.TextInput(attrs=_IN),
    )
    descriere = forms.CharField(
        label="Descriere scurtă obiect sponsorizare",
        max_length=800,
        required=False,
        widget=forms.Textarea(attrs=_TA),
        initial="Sprijin pentru activitățile platformei EU-ADOPT (proiect adopție, transport educativ, cuști autocar).",
    )
    memoreaza_in_profil = forms.BooleanField(
        label="Memorează date firmă în profilul meu (opțional)",
        required=False,
    )

    def __init__(self, *args, user=None, **kwargs):
        super().__init__(*args, **kwargs)
        if not user or not getattr(user, "is_authenticated", False):
            self.fields.pop("memoreaza_in_profil", None)
