from django.contrib import admin

from apps.corporate_actions.models import BonusShare, Dividend


@admin.register(Dividend)
class DividendAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "fiscal_year",
        "dividend_per_share",
        "bonus_shares",
        "announcement_date",
    )
    list_filter = ("fiscal_year",)
    search_fields = ("security__symbol",)
    ordering = ("-fiscal_year", "security__symbol")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("security",)


@admin.register(BonusShare)
class BonusShareAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "fiscal_year",
        "bonus_ratio",
        "announcement_date",
    )
    list_filter = ("fiscal_year",)
    search_fields = ("security__symbol",)
    ordering = ("-fiscal_year", "security__symbol")
    readonly_fields = ("created_at", "updated_at")
    raw_id_fields = ("security",)
