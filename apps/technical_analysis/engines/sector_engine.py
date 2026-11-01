"""Sector Intelligence Engine.

Analyzes every eligible NEPSE sector:
- Official index OHLCV analysis with transparent fallback to derived constituent basket
- Sector returns (daily, weekly, monthly)
- Technical indicators (EMA 20/50/200, RSI, MACD, ADX/DMI, Volume)
- Sector relative strength against NEPSE index
- Sector constituent breadth (advancing, declining, % above EMA 20/50)
- Sector Strength Score (0 to 100)
- Top 3 trending sector highlights and rotation candidate identification
"""

from __future__ import annotations

import datetime
from dataclasses import dataclass
from typing import Any

from django.db.models import Max

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.technical_analysis.engines.market_engine import get_market_candles
from apps.technical_analysis.indicators import (
    Candle,
    FullIndicatorSet,
    calculate_all_indicators,
    calculate_ema,
    candles_from_records,
)
from apps.technical_analysis.scoring.relative_strength import (
    RelativeStrengthAnalysis,
    calculate_relative_performance,
)
from apps.technical_analysis.scoring.sector_scoring import (
    SectorStrengthScore,
    score_sector_strength,
)

# Canonical mapping of NEPSE Sector names to MarketIndex upstream IDs
SECTOR_NAME_TO_INDEX_ID: dict[str, int] = {
    "Commercial Banks": 51,              # Banking SubIndex
    "Hotels And Tourism": 52,            # Hotels And Tourism Index
    "Others": 53,                        # Others Index
    "Hydro Power": 54,                   # HydroPower Index
    "Development Banks": 55,             # Development Bank Index
    "Manufacturing And Processing": 56,  # Manufacturing And Processing
    "Non Life Insurance": 59,            # Non Life Insurance
    "Finance": 60,                       # Finance Index
    "Tradings": 61,                      # Trading Index
    "Microfinance": 64,                  # Microfinance Index
    "Life Insurance": 65,                # Life Insurance
    "Mutual Fund": 66,                   # Mutual Fund
    "Investment": 67,                    # Investment Index
}


@dataclass(frozen=True)
class SectorBreadth:
    """Constituent breadth metrics within a single sector."""

    constituent_count: int
    active_traded_count: int
    advancing_count: int
    declining_count: int
    unchanged_count: int
    stocks_above_ema_20: int
    pct_above_ema_20: float | None
    stocks_above_ema_50: int
    pct_above_ema_50: float | None


@dataclass(frozen=True)
class SingleSectorAnalysis:
    """Complete analysis and ranking metrics for an individual sector."""

    sector_id: int
    sector_nepse_id: int
    sector_name: str
    display_name: str
    as_of_date: datetime.date

    latest_close: float
    point_change: float | None
    daily_return_pct: float | None
    weekly_return_pct: float | None
    monthly_return_pct: float | None
    volume: float

    data_source: str  # "official_index" or "derived_basket"
    indicators: FullIndicatorSet
    relative_strength: RelativeStrengthAnalysis
    breadth: SectorBreadth
    score: SectorStrengthScore


@dataclass(frozen=True)
class SectorIntelligenceResult:
    """Market-wide sector rankings and intelligence."""

    as_of_date: datetime.date
    total_sectors: int
    top_three_trending: list[SingleSectorAnalysis]
    all_sector_rankings: list[SingleSectorAnalysis]
    strongest_sectors: list[SingleSectorAnalysis]
    weakest_sectors: list[SingleSectorAnalysis]
    emerging_sectors: list[SingleSectorAnalysis]
    improving_sectors: list[SingleSectorAnalysis]
    weakening_sectors: list[SingleSectorAnalysis]
    rotation_candidates: list[dict[str, Any]]


def get_sector_candles(
    sector: Sector,
    as_of_date: datetime.date,
    lookback_bars: int = 250,
) -> tuple[list[Candle], str]:
    """Retrieve historical candles for a sector.

    Prefers official IndexSnapshot; falls back to an equal-weighted basket
    of its constituent securities if the official index is missing.
    """
    index_id = SECTOR_NAME_TO_INDEX_ID.get(sector.name)
    if index_id:
        index_obj = MarketIndex.objects.filter(nepse_id=index_id).first()
        if index_obj:
            snaps = list(
                IndexSnapshot.objects.filter(
                    index=index_obj,
                    trading_date__lte=as_of_date,
                )
                .order_by("-trading_date")[:lookback_bars]
            )
            if len(snaps) >= 15:
                snaps.reverse()
                candles = candles_from_records(snaps)
                if candles:
                    return candles, "official_index"

    # Fallback: Construct derived constituent basket
    constituent_ids = list(sector.securities.values_list("id", flat=True))
    if not constituent_ids:
        return [], "none"

    # Pull recent prices for constituents
    recent_dates = list(
        DailyPrice.objects.filter(
            security_id__in=constituent_ids,
            trading_date__lte=as_of_date,
        )
        .values_list("trading_date", flat=True)
        .distinct()
        .order_by("-trading_date")[:lookback_bars]
    )
    if not recent_dates:
        return [], "none"

    recent_dates.reverse()

    # Aggregate by date: average close, sum volume
    derived_candles: list[Candle] = []
    base_level = 1000.0
    current_index_level = base_level

    for i, t_date in enumerate(recent_dates):
        day_prices = list(
            DailyPrice.objects.filter(
                security_id__in=constituent_ids,
                trading_date=t_date,
                close__isnull=False,
                close__gt=0,
            ).values("close", "volume", "percentage_change")
        )
        if not day_prices:
            continue

        day_vol = sum(float(r["volume"] or 0) for r in day_prices)
        avg_pct_chg = sum(float(r["percentage_change"] or 0) for r in day_prices) / len(day_prices)

        if i == 0:
            current_index_level = base_level
        else:
            current_index_level *= (1.0 + (avg_pct_chg / 100.0))

        derived_candles.append(
            Candle(
                trading_date=t_date,
                open=current_index_level,
                high=current_index_level,
                low=current_index_level,
                close=current_index_level,
                volume=day_vol,
            )
        )

    return derived_candles, "derived_basket"


def compute_sector_breadth(
    sector: Sector,
    as_of_date: datetime.date,
) -> SectorBreadth:
    """Compute constituent breadth within a sector."""
    constituent_ids = list(sector.securities.values_list("id", flat=True))
    total_constituents = len(constituent_ids)

    if total_constituents == 0:
        return SectorBreadth(
            constituent_count=0, active_traded_count=0,
            advancing_count=0, declining_count=0, unchanged_count=0,
            stocks_above_ema_20=0, pct_above_ema_20=None,
            stocks_above_ema_50=0, pct_above_ema_50=None,
        )

    # Active prices on as_of_date
    active_rows = list(
        DailyPrice.objects.filter(
            security_id__in=constituent_ids,
            trading_date=as_of_date,
            close__isnull=False,
            close__gt=0,
        ).values("security_id", "close", "percentage_change")
    )

    active_count = len(active_rows)
    if active_count == 0:
        return SectorBreadth(
            constituent_count=total_constituents, active_traded_count=0,
            advancing_count=0, declining_count=0, unchanged_count=0,
            stocks_above_ema_20=0, pct_above_ema_20=None,
            stocks_above_ema_50=0, pct_above_ema_50=None,
        )

    advancing = sum(1 for r in active_rows if float(r["percentage_change"] or 0) > 0.0)
    declining = sum(1 for r in active_rows if float(r["percentage_change"] or 0) < 0.0)
    unchanged = sum(1 for r in active_rows if float(r["percentage_change"] or 0) == 0.0)

    # Price history for constituents to check EMA 20 & 50
    recent_dates = list(
        DailyPrice.objects.filter(
            security_id__in=constituent_ids,
            trading_date__lte=as_of_date,
        )
        .values_list("trading_date", flat=True)
        .distinct()
        .order_by("-trading_date")[:60]
    )
    min_date = recent_dates[-1] if recent_dates else as_of_date

    hist_prices = list(
        DailyPrice.objects.filter(
            security_id__in=constituent_ids,
            trading_date__gte=min_date,
            trading_date__lte=as_of_date,
            close__isnull=False,
            close__gt=0,
        )
        .values("security_id", "trading_date", "close")
        .order_by("security_id", "trading_date")
    )

    sec_series: dict[int, list[float]] = {}
    for hp in hist_prices:
        s_id = hp["security_id"]
        if s_id not in sec_series:
            sec_series[s_id] = []
        if hp["close"] is not None:
            sec_series[s_id].append(float(hp["close"]))

    above_20 = 0
    above_50 = 0
    for act_row in active_rows:
        s_id = act_row["security_id"]
        c_price = float(act_row["close"]) if act_row["close"] is not None else 0.0
        series = sec_series.get(s_id, [])
        if len(series) >= 20:
            ema20 = calculate_ema(series, 20)[-1]
            if ema20 is not None and c_price > ema20:
                above_20 += 1
        if len(series) >= 50:
            ema50 = calculate_ema(series, 50)[-1]
            if ema50 is not None and c_price > ema50:
                above_50 += 1

    pct_20 = round((above_20 / active_count) * 100.0, 1) if active_count > 0 else None
    pct_50 = round((above_50 / active_count) * 100.0, 1) if active_count > 0 else None

    return SectorBreadth(
        constituent_count=total_constituents,
        active_traded_count=active_count,
        advancing_count=advancing,
        declining_count=declining,
        unchanged_count=unchanged,
        stocks_above_ema_20=above_20,
        pct_above_ema_20=pct_20,
        stocks_above_ema_50=above_50,
        pct_above_ema_50=pct_50,
    )


def run_sector_intelligence(
    as_of_date: datetime.date | None = None,
) -> SectorIntelligenceResult:
    """Execute complete intelligence analysis and ranking for all NEPSE sectors."""
    if as_of_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            latest_d = datetime.date.today()
        as_of_date = latest_d

    # Fetch benchmark NEPSE candles
    nepse_candles, _ = get_market_candles(as_of_date, lookback_bars=250)

    all_sectors = list(Sector.objects.all().order_by("name"))
    analyzed_sectors: list[SingleSectorAnalysis] = []

    for sector in all_sectors:
        candles, data_source = get_sector_candles(sector, as_of_date, lookback_bars=250)
        indicator_set = calculate_all_indicators(candles)
        relative_strength = calculate_relative_performance(candles, nepse_candles)
        breadth = compute_sector_breadth(sector, as_of_date)

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

        score = score_sector_strength(
            indicator_set,
            relative_strength,
            daily_return_pct=daily_ret,
            weekly_return_pct=weekly_ret,
            monthly_return_pct=monthly_ret,
        )

        analyzed_sectors.append(
            SingleSectorAnalysis(
                sector_id=sector.id,
                sector_nepse_id=sector.nepse_id,
                sector_name=sector.name,
                display_name=sector.display_name or sector.name,
                as_of_date=as_of_date,
                latest_close=round(last_close, 2),
                point_change=point_chg,
                daily_return_pct=daily_ret,
                weekly_return_pct=weekly_ret,
                monthly_return_pct=monthly_ret,
                volume=vol,
                data_source=data_source,
                indicators=indicator_set,
                relative_strength=relative_strength,
                breadth=breadth,
                score=score,
            )
        )

    # Rank all sectors by Sector Strength Score descending
    ranked_sectors = sorted(analyzed_sectors, key=lambda s: s.score.total_score, reverse=True)

    # Top 3 trending highlights (highlights only, all sectors remain accessible)
    top_three = ranked_sectors[:3]
    strongest = [s for s in ranked_sectors if s.score.total_score >= 65.0]
    weakest = [s for s in ranked_sectors if s.score.total_score < 35.0]
    emerging = [s for s in ranked_sectors if s.score.rotation_stage == "emerging"]
    improving = [s for s in ranked_sectors if s.score.rotation_stage == "improving"]
    weakening = [s for s in ranked_sectors if s.score.rotation_stage == "weakening"]

    # Rotation candidate details
    rotation_candidates: list[dict[str, Any]] = []
    for s in ranked_sectors:
        if s.score.rotation_stage in ("leading", "improving", "emerging"):
            rotation_candidates.append({
                "sector_id": s.sector_id,
                "name": s.sector_name,
                "stage": s.score.rotation_stage,
                "score": s.score.total_score,
                "classification": s.score.classification,
                "rs_20": s.relative_strength.rs_20.excess_return_pct,
                "weekly_return": s.weekly_return_pct,
            })

    return SectorIntelligenceResult(
        as_of_date=as_of_date,
        total_sectors=len(ranked_sectors),
        top_three_trending=top_three,
        all_sector_rankings=ranked_sectors,
        strongest_sectors=strongest,
        weakest_sectors=weakest,
        emerging_sectors=emerging,
        improving_sectors=improving,
        weakening_sectors=weakening,
        rotation_candidates=rotation_candidates,
    )
