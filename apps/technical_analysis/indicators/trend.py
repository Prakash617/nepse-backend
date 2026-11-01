"""Trend indicators: Full Wilder's ADX and DMI (+DI / -DI).

Calculates:
- +DI (14)
- -DI (14)
- ADX (14)
- Directional Dominance (bullish vs bearish)
- Directional Crossovers
- Trend Strength classification (Weak, Developing, Strong, Very Strong)
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class ADXAnalysis:
    """Complete ADX / DMI directional system output."""

    adx: float | None
    plus_di: float | None
    minus_di: float | None
    trend_strength: str  # "weak", "developing", "strong", "very_strong", or "unknown"
    directional_dominance: str  # "bullish", "bearish", "neutral"
    crossover: str  # "bullish_crossover", "bearish_crossover", "none"


def calculate_dmi_adx(
    candles: Sequence[Candle],
    period: int = 14,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Compute the full Wilder's Directional Movement Index (+DI, -DI, ADX).

    Args:
        candles: Chronological sequence of OHLCV candles.
        period: Lookback smoothing period (default 14).

    Returns:
        Tuple of (plus_di_series, minus_di_series, adx_series).
        Each list has length equal to len(candles).
    """
    n = len(candles)
    if period <= 0 or n < (period * 2):
        return [None] * n, [None] * n, [None] * n

    # Step 1: Calculate raw TR, +DM, -DM for each step from 1 to n-1
    tr_list: list[float] = []
    plus_dm_list: list[float] = []
    minus_dm_list: list[float] = []

    for i in range(1, n):
        curr = candles[i]
        prev = candles[i - 1]

        # True Range
        tr = max(
            curr.high - curr.low,
            abs(curr.high - prev.close),
            abs(curr.low - prev.close),
        )
        tr_list.append(tr)

        # Directional Movement
        up_move = curr.high - prev.high
        down_move = prev.low - curr.low

        if up_move > down_move and up_move > 0.0:
            plus_dm_list.append(up_move)
        else:
            plus_dm_list.append(0.0)

        if down_move > up_move and down_move > 0.0:
            minus_dm_list.append(down_move)
        else:
            minus_dm_list.append(0.0)

    # Step 2: Wilder's smoothing for TR, +DM, -DM
    # First smoothed value at index `period - 1` of the changes (index `period` of candles)
    plus_di_series: list[float | None] = [None] * n
    minus_di_series: list[float | None] = [None] * n
    dx_values: list[float] = []
    dx_indices: list[int] = []

    smoothed_tr = sum(tr_list[:period])
    smoothed_plus_dm = sum(plus_dm_list[:period])
    smoothed_minus_dm = sum(minus_dm_list[:period])

    # First DI at candle index = period
    if smoothed_tr > 0.0:
        p_di = (smoothed_plus_dm / smoothed_tr) * 100.0
        m_di = (smoothed_minus_dm / smoothed_tr) * 100.0
    else:
        p_di, m_di = 0.0, 0.0

    plus_di_series[period] = p_di
    minus_di_series[period] = m_di

    di_sum = p_di + m_di
    dx0 = (abs(p_di - m_di) / di_sum * 100.0) if di_sum > 0.0 else 0.0
    dx_values.append(dx0)
    dx_indices.append(period)

    for i in range(period, len(tr_list)):
        candle_idx = i + 1
        smoothed_tr = smoothed_tr - (smoothed_tr / period) + tr_list[i]
        smoothed_plus_dm = smoothed_plus_dm - (smoothed_plus_dm / period) + plus_dm_list[i]
        smoothed_minus_dm = smoothed_minus_dm - (smoothed_minus_dm / period) + minus_dm_list[i]

        if smoothed_tr > 0.0:
            curr_p_di = (smoothed_plus_dm / smoothed_tr) * 100.0
            curr_m_di = (smoothed_minus_dm / smoothed_tr) * 100.0
        else:
            curr_p_di, curr_m_di = 0.0, 0.0

        plus_di_series[candle_idx] = curr_p_di
        minus_di_series[candle_idx] = curr_m_di

        curr_di_sum = curr_p_di + curr_m_di
        curr_dx = (abs(curr_p_di - curr_m_di) / curr_di_sum * 100.0) if curr_di_sum > 0.0 else 0.0
        dx_values.append(curr_dx)
        dx_indices.append(candle_idx)

    # Step 3: Calculate ADX from DX series
    # First ADX is the simple average of the first `period` DX values
    adx_series: list[float | None] = [None] * n
    if len(dx_values) >= period:
        first_adx = sum(dx_values[:period]) / period
        first_adx_idx = dx_indices[period - 1]
        adx_series[first_adx_idx] = first_adx
        prev_adx = first_adx

        # Subsequent ADX values: Wilder's smoothing
        for j in range(period, len(dx_values)):
            curr_adx = (prev_adx * (period - 1) + dx_values[j]) / period
            target_idx = dx_indices[j]
            adx_series[target_idx] = curr_adx
            prev_adx = curr_adx

    return plus_di_series, minus_di_series, adx_series


def analyze_trend(
    candles: Sequence[Candle],
    period: int = 14,
) -> ADXAnalysis:
    """Analyze trend direction and strength using the full ADX/DMI system."""
    n = len(candles)
    if n < (period * 2):
        return ADXAnalysis(
            adx=None,
            plus_di=None,
            minus_di=None,
            trend_strength="unknown",
            directional_dominance="neutral",
            crossover="none",
        )

    plus_di_s, minus_di_s, adx_s = calculate_dmi_adx(candles, period=period)

    curr_adx = adx_s[-1]
    curr_plus = plus_di_s[-1]
    curr_minus = minus_di_s[-1]

    if curr_adx is None or curr_plus is None or curr_minus is None:
        return ADXAnalysis(
            adx=round(curr_adx, 2) if curr_adx is not None else None,
            plus_di=round(curr_plus, 2) if curr_plus is not None else None,
            minus_di=round(curr_minus, 2) if curr_minus is not None else None,
            trend_strength="unknown",
            directional_dominance="neutral",
            crossover="none",
        )

    # Trend Strength (ADX measures trend strength, NOT direction)
    if curr_adx < 20.0:
        strength = "weak"
    elif curr_adx < 25.0:
        strength = "developing"
    elif curr_adx < 50.0:
        strength = "strong"
    else:
        strength = "very_strong"

    # Directional Dominance
    if curr_plus > curr_minus + 1.0:
        dominance = "bullish"
    elif curr_minus > curr_plus + 1.0:
        dominance = "bearish"
    else:
        dominance = "neutral"

    # Directional Crossover (between +DI and -DI over the last bar)
    crossover = "none"
    if n >= 2 and plus_di_s[-2] is not None and minus_di_s[-2] is not None:
        prev_p = plus_di_s[-2]
        prev_m = minus_di_s[-2]
        assert prev_p is not None and prev_m is not None

        if prev_p <= prev_m and curr_plus > curr_minus:
            crossover = "bullish_crossover"
        elif prev_p >= prev_m and curr_minus > curr_plus:
            crossover = "bearish_crossover"

    return ADXAnalysis(
        adx=round(curr_adx, 2),
        plus_di=round(curr_plus, 2),
        minus_di=round(curr_minus, 2),
        trend_strength=strength,
        directional_dominance=dominance,
        crossover=crossover,
    )
