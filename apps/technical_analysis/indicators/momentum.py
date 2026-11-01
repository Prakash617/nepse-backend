"""Momentum indicators: RSI (Relative Strength Index) and MACD.

Implements Wilder's smoothed RSI (14), divergence detection,
and standard MACD (12, 26, 9) with crossovers and histogram analysis.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.moving_averages import calculate_ema
from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class RSIAnalysis:
    """RSI calculation and momentum analysis."""

    value: float | None
    is_overbought: bool
    is_oversold: bool
    momentum_zone: str  # "bullish_momentum", "bearish_momentum", "neutral"
    is_rising: bool | None
    bullish_divergence: bool
    bearish_divergence: bool


@dataclass(frozen=True)
class MACDAnalysis:
    """MACD calculation and crossover analysis."""

    macd_line: float | None
    signal_line: float | None
    histogram: float | None
    is_above_zero: bool | None
    is_above_signal: bool | None
    crossover: str  # "bullish_crossover", "bearish_crossover", "none"
    histogram_expanding: bool | None


@dataclass(frozen=True)
class MomentumAnalysis:
    """Combined momentum indicators summary."""

    rsi: RSIAnalysis
    macd: MACDAnalysis


def calculate_rsi(
    prices: Sequence[float],
    period: int = 14,
) -> list[float | None]:
    """Calculate RSI using Wilder's smoothing technique.

    Args:
        prices: List of closing prices.
        period: Lookback period (default 14).

    Returns:
        List of RSI values matching the input length. Elements before index
        `period` are None.
    """
    n = len(prices)
    if period <= 0 or n <= period:
        return [None] * n

    changes = [prices[i] - prices[i - 1] for i in range(1, n)]
    result: list[float | None] = [None] * period

    # First average gain and loss over the first `period` changes
    gains = [max(0.0, chg) for chg in changes[:period]]
    losses = [max(0.0, -chg) for chg in changes[:period]]

    avg_gain = sum(gains) / period
    avg_loss = sum(losses) / period

    if avg_loss == 0.0:
        first_rsi = 100.0 if avg_gain > 0 else 50.0
    else:
        rs = avg_gain / avg_loss
        first_rsi = 100.0 - (100.0 / (1.0 + rs))

    result.append(first_rsi)

    # Wilder's smoothing for subsequent periods
    for i in range(period, len(changes)):
        chg = changes[i]
        gain = max(0.0, chg)
        loss = max(0.0, -chg)

        avg_gain = (avg_gain * (period - 1) + gain) / period
        avg_loss = (avg_loss * (period - 1) + loss) / period

        if avg_loss == 0.0:
            rsi_val = 100.0 if avg_gain > 0 else 50.0
        else:
            rs = avg_gain / avg_loss
            rsi_val = 100.0 - (100.0 / (1.0 + rs))

        result.append(rsi_val)

    return result


def detect_rsi_divergence(
    prices: Sequence[float],
    rsi_series: Sequence[float | None],
    lookback: int = 25,
) -> tuple[bool, bool]:
    """Detect bullish and bearish RSI divergence over a recent lookback window.

    - Bullish Divergence: Price creates a lower low while RSI creates a higher low.
    - Bearish Divergence: Price creates a higher high while RSI creates a lower high.
    """
    n = len(prices)
    if n < lookback or len(rsi_series) < lookback:
        return False, False

    window_prices = prices[-lookback:]
    window_rsi = rsi_series[-lookback:]

    if any(r is None for r in window_rsi):
        return False, False

    valid_rsi = [float(r) for r in window_rsi if r is not None]

    # Split lookback into two halves to detect pivot progression
    mid = lookback // 2
    p_half1, p_half2 = window_prices[:mid], window_prices[mid:]
    r_half1, r_half2 = valid_rsi[:mid], valid_rsi[mid:]

    min_p1, min_p2 = min(p_half1), min(p_half2)
    max_p1, max_p2 = max(p_half1), max(p_half2)

    min_r1, min_r2 = min(r_half1), min(r_half2)
    max_r1, max_r2 = max(r_half1), max(r_half2)

    bullish_div = (min_p2 < min_p1 * 0.99) and (min_r2 > min_r1 + 2.0)
    bearish_div = (max_p2 > max_p1 * 1.01) and (max_r2 < max_r1 - 2.0)

    return bullish_div, bearish_div


def calculate_macd(
    prices: Sequence[float],
    fast_period: int = 12,
    slow_period: int = 26,
    signal_period: int = 9,
) -> tuple[list[float | None], list[float | None], list[float | None]]:
    """Calculate MACD Line, Signal Line, and Histogram.

    MACD Line = EMA(12) - EMA(26)
    Signal Line = EMA(9) of MACD Line
    Histogram = MACD Line - Signal Line
    """
    n = len(prices)
    if n < slow_period + signal_period:
        return [None] * n, [None] * n, [None] * n

    fast_ema = calculate_ema(prices, fast_period)
    slow_ema = calculate_ema(prices, slow_period)

    macd_line: list[float | None] = [None] * n
    valid_macd_indices: list[int] = []
    valid_macd_values: list[float] = []

    for i in range(n):
        f = fast_ema[i]
        s = slow_ema[i]
        if f is not None and s is not None:
            val = f - s
            macd_line[i] = val
            valid_macd_indices.append(i)
            valid_macd_values.append(val)

    signal_line: list[float | None] = [None] * n
    histogram: list[float | None] = [None] * n

    if len(valid_macd_values) >= signal_period:
        valid_signal = calculate_ema(valid_macd_values, signal_period)
        for idx, orig_i in enumerate(valid_macd_indices):
            sig = valid_signal[idx]
            signal_line[orig_i] = sig
            m = macd_line[orig_i]
            if m is not None and sig is not None:
                histogram[orig_i] = m - sig

    return macd_line, signal_line, histogram


def analyze_momentum(
    candles: Sequence[Candle],
    *,
    rsi_period: int = 14,
    rsi_overbought: float = 70.0,
    rsi_oversold: float = 30.0,
) -> MomentumAnalysis:
    """Compute and analyze RSI and MACD indicators."""
    closes = [c.close for c in candles]
    n = len(closes)

    # RSI Analysis
    rsi_series = calculate_rsi(closes, period=rsi_period)
    last_rsi = rsi_series[-1] if rsi_series else None

    if last_rsi is not None:
        is_ob = last_rsi >= rsi_overbought
        is_os = last_rsi <= rsi_oversold

        is_rising: bool | None = None
        if len(rsi_series) >= 2 and rsi_series[-2] is not None:
            is_rising = last_rsi > (rsi_series[-2] or 0.0)

        if last_rsi >= 50.0:
            m_zone = "bullish_momentum"
        else:
            m_zone = "bearish_momentum"

        bull_div, bear_div = detect_rsi_divergence(closes, rsi_series)
        rsi_analysis = RSIAnalysis(
            value=round(last_rsi, 2),
            is_overbought=is_ob,
            is_oversold=is_os,
            momentum_zone=m_zone,
            is_rising=is_rising,
            bullish_divergence=bull_div,
            bearish_divergence=bear_div,
        )
    else:
        rsi_analysis = RSIAnalysis(
            value=None,
            is_overbought=False,
            is_oversold=False,
            momentum_zone="neutral",
            is_rising=None,
            bullish_divergence=False,
            bearish_divergence=False,
        )

    # MACD Analysis
    macd_l, sig_l, hist_l = calculate_macd(closes)
    last_m = macd_l[-1] if macd_l else None
    last_s = sig_l[-1] if sig_l else None
    last_h = hist_l[-1] if hist_l else None

    if last_m is not None and last_s is not None and last_h is not None:
        above_zero = last_m > 0.0
        above_signal = last_m > last_s

        crossover = "none"
        if n >= 2 and macd_l[-2] is not None and sig_l[-2] is not None:
            prev_m = macd_l[-2]
            prev_s = sig_l[-2]
            assert prev_m is not None and prev_s is not None
            if prev_m <= prev_s and last_m > last_s:
                crossover = "bullish_crossover"
            elif prev_m >= prev_s and last_m < last_s:
                crossover = "bearish_crossover"

        hist_expanding: bool | None = None
        if n >= 2 and hist_l[-2] is not None:
            prev_h = hist_l[-2]
            assert prev_h is not None
            # Absolute expansion
            hist_expanding = abs(last_h) > abs(prev_h)

        macd_analysis = MACDAnalysis(
            macd_line=round(last_m, 4),
            signal_line=round(last_s, 4),
            histogram=round(last_h, 4),
            is_above_zero=above_zero,
            is_above_signal=above_signal,
            crossover=crossover,
            histogram_expanding=hist_expanding,
        )
    else:
        macd_analysis = MACDAnalysis(
            macd_line=None,
            signal_line=None,
            histogram=None,
            is_above_zero=None,
            is_above_signal=None,
            crossover="none",
            histogram_expanding=None,
        )

    return MomentumAnalysis(rsi=rsi_analysis, macd=macd_analysis)
