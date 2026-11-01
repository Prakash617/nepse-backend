"""DRF Serializers for Technical Analysis endpoints."""

from __future__ import annotations

from typing import Any

from rest_framework import serializers

from apps.technical_analysis.models import (
    RecommendationSnapshot,
    SectorAnalysisSnapshot,
    SectorStockRanking,
    TechnicalIndicatorSnapshot,
    TechnicalScoreSnapshot,
    TechnicalSignal,
    TradingSignal,
    TradingSignalTracking,
)


class MarketBreadthSerializer(serializers.Serializer):
    total_eligible = serializers.IntegerField()
    advancing_count = serializers.IntegerField()
    declining_count = serializers.IntegerField()
    unchanged_count = serializers.IntegerField()
    advance_decline_ratio = serializers.FloatField(allow_null=True)
    stocks_above_ema_20 = serializers.IntegerField()
    pct_above_ema_20 = serializers.FloatField(allow_null=True)
    stocks_above_ema_50 = serializers.IntegerField()
    pct_above_ema_50 = serializers.FloatField(allow_null=True)
    stocks_above_sma_200 = serializers.IntegerField()
    pct_above_sma_200 = serializers.FloatField(allow_null=True)


class MarketConditionScoreSerializer(serializers.Serializer):
    total_score = serializers.FloatField()
    condition = serializers.CharField()
    trend_score = serializers.FloatField()
    momentum_score = serializers.FloatField()
    adx_score = serializers.FloatField()
    breadth_score = serializers.FloatField()
    summary_explanation = serializers.CharField()
    component_details = serializers.DictField()


class MarketOverviewResponseSerializer(serializers.Serializer):
    as_of_date = serializers.DateField()
    latest_close = serializers.FloatField()
    point_change = serializers.FloatField(allow_null=True)
    daily_return_pct = serializers.FloatField(allow_null=True)
    weekly_return_pct = serializers.FloatField(allow_null=True)
    monthly_return_pct = serializers.FloatField(allow_null=True)
    volume = serializers.FloatField()
    data_source = serializers.CharField()
    condition = MarketConditionScoreSerializer()
    breadth = MarketBreadthSerializer()
    indicators = serializers.SerializerMethodField()

    def get_indicators(self, obj: Any) -> dict[str, Any]:
        ind = getattr(obj, "indicators", None)
        if not ind:
            return {}
        res: dict[str, Any] = {}
        if hasattr(ind, "moving_averages") and ind.moving_averages:
            res["ema_20"] = ind.moving_averages.ema_20
            res["ema_50"] = ind.moving_averages.ema_50
            res["ema_200"] = ind.moving_averages.ema_200
            res["sma_20"] = ind.moving_averages.sma_20
            res["sma_50"] = ind.moving_averages.sma_50
            res["sma_200"] = ind.moving_averages.sma_200
            res["price_above_ema_20"] = ind.moving_averages.price_above_ema_20
            res["price_above_ema_50"] = ind.moving_averages.price_above_ema_50
            res["price_above_sma_200"] = ind.moving_averages.price_above_sma_200
            res["golden_cross"] = ind.moving_averages.golden_cross
            res["death_cross"] = ind.moving_averages.death_cross
        if hasattr(ind, "momentum") and ind.momentum:
            if hasattr(ind.momentum, "rsi") and ind.momentum.rsi:
                res["rsi_14"] = ind.momentum.rsi.value
                res["rsi_condition"] = ind.momentum.rsi.momentum_zone
                res["rsi_is_overbought"] = ind.momentum.rsi.is_overbought
                res["rsi_is_oversold"] = ind.momentum.rsi.is_oversold
            if hasattr(ind.momentum, "macd") and ind.momentum.macd:
                res["macd_line"] = ind.momentum.macd.macd_line
                res["macd_signal"] = ind.momentum.macd.signal_line
                res["macd_histogram"] = ind.momentum.macd.histogram
                res["macd_crossover"] = ind.momentum.macd.crossover
        if hasattr(ind, "trend") and ind.trend:
            res["adx_14"] = ind.trend.adx
            res["plus_di_14"] = ind.trend.plus_di
            res["minus_di_14"] = ind.trend.minus_di
            res["trend_strength"] = ind.trend.trend_strength
            res["directional_dominance"] = ind.trend.directional_dominance
        if hasattr(ind, "volatility") and ind.volatility:
            if hasattr(ind.volatility, "bollinger") and ind.volatility.bollinger:
                res["bollinger_upper"] = ind.volatility.bollinger.upper_band
                res["bollinger_middle"] = ind.volatility.bollinger.middle_band
                res["bollinger_lower"] = ind.volatility.bollinger.lower_band
                res["bandwidth"] = ind.volatility.bollinger.bandwidth
                res["percent_b"] = ind.volatility.bollinger.percent_b
                res["is_squeeze"] = ind.volatility.bollinger.is_squeeze
            if hasattr(ind.volatility, "atr") and ind.volatility.atr:
                res["atr_14"] = ind.volatility.atr.atr
                res["atr_pct"] = ind.volatility.atr.atr_percentage
        return res


class SectorAnalysisSnapshotSerializer(serializers.ModelSerializer):
    sector_name = serializers.CharField(source="sector.name", read_only=True)
    sector_display_name = serializers.CharField(source="sector.display_name", read_only=True)

    class Meta:
        model = SectorAnalysisSnapshot
        fields = [
            "id",
            "sector",
            "sector_name",
            "sector_display_name",
            "trading_date",
            "sector_score",
            "classification",
            "rotation_stage",
            "daily_return_pct",
            "weekly_return_pct",
            "monthly_return_pct",
            "relative_strength_vs_nepse_20",
            "relative_strength_vs_nepse_60",
            "constituent_count",
            "advancing_count",
            "declining_count",
            "unchanged_count",
            "pct_above_ema_20",
            "pct_above_ema_50",
            "data_source",
            "explanation",
            "component_scores",
        ]


class SectorStockRankingSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)
    company_name = serializers.CharField(source="security.company_name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", read_only=True)

    class Meta:
        model = SectorStockRanking
        fields = [
            "id",
            "rank",
            "security",
            "symbol",
            "company_name",
            "sector",
            "sector_name",
            "trading_date",
            "total_constituents",
            "technical_score",
            "relative_strength_vs_sector",
        ]


class TechnicalScoreListSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)
    company_name = serializers.CharField(source="security.company_name", read_only=True)
    sector_id = serializers.IntegerField(source="security.sector_id", read_only=True)
    sector_name = serializers.CharField(source="security.sector.name", default="", read_only=True)

    class Meta:
        model = TechnicalScoreSnapshot
        fields = [
            "id",
            "security",
            "symbol",
            "company_name",
            "sector_id",
            "sector_name",
            "trading_date",
            "total_score",
            "classification",
            "trend_score",
            "momentum_score",
            "volume_score",
            "relative_strength_score",
            "breakout_score",
            "risk_score",
        ]


class TechnicalScoreDetailSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)
    company_name = serializers.CharField(source="security.company_name", read_only=True)
    sector_id = serializers.IntegerField(source="security.sector_id", read_only=True)
    sector_name = serializers.CharField(source="security.sector.name", default="", read_only=True)

    class Meta:
        model = TechnicalScoreSnapshot
        fields = [
            "id",
            "security",
            "symbol",
            "company_name",
            "sector_id",
            "sector_name",
            "trading_date",
            "total_score",
            "classification",
            "trend_score",
            "momentum_score",
            "volume_score",
            "relative_strength_score",
            "breakout_score",
            "risk_score",
            "explanation",
            "bullish_signals",
            "bearish_signals",
            "warnings",
            "component_details",
            "calculation_version",
            "created_at",
        ]


class TechnicalIndicatorSnapshotSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)

    class Meta:
        model = TechnicalIndicatorSnapshot
        fields = [
            "id",
            "security",
            "symbol",
            "trading_date",
            "sma_20",
            "sma_50",
            "sma_200",
            "ema_20",
            "ema_50",
            "ema_200",
            "rsi_14",
            "macd_line",
            "macd_signal",
            "macd_histogram",
            "adx_14",
            "plus_di_14",
            "minus_di_14",
            "bollinger_upper",
            "bollinger_middle",
            "bollinger_lower",
            "bandwidth",
            "percent_b",
            "atr_14",
            "atr_pct",
            "volume",
            "avg_volume_20",
            "avg_volume_50",
            "relative_volume",
            "high_20",
            "low_20",
            "high_52w",
            "low_52w",
        ]


class TechnicalSignalSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", allow_null=True, read_only=True)
    sector_name = serializers.CharField(source="sector.name", allow_null=True, read_only=True)

    class Meta:
        model = TechnicalSignal
        fields = [
            "id",
            "trading_date",
            "security",
            "symbol",
            "sector",
            "sector_name",
            "signal_type",
            "category",
            "signal_strength",
            "explanation",
            "is_confirmed",
        ]


class RecommendationSnapshotSerializer(serializers.ModelSerializer):
    symbol = serializers.CharField(source="security.symbol", read_only=True)
    company_name = serializers.CharField(source="security.company_name", read_only=True)
    sector_name = serializers.CharField(source="sector.name", default="", read_only=True)

    class Meta:
        model = RecommendationSnapshot
        fields = [
            "id",
            "trading_date",
            "security",
            "symbol",
            "company_name",
            "sector",
            "sector_name",
            "category",
            "technical_score",
            "sector_score",
            "rank_overall",
            "rank_in_sector",
            "reason",
        ]


class BacktestRequestSerializer(serializers.Serializer):
    start_date = serializers.DateField(required=False, default=None)
    end_date = serializers.DateField(required=False, default=None)
    min_technical_score = serializers.FloatField(required=False, default=70.0)
    category = serializers.CharField(required=False, allow_null=True, allow_blank=True, default=None)
    horizons = serializers.ListField(child=serializers.IntegerField(), required=False, default=lambda: [5, 10, 20, 60])
    rebalance_frequency_days = serializers.IntegerField(required=False, default=5)
    initial_capital = serializers.FloatField(required=False, default=1000000.0)


class SimulatedTradeSerializer(serializers.Serializer):
    security_id = serializers.IntegerField()
    symbol = serializers.CharField()
    entry_date = serializers.DateField()
    exit_date = serializers.DateField()
    entry_price = serializers.FloatField()
    exit_price = serializers.FloatField()
    return_pct = serializers.FloatField()
    benchmark_return_pct = serializers.FloatField()
    excess_return_pct = serializers.FloatField()
    holding_period_days = serializers.IntegerField()
    candidate_category = serializers.CharField()
    technical_score_at_entry = serializers.FloatField()
    is_win = serializers.BooleanField()


class PortfolioEquityPointSerializer(serializers.Serializer):
    date = serializers.DateField()
    strategy_equity = serializers.FloatField()
    benchmark_equity = serializers.FloatField()
    drawdown_pct = serializers.FloatField()
    active_positions_count = serializers.IntegerField()


class HorizonReturnMetricSerializer(serializers.Serializer):
    horizon_days = serializers.IntegerField()
    total_trades = serializers.IntegerField()
    winning_trades = serializers.IntegerField()
    losing_trades = serializers.IntegerField()
    win_rate_pct = serializers.FloatField()
    average_return_pct = serializers.FloatField()
    median_return_pct = serializers.FloatField()
    max_return_pct = serializers.FloatField()
    min_return_pct = serializers.FloatField()
    benchmark_average_return_pct = serializers.FloatField()
    excess_return_pct = serializers.FloatField()


class StrategyPerformanceMetricsSerializer(serializers.Serializer):
    total_candidates_evaluated = serializers.IntegerField()
    overall_win_rate_pct = serializers.FloatField()
    profit_factor = serializers.FloatField()
    max_drawdown_pct = serializers.FloatField()
    approx_sharpe_ratio = serializers.FloatField()
    horizon_metrics = serializers.DictField(child=HorizonReturnMetricSerializer())
    summary_notes = serializers.ListField(child=serializers.CharField())


class PortfolioSimulationResultSerializer(serializers.Serializer):
    initial_capital = serializers.FloatField()
    final_strategy_equity = serializers.FloatField()
    final_benchmark_equity = serializers.FloatField()
    total_strategy_return_pct = serializers.FloatField()
    total_benchmark_return_pct = serializers.FloatField()
    total_trades = serializers.IntegerField()
    winning_trades = serializers.IntegerField()
    losing_trades = serializers.IntegerField()
    win_rate_pct = serializers.FloatField()
    equity_curve = PortfolioEquityPointSerializer(many=True)


class BacktestReportSerializer(serializers.Serializer):
    total_signals = serializers.IntegerField()
    overall_performance = StrategyPerformanceMetricsSerializer()
    portfolio_simulation = PortfolioSimulationResultSerializer()


class TradingSignalTrackingSerializer(serializers.ModelSerializer):
    """Serializer for daily progression tracking of an active trade."""

    class Meta:
        model = TradingSignalTracking
        fields = [
            "id",
            "trading_date",
            "close_price",
            "high_price",
            "low_price",
            "unrealized_return_pct",
            "trailing_stop_level",
            "day_in_trade",
            "notes",
            "created_at",
        ]


class TradingSignalSerializer(serializers.ModelSerializer):
    """Summary serializer for daily and active trading signals."""

    symbol = serializers.CharField(source="security.symbol", read_only=True)
    company_name = serializers.CharField(source="security.company_name", read_only=True)
    sector_name = serializers.CharField(source="security.sector.name", default="", read_only=True)

    class Meta:
        model = TradingSignal
        fields = [
            "id",
            "symbol",
            "company_name",
            "sector_name",
            "strategy_type",
            "setup_type",
            "status",
            "signal_date",
            "entry_date",
            "exit_date",
            "suggested_entry",
            "entry_zone_low",
            "entry_zone_high",
            "actual_entry_price",
            "actual_exit_price",
            "stop_loss",
            "trailing_stop",
            "target_1",
            "target_2",
            "risk_per_share",
            "risk_reward_ratio",
            "holding_period_days",
            "max_holding_period",
            "composite_score",
            "return_pct",
            "highest_price_reached",
            "lowest_price_reached",
            "rationale",
            "metadata",
            "created_at",
            "updated_at",
        ]


class TradingSignalDetailSerializer(TradingSignalSerializer):
    """Detailed serializer for a trading signal including its complete tracking history."""

    tracking_history = TradingSignalTrackingSerializer(many=True, read_only=True)

    class Meta(TradingSignalSerializer.Meta):
        fields = TradingSignalSerializer.Meta.fields + ["tracking_history"]


class SignalPerformanceStatsSerializer(serializers.Serializer):
    """Aggregate statistics for realized trading signals."""

    strategy_type = serializers.CharField()
    total_signals = serializers.IntegerField()
    closed_signals = serializers.IntegerField()
    active_signals = serializers.IntegerField()
    winning_signals = serializers.IntegerField()
    losing_signals = serializers.IntegerField()
    win_rate_pct = serializers.FloatField()
    average_return_pct = serializers.FloatField()
    profit_factor = serializers.FloatField(allow_null=True)
    average_holding_days = serializers.FloatField()


class TradingStrategyMetaSerializer(serializers.Serializer):
    """Metadata describing a trading strategy and its active configuration."""

    strategy_type = serializers.CharField()
    name = serializers.CharField()
    description = serializers.CharField()
    holding_period = serializers.CharField()
    min_rr_ratio = serializers.FloatField()
    entry_patterns = serializers.ListField(child=serializers.CharField())
    exit_rules = serializers.ListField(child=serializers.CharField())

    recent_sample_trades = SimulatedTradeSerializer(many=True)
