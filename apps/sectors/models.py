"""Sector models.

Represents NEPSE market sectors (e.g., Commercial Banks, Hydro Power).
Fields derived from parse_sectors() upstream response.
"""

from django.db import models


class Sector(models.Model):
    """A NEPSE market sector."""

    nepse_id = models.PositiveIntegerField(
        unique=True,
        help_text="Upstream NEPSE sector ID.",
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Short sector name (e.g., 'Commercial Banks').",
    )
    display_name = models.CharField(
        max_length=200,
        blank=True,
        default="",
        help_text="Human-readable display name.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["name"]
        verbose_name = "Sector"
        verbose_name_plural = "Sectors"

    def __str__(self) -> str:
        return self.name
