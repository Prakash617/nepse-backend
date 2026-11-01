"""Volume indicators and price-volume confirmation analysis.

Calculates:
- 20-day and 50-day average volume
- Relative volume (RVOL)
- Unusual volume spikes
- Price-volume confirmation
- Volume breakout conditions
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.moving_averages import calculate_sma
from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class VolumeAnalysis:
    """Volume analysis and price confirmation output."""

    daily_volume: float
    avg_volume_20: float | None
    avg_volume_50: float | None
    relative_volume: float | None
    volume_trend: str  # "expanding", "contracting", "stable"
    is_unusual_volume: bool
    price_volume_confirmation: str  # "bullish_confirmation", "bearish_confirmation", "divergence", "neutral"
    is_volume_breakout: bool


def analyze_volume(
    candles: Sequence[Candle],
    *,
    unusual_threshold: float = 1.5,
) -> VolumeAnalysis:
    """Analyze volume metrics and price-volume confirmation."""
    if not candles:
        return VolumeAnalysis(
            daily_volume=0.0,
            avg_volume_20=None,
            avg_volume_50=None,
            relative_volume=None,
            volume_trend="stable",
            is_unusual_volume=False,
            price_volume_confirmation="neutral",
            is_volume_breakout=False,
        )

    volumes = [float(c.volume) for c in candles]
    closes = [c.close for c in candles]
    n = len(candles)

    daily_vol = volumes[-1]
    vol_20_series = calculate_sma(volumes, 20)
    vol_50_series = calculate_sma(volumes, 50)
    vol_5_series = calculate_sma(volumes, 5)

    avg_20 = vol_20_series[-1]
    avg_50 = vol_50_series[-1]
    avg_5 = vol_5_series[-1]

    # Relative Volume: current_volume / average_volume_20
    # Safe zero and missing handling
    relative_vol: float | None = None
    if avg_20 is not None and avg_20 > 0:
        relative_vol = round(daily_vol / avg_20, 2)

    # Volume trend
    vol_trend = "stable"
    if avg_5 is not None and avg_20 is not None and avg_20 > 0:
        if avg_5 > avg_20 * 1.15:
            vol_trend = "expanding"
        elif avg_5 < avg_20 * 0.85:
            vol_trend = "contracting"

    # Unusual volume detection
    is_unusual = False
    if relative_vol is not None and relative_vol >= unusual_threshold:
        is_unusual = True

    # Price-volume confirmation
    confirmation = "neutral"
    if n >= 2:
        price_change = closes[-1] - closes[-2]
        above_avg_vol = (relative_vol is not None and relative_vol >= 1.0) or (avg_20 is not None and daily_vol >= avg_20)

        if price_change > 0:
            if above_avg_vol:
                confirmation = "bullish_confirmation"  # Price up on strong volume
            else:
                confirmation = "neutral"
        elif price_change < 0:
            if above_avg_vol:
                confirmation = "bearish_confirmation"  # Heavy selling
            else:
                confirmation = "divergence"  # Price falling on low volume (lack of selling pressure)

    # Volume breakout condition:
    # 20-day high breakout confirmed by high relative volume (>= 1.5)
    is_breakout = False
    if n >= 21 and relative_vol is not None and relative_vol >= 1.5:
        # Check if current close is above previous 20 closes
        prev_20_high = max(closes[-21:-1])
        if closes[-1] > prev_20_high:
            is_breakout = True

    return VolumeAnalysis(
        daily_volume=round(daily_vol, 2),
        avg_volume_20=round(avg_20, 2) if avg_20 is not None else None,
        avg_volume_50=round(avg_50, 2) if avg_50 is not None else None,
        relative_volume=relative_vol,
        volume_trend=vol_trend,
        is_unusual_volume=is_unusual,
        price_volume_confirmation=confirmation,
        is_volume_breakout=is_breakout,
    )
