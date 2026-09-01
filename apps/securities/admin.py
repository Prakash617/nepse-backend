from django.contrib import admin

from apps.securities.models import Security


@admin.register(Security)
class SecurityAdmin(admin.ModelAdmin):
    list_display = (
        "symbol",
        "company_name",
        "sector",
        "security_type",
        "listing_date",
        "nepse_id",
    )
    search_fields = ("symbol", "company_name")
    list_filter = ("security_type", "sector")
    ordering = ("symbol",)
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("sector",)
