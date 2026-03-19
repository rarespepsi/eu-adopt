from django.contrib import admin
from .models import UserProfile, UserAdoption, UserPost, AdoptionRequest


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


@admin.register(UserPost)
class UserPostAdmin(admin.ModelAdmin):
    list_display = ("user", "post_type", "title", "is_published", "created_at")
    list_filter = ("post_type", "is_published")
    search_fields = ("title", "body", "user__email", "user__first_name", "user__last_name")
