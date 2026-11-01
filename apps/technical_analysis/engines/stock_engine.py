"""Individual Stock Technical Analysis Engine.

Analyzes individual securities:
- Historical OHLCV technical indicators
- Relative strength comparison against both NEPSE benchmark and sector index
- Multi-module technical scoring (0 to 100)
- Bullish and bearish signal detection
- Factual human-readable explanation generation
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from django.db.models import Max

from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.engines.market_engine import get_market_candles
from apps.technical_analysis.engines.sector_engine import get_sector_candles
from apps.technical_analysis.indicators import (
    Candle,
    FullIndicatorSet,
    calculate_all_indicators,
    candles_from_records,
)
from apps.technical_analysis.scoring.relative_strength import (
    RelativeStrengthAnalysis,
    calculate_relative_performance,
)
from apps.technical_analysis.scoring.stock_scoring import (
    StockTechnicalScore,
    score_stock_technical,
)
from apps.technical_analysis.services.explanation_service import (
    generate_stock_explanation,
)


@dataclass(frozen=True)
class SingleStockAnalysis:
    """Consolidated technical intelligence for an individual stock."""

    security_id: int
    nepse_id: int
    symbol: str
    company_name: str
    sector_id: int | None
    sector_name: str
    as_of_date: datetime.date

    latest_close: float
    point_change: float | None
    daily_return_pct: float | None
    volume: float

    indicators: FullIndicatorSet
    relative_strength_market: RelativeStrengthAnalysis
    relative_strength_sector: RelativeStrengthAnalysis
    score: StockTechnicalScore
    explanation: str


def analyze_single_security(
    security: Security,
    as_of_date: datetime.date,
    nepse_candles: list[Candle] | None = None,
    sector_candles: list[Candle] | None = None,
    sector_strength_score: float | None = None,
    lookback_bars: int = 250,
) -> SingleStockAnalysis | None:
    """Analyze a single security on as_of_date."""
    # Pull stock price history up to as_of_date
    price_records = list(
        DailyPrice.objects.filter(
            security=security,
            trading_date__lte=as_of_date,
            close__isnull=False,
            close__gt=0,
        )
        .order_by("-trading_date")[:lookback_bars]
    )
    if not price_records:
        return None

    price_records.reverse()
    candles = candles_from_records(price_records)
    if not candles:
        return None

    # Benchmark NEPSE candles
    if nepse_candles is None:
        nepse_candles, _ = get_market_candles(as_of_date, lookback_bars=lookback_bars)

    # Sector candles
    if sector_candles is None and security.sector:
        sector_candles, _ = get_sector_candles(security.sector, as_of_date, lookback_bars=lookback_bars)
    elif sector_candles is None:
        sector_candles = []

    # Indicators & Relative Strength
    indicators = calculate_all_indicators(candles)
    rs_market = calculate_relative_performance(candles, nepse_candles)
    rs_sector = calculate_relative_performance(candles, sector_candles)

    is_sec_strong = bool(sector_strength_score is not None and sector_strength_score >= 65.0)

    # Scoring
    stock_score = score_stock_technical(
        indicators,
        rs_market,
        rs_sector,
        is_sector_strong=is_sec_strong,
    )

    sector_title = security.sector.name if security.sector else "Unclassified"
    explanation = generate_stock_explanation(
        symbol=security.symbol,
        company_name=security.company_name,
        sector_name=sector_title,
        score=stock_score,
        sector_strength_score=sector_strength_score,
    )

    last_candle = candles[-1]
    pt_chg: float | None = None
    daily_ret: float | None = None
    if len(candles) >= 2:
        pt_chg = round(last_candle.close - candles[-2].close, 2)
        if candles[-2].close > 0:
            daily_ret = round((pt_chg / candles[-2].close) * 100.0, 2)

    return SingleStockAnalysis(
        security_id=security.id,
        nepse_id=security.nepse_id,
        symbol=security.symbol,
        company_name=security.company_name,
        sector_id=security.sector_id,
        sector_name=sector_title,
        as_of_date=as_of_date,
        latest_close=round(last_candle.close, 2),
        point_change=pt_chg,
        daily_return_pct=daily_ret,
        volume=last_candle.volume,
        indicators=indicators,
        relative_strength_market=rs_market,
        relative_strength_sector=rs_sector,
        score=stock_score,
        explanation=explanation,
    )


def run_all_stocks_analysis(
    as_of_date: datetime.date | None = None,
    *,
    sector_strength_map: dict[int, float] | None = None,
    lookback_bars: int = 250,
) -> list[SingleStockAnalysis]:
    """Execute high-performance bulk technical analysis across all active securities.

    Performs bulk pre-fetching and avoids querying inside loops.
    """
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            latest_d = datetime.date.today()
        as_of_date = latest_d

    nepse_candles, _ = get_market_candles(as_of_date, lookback_bars=lookback_bars)

    # Pre-fetch sector candles
    sector_candles_map: dict[int, list[Candle]] = {}
    for sec in Sector.objects.all():
        c_list, _ = get_sector_candles(sec, as_of_date, lookback_bars=lookback_bars)
        sector_candles_map[sec.id] = c_list

    # Identify active securities with a price on as_of_date
    active_sec_ids = set(
        DailyPrice.objects.filter(
            trading_date=as_of_date,
            close__isnull=False,
            close__gt=0,
        ).values_list("security_id", flat=True)
    )
    if not active_sec_ids:
        return []

    # Filter to equity securities primarily (or all active)
    securities = list(
        Security.objects.filter(id__in=active_sec_ids)
        .select_related("sector")
        .order_by("symbol")
    )

    # Determine date range for lookback bars
    distinct_dates = list(
        DailyPrice.objects.filter(trading_date__lte=as_of_date)
        .values_list("trading_date", flat=True)
        .distinct()
        .order_by("-trading_date")[:lookback_bars]
    )
    min_date = distinct_dates[-1] if distinct_dates else as_of_date

    # Bulk query price history for all active securities in one query
    price_rows = list(
        DailyPrice.objects.filter(
            security_id__in=active_sec_ids,
            trading_date__gte=min_date,
            trading_date__lte=as_of_date,
            close__isnull=False,
            close__gt=0,
        )
        .values(
            "security_id", "trading_date", "open", "high",
            "low", "close", "volume", "turnover", "percentage_change",
        )
        .order_by("security_id", "trading_date")
    )

    # Group price records by security_id
    grouped_prices: dict[int, list[Any]] = {}
    for r in price_rows:
        s_id = r["security_id"]
        if s_id not in grouped_prices:
            grouped_prices[s_id] = []
        grouped_prices[s_id].append(r)

    results: list[SingleStockAnalysis] = []

    for security in securities:
        sec_records = grouped_prices.get(security.id, [])
        if len(sec_records) < 5:  # skip completely illiquid / brand new listings with < 5 bars
            continue

        candles = candles_from_records(sec_records)
        if not candles:
            continue

        sec_candles = sector_candles_map.get(security.sector_id, []) if security.sector_id else []
        sec_strength_val = sector_strength_map.get(security.sector_id) if (sector_strength_map and security.sector_id) else None

        indicators = calculate_all_indicators(candles)
        rs_m = calculate_relative_performance(candles, nepse_candles)
        rs_s = calculate_relative_performance(candles, sec_candles)

        is_sec_strong = bool(sec_strength_val is not None and sec_strength_val >= 65.0)

        score = score_stock_technical(
            indicators,
            rs_m,
            rs_s,
            is_sector_strong=is_sec_strong,
        )

        sector_title = security.sector.name if security.sector else "Unclassified"
        explanation = generate_stock_explanation(
            symbol=security.symbol,
            company_name=security.company_name,
            sector_name=sector_title,
            score=score,
            sector_strength_score=sec_strength_val,
        )

        last_c = candles[-1]
        pt_chg: float | None = None
        daily_ret: float | None = None
        if len(candles) >= 2:
            pt_chg = round(last_c.close - candles[-2].close, 2)
            if candles[-2].close > 0:
                daily_ret = round((pt_chg / candles[-2].close) * 100.0, 2)

        results.append(
            SingleStockAnalysis(
                security_id=security.id,
                nepse_id=security.nepse_id,
                symbol=security.symbol,
                company_name=security.company_name,
                sector_id=security.sector_id,
                sector_name=sector_title,
                as_of_date=as_of_date,
                latest_close=round(last_c.close, 2),
                point_change=pt_chg,
                daily_return_pct=daily_ret,
                volume=last_c.volume,
                indicators=indicators,
                relative_strength_market=rs_m,
                relative_strength_sector=rs_s,
                score=score,
                explanation=explanation,
            )
        )

    return results
