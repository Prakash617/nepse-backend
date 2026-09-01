"""Price models.

Daily and intraday price data for securities.
Fields derived from parse_today_prices() and parse_price_history() upstream responses.
"""

from django.db import models


class DailyPrice(models.Model):
    """Daily market data for a security on a specific trading date.

    Derived from parse_today_prices() and parse_price_history().
    Unique constraint on (security, trading_date) prevents duplicate records.
    """

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="daily_prices",
        help_text="The security this price record belongs to.",
    )
    trading_date = models.DateField(
        db_index=True,
        help_text="The business/trading date.",
    )
    open = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Opening price.",
    )
    high = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Highest price during the session.",
    )
    low = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Lowest price during the session.",
    )
    close = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Closing price.",
    )
    ltp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Last traded price.",
    )
    previous_close = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Previous day's closing price.",
    )
    volume = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Total traded volume (shares).",
    )
    turnover = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Total traded value (NPR).",
    )
    percentage_change = models.DecimalField(
        max_digits=8,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Percentage change from previous close.",
    )
    point_change = models.DecimalField(
        max_digits=10,
        decimal_places=4,
        null=True,
        blank=True,
        help_text="Point change from previous close.",
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-trading_date", "security__symbol"]
        verbose_name = "Daily Price"
        verbose_name_plural = "Daily Prices"
        constraints = [
            models.UniqueConstraint(
                fields=["security", "trading_date"],
                name="unique_daily_price_security_date",
            ),
        ]
        indexes = [
            models.Index(
                fields=["security", "trading_date"],
                name="idx_daily_price_security_date",
            ),
            models.Index(
                fields=["trading_date"],
                name="idx_daily_price_date",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol} on {self.trading_date}"


class IntradayPrice(models.Model):
    """Intraday/tick data for a security.

    Derived from live trade data (parse_today_prices via stock_live_api).
    Note: upstream live data uses the same schema as today_prices.
    Timestamp semantics: each record represents a trade at a specific time.
    """

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="intraday_prices",
        help_text="The security this price record belongs to.",
    )
    timestamp = models.DateTimeField(
        db_index=True,
        help_text="Timestamp of the trade/tick.",
    )
    ltp = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Last traded price at this timestamp.",
    )
    volume = models.PositiveBigIntegerField(
        null=True,
        blank=True,
        help_text="Volume traded at this timestamp.",
    )
    turnover = models.DecimalField(
        max_digits=18,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Turnover at this timestamp.",
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-timestamp", "security__symbol"]
        verbose_name = "Intraday Price"
        verbose_name_plural = "Intraday Prices"
        indexes = [
            models.Index(
                fields=["security", "timestamp"],
                name="idx_intraday_st",
            ),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol} at {self.timestamp}"
