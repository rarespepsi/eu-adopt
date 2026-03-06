from django.contrib import admin
from django import forms
from django.conf import settings
from .models import Contest, ReferralVisit, Profile, Pet, PetFavorite, AdoptionRequest, UserProfile, BeneficiaryPartner, CouponClaim


class PetAdminForm(forms.ModelForm):
    """Validare: adăpost public → sterilizat, CIP și carnet sănătate obligatorii."""

    class Meta:
        model = Pet
        fields = "__all__"

    def clean(self):
        data = super().clean()
        if data.get("adapost_public"):
            if data.get("sterilizat") is None:
                self.add_error("sterilizat", "Pentru adăpost public, câmpul Sterilizat/Castrat este obligatoriu.")
            if not (data.get("cip") or "").strip():
                self.add_error("cip", "Pentru adăpost public, numărul CIP este obligatoriu.")
            if not (data.get("carnet_sanatate") or "").strip():
                self.add_error("carnet_sanatate", "Pentru adăpost public, carnetul de sănătate este obligatoriu.")
        return data


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_type', 'phone', 'email_opt_in_wishlist', 'pf_daily_limit_display', 'last_wishlist_email_at', 'last_followup_30d_at')
    list_filter = ('account_type', 'email_opt_in_wishlist')
    search_fields = ('user__username', 'user__email', 'company_name', 'organization_name')

    def pf_daily_limit_display(self, obj):
        if obj and getattr(obj, 'account_type', None) == 'individual':
            limit = getattr(settings, 'PF_DAILY_ADOPTION_REQUEST_LIMIT', 5)
            return f"max {limit}/24h"
        return "—"
    pf_daily_limit_display.short_description = "Limită cereri (PF)"


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('name', 'prize_title')
    date_hierarchy = 'start_date'


@admin.register(Pet)
class PetAdmin(admin.ModelAdmin):
    form = PetAdminForm
    list_display = ("nume", "tip", "rasa", "status", "adoption_status", "judet", "adapost_public", "data_adaugare")
    list_filter = ("tip", "status", "adoption_status", "judet", "adapost_public")
    search_fields = ("nume", "rasa", "ong_email")
    prepopulated_fields = {"slug": ("nume",)}
    readonly_fields = ("data_adaugare", "cereri_summary")
    actions = ["mark_as_adopted"]

    @admin.action(description="Marchează ca adoptat")
    def mark_as_adopted(self, request, queryset):
        updated = queryset.update(status="adopted", adoption_status="adopted")
        self.message_user(request, f"{updated} animal(e) marcat(e) ca adoptat(e).")

    fieldsets = (
        (None, {"fields": ("nume", "slug", "rasa", "tip", "tip_altele", "varsta_aproximativa", "sex", "marime", "status", "adoption_status", "descriere", "tags")}),
        ("Cereri adopție", {"fields": ("cereri_summary", "reserved_for_request")}),
        ("Poze (max 3)", {"fields": ("imagine", "imagine_2", "imagine_3", "imagine_fallback", "video_url")}),
        (
            "Sanitar (obligatoriu pentru adăpost public; casutele pot fi completate de oricine)",
            {
                "fields": ("adapost_public", "sterilizat", "sterilized_status", "vaccinated_status", "dewormed_status", "microchipped_status", "cip", "carnet_sanatate", "vaccin"),
                "description": "Adăposturile publice au obligația să completeze sterilizat, CIP și carnet de sănătate. Persoanele fizice și ONG/asociațiile pot completa la fel casutele de mai jos (vaccin, carnet, etc.).",
            },
        ),
        (
            "Descriere structurată (temperament, stil viață, compatibilitate, medical, educație)",
            {
                "fields": (
                    "prietenos_cu_oamenii", "prietenos_cu_copiii", "timid", "protector", "energic_jucaus",
                    "linistit", "independent", "cauta_atentie", "latra_des", "calm_in_casa",
                    "potrivit_apartament", "prefera_curte", "poate_sta_afara", "poate_sta_interior",
                    "obisnuit_in_lesa", "merge_bine_la_plimbare", "necesita_miscare_multa",
                    "potrivit_persoane_varstnice", "potrivit_familie_activa",
                    "ok_cu_alti_caini", "ok_cu_pisici", "prefera_singurul_animal", "accepta_vizitatori", "necesita_socializare",
                    "vaccinat", "deparazitat", "microcipat", "are_pasaport", "necesita_tratament", "sensibil_zgomote",
                    "stie_comenzi_baza", "face_nevoile_afara", "invata_repede", "necesita_dresaj", "nu_roade", "obisnuit_masina",
                    "recomandat_prima_adoptie",
                    "descriere_personalitate",
                ),
            },
        ),
        (
            "Matching (potrivire – Potrivirea perfectă)",
            {"fields": ("energy_level", "size_category", "age_category", "good_with_children", "good_with_dogs", "good_with_cats", "housing_fit", "experience_required", "attention_need")},
        ),
        ("Locație / contact", {"fields": ("judet", "ong_email", "ong_address", "ong_contact_person", "ong_phone", "ong_visiting_hours")}),
        ("Alte", {"fields": ("featured", "added_by_user", "data_adaugare")}),
    )


@admin.register(AdoptionRequest)
class AdoptionRequestAdmin(admin.ModelAdmin):
    list_display = ("pet", "adopter", "status", "queue_position", "nume_complet", "email", "data_cerere", "approved_at", "finalized_at", "finalized_by")
    list_filter = ("status", "data_cerere")
    search_fields = ("pet__nume", "nume_complet", "email", "adopter__email")
    readonly_fields = ("data_cerere", "approved_at", "finalized_at", "cancelled_at")
    raw_id_fields = ("pet", "adopter", "owner", "finalized_by")
    date_hierarchy = "data_cerere"
    ordering = ["pet", "queue_position"]
    actions = ["approve_first_request_for_selected_pets"]

    @admin.action(description="Aprobă prima cerere (rezervă animalul) pentru animalele selectate")
    def approve_first_request_for_selected_pets(self, request, queryset):
        from .adoption_platform import approve_first_adoption_request
        pets_done = set()
        for ar in queryset.select_related("pet"):
            pet = ar.pet
            if pet.pk in pets_done:
                continue
            success, err, _ = approve_first_adoption_request(pet)
            if success:
                pets_done.add(pet.pk)
        if pets_done:
            self.message_user(request, f"Aprobată prima cerere pentru {len(pets_done)} animal(e).")
        else:
            self.message_user(request, "Nicio cerere aprobată (animal indisponibil sau fără cereri pending).", level=40)


@admin.register(PetFavorite)
class PetFavoriteAdmin(admin.ModelAdmin):
    list_display = ("user", "pet", "created_at", "notified_adopted", "reminder_72h_sent_at")
    list_filter = ("notified_adopted", "created_at")
    search_fields = ("user__email", "user__username", "pet__nume")
    readonly_fields = ("created_at",)
    date_hierarchy = "created_at"


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'nume', 'prenume', 'email', 'telefon', 'judet', 'oras', 'phone_verified')
    list_filter = ('phone_verified', 'judet')
    search_fields = ('user__username', 'user__email', 'nume', 'prenume', 'telefon')
    raw_id_fields = ('user',)


@admin.register(ReferralVisit)
class ReferralVisitAdmin(admin.ModelAdmin):
    list_display = ('ref_code', 'user', 'timestamp', 'counted', 'ip_hash')
    list_filter = ('counted', 'timestamp', 'ref_code')
    search_fields = ('ref_code', 'user__username', 'ip_hash')
    date_hierarchy = 'timestamp'
    readonly_fields = ('timestamp', 'ip_hash')
    
    def get_queryset(self, request):
        qs = super().get_queryset(request)
        return qs.select_related('user')


@admin.register(BeneficiaryPartner)
class BeneficiaryPartnerAdmin(admin.ModelAdmin):
    list_display = ("name", "category", "county", "city", "is_active", "order")
    list_filter = ("category", "is_active")
    search_fields = ("name", "city", "offer_text")
    list_editable = ("is_active", "order")


@admin.register(CouponClaim)
class CouponClaimAdmin(admin.ModelAdmin):
    list_display = ("user", "partner", "category", "status", "created_at")
    list_filter = ("category", "status", "created_at")
    search_fields = ("user__email", "user__username", "partner__name")
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "partner")
    date_hierarchy = "created_at"
