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

# Pagina Add USER (staff): 4 tipuri colaborator (fără servicii în lista principală).
_COLLAB_RADIO_STAFF_ADD_USER = [
    (StaffOnboardingLead.COLLAB_CABINET, "CV"),
    (StaffOnboardingLead.COLLAB_MAGAZIN, "Magazin"),
    (StaffOnboardingLead.COLLAB_GROOMING, "Grooming"),
    (StaffOnboardingLead.COLLAB_TRANSPORT, "Transportator"),
]
_ADAPOST_SUBTYPE_RADIO = [
    (StaffOnboardingLead.COLLAB_ADPUB, "ADPUB"),
    (StaffOnboardingLead.COLLAB_ADPRV, "ADPRV"),
]

SEGMENT_KEYS = frozenset(dict(SEGMENT_CHOICES).keys())


class StaffOnboardingLeadForm(forms.ModelForm):
    """Prospect staff — câmpuri aliniate la fișele de înregistrare (PF / ONG / colaborator / adăpost)."""

    segments = forms.MultipleChoiceField(
        label="Segmente / noutăți email (ca la înregistrare)",
        choices=SEGMENT_CHOICES,
        required=False,
        widget=forms.CheckboxSelectMultiple,
    )

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
            "vet_prospect_kind",
            "segments",
            "marketing_emails_requested",
            "notes",
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
            "vet_prospect_kind": forms.RadioSelect,
            "is_public_shelter": forms.CheckboxInput(attrs={"class": "manual-checkbox"}),
            "company_cui_has_ro": forms.CheckboxInput(attrs={"class": "manual-checkbox"}),
            "marketing_emails_requested": forms.CheckboxInput(attrs={"class": "manual-checkbox"}),
            "notes": forms.Textarea(attrs={"rows": 4, "cols": 56, "class": "manual-notes-text"}),
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
            "vet_prospect_kind": "Prospect cabinet (clinică vs farmacie)",
            "marketing_emails_requested": "Notificări email EU-Adopt (noutăți — ca la înregistrare)",
            "notes": "Notă internă staff",
        }

    def __init__(self, *args, **kwargs):
        super().__init__(*args, **kwargs)
        collab_choices = list(_COLLAB_RADIO_STAFF_ADD_USER)
        inst = getattr(self, "instance", None)
        if inst and getattr(inst, "pk", None):
            s = (inst.collaborator_subtype or "").strip()
            if s == StaffOnboardingLead.COLLAB_SERVICII:
                label = dict(StaffOnboardingLead.COLLAB_SUBTYPE_CHOICES).get(s, s)
                collab_choices = [(s, label)] + collab_choices
        self.fields["collaborator_subtype"].choices = collab_choices + list(_ADAPOST_SUBTYPE_RADIO)
        self.fields["collaborator_subtype"].required = False
        self.fields["vet_prospect_kind"].choices = [
            (StaffOnboardingLead.VET_PROSPECT_CV, "CV — clinică veterinară"),
            (StaffOnboardingLead.VET_PROSPECT_FV, "FV — farmacie veterinară"),
        ]
        self.fields["vet_prospect_kind"].required = False
        # Prospect nou: rol implicit PF ca să nu rămână ascunse toate secțiunile specifice rolului.
        if not self.data and not getattr(self.instance, "pk", None):
            self.initial.setdefault("account_kind", StaffOnboardingLead.KIND_PF)
        if self.instance and getattr(self.instance, "pk", None):
            seg = self.instance.segments
            if isinstance(seg, list) and seg:
                valid = [x for x in seg if x in SEGMENT_KEYS]
                if valid:
                    self.initial["segments"] = valid
            if (
                self.instance.account_kind == StaffOnboardingLead.KIND_COLLAB
                and (self.instance.collaborator_subtype or "").strip() == StaffOnboardingLead.COLLAB_CABINET
                and (self.instance.vet_prospect_kind or "").strip() not in (
                    StaffOnboardingLead.VET_PROSPECT_CV,
                    StaffOnboardingLead.VET_PROSPECT_FV,
                )
            ):
                self.initial.setdefault("vet_prospect_kind", StaffOnboardingLead.VET_PROSPECT_CV)

    def clean(self):
        cleaned = super().clean()
        kind = cleaned.get("account_kind")
        sub = (cleaned.get("collaborator_subtype") or "").strip()
        if kind == StaffOnboardingLead.KIND_COLLAB:
            if not sub:
                self.add_error("collaborator_subtype", "Alege unul dintre tipurile de colaborator.")
            elif sub in (StaffOnboardingLead.COLLAB_ADPUB, StaffOnboardingLead.COLLAB_ADPRV):
                self.add_error("collaborator_subtype", "ADPUB/ADPRV sunt doar pentru tipul Adăpost.")
        elif kind == StaffOnboardingLead.KIND_ADAPOST:
            if sub not in (StaffOnboardingLead.COLLAB_ADPUB, StaffOnboardingLead.COLLAB_ADPRV):
                self.add_error("collaborator_subtype", "Alege ADPUB (public) sau ADPRV (privat).")
        else:
            cleaned["collaborator_subtype"] = ""

        segs = cleaned.get("segments")
        if not segs:
            cleaned["segments"] = []
        elif isinstance(segs, tuple):
            cleaned["segments"] = list(segs)
        else:
            cleaned["segments"] = list(segs)

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
        elif kind == StaffOnboardingLead.KIND_ADAPOST and sub in (
            StaffOnboardingLead.COLLAB_ADPUB,
            StaffOnboardingLead.COLLAB_ADPRV,
        ):
            cleaned["is_public_shelter"] = sub == StaffOnboardingLead.COLLAB_ADPUB

        sub_final = (cleaned.get("collaborator_subtype") or "").strip()
        if kind == StaffOnboardingLead.KIND_COLLAB and sub_final == StaffOnboardingLead.COLLAB_CABINET:
            vk = (cleaned.get("vet_prospect_kind") or "").strip()
            if vk == StaffOnboardingLead.VET_PROSPECT_FV:
                cleaned["vet_prospect_kind"] = StaffOnboardingLead.VET_PROSPECT_FV
            else:
                cleaned["vet_prospect_kind"] = StaffOnboardingLead.VET_PROSPECT_CV
        else:
            cleaned["vet_prospect_kind"] = ""

        return cleaned
