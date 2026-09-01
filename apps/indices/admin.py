from django.contrib import admin

from apps.indices.models import IndexSnapshot, MarketIndex


@admin.register(MarketIndex)
class MarketIndexAdmin(admin.ModelAdmin):
    list_display = ("nepse_id", "name", "created_at")
    search_fields = ("name",)
    ordering = ("nepse_id",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(IndexSnapshot)
class IndexSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "index",
        "trading_date",
        "close",
        "open",
        "high",
        "low",
        "volume",
        "point_change",
        "percentage_change",
    )
    list_filter = ("trading_date", "index")
    search_fields = ("index__name",)
    ordering = ("-trading_date", "index__name")
    raw_id_fields = ("index",)
    readonly_fields = ("created_at", "updated_at")
