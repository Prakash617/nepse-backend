"""Notification models.

Stores notifications delivered to users, triggered by alerts, market events, watchlists, or system messages.
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A notification delivered to a user."""

    class NotificationType(models.TextChoices):
        PRICE_ALERT = "price_alert", "Price Alert"
        PERCENTAGE_ALERT = "percentage_alert", "Percentage Alert"
        VOLUME_ALERT = "volume_alert", "Volume Alert"
        WATCHLIST_EVENT = "watchlist_event", "Watchlist Event"
        SYSTEM = "system", "System"
        MARKET = "market", "Market"

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="notifications",
        help_text="The user receiving this notification.",
    )
    alert = models.ForeignKey(
        "alerts.Alert",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="The alert that triggered this notification, if any.",
    )
    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="notifications",
        help_text="The security related to this notification, if any.",
    )
    notification_type = models.CharField(
        max_length=30,
        choices=NotificationType.choices,
        default=NotificationType.SYSTEM,
        help_text="Category/type of notification.",
    )
    title = models.CharField(
        max_length=200,
        help_text="Notification title.",
    )
    message = models.TextField(
        help_text="Notification body text.",
    )
    data = models.JSONField(
        default=dict,
        blank=True,
        help_text="Structured event metadata (e.g., symbol, price, target).",
    )
    is_read = models.BooleanField(
        default=False,
        help_text="Whether the user has read this notification.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Notification"
        verbose_name_plural = "Notifications"
        indexes = [
            models.Index(fields=["user", "is_read"]),
            models.Index(fields=["user", "created_at"]),
            models.Index(fields=["user", "is_read", "created_at"]),
            models.Index(fields=["notification_type"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - [{self.notification_type}] {self.title}"


class PushSubscription(models.Model):
    """Stores Web Push API subscriptions for browser/device push notifications."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="push_subscriptions",
        help_text="The user this push subscription belongs to.",
    )
    endpoint = models.TextField(
        help_text="Unique push subscription endpoint URL provided by the browser push service.",
    )
    p256dh = models.CharField(
        max_length=255,
        help_text="Client P-256 public key from subscription keys.",
    )
    auth = models.CharField(
        max_length=255,
        help_text="Client authentication secret from subscription keys.",
    )
    user_agent = models.TextField(
        blank=True,
        default="",
        help_text="User agent string of the subscribing device/browser.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this push subscription is active and eligible to receive pushes.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Push Subscription"
        verbose_name_plural = "Push Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "endpoint"],
                name="unique_user_push_endpoint",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["endpoint"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - PushSubscription ({'active' if self.is_active else 'inactive'})"


class TelegramSubscription(models.Model):
    """Stores user Telegram chat bindings for bot notifications."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="telegram_subscriptions",
        help_text="The user this Telegram subscription belongs to.",
    )
    chat_id = models.CharField(
        max_length=100,
        help_text="Telegram chat ID for delivering messages.",
    )
    username = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Telegram username (e.g. @prakash).",
    )
    first_name = models.CharField(
        max_length=255,
        blank=True,
        default="",
        help_text="Telegram user first name.",
    )
    is_active = models.BooleanField(
        default=True,
        db_index=True,
        help_text="Whether this Telegram subscription is active.",
    )
    verification_code = models.CharField(
        max_length=64,
        blank=True,
        default="",
        help_text="One-time code for account linking via /start <code>.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-created_at"]
        verbose_name = "Telegram Subscription"
        verbose_name_plural = "Telegram Subscriptions"
        constraints = [
            models.UniqueConstraint(
                fields=["user", "chat_id"],
                name="unique_user_telegram_chat",
            )
        ]
        indexes = [
            models.Index(fields=["user", "is_active"]),
            models.Index(fields=["chat_id"]),
            models.Index(fields=["verification_code"]),
        ]

    def __str__(self) -> str:
        return f"{self.user.username} - Telegram ({self.chat_id}) {'active' if self.is_active else 'inactive'}"



