"""Corporate actions models.

Dividend and bonus data from NEPSE upstream.
Fields derived from get_company_financials() responses.
"""

from django.db import models


class Dividend(models.Model):
    """Dividend record for a listed security.

    Synced from company financial reports / upstream dividend data.
    """

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="dividends",
        help_text="The security this dividend belongs to.",
    )
    fiscal_year = models.CharField(
        max_length=20,
        help_text="Fiscal year (e.g., '2081/82').",
    )
    dividend_per_share = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dividend amount per share.",
    )
    bonus_shares = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Bonus shares per share held.",
    )
    announcement_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the dividend/bonus was announced.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fiscal_year"]
        verbose_name = "Dividend"
        verbose_name_plural = "Dividends"

    def __str__(self) -> str:
        return f"{self.security.symbol} - {self.fiscal_year}"


class BonusShare(models.Model):
    """Bonus share record for a listed security.

    Synced from company financial reports / upstream bonus data.
    """

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="bonus_shares",
        help_text="The security this bonus share belongs to.",
    )
    fiscal_year = models.CharField(
        max_length=20,
        help_text="Fiscal year (e.g., '2081/82').",
    )
    bonus_ratio = models.CharField(
        max_length=20,
        blank=True,
        default="",
        help_text="Bonus ratio (e.g., '1:1', '10%').",
    )
    announcement_date = models.DateField(
        null=True,
        blank=True,
        help_text="Date the bonus was announced.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-fiscal_year"]
        verbose_name = "Bonus Share"
        verbose_name_plural = "Bonus Shares"

    def __str__(self) -> str:
        return f"{self.security.symbol} - {self.fiscal_year} ({self.bonus_ratio})"
