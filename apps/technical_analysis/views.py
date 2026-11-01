"""REST API views for the Technical Analysis, Sector Intelligence, and Stock Ranking system."""

from __future__ import annotations

import datetime

from django.shortcuts import get_object_or_404
from drf_spectacular.utils import OpenApiParameter, extend_schema
from rest_framework import generics, permissions, status
from rest_framework.response import Response
from rest_framework.views import APIView

from apps.securities.models import Security
from apps.technical_analysis.backtesting.engine import (
    BacktestConfiguration,
    TechnicalBacktestEngine,
)
from apps.technical_analysis.engines.market_engine import run_market_analysis
from apps.technical_analysis.filters import (
    RecommendationFilter,
    SectorSnapshotFilter,
    StockRankingFilter,
    TradingSignalFilter,
)
from apps.technical_analysis.models import (
    SectorAnalysisSnapshot,
    TechnicalIndicatorSnapshot,
    TechnicalScoreSnapshot,
    TradingSignal,
)
from apps.technical_analysis.selectors import (
    get_latest_trading_date,
    get_recommendations_queryset,
    get_sector_snapshots_queryset,
    get_sector_stock_rankings_queryset,
    get_stock_history_queryset,
    get_stock_scores_queryset,
    get_stock_technical_signals_queryset,
)
from apps.technical_analysis.serializers import (
    BacktestReportSerializer,
    BacktestRequestSerializer,
    MarketOverviewResponseSerializer,
    RecommendationSnapshotSerializer,
    SectorAnalysisSnapshotSerializer,
    SectorStockRankingSerializer,
    SignalPerformanceStatsSerializer,
    TechnicalIndicatorSnapshotSerializer,
    TechnicalScoreDetailSerializer,
    TechnicalScoreListSerializer,
    TechnicalSignalSerializer,
    TradingSignalDetailSerializer,
    TradingSignalSerializer,
    TradingStrategyMetaSerializer,
)


class MarketOverviewView(APIView):
    """Overall NEPSE market technical overview and breadth."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Overall NEPSE market technical condition and breadth",
        description="Returns market condition (Strong Bullish, Bullish, Neutral, Bearish), technical indicators, returns, and market breadth.",
        responses={200: MarketOverviewResponseSerializer},
        parameters=[
            OpenApiParameter("date", str, description="Optional trading date (YYYY-MM-DD)", required=False),
        ],
    )
    def get(self, request) -> Response:
        date_str = request.query_params.get("date")
        target_date: datetime.date | None = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                return Response({"detail": "Invalid date format. Use YYYY-MM-DD."}, status=status.HTTP_400_BAD_REQUEST)

        market_res = run_market_analysis(target_date)
        serializer = MarketOverviewResponseSerializer(market_res)
        return Response(serializer.data)


class SectorListView(generics.ListAPIView):
    """List all NEPSE sectors ranked by technical strength score."""

    permission_classes = [permissions.AllowAny]
    serializer_class = SectorAnalysisSnapshotSerializer
    filterset_class = SectorSnapshotFilter
    ordering_fields = ["sector_score", "daily_return_pct", "weekly_return_pct", "monthly_return_pct"]
    pagination_class = None

    @extend_schema(
        summary="List all sector strength rankings",
        description="Returns all 13 NEPSE sectors with their 0–100 Sector Strength Score, classification, rotation stage, and returns.",
    )
    def get_queryset(self):
        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return get_sector_snapshots_queryset(target_date)


class TrendingSectorsView(APIView):
    """Top three trending sectors highlighted."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Top three trending sectors highlight",
        description="Returns the top three sectors by Sector Strength Score with their constituent top candidate picks.",
    )
    def get(self, request) -> Response:
        date_str = request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass

        sectors_qs = get_sector_snapshots_queryset(target_date)[:3]
        sector_data = SectorAnalysisSnapshotSerializer(sectors_qs, many=True).data

        # Enrich each top sector with its top 3 candidate stocks
        enriched = []
        for s in sector_data:
            sec_id = s["sector"]
            top_stocks = get_sector_stock_rankings_queryset(sec_id, target_date)[:3]
            s["top_candidates"] = SectorStockRankingSerializer(top_stocks, many=True).data
            enriched.append(s)

        return Response(enriched)


class SectorDetailView(generics.RetrieveAPIView):
    """Technical details for a specific sector."""

    permission_classes = [permissions.AllowAny]
    serializer_class = SectorAnalysisSnapshotSerializer

    @extend_schema(
        summary="Sector technical detail",
        description="Returns detailed technical score, breadth, and indicators for a specific sector.",
    )
    def get_object(self):
        sector_id = self.kwargs["sector_id"]
        target_date = get_latest_trading_date()
        date_str = self.request.query_params.get("trading_date")
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass

        return get_object_or_404(
            SectorAnalysisSnapshot.objects.select_related("sector"),
            sector_id=sector_id,
            trading_date=target_date,
        )


class SectorStocksView(generics.ListAPIView):
    """Constituent stocks inside a sector ranked by technical score."""

    permission_classes = [permissions.AllowAny]
    serializer_class = SectorStockRankingSerializer

    @extend_schema(
        summary="Sector constituent stock rankings",
        description="Returns stocks belonging to this sector, ordered by technical rank with relative strength vs sector.",
    )
    def get_queryset(self):
        sector_id = self.kwargs["sector_id"]
        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return get_sector_stock_rankings_queryset(sector_id, target_date)


class SectorTopStocksView(generics.ListAPIView):
    """Top constituent stocks for a specific sector."""

    permission_classes = [permissions.AllowAny]
    serializer_class = SectorStockRankingSerializer
    pagination_class = None

    @extend_schema(
        summary="Top constituent stocks in sector",
        description="Returns the top constituent stocks in this sector.",
        parameters=[
            OpenApiParameter("trading_date", str, description="Optional trading date (YYYY-MM-DD)", required=False),
            OpenApiParameter("limit", int, description="Number of top stocks to return (default: 5)", required=False),
        ],
    )
    def get_queryset(self):
        sector_id = self.kwargs["sector_id"]
        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        try:
            limit = int(self.request.query_params.get("limit", 5))
        except (ValueError, TypeError):
            limit = 5
        return get_sector_stock_rankings_queryset(sector_id, target_date)[:limit]


class StockRankingsView(generics.ListAPIView):
    """Overall NEPSE stock screener and market-wide rankings."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TechnicalScoreListSerializer
    filterset_class = StockRankingFilter
    ordering_fields = ["total_score", "trend_score", "momentum_score", "volume_score", "relative_strength_score"]
    ordering = ["-total_score"]

    @extend_schema(
        summary="Stock technical rankings and screener",
        description="Overall NEPSE stock rankings. Filter by sector, classification, min/max score, and search by ticker symbol.",
    )
    def get_queryset(self):
        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return get_stock_scores_queryset(target_date)


class StockRecommendationsView(generics.ListAPIView):
    """Algorithmic candidate recommendations grouped by research classification."""

    permission_classes = [permissions.AllowAny]
    serializer_class = RecommendationSnapshotSerializer
    filterset_class = RecommendationFilter
    ordering = ["-technical_score"]

    @extend_schema(
        summary="Algorithmic technical candidate recommendations",
        description="Filtered algorithmic candidates: strong_bullish, bullish, emerging, breakout, idiosyncratic_standout, trending_sector_top.",
    )
    def get_queryset(self):
        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass
        return get_recommendations_queryset(target_date)


class StockDetailView(generics.RetrieveAPIView):
    """Detailed technical profile and explanation for an individual stock."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TechnicalScoreDetailSerializer

    @extend_schema(
        summary="Stock technical detail and explanation",
        description="Returns the complete technical score, component breakdown, bullish signals, bearish signals, warnings, and factual explanation.",
    )
    def get_object(self):
        symbol = self.kwargs["symbol"].upper().strip()
        security = get_object_or_404(Security, symbol=symbol)

        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass

        if not target_date:
            target_date = get_latest_trading_date()

        return get_object_or_404(
            TechnicalScoreSnapshot.objects.select_related("security", "security__sector"),
            security=security,
            trading_date=target_date,
        )


class StockIndicatorsView(generics.RetrieveAPIView):
    """Raw technical indicators for an individual stock."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TechnicalIndicatorSnapshotSerializer

    @extend_schema(
        summary="Stock raw indicator values",
        description="Returns SMA (20, 50, 200), EMA (20, 50, 200), RSI 14, MACD, ADX 14, +DI/-DI, Bollinger Bands, ATR 14, and Volume.",
    )
    def get_object(self):
        symbol = self.kwargs["symbol"].upper().strip()
        security = get_object_or_404(Security, symbol=symbol)

        date_str = self.request.query_params.get("trading_date")
        target_date = None
        if date_str:
            try:
                target_date = datetime.date.fromisoformat(date_str)
            except ValueError:
                pass

        if not target_date:
            target_date = get_latest_trading_date()

        return get_object_or_404(
            TechnicalIndicatorSnapshot.objects.select_related("security"),
            security=security,
            trading_date=target_date,
        )


class StockSignalsView(generics.ListAPIView):
    """Recent technical signals for an individual stock."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TechnicalSignalSerializer
    pagination_class = None

    @extend_schema(
        summary="Stock recent technical signals",
        description="Returns recent algorithmic signals triggered for this stock (e.g. golden cross, breakout, RSI divergence).",
    )
    def get_queryset(self):
        symbol = self.kwargs["symbol"].upper().strip()
        security = get_object_or_404(Security, symbol=symbol)
        return get_stock_technical_signals_queryset(security.id, limit=25)


class StockHistoryView(generics.ListAPIView):
    """Historical technical score progression for an individual stock."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TechnicalScoreListSerializer
    pagination_class = None

    @extend_schema(
        summary="Stock historical score trend",
        description="Returns chronological historical score snapshots for charting technical score changes over time.",
    )
    def get_queryset(self):
        symbol = self.kwargs["symbol"].upper().strip()
        security = get_object_or_404(Security, symbol=symbol)
        limit = int(self.request.query_params.get("limit", 60))
        return get_stock_history_queryset(security.id, limit=limit)


class BacktestRunView(APIView):
    """Run historical backtest and strategy evaluation across historical NEPSE sessions."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Historical backtest and strategy evaluation",
        description="Simulates technical candidate selection over historical periods and computes forward horizon returns (5d, 10d, 20d, 60d), win rates, and portfolio equity curve against NEPSE benchmark.",
        request=BacktestRequestSerializer,
        responses={200: BacktestReportSerializer},
    )
    def post(self, request) -> Response:
        req_serializer = BacktestRequestSerializer(data=request.data)
        req_serializer.is_valid(raise_exception=True)
        validated = req_serializer.validated_data

        end_d = validated.get("end_date") or get_latest_trading_date()
        start_d = validated.get("start_date") or (end_d - datetime.timedelta(days=90))
        min_score = validated.get("min_technical_score", 70.0)
        cat = validated.get("category")
        horizons = validated.get("horizons") or [5, 10, 20, 60]
        rebal_days = validated.get("rebalance_frequency_days", 5)
        cap = validated.get("initial_capital", 1000000.0)

        config = BacktestConfiguration(
            start_date=start_d,
            end_date=end_d,
            min_technical_score=min_score,
            category=cat,
            horizons=horizons,
            rebalance_frequency_days=rebal_days,
            initial_capital=cap,
        )

        engine = TechnicalBacktestEngine(config)
        report = engine.run()
        res_serializer = BacktestReportSerializer(report)
        return Response(res_serializer.data, status=status.HTTP_200_OK)

    @extend_schema(
        summary="Get backtest report via query parameters",
        description="Run historical backtest simulation using GET query parameters.",
        parameters=[
            OpenApiParameter("start_date", str, description="Start date (YYYY-MM-DD)", required=False),
            OpenApiParameter("end_date", str, description="End date (YYYY-MM-DD)", required=False),
            OpenApiParameter("min_technical_score", float, description="Minimum score threshold (default: 70.0)", required=False),
            OpenApiParameter("category", str, description="Candidate category", required=False),
            OpenApiParameter("rebalance_frequency_days", int, description="Rebalance period in sessions (default: 5)", required=False),
        ],
        responses={200: BacktestReportSerializer},
    )
    def get(self, request) -> Response:
        end_d = get_latest_trading_date()
        date_end_str = request.query_params.get("end_date")
        if date_end_str:
            try:
                end_d = datetime.date.fromisoformat(date_end_str)
            except ValueError:
                pass

        date_start_str = request.query_params.get("start_date")
        start_d = end_d - datetime.timedelta(days=90)
        if date_start_str:
            try:
                start_d = datetime.date.fromisoformat(date_start_str)
            except ValueError:
                pass

        try:
            min_score = float(request.query_params.get("min_technical_score", 70.0))
        except (ValueError, TypeError):
            min_score = 70.0

        cat = request.query_params.get("category")
        try:
            rebal_days = int(request.query_params.get("rebalance_frequency_days", 5))
        except (ValueError, TypeError):
            rebal_days = 5

        config = BacktestConfiguration(
            start_date=start_d,
            end_date=end_d,
            min_technical_score=min_score,
            category=cat,
            horizons=[5, 10, 20, 60],
            rebalance_frequency_days=rebal_days,
            initial_capital=1000000.0,
        )

        engine = TechnicalBacktestEngine(config)
        report = engine.run()
        res_serializer = BacktestReportSerializer(report)
        return Response(res_serializer.data, status=status.HTTP_200_OK)


class TradingSignalListView(generics.ListAPIView):
    """List daily and historical trading signals with filters for strategy, setup, and status."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TradingSignalSerializer
    filterset_class = TradingSignalFilter
    queryset = TradingSignal.objects.select_related("security", "security__sector").all().order_by("-signal_date", "-composite_score")

    @extend_schema(
        summary="List generated trading signals",
        description="Filterable list of daily signals for Short-Term (2-10 days) and Swing (1-8 weeks) strategies.",
        parameters=[
            OpenApiParameter("strategy", str, description="Filter by strategy: 'short_term' or 'swing'"),
            OpenApiParameter("setup_type", str, description="Filter by setup: 'breakout', 'pullback', 'support_rebound', etc."),
            OpenApiParameter("status", str, description="Filter by status: 'pending', 'active', 'target_1_hit', 'stopped_out', etc."),
            OpenApiParameter("signal_date", str, description="Filter by signal date (YYYY-MM-DD)"),
            OpenApiParameter("symbol", str, description="Filter by stock ticker symbol (e.g. NABIL)"),
            OpenApiParameter("min_score", float, description="Minimum composite score threshold (0-100)"),
        ],
        responses={200: TradingSignalSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class ActiveTradingSignalsView(generics.ListAPIView):
    """List currently active/open positions being tracked by the lifecycle engine."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TradingSignalSerializer
    filterset_class = TradingSignalFilter
    queryset = TradingSignal.objects.filter(status=TradingSignal.STATUS_ACTIVE).select_related("security", "security__sector").order_by("-composite_score")

    @extend_schema(
        summary="List currently active trading positions",
        description="Returns open positions that have been filled and are actively managed with trailing stops.",
        responses={200: TradingSignalSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class TradingSignalDetailView(generics.RetrieveAPIView):
    """Detailed view of an individual trading signal including complete daily tracking history."""

    permission_classes = [permissions.AllowAny]
    serializer_class = TradingSignalDetailSerializer
    queryset = TradingSignal.objects.prefetch_related("tracking_history").select_related("security", "security__sector").all()

    @extend_schema(
        summary="Retrieve trading signal detail with tracking logs",
        description="Returns full signal specification, price levels, targets, stop-loss, rationale, and daily tracking history.",
        responses={200: TradingSignalDetailSerializer},
    )
    def get(self, request, *args, **kwargs):
        return super().get(request, *args, **kwargs)


class SignalPerformanceHistoryView(APIView):
    """Aggregate statistical performance for realized/closed trading signals."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Get realized performance statistics for trading strategies",
        description="Computes win rate, profit factor, average return, and average holding period for realized trades.",
        responses={200: SignalPerformanceStatsSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        results = []
        for strat_type in [TradingSignal.STRATEGY_SHORT_TERM, TradingSignal.STRATEGY_SWING]:
            qs = TradingSignal.objects.filter(strategy_type=strat_type)
            total = qs.count()
            closed_qs = qs.exclude(status__in=[TradingSignal.STATUS_PENDING, TradingSignal.STATUS_ACTIVE])
            closed_count = closed_qs.count()
            active_count = qs.filter(status=TradingSignal.STATUS_ACTIVE).count()

            wins = closed_qs.filter(return_pct__gt=0).count()
            losses = closed_qs.filter(return_pct__lt=0).count()
            win_rate = (wins / closed_count * 100.0) if closed_count > 0 else 0.0

            returns = list(closed_qs.exclude(return_pct__isnull=True).values_list("return_pct", flat=True))
            avg_return = (sum(float(r) for r in returns) / len(returns)) if returns else 0.0

            gross_gain = sum(float(r) for r in returns if float(r) > 0)
            gross_loss = abs(sum(float(r) for r in returns if float(r) < 0))
            profit_factor = (gross_gain / gross_loss) if gross_loss > 0 else (gross_gain if gross_gain > 0 else 1.0)

            holding_days = list(closed_qs.values_list("holding_period_days", flat=True))
            avg_holding = (sum(holding_days) / len(holding_days)) if holding_days else 0.0

            results.append({
                "strategy_type": strat_type,
                "total_signals": total,
                "closed_signals": closed_count,
                "active_signals": active_count,
                "winning_signals": wins,
                "losing_signals": losses,
                "win_rate_pct": round(win_rate, 2),
                "average_return_pct": round(avg_return, 2),
                "profit_factor": round(profit_factor, 2) if gross_loss > 0 else None,
                "average_holding_days": round(avg_holding, 1),
            })

        return Response(results, status=status.HTTP_200_OK)


class TradingStrategiesMetaView(APIView):
    """Metadata describing available strategies and their trading rules."""

    permission_classes = [permissions.AllowAny]

    @extend_schema(
        summary="Get strategies metadata and decision rules",
        description="Returns specifications, target holding periods, entry patterns, and exit rules for Strategy A and Strategy B.",
        responses={200: TradingStrategyMetaSerializer(many=True)},
    )
    def get(self, request, *args, **kwargs):
        meta = [
            {
                "strategy_type": "short_term",
                "name": "Short-Term Trading Strategy",
                "description": "Captures quick momentum moves, resistance breakouts, and EMA 20 pullbacks over short holding horizons.",
                "holding_period": "2 to 10 trading sessions",
                "min_rr_ratio": 1.5,
                "entry_patterns": [
                    "Resistance Breakout (20-day high with volume expansion)",
                    "EMA 20 Pullback Rebound (Retest of rising EMA 20)",
                    "Horizontal Support Level Rebound",
                ],
                "exit_rules": [
                    "Stop Loss triggered (max swing low or 1.5x ATR)",
                    "Target 1 reached (1.5x Risk - move stop to breakeven)",
                    "Target 2 reached (2.0x Risk - full exit)",
                    "Technical breakdown (close below falling EMA 20 with bearish MACD)",
                    "Time-based exit (Day 10 session close)",
                ],
            },
            {
                "strategy_type": "swing",
                "name": "Swing Trading Strategy",
                "description": "Rides sustained multi-week trends and base consolidation breakouts with multi-timeframe confirmation.",
                "holding_period": "1 to 8 weeks (up to 40 sessions)",
                "min_rr_ratio": 2.0,
                "entry_patterns": [
                    "Trend Continuation (Price > EMA 20 > EMA 50 with rising slope)",
                    "Base Consolidation Breakout (Multi-week base breakout on volume)",
                    "Sector Rotation Pullback (Top-ranked stock in leading sector)",
                ],
                "exit_rules": [
                    "Stop Loss triggered (major 20-session swing low or 2.0x ATR)",
                    "Target 1 reached (2.0x Risk - initiate EMA 20 trailing stop)",
                    "Target 2 reached (3.0x Risk - profit booking)",
                    "Structural breakdown (close below EMA 50 or -DI > +DI with strong ADX)",
                    "Time-based exit (Day 40 session close)",
                ],
            },
        ]
        return Response(meta, status=status.HTTP_200_OK)

