"""Watchlist models.

User-owned watchlists for tracking securities of interest.
No upstream sync — purely user-created and managed.
"""

from django.conf import settings
from django.db import models


class Watchlist(models.Model):
    """A user's named watchlist of securities."""

    user = models.ForeignKey(
        settings.AUTH_USER_MODEL,
        on_delete=models.CASCADE,
        related_name="watchlists",
        help_text="The user who owns this watchlist.",
    )
    name = models.CharField(
        max_length=100,
        help_text="User-defined watchlist name.",
    )
    description = models.TextField(
        blank=True,
        default="",
        help_text="Optional description for this watchlist.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-updated_at"]
        unique_together = [("user", "name")]
        verbose_name = "Watchlist"
        verbose_name_plural = "Watchlists"

    def __str__(self) -> str:
        return f"{self.user.username} - {self.name}"


class WatchlistItem(models.Model):
    """A security added to a watchlist."""

    watchlist = models.ForeignKey(
        Watchlist,
        on_delete=models.CASCADE,
        related_name="items",
        help_text="The watchlist this item belongs to.",
    )
    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="watchlist_items",
        help_text="The security being tracked.",
    )
    note = models.CharField(
        max_length=300,
        blank=True,
        default="",
        help_text="Optional user note about this security.",
    )
    added_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-added_at"]
        unique_together = [("watchlist", "security")]
        verbose_name = "Watchlist Item"
        verbose_name_plural = "Watchlist Items"

    def __str__(self) -> str:
        return f"{self.watchlist.name} - {self.security.symbol}"
