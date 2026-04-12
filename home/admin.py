from datetime import timedelta

from django.contrib import admin
from django.utils import timezone
from .models import (
    UserProfile,
    UserAdoption,
    UserPost,
    AdoptionRequest,
    UserInboxNotification,
    CollabServiceMessage,
    CollaboratorServiceOffer,
    CollaboratorOfferClaim,
    PromoA2Order,
    ReclamaSlotNote,
    PublicitateOrder,
    PublicitateOrderLine,
    TransportVeterinaryRequest,
    TransportOperatorProfile,
    TransportDispatchJob,
    TransportDispatchRecipient,
    TransportTripRating,
)


@admin.register(UserProfile)
class UserProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "phone", "oras", "created_at")
    search_fields = ("user__email", "user__first_name", "user__last_name", "phone", "oras")


@admin.register(UserAdoption)
class UserAdoptionAdmin(admin.ModelAdmin):
    list_display = ("user", "animal_name", "animal_type", "status", "requested_at")
    list_filter = ("status", "animal_type", "source")
    search_fields = ("user__email", "user__first_name", "user__last_name", "animal_name", "source")


@admin.register(UserInboxNotification)
class UserInboxNotificationAdmin(admin.ModelAdmin):
    list_display = ("id", "user", "kind", "title", "is_read", "created_at")
    list_filter = ("is_read", "kind")
    search_fields = ("title", "body", "user__username", "user__email")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at",)


@admin.register(AdoptionRequest)
class AdoptionRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "animal", "adopter", "status", "accepted_at", "created_at")
    list_filter = ("status",)
    search_fields = ("animal__name", "adopter__email", "adopter__username")
    raw_id_fields = ("animal", "adopter")


@admin.register(CollabServiceMessage)
class CollabServiceMessageAdmin(admin.ModelAdmin):
    list_display = ("id", "collaborator", "context_type", "context_ref", "sender", "receiver", "is_read", "created_at")
    list_filter = ("context_type", "is_read")
    search_fields = ("body", "context_ref", "collaborator__username", "sender__username", "receiver__username")
    raw_id_fields = ("collaborator", "sender", "receiver")


@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ("user", "post_type", "title", "is_published", "created_at")
    list_filter = ("post_type", "is_published")
    search_fields = ("title", "body", "user__email", "user__first_name", "user__last_name")


@admin.register(CollaboratorServiceOffer)
class CollaboratorServiceOfferAdmin(admin.ModelAdmin):
    list_display = (
        "title",
        "collaborator",
        "partner_kind",
        "target_species",
        "target_size",
        "target_age_band",
        "external_url",
        "product_sheet",
        "valid_from",
        "valid_until",
        "quantity_available",
        "discount_percent",
        "is_active",
        "expiry_notice_sent_for_valid_until",
        "low_stock_notice_sent",
        "created_at",
    )
    list_filter = ("is_active", "partner_kind", "target_species")
    search_fields = ("title", "description", "external_url", "collaborator__username")
    raw_id_fields = ("collaborator",)


@admin.register(CollaboratorOfferClaim)
class CollaboratorOfferClaimAdmin(admin.ModelAdmin):
    list_display = ("code", "offer", "buyer_email", "buyer_name_snapshot", "created_at")
    list_filter = ("created_at",)
    search_fields = ("code", "buyer_email", "buyer_name_snapshot", "offer__title")
    raw_id_fields = ("offer", "buyer_user")
    readonly_fields = ("created_at",)


@admin.register(PromoA2Order)
class PromoA2OrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "pet",
        "payer_email",
        "package",
        "quantity",
        "total_price",
        "status",
        "start_date",
        "starts_at",
        "ends_at",
        "summary_sent_at",
        "created_at",
    )
    list_filter = ("status", "package", "payment_provider")
    search_fields = ("payer_email", "payer_name_snapshot", "payment_ref", "pet__name")
    raw_id_fields = ("pet", "payer_user")


@admin.register(ReclamaSlotNote)
class ReclamaSlotNoteAdmin(admin.ModelAdmin):
    list_display = ("section", "slot_code", "updated_by", "updated_at")
    list_filter = ("section",)
    search_fields = ("section", "slot_code", "text")
    raw_id_fields = ("updated_by",)


class PublicitateOrderLineInline(admin.TabularInline):
    model = PublicitateOrderLine
    extra = 0
    readonly_fields = ("section", "slot_code", "title_snapshot", "unit_label", "unit_price_lei", "quantity", "line_total_lei")
    can_delete = False


@admin.register(PublicitateOrder)
class PublicitateOrderAdmin(admin.ModelAdmin):
    list_display = (
        "id",
        "user",
        "status",
        "total_lei",
        "payment_provider",
        "payment_ref",
        "paid_at",
        "created_at",
    )
    list_filter = ("status", "payment_provider")
    search_fields = ("user__username", "user__email", "payment_ref")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "paid_at")
    inlines = [PublicitateOrderLineInline]


def _block_transport_operators(queryset, days: int):
    now = timezone.now()
    until = now + timedelta(days=days)
    for obj in queryset:
        obj.block_count += 1
        obj.blocked_until = until
        if obj.block_count >= 3:
            obj.removed_after_third_block = True
            obj.approval_status = TransportOperatorProfile.APPROVAL_INACTIVE
        obj.save()


@admin.action(description="Blochează 7 zile (increment blocare)")
def transport_op_block_7(modeladmin, request, queryset):
    _block_transport_operators(queryset, 7)


@admin.action(description="Blochează 14 zile (increment blocare)")
def transport_op_block_14(modeladmin, request, queryset):
    _block_transport_operators(queryset, 14)


@admin.action(description="Blochează 21 zile (increment blocare)")
def transport_op_block_21(modeladmin, request, queryset):
    _block_transport_operators(queryset, 21)


@admin.register(TransportOperatorProfile)
class TransportOperatorProfileAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "approval_status",
        "transport_national",
        "transport_international",
        "max_caini",
        "max_pisici",
        "block_count",
        "blocked_until",
        "removed_after_third_block",
        "rating_count",
        "updated_at",
    )
    # Bife + status editabile din listă → Salvează, fără să deschizi formularul complet
    list_display_links = ("user",)
    list_editable = ("approval_status", "transport_national", "transport_international")
    list_filter = ("approval_status", "transport_national", "transport_international")
    search_fields = ("user__email", "user__username", "user__first_name", "user__last_name")
    raw_id_fields = ("user",)
    readonly_fields = ("created_at", "updated_at", "rating_sum", "rating_count")
    actions = (transport_op_block_7, transport_op_block_14, transport_op_block_21)


@admin.register(TransportDispatchJob)
class TransportDispatchJobAdmin(admin.ModelAdmin):
    list_display = ("id", "tvr", "status", "assigned_transporter", "expires_at", "reopen_count", "updated_at")
    list_filter = ("status",)
    raw_id_fields = ("tvr", "assigned_transporter")
    search_fields = ("tvr__judet", "tvr__oras")


@admin.register(TransportDispatchRecipient)
class TransportDispatchRecipientAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "transporter", "status", "updated_at")
    list_filter = ("status",)
    raw_id_fields = ("job", "transporter")


@admin.register(TransportTripRating)
class TransportTripRatingAdmin(admin.ModelAdmin):
    list_display = ("id", "job", "from_user", "to_user", "direction", "stars", "visible_to_public_profile", "created_at")
    list_filter = ("direction", "visible_to_public_profile")
    raw_id_fields = ("job", "from_user", "to_user")


@admin.register(TransportVeterinaryRequest)
class TransportVeterinaryRequestAdmin(admin.ModelAdmin):
    list_display = ("id", "judet", "oras", "user", "related_animal", "nr_caini", "created_at")
    list_filter = ("judet",)
    search_fields = ("judet", "oras", "plecare", "sosire", "user__email", "user__username")
    raw_id_fields = ("user", "related_animal")
    readonly_fields = ("created_at",)
