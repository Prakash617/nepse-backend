"""Stop-loss calculations for Short-Term Trading Strategy."""

from __future__ import annotations

from decimal import Decimal

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle


def calculate_short_term_stop_loss(
    candles: list[Candle],
    indicators: FullIndicatorSet,
    entry_price: Decimal,
    *,
    atr_multiplier: float = 1.5,
    lookback_swing_bars: int = 5,
) -> Decimal:
    """Calculate the stop-loss level using the tighter of swing-low and ATR trailing stop.

    Stop Loss = max(Recent 5-bar swing low, Entry Price - (1.5 * ATR 14))
    Bounded strictly below Entry Price.
    """
    atr = indicators.volatility.atr.atr or (float(entry_price) * 0.03)
    atr_stop = float(entry_price) - (atr * atr_multiplier)

    # Calculate recent swing low
    recent_lows = [c.low for c in candles[-lookback_swing_bars:]] if len(candles) >= lookback_swing_bars else [c.low for c in candles]
    swing_low = min(recent_lows) if recent_lows else atr_stop

    # Use structural support if valid and below entry, else ATR stop
    # Buffer swing low by 0.2%
    buffered_swing_low = swing_low * 0.998

    chosen_stop = max(buffered_swing_low, atr_stop)

    # Ensure stop loss is strictly below entry price (at least 0.5% below)
    max_permitted_stop = float(entry_price) * 0.995
    if chosen_stop > max_permitted_stop:
        chosen_stop = max_permitted_stop

    return Decimal(str(round(chosen_stop, 2)))
