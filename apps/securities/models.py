"""Security models.

Represents a listed security/instrument on NEPSE.
Fields derived from parse_securities_list() upstream response.
"""

from django.db import models


class Security(models.Model):
    """A listed security on NEPSE.

    Supports multiple security types (ordinary shares, debentures, mutual funds, etc.)
    based on actual upstream data. Sector is a ForeignKey with a nullable constraint
    because upstream sector data may be incomplete or use string names that don't
    exactly match our Sector records.
    """

    nepse_id = models.PositiveIntegerField(
        unique=True,
        help_text="Upstream NEPSE security/company ID.",
    )
    symbol = models.CharField(
        max_length=20,
        unique=True,
        db_index=True,
        help_text="Stock ticker symbol (e.g., 'NABIL').",
    )
    company_name = models.CharField(
        max_length=300,
        help_text="Full company/instrument name.",
    )
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="securities",
        help_text="Market sector this security belongs to.",
    )
    security_type = models.CharField(
        max_length=50,
        blank=True,
        default="",
        help_text="Type of security (e.g., 'Ordinary Share', 'Debenture').",
    )
    listing_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the security was listed on NEPSE.",
    )
    paid_up_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Paid-up value per share.",
    )
    face_value = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Face value per share.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["symbol"]
        verbose_name = "Security"
        verbose_name_plural = "Securities"

    def __str__(self) -> str:
        return f"{self.symbol} - {self.company_name}"
