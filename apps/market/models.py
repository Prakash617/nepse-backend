"""Market models.

Market-level aggregate data (daily snapshots).
Fields derived from parse_market_summary() upstream response.
"""

from django.db import models


class MarketSnapshot(models.Model):
    """Daily market-wide aggregate snapshot.

    One record per trading day, derived from parse_market_summary().
    Stores the end-of-day aggregate values for the entire NEPSE market.
    """

    trading_date = models.DateField(
        unique=True,
        db_index=True,
        help_text="The business/trading date.",
    )
    total_volume = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Total shares traded across the market.",
    )
    total_turnover = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total value traded across the market (NPR).",
    )
    transactions = models.PositiveIntegerField(
        null=True,
        blank=True,
        help_text="Total number of transactions.",
    )
    open = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market opening index value.",
    )
    high = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market highest index value.",
    )
    low = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market lowest index value.",
    )
    close = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Market closing index value.",
    )
    previous_close = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Previous day's closing index value.",
    )
    point_change = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Point change from previous close.",
    )
    percentage_change = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage change from previous close.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trading_date"]
        verbose_name = "Market Snapshot"
        verbose_name_plural = "Market Snapshots"

    def __str__(self) -> str:
        return f"Market on {self.trading_date}"
