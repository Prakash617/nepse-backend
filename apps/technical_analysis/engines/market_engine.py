"""Market Analysis Engine.

Analyzes the overall NEPSE market:
- Daily, weekly, monthly market returns
- Technical indicators (EMA 20/50, SMA 200, RSI 14, MACD, ADX/DMI, Volume)
- Market breadth (stocks above EMA 20/50/200, advance/decline ratio)
- Composite multi-signal Market Condition rating
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass

from django.db.models import Max

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.market.models import MarketSnapshot
from apps.prices.models import DailyPrice
from apps.technical_analysis.indicators import (
    Candle,
    FullIndicatorSet,
    calculate_all_indicators,
    calculate_ema,
    calculate_sma,
    candles_from_records,
)
from apps.technical_analysis.scoring.market_scoring import (
    MarketBreadth,
    MarketConditionScore,
    score_market_condition,
)


@dataclass(frozen=True)
class MarketAnalysisResult:
    """Consolidated market analysis output for a specific trading session."""

    as_of_date: datetime.date
    latest_close: float
    point_change: float | None
    daily_return_pct: float | None
    weekly_return_pct: float | None
    monthly_return_pct: float | None
    volume: float

    indicators: FullIndicatorSet
    breadth: MarketBreadth
    condition: MarketConditionScore
    data_source: str  # "official_index" or "market_snapshot"


def get_market_candles(
    as_of_date: datetime.date,
    lookback_bars: int = 250,
) -> tuple[list[Candle], str]:
    """Retrieve historical market benchmark candles up to as_of_date.

    Prefers official NEPSE Index (nepse_id=58); falls back to MarketSnapshot.
    """
    # 1. Try IndexSnapshot for NEPSE Index (nepse_id=58)
    nepse_index = MarketIndex.objects.filter(nepse_id=58).first()
    if nepse_index:
        snaps = list(
            IndexSnapshot.objects.filter(
                index=nepse_index,
                trading_date__lte=as_of_date,
            )
            .order_by("-trading_date")[:lookback_bars]
        )
        if len(snaps) >= 15:
            snaps.reverse()
            candles = candles_from_records(snaps)
            if candles:
                return candles, "official_index"

    # 2. Fallback to MarketSnapshot
    market_snaps = list(
        MarketSnapshot.objects.filter(trading_date__lte=as_of_date)
        .order_by("-trading_date")[:lookback_bars]
    )
    if market_snaps:
        market_snaps.reverse()
        candles = candles_from_records(market_snaps)
        if candles:
            return candles, "market_snapshot"

    return [], "none"


def compute_market_breadth(as_of_date: datetime.date) -> MarketBreadth:
    """Compute market-wide constituent breadth on as_of_date efficiently.

    Uses a single bulk query of recent prices across all active securities.
    """
    # Identify distinct trading dates up to as_of_date (last 210 sessions)
    recent_dates = list(
        DailyPrice.objects.filter(trading_date__lte=as_of_date)
        .values_list("trading_date", flat=True)
        .distinct()
        .order_by("-trading_date")[:210]
    )
    if not recent_dates:
        return MarketBreadth(
            total_eligible=0, advancing_count=0, declining_count=0,
            unchanged_count=0, advance_decline_ratio=None,
            stocks_above_ema_20=0, pct_above_ema_20=None,
            stocks_above_ema_50=0, pct_above_ema_50=None,
            stocks_above_sma_200=0, pct_above_sma_200=None,
        )

    min_date = recent_dates[-1]

    # Bulk query prices for these dates
    price_rows = list(
        DailyPrice.objects.filter(
            trading_date__gte=min_date,
            trading_date__lte=as_of_date,
            close__isnull=False,
            close__gt=0,
        )
        .values("security_id", "trading_date", "close", "percentage_change")
        .order_by("security_id", "trading_date")
    )

    # Group price series by security
    security_prices: dict[int, list[float]] = {}
    active_changes: dict[int, float] = {}

    for row in price_rows:
        if row["close"] is None:
            continue
        sec_id = row["security_id"]
        c_price = float(row["close"])
        t_date = row["trading_date"]

        if sec_id not in security_prices:
            security_prices[sec_id] = []
        security_prices[sec_id].append(c_price)

        if t_date == as_of_date:
            pct_chg = float(row["percentage_change"]) if row["percentage_change"] is not None else 0.0
            active_changes[sec_id] = pct_chg

    total_active = len(active_changes)
    if total_active == 0:
        return MarketBreadth(
            total_eligible=0, advancing_count=0, declining_count=0,
            unchanged_count=0, advance_decline_ratio=None,
            stocks_above_ema_20=0, pct_above_ema_20=None,
            stocks_above_ema_50=0, pct_above_ema_50=None,
            stocks_above_sma_200=0, pct_above_sma_200=None,
        )

    # Advance / Decline counts
    advancing = sum(1 for chg in active_changes.values() if chg > 0.0)
    declining = sum(1 for chg in active_changes.values() if chg < 0.0)
    unchanged = sum(1 for chg in active_changes.values() if chg == 0.0)
    ad_ratio = round(advancing / declining, 2) if declining > 0 else (float(advancing) if advancing > 0 else 1.0)

    # Moving Average breadth checks for active stocks
    above_ema_20 = 0
    above_ema_50 = 0
    above_sma_200 = 0

    for sec_id in active_changes:
        series = security_prices.get(sec_id, [])
        if not series:
            continue
        last_price = series[-1]

        if len(series) >= 20:
            ema_20 = calculate_ema(series, 20)[-1]
            if ema_20 is not None and last_price > ema_20:
                above_ema_20 += 1

        if len(series) >= 50:
            ema_50 = calculate_ema(series, 50)[-1]
            if ema_50 is not None and last_price > ema_50:
                above_ema_50 += 1

        if len(series) >= 200:
            sma_200 = calculate_sma(series, 200)[-1]
            if sma_200 is not None and last_price > sma_200:
                above_sma_200 += 1

    pct_20 = round((above_ema_20 / total_active) * 100.0, 1) if total_active > 0 else None
    pct_50 = round((above_ema_50 / total_active) * 100.0, 1) if total_active > 0 else None
    pct_200 = round((above_sma_200 / total_active) * 100.0, 1) if total_active > 0 else None

    return MarketBreadth(
        total_eligible=total_active,
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        advance_decline_ratio=ad_ratio,
        stocks_above_ema_20=above_ema_20,
        pct_above_ema_20=pct_20,
        stocks_above_ema_50=above_ema_50,
        pct_above_ema_50=pct_50,
        stocks_above_sma_200=above_sma_200,
        pct_above_sma_200=pct_200,
    )


def run_market_analysis(as_of_date: datetime.date | None = None) -> MarketAnalysisResult:
    """Execute complete technical and breadth analysis for the NEPSE market."""
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            latest_d = datetime.date.today()
        as_of_date = latest_d

    candles, source = get_market_candles(as_of_date, lookback_bars=250)
    indicator_set = calculate_all_indicators(candles)
    breadth = compute_market_breadth(as_of_date)
    condition_score = score_market_condition(indicator_set, breadth)

    n = len(candles)
    last_close = candles[-1].close if candles else 0.0
    vol = candles[-1].volume if candles else 0.0

    point_chg: float | None = None
    daily_ret: float | None = None
    if n >= 2:
        point_chg = round(candles[-1].close - candles[-2].close, 2)
        prev_c = candles[-2].close
        if prev_c > 0:
            daily_ret = round((point_chg / prev_c) * 100.0, 2)

    weekly_ret: float | None = None
    if n >= 6 and candles[-6].close > 0:
        weekly_ret = round(((last_close - candles[-6].close) / candles[-6].close) * 100.0, 2)

    monthly_ret: float | None = None
    if n >= 21 and candles[-21].close > 0:
        monthly_ret = round(((last_close - candles[-21].close) / candles[-21].close) * 100.0, 2)

    return MarketAnalysisResult(
        as_of_date=as_of_date,
        latest_close=last_close,
        point_change=point_chg,
        daily_return_pct=daily_ret,
        weekly_return_pct=weekly_ret,
        monthly_return_pct=monthly_ret,
        volume=vol,
        indicators=indicator_set,
        breadth=breadth,
        condition=condition_score,
        data_source=source,
    )
