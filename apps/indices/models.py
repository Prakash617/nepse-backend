"""Index models.

Market index definitions and historical snapshots.
Fields derived from parse_indices(), parse_sector_indices(), and parse_index_history().
"""

from django.db import models


class MarketIndex(models.Model):
    """A NEPSE market index.

    Covers both the main NEPSE index and sector sub-indices.
    The nepse_id is unique because both /nepse-index and /sector-index
    return the same ID space (51-67).
    """

    nepse_id = models.PositiveIntegerField(
        unique=True,
        help_text="Upstream NEPSE index ID (valid range: 51-67).",
    )
    name = models.CharField(
        max_length=100,
        unique=True,
        help_text="Index name (e.g., 'NEPSE Index', 'Sensitive Index').",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["nepse_id"]
        verbose_name = "Market Index"
        verbose_name_plural = "Market Indices"

    def __str__(self) -> str:
        return self.name


class IndexSnapshot(models.Model):
    """Historical daily snapshot of a market index.

    Derived from parse_index_history() and the daily values in parse_indices().
    Each record represents one trading day's OHLCV data for an index.
    """

    index = models.ForeignKey(
        "indices.MarketIndex",
        on_delete=models.CASCADE,
        related_name="snapshots",
        help_text="The market index this snapshot belongs to.",
    )
    trading_date = models.DateField(
        db_index=True,
        help_text="The business/trading date.",
    )
    open = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Index opening value.",
    )
    high = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Index highest value.",
    )
    low = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Index lowest value.",
    )
    close = models.DecimalField(
        max_digits=12,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Index closing value.",
    )
    volume = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Total traded volume for the index constituents.",
    )
    turnover = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total traded value for the index constituents.",
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
        ordering = ["-trading_date", "index__name"]
        verbose_name = "Index Snapshot"
        verbose_name_plural = "Index Snapshots"
        constraints = [
            models.UniqueConstraint(
                fields=["index", "trading_date"],
                name="unique_index_snapshot_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["index", "trading_date"],
                name="idx_index_snapshot_date",
            ),
            models.Index(
                fields=["trading_date"],
                name="idx_isnap_tdate",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.index.name} on {self.trading_date}"
