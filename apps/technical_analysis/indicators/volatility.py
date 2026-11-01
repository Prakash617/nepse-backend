"""Volatility indicators: Bollinger Bands and Average True Range (ATR).

Implements:
- Bollinger Bands (20, 2.0 std dev) with Bandwidth, %B, and Squeeze detection.
- Average True Range (14) with ATR percentage and volatility classification.
"""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.moving_averages import calculate_sma
from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class BollingerBandsAnalysis:
    """Bollinger Bands analysis summary."""

    upper_band: float | None
    middle_band: float | None
    lower_band: float | None
    bandwidth: float | None
    percent_b: float | None
    is_squeeze: bool
    position: str  # "above_upper", "below_lower", "upper_half", "lower_half", "unknown"
    crossed_band: str  # "cross_above_upper", "cross_below_lower", "cross_middle", "none"


@dataclass(frozen=True)
class ATRAnalysis:
    """Average True Range (ATR) analysis summary."""

    atr: float | None
    atr_percentage: float | None
    volatility_class: str  # "low", "moderate", "high", "extreme", "unknown"
    is_large_movement: bool


@dataclass(frozen=True)
class VolatilityAnalysis:
    """Combined volatility indicators summary."""

    bollinger: BollingerBandsAnalysis
    atr: ATRAnalysis


def calculate_bollinger_bands(
    prices: Sequence[float],
    period: int = 20,
    num_std: float = 2.0,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Compute Bollinger Bands (Upper, Middle, Lower).

    Returns:
        Tuple of (upper_series, middle_series, lower_series).
    """
    n = len(prices)
    if period <= 0 or n < period:
        return [None] * n, [None] * n, [None] * n

    middle_series = calculate_sma(prices, period)
    upper_series: list[float | None] = [None] * n
    lower_series: list[float | None] = [None] * n

    for i in range(period - 1, n):
        window = prices[i - period + 1 : i + 1]
        mean = middle_series[i]
        assert mean is not None

        variance = sum((x - mean) ** 2 for x in window) / period
        std_dev = math.sqrt(variance)

        upper_series[i] = mean + (num_std * std_dev)
        lower_series[i] = mean - (num_std * std_dev)

    return upper_series, middle_series, lower_series


def calculate_atr(
    candles: Sequence[Candle],
    period: int = 14,
) -> list[float | None]:
    """Compute Wilder's Average True Range (ATR).

    TR = max(High - Low, abs(High - PrevClose), abs(Low - PrevClose))
    ATR = Wilder's 14-period smoothed TR.
    """
    n = len(candles)
    if period <= 0 or n <= period:
        return [None] * n

    # Step 1: calculate TR
    tr_list: list[float] = []
    for i in range(1, n):
        curr = candles[i]
        prev = candles[i - 1]
        tr = max(
            curr.high - curr.low,
            abs(curr.high - prev.close),
            abs(curr.low - prev.close),
        )
        tr_list.append(tr)

    atr_series: list[float | None] = [None] * n

    # First ATR: simple average of first `period` TRs
    first_atr = sum(tr_list[:period]) / period
    atr_series[period] = first_atr
    prev_atr = first_atr

    # Subsequent ATRs: Wilder's smoothing
    for i in range(period, len(tr_list)):
        curr_atr = (prev_atr * (period - 1) + tr_list[i]) / period
        candle_idx = i + 1
        atr_series[candle_idx] = curr_atr
        prev_atr = curr_atr

    return atr_series


def analyze_volatility(
    candles: Sequence[Candle],
    *,
    bb_period: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 14,
) -> VolatilityAnalysis:
    """Analyze volatility using Bollinger Bands and ATR."""
    closes = [c.close for c in candles]
    n = len(candles)

    # Bollinger Bands
    upper_s, middle_s, lower_s = calculate_bollinger_bands(closes, period=bb_period, num_std=bb_std)
    u_curr, m_curr, l_curr = upper_s[-1] if upper_s else None, middle_s[-1] if middle_s else None, lower_s[-1] if lower_s else None

    if u_curr is not None and m_curr is not None and l_curr is not None and m_curr > 0:
        band_width = (u_curr - l_curr) / m_curr
        band_range = u_curr - l_curr
        percent_b = ((closes[-1] - l_curr) / band_range) if band_range > 0 else 0.5

        # Position
        c_price = closes[-1]
        if c_price > u_curr:
            pos = "above_upper"
        elif c_price < l_curr:
            pos = "below_lower"
        elif c_price >= m_curr:
            pos = "upper_half"
        else:
            pos = "lower_half"

        # Crossed Band
        crossed = "none"
        if n >= 2 and upper_s[-2] is not None and lower_s[-2] is not None and middle_s[-2] is not None:
            p_prev = closes[-2]
            u_prev, m_prev, l_prev = upper_s[-2], middle_s[-2], lower_s[-2]
            assert u_prev is not None and m_prev is not None and l_prev is not None

            if p_prev <= u_prev and c_price > u_curr:
                crossed = "cross_above_upper"
            elif p_prev >= l_prev and c_price < l_curr:
                crossed = "cross_below_lower"
            elif (p_prev <= m_prev and c_price > m_curr) or (p_prev >= m_prev and c_price < m_curr):
                crossed = "cross_middle"

        # Squeeze Detection: check if current bandwidth is in the bottom 10% of last 60 bars
        is_squeeze = False
        valid_bws: list[float] = []
        lookback_sq = min(n, 60)
        for idx in range(n - lookback_sq, n):
            u_i, m_i, l_i = upper_s[idx], middle_s[idx], lower_s[idx]
            if u_i is not None and m_i is not None and l_i is not None and m_i > 0:
                valid_bws.append((u_i - l_i) / m_i)

        if len(valid_bws) >= 20:
            min_bw = min(valid_bws)
            if band_width <= min_bw * 1.05:  # within 5% of minimum
                is_squeeze = True

        bb_analysis = BollingerBandsAnalysis(
            upper_band=round(u_curr, 2),
            middle_band=round(m_curr, 2),
            lower_band=round(l_curr, 2),
            bandwidth=round(band_width, 4),
            percent_b=round(percent_b, 4),
            is_squeeze=is_squeeze,
            position=pos,
            crossed_band=crossed,
        )
    else:
        bb_analysis = BollingerBandsAnalysis(
            upper_band=None,
            middle_band=None,
            lower_band=None,
            bandwidth=None,
            percent_b=None,
            is_squeeze=False,
            position="unknown",
            crossed_band="none",
        )

    # ATR Analysis
    atr_series = calculate_atr(candles, period=atr_period)
    atr_curr = atr_series[-1] if atr_series else None

    if atr_curr is not None and closes[-1] > 0:
        c_price = closes[-1]
        atr_pct = (atr_curr / c_price) * 100.0

        if atr_pct < 2.0:
            v_class = "low"
        elif atr_pct < 4.5:
            v_class = "moderate"
        elif atr_pct < 8.0:
            v_class = "high"
        else:
            v_class = "extreme"

        # Large daily price movement
        is_large = False
        if n >= 2:
            prev_close = closes[-2]
            daily_pct = abs((c_price - prev_close) / prev_close) * 100.0
            if daily_pct > (atr_pct * 1.8):
                is_large = True

        atr_analysis = ATRAnalysis(
            atr=round(atr_curr, 2),
            atr_percentage=round(atr_pct, 2),
            volatility_class=v_class,
            is_large_movement=is_large,
        )
    else:
        atr_analysis = ATRAnalysis(
            atr=None,
            atr_percentage=None,
            volatility_class="unknown",
            is_large_movement=False,
        )

    return VolatilityAnalysis(bollinger=bb_analysis, atr=atr_analysis)
