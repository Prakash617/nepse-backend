"""Price structure, pivot identification, and breakout/breakdown detection.

Calculates:
- 20-day, 50-day, and 52-week highs and lows
- Swing high and swing low pivot identification
- Higher Highs (HH), Higher Lows (HL), Lower Highs (LH), Lower Lows (LL)
- Breakout & Breakdown conditions
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class PriceStructureAnalysis:
    """Price structure and breakout analysis summary."""

    high_20: float | None
    low_20: float | None
    high_50: float | None
    low_50: float | None
    high_52w: float | None
    low_52w: float | None

    distance_from_52w_high: float | None  # Percentage below 52-week high (negative or zero)
    distance_from_52w_low: float | None   # Percentage above 52-week low (positive or zero)

    has_higher_high: bool
    has_higher_low: bool
    has_lower_high: bool
    has_lower_low: bool
    structure_trend: str  # "uptrend_structure", "downtrend_structure", "consolidation"

    is_breakout_20: bool  # Current close broke above previous 20-day high
    is_breakout_50: bool  # Current close broke above previous 50-day high
    is_breakdown_20: bool # Current close broke below previous 20-day low
    is_breakdown_50: bool # Current close broke below previous 50-day low


def analyze_price_structure(
    candles: Sequence[Candle],
) -> PriceStructureAnalysis:
    """Analyze price structure without any future data leakage."""
    if not candles:
        return PriceStructureAnalysis(
            high_20=None, low_20=None,
            high_50=None, low_50=None,
            high_52w=None, low_52w=None,
            distance_from_52w_high=None, distance_from_52w_low=None,
            has_higher_high=False, has_higher_low=False,
            has_lower_high=False, has_lower_low=False,
            structure_trend="consolidation",
            is_breakout_20=False, is_breakout_50=False,
            is_breakdown_20=False, is_breakdown_50=False,
        )

    n = len(candles)
    highs = [c.high for c in candles]
    lows = [c.low for c in candles]
    closes = [c.close for c in candles]
    curr_close = closes[-1]

    # 20-day High / Low
    lookback_20 = min(n, 20)
    high_20 = max(highs[-lookback_20:])
    low_20 = min(lows[-lookback_20:])

    # 50-day High / Low
    high_50 = max(highs[-50:]) if n >= 50 else None
    low_50 = min(lows[-50:]) if n >= 50 else None

    # 52-week High / Low (~240 trading sessions in NEPSE)
    lookback_52w = min(n, 240)
    high_52w = max(highs[-lookback_52w:]) if n >= 30 else None
    low_52w = min(lows[-lookback_52w:]) if n >= 30 else None

    dist_52w_high: float | None = None
    dist_52w_low: float | None = None
    if high_52w is not None and high_52w > 0:
        dist_52w_high = round(((curr_close - high_52w) / high_52w) * 100.0, 2)
    if low_52w is not None and low_52w > 0:
        dist_52w_low = round(((curr_close - low_52w) / low_52w) * 100.0, 2)

    # Breakouts & Breakdowns
    # Compare current close against the previous window (excluding current bar)
    is_bo_20 = False
    is_bd_20 = False
    if n >= 21:
        prev_20_high = max(highs[-21:-1])
        prev_20_low = min(lows[-21:-1])
        if curr_close > prev_20_high:
            is_bo_20 = True
        elif curr_close < prev_20_low:
            is_bd_20 = True

    is_bo_50 = False
    is_bd_50 = False
    if n >= 51:
        prev_50_high = max(highs[-51:-1])
        prev_50_low = min(lows[-51:-1])
        if curr_close > prev_50_high:
            is_bo_50 = True
        elif curr_close < prev_50_low:
            is_bd_50 = True

    # Pivot Identification for Market Structure:
    # Look for local swing highs and swing lows over recent 30-40 bars
    # Using 3-bar swing definition: high[t] > high[t-1] and high[t] > high[t+1]
    swing_highs: list[float] = []
    swing_lows: list[float] = []

    # Note: to avoid lookahead bias, we only check completed pivots up to bar n-2
    window_pivot = min(n - 1, 60)
    for i in range(n - window_pivot + 1, n - 1):
        if highs[i] > highs[i - 1] and highs[i] > highs[i + 1]:
            swing_highs.append(highs[i])
        if lows[i] < lows[i - 1] and lows[i] < lows[i + 1]:
            swing_lows.append(lows[i])

    hh = False
    hl = False
    lh = False
    ll = False

    if len(swing_highs) >= 2:
        if swing_highs[-1] > swing_highs[-2]:
            hh = True
        elif swing_highs[-1] < swing_highs[-2]:
            lh = True

    if len(swing_lows) >= 2:
        if swing_lows[-1] > swing_lows[-2]:
            hl = True
        elif swing_lows[-1] < swing_lows[-2]:
            ll = True

    if hh and hl:
        structure = "uptrend_structure"
    elif lh and ll:
        structure = "downtrend_structure"
    else:
        structure = "consolidation"

    return PriceStructureAnalysis(
        high_20=round(high_20, 2),
        low_20=round(low_20, 2),
        high_50=round(high_50, 2) if high_50 is not None else None,
        low_50=round(low_50, 2) if low_50 is not None else None,
        high_52w=round(high_52w, 2) if high_52w is not None else None,
        low_52w=round(low_52w, 2) if low_52w is not None else None,
        distance_from_52w_high=dist_52w_high,
        distance_from_52w_low=dist_52w_low,
        has_higher_high=hh,
        has_higher_low=hl,
        has_lower_high=lh,
        has_lower_low=ll,
        structure_trend=structure,
        is_breakout_20=is_bo_20,
        is_breakout_50=is_bo_50,
        is_breakdown_20=is_bd_20,
        is_breakdown_50=is_bd_50,
    )
