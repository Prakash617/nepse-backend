"""Alert models.

User-owned price and market condition alerts for securities.
Supports flexible condition types, crossing operators, alert states,
frequency (one-time vs recurring), cooldowns, and notification preferences.
"""

from django.conf import settings
from django.db import models


class Alert(models.Model):
    """A user-defined price/market alert for a security."""

    class ConditionType(models.TextChoices):
        PRICE_ABOVE = "price_above", "Price Above (>=)"
        PRICE_BELOW = "price_below", "Price Below (<=)"
        PRICE_CROSS_ABOVE = "price_cross_above", "Crosses Above"
        PRICE_CROSS_BELOW = "price_cross_below", "Crosses Below"
        PERCENT_CHANGE_UP = "percent_change_up", "Gain % Above (>=)"
        PERCENT_CHANGE_DOWN = "percent_change_down", "Drop % Below (>=)"
        VOLUME_ABOVE = "volume_above", "Volume Above (>=)"
        PRICE_CHANGE_ABOVE = "price_change_above", "Point Change Above (>=)"
        PRICE_CHANGE_BELOW = "price_change_below", "Point Change Below (<=)"

    class AlertStatus(models.TextChoices):
        ACTIVE = "active", "Active"
        TRIGGERED = "triggered", "Triggered"
        PAUSED = "paused", "Paused"
        DISABLED = "disabled", "Disabled"

    class FrequencyType(models.TextChoices):
        ONCE = "once", "Once"
        RECURRING = "recurring", "Every time condition is met"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="The user who owns this alert.",
    )
    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="alerts",
        help_text="The security to monitor.",
    )
    condition = models.CharField(
        max_length=30,
        choices=ConditionType.choices,
        help_text="Type of condition to trigger the alert.",
    )
    threshold = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Threshold value for the condition.",
    )
    status = models.CharField(
        max_length=20,
        choices=AlertStatus.choices,
        default=AlertStatus.ACTIVE,
        db_index=True,
        help_text="Current lifecycle state of the alert.",
    )
    frequency = models.CharField(
        max_length=20,
        choices=FrequencyType.choices,
        default=FrequencyType.RECURRING,
        help_text="Whether the alert triggers once or repeatedly on crossing.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this alert is enabled.",
    )
    notify_browser_push = models.BooleanField(
        default=True,
        help_text="Send real browser/OS Web Push notifications when triggered.",
    )
    notify_in_app = models.BooleanField(
        default=True,
        help_text="Create persistent in-app notifications and real-time toasts.",
    )
    notify_telegram = models.BooleanField(
        default=True,
        help_text="Send instant Telegram bot notifications when triggered.",
    )
    cooldown_minutes = models.PositiveIntegerField(
        default=0,
        help_text="Minimum cooldown minutes between triggers (0 = instant).",
    )
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last time this alert was triggered.",
    )
    triggered_price = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Price when the alert was last triggered.",
    )
    trigger_count = models.PositiveIntegerField(
        default=0,
        help_text="Total number of times this alert has fired.",
    )
    notes = models.TextField(
        blank=True,
        default="",
        help_text="Optional user notes or description for this alert.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["security", "is_active", "status"]),
            models.Index(fields=["status"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - {self.security.symbol} {self.get_condition_display()} {self.threshold} ({self.status})"

    def pause(self) -> None:
        """Pause the alert."""
        self.status = self.AlertStatus.PAUSED
        self.is_active = False
        self.save(update_fields=["status", "is_active", "updated_at"])

    def resume(self) -> None:
        """Resume the alert."""
        self.status = self.AlertStatus.ACTIVE
        self.is_active = True
        self.save(update_fields=["status", "is_active", "updated_at"])


class AlertHistory(models.Model):
    """Historical audit log of alert triggers."""

    alert = models.ForeignKey(
        Alert,
        on_delete=models.CASCADE,
        related_name="history",
        help_text="The alert that triggered.",
    )
    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="alert_history",
    )
    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="alert_history",
    )
    triggered_at = models.DateTimeField(
        auto_now_add=True,
        db_index=True,
    )
    triggered_value = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Actual market value at the time of trigger.",
    )
    threshold = models.DecimalField(
        max_digits=14,
        decimal_places=2,
        help_text="Target threshold of the alert.",
    )
    condition = models.CharField(
        max_length=30,
        help_text="Condition operator.",
    )
    message = models.TextField(
        help_text="Formatted alert notification message.",
    )
    push_sent = models.BooleanField(
        default=False,
        help_text="Whether Web Push was dispatched.",
    )
    in_app_sent = models.BooleanField(
        default=True,
        help_text="Whether in-app notification was created.",
    )

    class Meta:
        ordering = ["-triggered_at"]
        verbose_name = "Alert History"
        verbose_name_plural = "Alert Histories"
        indexes = [
            models.Index(fields=["user", "-triggered_at"]),
            models.Index(fields=["alert", "-triggered_at"]),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol} triggered at {self.triggered_at} (Val: {self.triggered_value})"
