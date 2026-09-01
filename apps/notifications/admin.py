from django.contrib import admin

from apps.notifications.models import Notification


@admin.register(Notification)
class NotificationAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "title",
        "alert",
        "is_read",
        "created_at",
    )
    list_filter = ("is_read", "created_at")
    search_fields = ("user__username", "title")
    ordering = ("-created_at",)
    readonly_fields = ("created_at",)
    raw_id_fields = ("user", "alert")
