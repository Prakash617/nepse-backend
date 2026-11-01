"""URL routing for Technical Analysis endpoints."""

from __future__ import annotations

from django.urls import path

from apps.technical_analysis.views import (
    ActiveTradingSignalsView,
    BacktestRunView,
    MarketOverviewView,
    SectorDetailView,
    SectorListView,
    SectorStocksView,
    SectorTopStocksView,
    SignalPerformanceHistoryView,
    StockDetailView,
    StockHistoryView,
    StockIndicatorsView,
    StockRankingsView,
    StockRecommendationsView,
    StockSignalsView,
    TradingSignalDetailView,
    TradingSignalListView,
    TradingStrategiesMetaView,
    TrendingSectorsView,
)

app_name = "technical_analysis"

urlpatterns = [
    # Market Overview
    path("market-overview/", MarketOverviewView.as_view(), name="market-overview"),

    # Sectors Intelligence
    path("sectors/", SectorListView.as_view(), name="sector-list"),
    path("sectors/trending/", TrendingSectorsView.as_view(), name="sectors-trending"),
    path("sectors/top/", TrendingSectorsView.as_view(), name="sectors-top"),
    path("sectors/<int:sector_id>/", SectorDetailView.as_view(), name="sector-detail"),
    path("sectors/<int:sector_id>/stocks/", SectorStocksView.as_view(), name="sector-stocks"),
    path("sectors/<int:sector_id>/top-stocks/", SectorTopStocksView.as_view(), name="sector-top-stocks"),

    # Stocks Rankings & Screener
    path("stocks/rankings/", StockRankingsView.as_view(), name="stock-rankings"),
    path("stocks/recommendations/", StockRecommendationsView.as_view(), name="stock-recommendations"),
    path("stocks/<str:symbol>/", StockDetailView.as_view(), name="stock-detail"),
    path("stocks/<str:symbol>/indicators/", StockIndicatorsView.as_view(), name="stock-indicators"),
    path("stocks/<str:symbol>/signals/", StockSignalsView.as_view(), name="stock-signals"),
    path("stocks/<str:symbol>/history/", StockHistoryView.as_view(), name="stock-history"),

    # Daily Trading Signal Engine
    path("signals/", TradingSignalListView.as_view(), name="signal-list"),
    path("signals/daily/", TradingSignalListView.as_view(), name="signal-daily"),
    path("signals/active/", ActiveTradingSignalsView.as_view(), name="signal-active"),
    path("signals/history/", SignalPerformanceHistoryView.as_view(), name="signal-history"),
    path("signals/<int:pk>/", TradingSignalDetailView.as_view(), name="signal-detail"),
    path("strategies/", TradingStrategiesMetaView.as_view(), name="strategies-meta"),

    # Historical Backtesting & Strategy Evaluation
    path("backtesting/run/", BacktestRunView.as_view(), name="backtesting-run"),
    path("backtesting/results/", BacktestRunView.as_view(), name="backtesting-results"),
]
