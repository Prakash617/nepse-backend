from django.contrib import admin

from apps.alerts.models import Alert


@admin.register(Alert)
class AlertAdmin(admin.ModelAdmin):
    list_display = (
        "user",
        "security",
        "condition",
        "threshold",
        "is_active",
        "last_triggered_at",
        "created_at",
    )
    list_filter = ("condition", "is_active", "created_at")
    search_fields = ("user__username", "security__symbol")
    ordering = ("-created_at",)
    readonly_fields = ("last_triggered_at", "created_at", "updated_at")
    raw_id_fields = ("user", "security")
