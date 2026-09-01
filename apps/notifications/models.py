"""Notification models.

Stores notifications delivered to users, primarily triggered by alert conditions.
"""

from django.conf import settings
from django.db import models


class Notification(models.Model):
    """A notification delivered to a user."""

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
    title = models.CharField(
        max_length=200,
        help_text="Notification title.",
    )
    message = models.TextField(
        help_text="Notification body text.",
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

    def __str__(self) -> str:
        return f"{self.user.username} - {self.title}"
