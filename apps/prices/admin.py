from django.contrib import admin

from apps.prices.models import DailyPrice, IntradayPrice


@admin.register(DailyPrice)
class DailyPriceAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "trading_date",
        "ltp",
        "open",
        "high",
        "low",
        "close",
        "volume",
        "turnover",
    )
    list_filter = ("trading_date",)
    search_fields = ("security__symbol",)
    ordering = ("-trading_date", "security__symbol")
    raw_id_fields = ("security",)
    readonly_fields = ("created_at", "updated_at")


@admin.register(IntradayPrice)
class IntradayPriceAdmin(admin.ModelAdmin):
    list_display = ("security", "timestamp", "ltp", "volume", "turnover")
    list_filter = ("timestamp",)
    search_fields = ("security__symbol",)
    ordering = ("-timestamp",)
    raw_id_fields = ("security",)
    readonly_fields = ("created_at",)
