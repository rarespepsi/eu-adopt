from django.contrib import admin
from .models import Contest, ReferralVisit, Profile


@admin.register(Profile)
class ProfileAdmin(admin.ModelAdmin):
    list_display = ('user', 'account_type', 'phone')
    list_filter = ('account_type',)
    search_fields = ('user__username', 'user__email', 'company_name', 'organization_name')


@admin.register(Contest)
class ContestAdmin(admin.ModelAdmin):
    list_display = ('name', 'start_date', 'end_date', 'is_active')
    list_filter = ('is_active', 'start_date', 'end_date')
    search_fields = ('name', 'prize_title')
    date_hierarchy = 'start_date'


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
