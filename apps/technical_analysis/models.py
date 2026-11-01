"""Database models for Technical Analysis, Sector Intelligence, and Stock Rankings.

Stores historical indicator snapshots, composite score snapshots, sector intelligence
snapshots, constituent rankings, signals, recommendations, and analysis run audits.
"""

from __future__ import annotations

from decimal import Decimal

from django.db import models

DEFAULT_CALCULATION_VERSION = "v1.0"


class AnalysisRun(models.Model):
    """Tracks and audits execution of technical analysis runs."""

    RUN_TYPE_SCHEDULED = "scheduled"
    RUN_TYPE_MANUAL = "manual"
    RUN_TYPE_BACKFILL = "backfill"
    RUN_TYPE_CHOICES = [
        (RUN_TYPE_SCHEDULED, "Scheduled (End-of-Day)"),
        (RUN_TYPE_MANUAL, "Manual Administrative"),
        (RUN_TYPE_BACKFILL, "Historical Backfill"),
    ]

    STATUS_PENDING = "pending"
    STATUS_RUNNING = "running"
    STATUS_SUCCESS = "success"
    STATUS_FAILED = "failed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending"),
        (STATUS_RUNNING, "Running"),
        (STATUS_SUCCESS, "Success"),
        (STATUS_FAILED, "Failed"),
    ]

    analysis_date = models.DateField(
        db_index=True,
        help_text="The trading date analyzed.",
    )
    run_type = models.CharField(
        max_length=20,
        choices=RUN_TYPE_CHOICES,
        default=RUN_TYPE_SCHEDULED,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )
    started_at = models.DateTimeField(auto_now_add=True)
    finished_at = models.DateTimeField(null=True, blank=True)

    securities_processed = models.PositiveIntegerField(default=0)
    sectors_processed = models.PositiveIntegerField(default=0)
    error_count = models.PositiveIntegerField(default=0)
    error_details = models.JSONField(default=list, blank=True)

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )

    class Meta:
        ordering = ["-analysis_date", "-started_at"]
        verbose_name = "Analysis Run"
        verbose_name_plural = "Analysis Runs"
        indexes = [
            models.Index(fields=["analysis_date", "status"], name="idx_arun_date_status"),
        ]

    def __str__(self) -> str:
        return f"Analysis Run for {self.analysis_date} ({self.status})"


class TechnicalIndicatorSnapshot(models.Model):
    """Calculated technical indicators for a security and trading date."""

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="technical_indicator_snapshots",
    )
    trading_date = models.DateField(db_index=True)

    # Moving Averages
    sma_20 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sma_50 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    sma_200 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ema_20 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ema_50 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    ema_200 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    # Momentum
    rsi_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    macd_line = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    macd_signal = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)
    macd_histogram = models.DecimalField(max_digits=10, decimal_places=4, null=True, blank=True)

    # Trend / Directional
    adx_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    plus_di_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    minus_di_14 = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Volatility
    bollinger_upper = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bollinger_middle = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bollinger_lower = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    bandwidth = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    percent_b = models.DecimalField(max_digits=8, decimal_places=4, null=True, blank=True)
    atr_14 = models.DecimalField(max_digits=10, decimal_places=2, null=True, blank=True)
    atr_pct = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    # Volume
    volume = models.DecimalField(max_digits=16, decimal_places=2, default=Decimal("0.0"))
    avg_volume_20 = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    avg_volume_50 = models.DecimalField(max_digits=16, decimal_places=2, null=True, blank=True)
    relative_volume = models.DecimalField(max_digits=8, decimal_places=2, null=True, blank=True)

    # Price Structure
    high_20 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    low_20 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    high_52w = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    low_52w = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trading_date", "security__symbol"]
        constraints = [
            models.UniqueConstraint(
                fields=["security", "trading_date", "calculation_version"],
                name="unique_tech_indicator_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["security", "trading_date"], name="idx_tisnap_sec_date"),
            models.Index(fields=["trading_date"], name="idx_tisnap_date"),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol} indicators on {self.trading_date}"


class TechnicalScoreSnapshot(models.Model):
    """Calculated technical composite scores and classifications for a security."""

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="technical_score_snapshots",
    )
    trading_date = models.DateField(db_index=True)

    total_score = models.DecimalField(max_digits=5, decimal_places=1, db_index=True)
    trend_score = models.DecimalField(max_digits=5, decimal_places=1)
    momentum_score = models.DecimalField(max_digits=5, decimal_places=1)
    volume_score = models.DecimalField(max_digits=5, decimal_places=1)
    relative_strength_score = models.DecimalField(max_digits=5, decimal_places=1)
    breakout_score = models.DecimalField(max_digits=5, decimal_places=1)
    risk_score = models.DecimalField(max_digits=5, decimal_places=1)

    classification = models.CharField(max_length=50, db_index=True)
    explanation = models.TextField(blank=True, default="")

    bullish_signals = models.JSONField(default=list, blank=True)
    bearish_signals = models.JSONField(default=list, blank=True)
    warnings = models.JSONField(default=list, blank=True)
    component_details = models.JSONField(default=dict, blank=True)

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trading_date", "-total_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["security", "trading_date", "calculation_version"],
                name="unique_tech_score_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["trading_date", "total_score"], name="idx_tssnap_date_score"),
            models.Index(fields=["classification", "trading_date"], name="idx_tssnap_class_date"),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol}: {self.total_score} on {self.trading_date}"


class SectorAnalysisSnapshot(models.Model):
    """Sector strength rating, trend classification, and breadth metrics."""

    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.CASCADE,
        related_name="technical_snapshots",
    )
    trading_date = models.DateField(db_index=True)

    sector_score = models.DecimalField(max_digits=5, decimal_places=1, db_index=True)
    classification = models.CharField(max_length=50, db_index=True)
    rotation_stage = models.CharField(max_length=30, db_index=True)

    daily_return_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    weekly_return_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    monthly_return_pct = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    relative_strength_vs_nepse_20 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)
    relative_strength_vs_nepse_60 = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    constituent_count = models.PositiveIntegerField(default=0)
    advancing_count = models.PositiveIntegerField(default=0)
    declining_count = models.PositiveIntegerField(default=0)
    unchanged_count = models.PositiveIntegerField(default=0)
    pct_above_ema_20 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    pct_above_ema_50 = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)

    data_source = models.CharField(max_length=30, default="official_index")  # "official_index" or "derived_basket"
    component_scores = models.JSONField(default=dict, blank=True)
    explanation = models.TextField(blank=True, default="")

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trading_date", "-sector_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["sector", "trading_date", "calculation_version"],
                name="unique_sector_analysis_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["trading_date", "sector_score"], name="idx_sasnap_date_score"),
        ]

    def __str__(self) -> str:
        return f"{self.sector.name}: {self.sector_score} on {self.trading_date}"


class SectorStockRanking(models.Model):
    """Rank position of a security within its sector for an analysis session."""

    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.CASCADE,
        related_name="stock_rankings",
    )
    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="sector_rankings",
    )
    trading_date = models.DateField(db_index=True)

    rank = models.PositiveIntegerField(db_index=True)
    total_constituents = models.PositiveIntegerField()
    technical_score = models.DecimalField(max_digits=5, decimal_places=1)
    relative_strength_vs_sector = models.DecimalField(max_digits=7, decimal_places=2, null=True, blank=True)

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["trading_date", "sector", "rank"]
        constraints = [
            models.UniqueConstraint(
                fields=["sector", "security", "trading_date", "calculation_version"],
                name="unique_sector_stock_ranking",
            ),
        ]
        indexes = [
            models.Index(fields=["sector", "trading_date", "rank"], name="idx_ssrank_sec_date_rk"),
        ]

    def __str__(self) -> str:
        return f"#{self.rank} {self.security.symbol} in {self.sector.name} ({self.trading_date})"


class TechnicalSignal(models.Model):
    """Discrete algorithmic signal event triggered for a stock or sector."""

    CATEGORY_BULLISH = "bullish"
    CATEGORY_BEARISH = "bearish"
    CATEGORY_WARNING = "warning"
    CATEGORY_CHOICES = [
        (CATEGORY_BULLISH, "Bullish"),
        (CATEGORY_BEARISH, "Bearish"),
        (CATEGORY_WARNING, "Cautionary Warning"),
    ]

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="technical_signals",
    )
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.CASCADE,
        null=True,
        blank=True,
        related_name="technical_signals",
    )
    trading_date = models.DateField(db_index=True)

    signal_type = models.CharField(max_length=80, db_index=True)
    category = models.CharField(max_length=20, choices=CATEGORY_CHOICES, db_index=True)
    signal_strength = models.CharField(max_length=20, default="moderate")
    explanation = models.TextField()
    is_confirmed = models.BooleanField(default=True)

    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trading_date", "-id"]
        indexes = [
            models.Index(fields=["trading_date", "signal_type"], name="idx_tsig_date_type"),
            models.Index(fields=["security", "trading_date"], name="idx_tsig_sec_date"),
        ]

    def __str__(self) -> str:
        target = self.security.symbol if self.security else (self.sector.name if self.sector else "Unknown")
        return f"{self.signal_type} on {target} ({self.trading_date})"


class RecommendationSnapshot(models.Model):
    """Archived algorithmic candidate selection and rationale for tracking."""

    CATEGORY_STRONG_BULLISH = "strong_bullish"
    CATEGORY_BULLISH = "bullish"
    CATEGORY_EMERGING = "emerging"
    CATEGORY_BREAKOUT = "breakout"
    CATEGORY_IDIOSYNCRATIC = "idiosyncratic_standout"
    CATEGORY_TRENDING_SECTOR_TOP = "trending_sector_top"
    CATEGORY_CHOICES = [
        (CATEGORY_STRONG_BULLISH, "Strong Bullish"),
        (CATEGORY_BULLISH, "Bullish Candidate"),
        (CATEGORY_EMERGING, "Emerging Candidate"),
        (CATEGORY_BREAKOUT, "Breakout Candidate"),
        (CATEGORY_IDIOSYNCRATIC, "Idiosyncratic Standout"),
        (CATEGORY_TRENDING_SECTOR_TOP, "Top Pick in Trending Sector"),
    ]

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="recommendation_snapshots",
    )
    sector = models.ForeignKey(
        "sectors.Sector",
        on_delete=models.SET_NULL,
        null=True,
        blank=True,
        related_name="recommendations",
    )
    trading_date = models.DateField(db_index=True)

    category = models.CharField(max_length=40, choices=CATEGORY_CHOICES, db_index=True)
    technical_score = models.DecimalField(max_digits=5, decimal_places=1)
    sector_score = models.DecimalField(max_digits=5, decimal_places=1, null=True, blank=True)
    rank_overall = models.PositiveIntegerField(null=True, blank=True)
    rank_in_sector = models.PositiveIntegerField(null=True, blank=True)

    reason = models.TextField()
    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-trading_date", "-technical_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["security", "trading_date", "category", "calculation_version"],
                name="unique_recommendation_snapshot",
            ),
        ]
        indexes = [
            models.Index(fields=["trading_date", "category"], name="idx_recsnap_date_cat"),
        ]

    def __str__(self) -> str:
        return f"{self.security.symbol} [{self.category}] on {self.trading_date}"


class TradingSignal(models.Model):
    """Daily trading signal generated by Short-Term or Swing trading strategies."""

    STRATEGY_SHORT_TERM = "short_term"
    STRATEGY_SWING = "swing"
    STRATEGY_CHOICES = [
        (STRATEGY_SHORT_TERM, "Short-Term Trading (2-10 Sessions)"),
        (STRATEGY_SWING, "Swing Trading (1-8 Weeks)"),
    ]

    SETUP_BREAKOUT = "breakout"
    SETUP_PULLBACK = "pullback"
    SETUP_SUPPORT_REBOUND = "support_rebound"
    SETUP_TREND_CONTINUATION = "trend_continuation"
    SETUP_CONSOLIDATION_BREAKOUT = "consolidation_breakout"
    SETUP_CHOICES = [
        (SETUP_BREAKOUT, "Resistance Breakout"),
        (SETUP_PULLBACK, "Pullback to EMA / Support"),
        (SETUP_SUPPORT_REBOUND, "Support Level Rebound"),
        (SETUP_TREND_CONTINUATION, "Trend Continuation Expansion"),
        (SETUP_CONSOLIDATION_BREAKOUT, "Base Consolidation Breakout"),
    ]

    STATUS_PENDING = "pending"
    STATUS_ACTIVE = "active"
    STATUS_TARGET_1_HIT = "target_1_hit"
    STATUS_TARGET_2_HIT = "target_2_hit"
    STATUS_STOPPED_OUT = "stopped_out"
    STATUS_EXPIRED = "expired"
    STATUS_INVALIDATED = "invalidated"
    STATUS_CLOSED = "closed"
    STATUS_CHOICES = [
        (STATUS_PENDING, "Pending Entry Fill"),
        (STATUS_ACTIVE, "Active (Position Open)"),
        (STATUS_TARGET_1_HIT, "Target 1 Reached"),
        (STATUS_TARGET_2_HIT, "Target 2 Reached"),
        (STATUS_STOPPED_OUT, "Stopped Out"),
        (STATUS_EXPIRED, "Expired (Max Period Elapsed)"),
        (STATUS_INVALIDATED, "Invalidated (Setup Broken Before Fill)"),
        (STATUS_CLOSED, "Closed"),
    ]

    security = models.ForeignKey(
        "securities.Security",
        on_delete=models.CASCADE,
        related_name="trading_signals",
    )
    strategy_type = models.CharField(
        max_length=20,
        choices=STRATEGY_CHOICES,
        db_index=True,
    )
    setup_type = models.CharField(
        max_length=30,
        choices=SETUP_CHOICES,
        db_index=True,
    )
    status = models.CharField(
        max_length=20,
        choices=STATUS_CHOICES,
        default=STATUS_PENDING,
        db_index=True,
    )

    signal_date = models.DateField(
        db_index=True,
        help_text="Date on which the daily candle closed and generated the signal.",
    )
    entry_date = models.DateField(
        null=True,
        blank=True,
        help_text="Session on which position was actually filled at open.",
    )
    exit_date = models.DateField(
        null=True,
        blank=True,
        help_text="Session on which position was completely closed.",
    )

    # Price and execution levels
    suggested_entry = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Recommended entry price (usually next day's open or pivot price).",
    )
    entry_zone_low = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    entry_zone_high = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_entry_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    actual_exit_price = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    stop_loss = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        help_text="Initial structural / ATR stop loss.",
    )
    trailing_stop = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Dynamic trailing stop updated as trade develops.",
    )
    target_1 = models.DecimalField(max_digits=12, decimal_places=2)
    target_2 = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)

    risk_per_share = models.DecimalField(max_digits=10, decimal_places=2)
    risk_reward_ratio = models.DecimalField(max_digits=6, decimal_places=2)

    # Holding period & Performance
    holding_period_days = models.PositiveIntegerField(
        default=0,
        help_text="Number of trading sessions the position has been open.",
    )
    max_holding_period = models.PositiveIntegerField(
        default=10,
        help_text="Max permitted sessions before time-based exit (10 for short-term, 40 for swing).",
    )
    composite_score = models.DecimalField(
        max_digits=5,
        decimal_places=1,
        help_text="Quantitative setup score (0-100).",
    )
    return_pct = models.DecimalField(
        max_digits=7,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Final realized percentage return.",
    )
    highest_price_reached = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum favorable excursion (MFE) during trade life.",
    )
    lowest_price_reached = models.DecimalField(
        max_digits=12,
        decimal_places=2,
        null=True,
        blank=True,
        help_text="Maximum adverse excursion (MAE) during trade life.",
    )

    rationale = models.TextField(
        help_text="Human-readable breakdown of technical setup, indicators, and conditions.",
    )
    metadata = models.JSONField(
        default=dict,
        blank=True,
        help_text="Key indicators and context at signal emission (RSI, ADX, EMA slopes, volume ratio).",
    )

    calculation_version = models.CharField(
        max_length=20,
        default=DEFAULT_CALCULATION_VERSION,
        db_index=True,
    )
    created_at = models.DateTimeField(auto_now_add=True)
    updated_at = models.DateTimeField(auto_now=True)

    class Meta:
        ordering = ["-signal_date", "-composite_score"]
        constraints = [
            models.UniqueConstraint(
                fields=["security", "signal_date", "strategy_type", "calculation_version"],
                name="unique_trading_signal",
            ),
        ]
        indexes = [
            models.Index(fields=["strategy_type", "status"], name="idx_tsig_strat_status"),
            models.Index(fields=["signal_date", "strategy_type"], name="idx_tsig_date_strat"),
            models.Index(fields=["status", "signal_date"], name="idx_tsig_status_date"),
        ]

    def __str__(self) -> str:
        return f"{self.strategy_type.upper()} [{self.status}] on {self.security.symbol} ({self.signal_date})"


class TradingSignalTracking(models.Model):
    """Daily progression log for an active trading signal position."""

    signal = models.ForeignKey(
        TradingSignal,
        on_delete=models.CASCADE,
        related_name="tracking_history",
    )
    trading_date = models.DateField(db_index=True)
    close_price = models.DecimalField(max_digits=12, decimal_places=2)
    high_price = models.DecimalField(max_digits=12, decimal_places=2)
    low_price = models.DecimalField(max_digits=12, decimal_places=2)
    unrealized_return_pct = models.DecimalField(max_digits=7, decimal_places=2)
    trailing_stop_level = models.DecimalField(max_digits=12, decimal_places=2, null=True, blank=True)
    day_in_trade = models.PositiveIntegerField(default=1)
    notes = models.CharField(max_length=255, blank=True, default="")
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["trading_date"]
        constraints = [
            models.UniqueConstraint(
                fields=["signal", "trading_date"],
                name="unique_trading_signal_tracking",
            ),
        ]

    def __str__(self) -> str:
        return f"Day {self.day_in_trade} for Signal #{self.signal_id} on {self.trading_date}"


class BacktestRunRecord(models.Model):
    """Execution audit, metrics, and equity curve for historical strategy backtests."""

    strategy_type = models.CharField(max_length=20, db_index=True)
    start_date = models.DateField(db_index=True)
    end_date = models.DateField(db_index=True)

    initial_capital = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("1000000.00"))
    final_equity = models.DecimalField(max_digits=14, decimal_places=2, default=Decimal("1000000.00"))
    total_return_pct = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))
    benchmark_return_pct = models.DecimalField(max_digits=8, decimal_places=2, default=Decimal("0.00"))

    total_trades = models.PositiveIntegerField(default=0)
    winning_trades = models.PositiveIntegerField(default=0)
    losing_trades = models.PositiveIntegerField(default=0)
    win_rate_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    profit_factor = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)
    max_drawdown_pct = models.DecimalField(max_digits=6, decimal_places=2, default=Decimal("0.00"))
    sharpe_ratio = models.DecimalField(max_digits=6, decimal_places=2, null=True, blank=True)

    parameters = models.JSONField(default=dict, blank=True)
    summary_metrics = models.JSONField(default=dict, blank=True)
    equity_curve = models.JSONField(default=list, blank=True)
    created_at = models.DateTimeField(auto_now_add=True)

    class Meta:
        ordering = ["-created_at"]
        indexes = [
            models.Index(fields=["strategy_type", "-created_at"], name="idx_brrun_strat_created"),
        ]

    def __str__(self) -> str:
        return f"{self.strategy_type} Backtest ({self.start_date} to {self.end_date}): {self.total_return_pct}%"

