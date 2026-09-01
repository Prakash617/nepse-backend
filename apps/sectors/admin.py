from django.contrib import admin

from apps.sectors.models import Sector


@admin.register(Sector)
class SectorAdmin(admin.ModelAdmin):
    list_display = ("nepse_id", "name", "display_name", "created_at")
    search_fields = ("name", "display_name")
    ordering = ("name",)
    readonly_fields = ("created_at", "updated_at")
