"""Relative strength calculation against benchmark.

Computes price performance of an asset/sector relative to a benchmark
(e.g., NEPSE Index or sector index) across multiple lookback windows (5, 20, 60 sessions).
"""

from __future__ import annotations

import datetime
from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class RelativeStrengthMetric:
    """Relative strength performance over a specific lookback horizon."""

    horizon_days: int
    asset_return_pct: float | None
    benchmark_return_pct: float | None
    excess_return_pct: float | None  # asset_return - benchmark_return
    is_outperforming: bool | None


@dataclass(frozen=True)
class RelativeStrengthAnalysis:
    """Consolidated relative strength evaluation across multiple horizons."""

    rs_5: RelativeStrengthMetric
    rs_20: RelativeStrengthMetric
    rs_60: RelativeStrengthMetric
    classification: str  # "strong_outperformer", "moderate_outperformer", "neutral", "moderate_underperformer", "strong_underperformer", "unknown"
    rs_ratio_series: list[tuple[datetime.date, float]]  # Date-stamped asset/benchmark ratio


def calculate_relative_performance(
    asset_candles: Sequence[Candle],
    benchmark_candles: Sequence[Candle],
    horizons: tuple[int, ...] = (5, 20, 60),
) -> RelativeStrengthAnalysis:
    """Calculate relative performance by matching candles on trading_date.

    Args:
        asset_candles: Chronological sequence of asset candles.
        benchmark_candles: Chronological sequence of benchmark candles.
        horizons: Trading session lookback windows.

    Returns:
        RelativeStrengthAnalysis object with metrics for each horizon.
    """
    if not asset_candles or not benchmark_candles:
        empty_metric = RelativeStrengthMetric(
            horizon_days=0, asset_return_pct=None, benchmark_return_pct=None,
            excess_return_pct=None, is_outperforming=None,
        )
        return RelativeStrengthAnalysis(
            rs_5=empty_metric, rs_20=empty_metric, rs_60=empty_metric,
            classification="unknown", rs_ratio_series=[],
        )

    # Build date lookup maps
    bench_map = {c.trading_date: c.close for c in benchmark_candles if c.close > 0}

    matched_pairs: list[tuple[datetime.date, float, float]] = []
    for c in asset_candles:
        if c.close > 0 and c.trading_date in bench_map:
            matched_pairs.append((c.trading_date, c.close, bench_map[c.trading_date]))

    # Sort chronologically
    matched_pairs.sort(key=lambda x: x[0])
    n = len(matched_pairs)

    ratio_series = [(d, round(a_close / b_close, 6)) for d, a_close, b_close in matched_pairs]

    metrics: dict[int, RelativeStrengthMetric] = {}

    for h in (5, 20, 60):
        if n > h:
            curr_date, curr_a, curr_b = matched_pairs[-1]
            past_date, past_a, past_b = matched_pairs[-1 - h]

            ret_a = ((curr_a - past_a) / past_a) * 100.0
            ret_b = ((curr_b - past_b) / past_b) * 100.0
            excess = ret_a - ret_b

            metrics[h] = RelativeStrengthMetric(
                horizon_days=h,
                asset_return_pct=round(ret_a, 2),
                benchmark_return_pct=round(ret_b, 2),
                excess_return_pct=round(excess, 2),
                is_outperforming=excess > 0.0,
            )
        else:
            metrics[h] = RelativeStrengthMetric(
                horizon_days=h,
                asset_return_pct=None,
                benchmark_return_pct=None,
                excess_return_pct=None,
                is_outperforming=None,
            )

    # Classify overall relative strength based on 20-day horizon
    rs_20_metric = metrics[20]
    excess_20 = rs_20_metric.excess_return_pct

    if excess_20 is not None:
        if excess_20 >= 5.0:
            classification = "strong_outperformer"
        elif excess_20 > 0.5:
            classification = "moderate_outperformer"
        elif excess_20 >= -0.5:
            classification = "neutral"
        elif excess_20 > -5.0:
            classification = "moderate_underperformer"
        else:
            classification = "strong_underperformer"
    else:
        classification = "unknown"

    return RelativeStrengthAnalysis(
        rs_5=metrics[5],
        rs_20=metrics[20],
        rs_60=metrics[60],
        classification=classification,
        rs_ratio_series=ratio_series[-60:],  # keep last 60 points for charting
    )
