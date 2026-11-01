"""Moving averages calculation and signal detection.

Implements SMA (20, 50, 200), EMA (20, 50, 200), slope calculations,
and crossover detections (Golden Cross, Death Cross, Price Crossovers).
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class MovingAverageAnalysis:
    """Output summary of moving average indicators for the latest candle."""

    sma_20: float | None
    sma_50: float | None
    sma_200: float | None
    ema_20: float | None
    ema_50: float | None
    ema_200: float | None

    price_above_ema_20: bool | None
    price_above_ema_50: bool | None
    price_above_sma_200: bool | None
    price_above_ema_200: bool | None

    ema_20_above_ema_50: bool | None
    ema_50_above_ema_200: bool | None
    sma_50_above_sma_200: bool | None

    golden_cross: bool  # 50 crossed above 200 within last 3 bars
    death_cross: bool   # 50 crossed below 200 within last 3 bars

    ema_20_slope: float | None  # Percentage change over past 3 bars
    ema_50_slope: float | None

    price_crossing_ema_20: str  # "cross_above", "cross_below", or "none"
    price_crossing_sma_200: str # "cross_above", "cross_below", or "none"


def calculate_sma(prices: Sequence[float], period: int) -> list[float | None]:
    """Calculate Simple Moving Average (SMA) over a given period.

    Returns:
        List of same length as prices, where elements before index `period - 1` are None.
    """
    n = len(prices)
    if period <= 0 or n < period:
        return [None] * n

    result: list[float | None] = [None] * (period - 1)
    current_sum = sum(prices[:period])
    result.append(current_sum / period)

    for i in range(period, n):
        current_sum += prices[i] - prices[i - period]
        result.append(current_sum / period)

    return result


def calculate_ema(prices: Sequence[float], period: int) -> list[float | None]:
    """Calculate Exponential Moving Average (EMA) using standard multiplier.

    Multiplier k = 2 / (period + 1)
    Seed value: SMA of the first `period` prices.

    Returns:
        List of same length as prices, where elements before index `period - 1` are None.
    """
    n = len(prices)
    if period <= 0 or n < period:
        return [None] * n

    result: list[float | None] = [None] * (period - 1)
    k = 2.0 / (period + 1)

    # Initial seed: simple average of first period values
    prev_ema = sum(prices[:period]) / period
    result.append(prev_ema)

    for i in range(period, n):
        curr_ema = (prices[i] * k) + (prev_ema * (1.0 - k))
        result.append(curr_ema)
        prev_ema = curr_ema

    return result


def analyze_moving_averages(candles: Sequence[Candle]) -> MovingAverageAnalysis:
    """Analyze moving averages from a sequence of chronological candles."""
    if not candles:
        return MovingAverageAnalysis(
            sma_20=None, sma_50=None, sma_200=None,
            ema_20=None, ema_50=None, ema_200=None,
            price_above_ema_20=None, price_above_ema_50=None,
            price_above_sma_200=None, price_above_ema_200=None,
            ema_20_above_ema_50=None, ema_50_above_ema_200=None,
            sma_50_above_sma_200=None,
            golden_cross=False, death_cross=False,
            ema_20_slope=None, ema_50_slope=None,
            price_crossing_ema_20="none", price_crossing_sma_200="none",
        )

    closes = [c.close for c in candles]
    n = len(closes)

    sma_20_series = calculate_sma(closes, 20)
    sma_50_series = calculate_sma(closes, 50)
    sma_200_series = calculate_sma(closes, 200)

    ema_20_series = calculate_ema(closes, 20)
    ema_50_series = calculate_ema(closes, 50)
    ema_200_series = calculate_ema(closes, 200)

    last_close = closes[-1]
    sma_20 = sma_20_series[-1]
    sma_50 = sma_50_series[-1]
    sma_200 = sma_200_series[-1]
    ema_20 = ema_20_series[-1]
    ema_50 = ema_50_series[-1]
    ema_200 = ema_200_series[-1]

    price_above_ema_20 = (last_close > ema_20) if ema_20 is not None else None
    price_above_ema_50 = (last_close > ema_50) if ema_50 is not None else None
    price_above_sma_200 = (last_close > sma_200) if sma_200 is not None else None
    price_above_ema_200 = (last_close > ema_200) if ema_200 is not None else None

    ema_20_above_ema_50 = (ema_20 > ema_50) if (ema_20 is not None and ema_50 is not None) else None
    ema_50_above_ema_200 = (ema_50 > ema_200) if (ema_50 is not None and ema_200 is not None) else None
    sma_50_above_sma_200 = (sma_50 > sma_200) if (sma_50 is not None and sma_200 is not None) else None

    # Golden cross / Death cross detection in the last 3 bars
    # Either EMA 50 vs EMA 200 or SMA 50 vs SMA 200
    golden_cross = False
    death_cross = False

    if n >= 201:
        # Check last 3 bars for cross
        for i in range(max(1, n - 3), n):
            e50_curr, e200_curr = ema_50_series[i], ema_200_series[i]
            e50_prev, e200_prev = ema_50_series[i - 1], ema_200_series[i - 1]
            if (
                e50_curr is not None and e200_curr is not None
                and e50_prev is not None and e200_prev is not None
            ):
                if e50_prev <= e200_prev and e50_curr > e200_curr:
                    golden_cross = True
                elif e50_prev >= e200_prev and e50_curr < e200_curr:
                    death_cross = True

    # Moving average slopes (EMA 20 and EMA 50) over 3 bars
    ema_20_slope: float | None = None
    if n >= 4 and ema_20_series[-1] is not None and ema_20_series[-4] is not None:
        prev_val = ema_20_series[-4]
        if prev_val and prev_val > 0:
            ema_20_slope = ((ema_20_series[-1] - prev_val) / prev_val) * 100.0

    ema_50_slope: float | None = None
    if n >= 5 and ema_50_series[-1] is not None and ema_50_series[-5] is not None:
        prev_val50 = ema_50_series[-5]
        if prev_val50 and prev_val50 > 0:
            ema_50_slope = ((ema_50_series[-1] - prev_val50) / prev_val50) * 100.0

    # Price crossing EMA 20 detection (current vs previous bar)
    price_crossing_ema_20 = "none"
    if n >= 2 and ema_20_series[-1] is not None and ema_20_series[-2] is not None:
        p_curr, p_prev = closes[-1], closes[-2]
        ema_curr, ema_prev = ema_20_series[-1], ema_20_series[-2]
        assert ema_curr is not None and ema_prev is not None
        if p_prev <= ema_prev and p_curr > ema_curr:
            price_crossing_ema_20 = "cross_above"
        elif p_prev >= ema_prev and p_curr < ema_curr:
            price_crossing_ema_20 = "cross_below"

    # Price crossing SMA 200 detection
    price_crossing_sma_200 = "none"
    if n >= 2 and sma_200_series[-1] is not None and sma_200_series[-2] is not None:
        p_curr, p_prev = closes[-1], closes[-2]
        sma_curr, sma_prev = sma_200_series[-1], sma_200_series[-2]
        assert sma_curr is not None and sma_prev is not None
        if p_prev <= sma_prev and p_curr > sma_curr:
            price_crossing_sma_200 = "cross_above"
        elif p_prev >= sma_prev and p_curr < sma_curr:
            price_crossing_sma_200 = "cross_below"

    return MovingAverageAnalysis(
        sma_20=round(sma_20, 2) if sma_20 is not None else None,
        sma_50=round(sma_50, 2) if sma_50 is not None else None,
        sma_200=round(sma_200, 2) if sma_200 is not None else None,
        ema_20=round(ema_20, 2) if ema_20 is not None else None,
        ema_50=round(ema_50, 2) if ema_50 is not None else None,
        ema_200=round(ema_200, 2) if ema_200 is not None else None,
        price_above_ema_20=price_above_ema_20,
        price_above_ema_50=price_above_ema_50,
        price_above_sma_200=price_above_sma_200,
        price_above_ema_200=price_above_ema_200,
        ema_20_above_ema_50=ema_20_above_ema_50,
        ema_50_above_ema_200=ema_50_above_ema_200,
        sma_50_above_sma_200=sma_50_above_sma_200,
        golden_cross=golden_cross,
        death_cross=death_cross,
        ema_20_slope=round(ema_20_slope, 2) if ema_20_slope is not None else None,
        ema_50_slope=round(ema_50_slope, 2) if ema_50_slope is not None else None,
        price_crossing_ema_20=price_crossing_ema_20,
        price_crossing_sma_200=price_crossing_sma_200,
    )
