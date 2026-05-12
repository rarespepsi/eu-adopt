from django import forms

from home.models import StaffOnboardingLead

SEGMENT_CHOICES = [
    ("noutati_adoptii", "Noutăți adopții / animale"),
    ("noutati_transport", "Noutăți transport"),
    ("noutati_ong_adapost", "Noutăți ONG / adăposturi"),
    ("noutati_colaboratori_servicii", "Noutăți colaboratori servicii"),
    ("noutati_magazin_grooming", "Noutăți magazin / grooming"),
    ("noutati_evenimente_site", "Evenimente site / EU-ADOPT"),
]

_COLLAB_RADIO = [
    (StaffOnboardingLead.COLLAB_CABINET, "Cabinet veterinar"),
    (StaffOnboardingLead.COLLAB_CV, "CV"),
    (StaffOnboardingLead.COLLAB_SERVICII, "Servicii (altele)"),
    (StaffOnboardingLead.COLLAB_MAGAZIN, "Magazin / grooming"),
    (StaffOnboardingLead.COLLAB_TRANSPORT, "Transportator"),
]


class StaffOnboardingLeadForm(forms.ModelForm):
    class Meta:
        model = StaffOnboardingLead
        fields = [
            "email",
            "phone",
            "account_kind",
            "display_name",
            "username_suggested",
            "first_name",
            "last_name",
            "judet",
            "oras",
            "org_display_name",
            "is_public_shelter",
            "company_legal_name",
            "company_cui",
            "company_cui_has_ro",
            "company_reg_com",
            "company_address",
            "company_representative",
            "company_judet",
            "company_oras",
            "collaborator_subtype",
        ]
        widgets = {
            "judet": forms.TextInput(
                attrs={
                    "list": "county-list-adduser-manual",
                    "autocomplete": "off",
                    "placeholder": "Scrie sau alege din listă",
                }
            ),
            "oras": forms.TextInput(
                attrs={
                    "list": "city-list-adduser-manual",
                    "autocomplete": "off",
                    "placeholder": "După județ: alege sau scrie",
                }
            ),
            "company_judet": forms.TextInput(
                attrs={
                    "list": "county-list-adduser-co",
                    "autocomplete": "off",
                    "placeholder": "Scrie sau alege din listă",
                }
            ),
            "company_oras": forms.TextInput(
                attrs={
                    "list": "city-list-adduser-co",
                    "autocomplete": "off",
                    "placeholder": "După județ: alege sau scrie",
                }
            ),
            "collaborator_subtype": forms.RadioSelect,
            "is_public_shelter": forms.CheckboxInput(attrs={"class": "manual-checkbox"}),
            "company_cui_has_ro": forms.CheckboxInput(attrs={"class": "manual-checkbox"}),
        }
        labels = {
            "email": "E-mail",
            "phone": "Telefon",
            "account_kind": "Rol țintă în site",
            "display_name": "Nume afișat / persoană contact",
            "username_suggested": "Username propus (login)",
            "first_name": "Prenume",
            "last_name": "Nume",
            "judet": "Județ (reședință)",
            "oras": "Oraș / localitate (reședință)",
            "org_display_name": "Denumire organizație (ONG / adăpost / firmă)",
            "is_public_shelter": "Adăpost public (ONG)",
            "company_legal_name": "Denumire legală firmă / ONG",
            "company_cui": "CUI / CIF",
            "company_cui_has_ro": "CUI cu RO",
            "company_reg_com": "Nr. Reg. Com. / J",
            "company_address": "Adresă firmă",
            "company_representative": "Reprezentant legal",
            "company_judet": "Județ firmă",
            "company_oras": "Oraș / localitate firmă",
            "collaborator_subtype": "Tip colaborator",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        self.fields["collaborator_subtype"].choices = _COLLAB_RADIO
        self.fields["collaborator_subtype"].required = False

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("account_kind")
        sub = (cleaned.get("collaborator_subtype") or "").strip()
        if kind == StaffOnboardingLead.KIND_COLLAB:
            if not sub:
                self.add_error("collaborator_subtype", "Alege unul dintre tipurile de colaborator.")
        else:
            cleaned["collaborator_subtype"] = ""

        if kind == StaffOnboardingLead.KIND_PF:
            cleaned["org_display_name"] = ""
            cleaned["is_public_shelter"] = False
            for fn in (
                "company_legal_name",
                "company_cui",
                "company_reg_com",
                "company_address",
                "company_representative",
                "company_judet",
                "company_oras",
            ):
                cleaned[fn] = (cleaned.get(fn) or "").strip()
            cleaned["company_cui_has_ro"] = False

        if kind == StaffOnboardingLead.KIND_COLLAB:
            cleaned["is_public_shelter"] = False

        return cleaned
