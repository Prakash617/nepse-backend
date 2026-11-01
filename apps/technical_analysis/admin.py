"""Django Admin registration for technical analysis models."""

from __future__ import annotations

from django.contrib import admin

from apps.technical_analysis.models import (
    AnalysisRun,
    BacktestRunRecord,
    RecommendationSnapshot,
    SectorAnalysisSnapshot,
    SectorStockRanking,
    TechnicalIndicatorSnapshot,
    TechnicalScoreSnapshot,
    TechnicalSignal,
    TradingSignal,
    TradingSignalTracking,
)


@admin.register(AnalysisRun)
class AnalysisRunAdmin(admin.ModelAdmin):
    list_display = (
        "analysis_date",
        "run_type",
        "status",
        "securities_processed",
        "sectors_processed",
        "error_count",
        "started_at",
        "finished_at",
    )
    list_filter = ("status", "run_type", "analysis_date")
    search_fields = ("analysis_date", "calculation_version")
    readonly_fields = ("started_at", "finished_at")


@admin.register(TechnicalIndicatorSnapshot)
class TechnicalIndicatorSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "trading_date",
        "sma_20",
        "ema_20",
        "sma_200",
        "rsi_14",
        "adx_14",
        "relative_volume",
    )
    list_filter = ("trading_date", "calculation_version")
    search_fields = ("security__symbol", "security__company_name")


@admin.register(TechnicalScoreSnapshot)
class TechnicalScoreSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "trading_date",
        "total_score",
        "classification",
        "trend_score",
        "momentum_score",
        "volume_score",
        "relative_strength_score",
    )
    list_filter = ("classification", "trading_date", "calculation_version")
    search_fields = ("security__symbol", "security__company_name")


@admin.register(SectorAnalysisSnapshot)
class SectorAnalysisSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "sector",
        "trading_date",
        "sector_score",
        "classification",
        "rotation_stage",
        "daily_return_pct",
        "weekly_return_pct",
        "data_source",
    )
    list_filter = ("classification", "rotation_stage", "data_source", "trading_date")
    search_fields = ("sector__name",)


@admin.register(SectorStockRanking)
class SectorStockRankingAdmin(admin.ModelAdmin):
    list_display = (
        "sector",
        "security",
        "trading_date",
        "rank",
        "total_constituents",
        "technical_score",
    )
    list_filter = ("sector", "trading_date")
    search_fields = ("security__symbol", "sector__name")


@admin.register(TechnicalSignal)
class TechnicalSignalAdmin(admin.ModelAdmin):
    list_display = (
        "signal_type",
        "category",
        "security",
        "sector",
        "trading_date",
        "is_confirmed",
    )
    list_filter = ("category", "signal_type", "trading_date", "is_confirmed")
    search_fields = ("signal_type", "security__symbol", "sector__name")


@admin.register(RecommendationSnapshot)
class RecommendationSnapshotAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "category",
        "sector",
        "trading_date",
        "technical_score",
        "rank_overall",
        "rank_in_sector",
    )
    list_filter = ("category", "trading_date")
    search_fields = ("security__symbol", "sector__name")


@admin.register(TradingSignal)
class TradingSignalAdmin(admin.ModelAdmin):
    list_display = (
        "security",
        "strategy_type",
        "setup_type",
        "status",
        "signal_date",
        "suggested_entry",
        "stop_loss",
        "target_1",
        "risk_reward_ratio",
        "composite_score",
    )
    list_filter = ("strategy_type", "setup_type", "status", "signal_date")
    search_fields = ("security__symbol", "security__company_name", "rationale")
    readonly_fields = ("created_at", "updated_at")


@admin.register(TradingSignalTracking)
class TradingSignalTrackingAdmin(admin.ModelAdmin):
    list_display = (
        "signal",
        "trading_date",
        "close_price",
        "unrealized_return_pct",
        "trailing_stop_level",
        "day_in_trade",
    )
    list_filter = ("trading_date",)
    search_fields = ("signal__security__symbol", "notes")


@admin.register(BacktestRunRecord)
class BacktestRunRecordAdmin(admin.ModelAdmin):
    list_display = (
        "strategy_type",
        "start_date",
        "end_date",
        "total_return_pct",
        "benchmark_return_pct",
        "total_trades",
        "win_rate_pct",
        "profit_factor",
        "max_drawdown_pct",
        "sharpe_ratio",
        "created_at",
    )
    list_filter = ("strategy_type", "created_at")
    readonly_fields = ("created_at",)

