"""Stop-loss calculations for Swing Trading Strategy."""

from __future__ import annotations

from decimal import Decimal

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle


def calculate_swing_stop_loss(
    candles: list[Candle],
    indicators: FullIndicatorSet,
    entry_price: Decimal,
    *,
    atr_multiplier: float = 2.0,
    lookback_swing_bars: int = 20,
) -> Decimal:
    """Calculate swing stop loss using structural major swing low or 2.0x ATR buffer.

    Stop Loss = max(Major swing low over 20 sessions, Entry - (2.0 * ATR 14))
    Bounded strictly below Entry Price.
    """
    atr = indicators.volatility.atr.atr or (float(entry_price) * 0.04)
    atr_stop = float(entry_price) - (atr * atr_multiplier)

    # Calculate major 20-bar swing low
    recent_lows = [c.low for c in candles[-lookback_swing_bars:]] if len(candles) >= lookback_swing_bars else [c.low for c in candles]
    swing_low = min(recent_lows) if recent_lows else atr_stop

    # Buffer swing low by 0.3%
    buffered_swing_low = swing_low * 0.997

    chosen_stop = max(buffered_swing_low, atr_stop)

    # Ensure stop loss is strictly below entry price (at least 1.0% below)
    max_permitted_stop = float(entry_price) * 0.990
    if chosen_stop > max_permitted_stop:
        chosen_stop = max_permitted_stop

    return Decimal(str(round(chosen_stop, 2)))
