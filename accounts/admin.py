from django.contrib import admin
from django.contrib.auth import get_user_model
from .models import Profile, EmailDeliveryLog

User = get_user_model()


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ("user", "account_type")
    list_filter = ("account_type",)
    search_fields = ("user__username", "user__email")
    raw_id_fields = ("user",)


@admin.register(EmailDeliveryLog)
class EmailDeliveryLogAdmin(admin.ModelAdmin):
    list_display = ("to_email", "subject", "email_type", "status", "sent_at", "user")
    list_filter = ("status", "email_type")
    search_fields = ("to_email", "subject", "user__username", "error_message")
    raw_id_fields = ("user",)
    readonly_fields = ("sent_at",)
