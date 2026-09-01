"""Alert models.

User-owned price/condition alerts for securities.
When a condition is met, the alert fires and records the trigger time.
No upstream sync — purely user-created and evaluated against local price data.
"""

from django.conf import settings
from django.db import models


class Alert(models.Model):
    """A user-defined price alert for a security."""

    class ConditionType(models.TextChoices):
        PRICE_ABOVE = "price_above", "Price Above"
        PRICE_BELOW = "price_below", "Price Below"
        PERCENT_CHANGE_UP = "percent_change_up", "Percent Change Up"
        PERCENT_CHANGE_DOWN = "percent_change_down", "Percent Change Down"

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
        max_digits=12,
        decimal_places=2,
        help_text="Threshold value for the condition.",
    )
    is_active = models.BooleanField(
        default=True,
        help_text="Whether this alert is currently active.",
    )
    last_triggered_at = models.DateTimeField(
        null=True,
        blank=True,
        help_text="Timestamp of the last time this alert was triggered.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Alert"
        verbose_name_plural = "Alerts"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.security.symbol} {self.get_condition_display()} {self.threshold}"
