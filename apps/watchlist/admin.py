from django.contrib import admin

from apps.watchlist.models import Watchlist, WatchlistItem


class WatchlistItemInline(admin.TabularInline):
    model = WatchlistItem
    extra = 0
    raw_id_fields = ("security",)
    readonly_fields = ("added_at",)


@admin.register(Watchlist)
class WatchlistAdmin(admin.ModelAdmin):
    list_display = ("name", "user", "item_count", "created_at", "updated_at")
    search_fields = ("name", "user__username")
    list_filter = ("created_at",)
    ordering = ("-updated_at",)
    readonly_fields = ("created_at", "updated_at")
    inlines = [WatchlistItemInline]

    def item_count(self, obj: Watchlist) -> int:
        return obj.items.count()

    item_count.short_description = "Items"


@admin.register(WatchlistItem)
class WatchlistItemAdmin(admin.ModelAdmin):
    list_display = ("watchlist", "security", "note", "added_at")
    search_fields = ("watchlist__name", "security__symbol")
    list_filter = ("added_at",)
    raw_id_fields = ("watchlist", "security")
    readonly_fields = ("added_at",)
