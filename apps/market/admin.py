from django.contrib import admin

from apps.market.models import MarketSnapshot


@admin.register(MarketSnapshot)
class MarketSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "trading_date",
        "close",
        "open",
        "high",
        "low",
        "total_volume",
        "total_turnover",
        "transactions",
        "point_change",
        "percentage_change",
    )
    search_fields = ("trading_date",)
    ordering = ("-trading_date",)
    readonly_fields = ("created_at", "updated_at")
