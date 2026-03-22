from django.contrib import admin
from .models import (
    UserProfile,
    UserAdoption,
    UserPost,
    AdoptionRequest,
    CollabServiceMessage,
    CollaboratorServiceOffer,
    CollaboratorOfferClaim,
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
        "valid_from",
        "valid_until",
        "quantity_available",
        "discount_percent",
        "is_active",
        "expiry_notice_sent_for_valid_until",
        "low_stock_notice_sent",
        "created_at",
    )
    list_filter = ("is_active",)
    search_fields = ("title", "description", "collaborator__username")
    raw_id_fields = ("collaborator",)


@admin.register(CollaboratorOfferClaim)
class CollaboratorOfferClaimAdmin(admin.ModelAdmin):
    list_display = ("code", "offer", "buyer_email", "buyer_name_snapshot", "created_at")
    list_filter = ("created_at",)
    search_fields = ("code", "buyer_email", "buyer_name_snapshot", "offer__title")
    raw_id_fields = ("offer", "buyer_user")
    readonly_fields = ("created_at",)
