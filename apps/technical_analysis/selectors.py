"""Optimized database selectors for technical analysis.

Provides clean ORM queries using select_related, prefetch_related,
and Redis caching for read-heavy dashboard endpoints.
"""

from __future__ import annotations

import datetime

from django.core.cache import cache
from django.db.models import Max, QuerySet

from apps.prices.models import DailyPrice
from apps.technical_analysis.models import (
    RecommendationSnapshot,
    SectorAnalysisSnapshot,
    SectorStockRanking,
    TechnicalScoreSnapshot,
    TechnicalSignal,
)


def get_latest_trading_date() -> datetime.date:
    """Get the latest analyzed trading date, or latest DailyPrice date."""
    cached_date = cache.get("tech:latest_trading_date")
    if isinstance(cached_date, datetime.date):
        return cached_date

    latest_snap_date = TechnicalScoreSnapshot.objects.aggregate(max_d=Max("trading_date"))["max_d"]
    if isinstance(latest_snap_date, datetime.date):
        cache.set("tech:latest_trading_date", latest_snap_date, timeout=300)
        return latest_snap_date

    latest_price_date = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
    result: datetime.date = (
        latest_price_date
        if isinstance(latest_price_date, datetime.date)
        else datetime.date.today()
    )
    cache.set("tech:latest_trading_date", result, timeout=300)
    return result


def get_sector_snapshots_queryset(
    as_of_date: datetime.date | None = None,
) -> QuerySet[SectorAnalysisSnapshot]:
    """Retrieve sector analysis snapshots for a date ordered by sector_score descending."""
    target_date = as_of_date or get_latest_trading_date()
    return (
        SectorAnalysisSnapshot.objects.filter(trading_date=target_date)
        .select_related("sector")
        .order_by("-sector_score")
    )


def get_stock_scores_queryset(
    as_of_date: datetime.date | None = None,
) -> QuerySet[TechnicalScoreSnapshot]:
    """Retrieve stock technical scores for a date with related security and sector."""
    target_date = as_of_date or get_latest_trading_date()
    return (
        TechnicalScoreSnapshot.objects.filter(trading_date=target_date)
        .select_related("security", "security__sector")
        .order_by("-total_score")
    )


def get_sector_stock_rankings_queryset(
    sector_id: int,
    as_of_date: datetime.date | None = None,
) -> QuerySet[SectorStockRanking]:
    """Retrieve constituent stock rankings for a specific sector."""
    target_date = as_of_date or get_latest_trading_date()
    return (
        SectorStockRanking.objects.filter(sector_id=sector_id, trading_date=target_date)
        .select_related("security", "sector")
        .order_by("rank")
    )


def get_recommendations_queryset(
    as_of_date: datetime.date | None = None,
    category: str | None = None,
) -> QuerySet[RecommendationSnapshot]:
    """Retrieve algorithmic candidate recommendations."""
    target_date = as_of_date or get_latest_trading_date()
    qs = (
        RecommendationSnapshot.objects.filter(trading_date=target_date)
        .select_related("security", "sector")
        .order_by("-technical_score")
    )
    if category:
        qs = qs.filter(category=category.lower())
    return qs


def get_stock_technical_signals_queryset(
    security_id: int,
    limit: int = 20,
) -> QuerySet[TechnicalSignal]:
    """Retrieve recent technical signals for a security."""
    return TechnicalSignal.objects.filter(security_id=security_id).order_by("-trading_date", "-id")[:limit]


def get_stock_history_queryset(
    security_id: int,
    limit: int = 60,
) -> QuerySet[TechnicalScoreSnapshot]:
    """Retrieve historical technical scores for charting score progression."""
    return TechnicalScoreSnapshot.objects.filter(security_id=security_id).order_by("trading_date")[:limit]
