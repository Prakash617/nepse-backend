"""Entry evaluation and pattern detection for Short-Term Trading Strategy."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class ShortTermEntrySetup:
    """Detected entry setup for short-term trading."""

    setup_type: str  # "breakout", "pullback", "support_rebound"
    suggested_entry: Decimal
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    composite_score: Decimal
    rationale: str
    is_valid: bool
    metadata: dict[str, Any]


def evaluate_short_term_entry(
    candles: list[Candle],
    indicators: FullIndicatorSet,
    *,
    market_context: dict[str, Any] | None = None,
    min_composite_score: float = 65.0,
) -> ShortTermEntrySetup | None:
    """Evaluate whether candles and indicators present a high-probability short-term BUY setup.

    Returns:
        ShortTermEntrySetup if criteria met, otherwise None.
    """
    if len(candles) < 20:
        return None

    last_candle = candles[-1]
    close = last_candle.close

    # Indicator references
    ema_20 = indicators.moving_averages.ema_20
    ema20_slope = indicators.moving_averages.ema_20_slope
    rsi_14 = indicators.momentum.rsi.value
    macd_hist = indicators.momentum.macd.histogram
    adx_14 = indicators.trend.adx
    rel_vol = indicators.volume.relative_volume or 1.0

    if ema_20 is None or rsi_14 is None:
        return None

    # Market gate: reject if market is in severe breakdown
    if market_context and market_context.get("status") == "bearish_breakdown":
        return None

    # General baseline condition: price closing above or reclaiming rising EMA 20
    is_above_ema20 = close >= ema_20 * 0.995  # within 0.5% tolerance
    ema20_rising = ema20_slope is not None and ema20_slope > 0

    # MACD momentum: positive histogram OR bullish crossover
    macd_bullish = False
    if macd_hist is not None and macd_hist > 0:
        macd_bullish = True
    elif indicators.momentum.macd.crossover == "bullish_crossover":
        macd_bullish = True

    # Setup 1: Resistance Breakout
    is_breakout = False
    if indicators.price_structure.is_breakout_20 or indicators.price_structure.is_breakout_50:
        if rel_vol >= 1.2 and 50.0 <= rsi_14 <= 78.0:
            is_breakout = True

    # Setup 2: EMA 20 Pullback Rebound
    is_pullback = False
    if not is_breakout and ema20_rising:
        # Low pierced near EMA 20, but candle closed green and above EMA 20
        tested_ema20 = (last_candle.low <= ema_20 * 1.015) and (close >= ema_20)
        closed_green = close >= last_candle.open
        if tested_ema20 and closed_green and macd_bullish and (48.0 <= rsi_14 <= 65.0):
            is_pullback = True

    # Setup 3: Support Rebound
    is_support_rebound = False
    if not is_breakout and not is_pullback:
        low_20 = indicators.price_structure.low_20
        if low_20 is not None and (last_candle.low <= low_20 * 1.015) and (close > low_20):
            if close >= last_candle.open and macd_bullish:
                is_support_rebound = True

    chosen_setup = None
    if is_breakout:
        chosen_setup = "breakout"
    elif is_pullback:
        chosen_setup = "pullback"
    elif is_support_rebound:
        chosen_setup = "support_rebound"
    else:
        return None

    # Compute Quantitative Composite Score (0 - 100)
    # 1. Trend component (max 25)
    trend_score = 15.0 if is_above_ema20 else 5.0
    if ema20_rising:
        trend_score += 10.0

    # 2. Momentum component (max 25)
    momentum_score = 10.0
    if 52.0 <= rsi_14 <= 65.0:
        momentum_score += 8.0
    elif 45.0 <= rsi_14 < 52.0 or 65.0 < rsi_14 <= 70.0:
        momentum_score += 4.0

    if macd_bullish:
        momentum_score += 7.0

    # 3. Volume component (max 25)
    volume_score = 5.0
    if rel_vol >= 1.8:
        volume_score = 25.0
    elif rel_vol >= 1.4:
        volume_score = 20.0
    elif rel_vol >= 1.1:
        volume_score = 15.0
    elif rel_vol >= 0.9:
        volume_score = 10.0

    # 4. Pattern strength & ADX (max 25)
    pattern_score = 10.0
    if adx_14 is not None and adx_14 >= 22.0:
        pattern_score += 8.0
    elif adx_14 is not None and adx_14 >= 18.0:
        pattern_score += 4.0

    if chosen_setup == "breakout":
        pattern_score += 7.0
    elif chosen_setup == "pullback":
        pattern_score += 5.0
    elif chosen_setup == "support_rebound":
        pattern_score += 4.0

    total_score = min(100.0, trend_score + momentum_score + volume_score + pattern_score)

    if total_score < min_composite_score:
        return None

    # Execution levels
    entry_price = Decimal(str(round(close, 2)))
    # Zone: 0.5% below close to 0.8% above close
    zone_low = Decimal(str(round(close * 0.995, 2)))
    zone_high = Decimal(str(round(close * 1.008, 2)))

    slope_label = "rising" if ema20_rising else "neutral/falling"
    rationale_parts = [
        f"Short-Term {chosen_setup.replace('_', ' ').title()} Setup (Score: {total_score:.1f}/100).",
        f"Price closed at {close:.2f} relative to EMA 20 ({ema_20:.2f}, {slope_label}).",
        f"Momentum: RSI 14 at {rsi_14:.1f}, Volume {rel_vol:.2f}x 20-day average.",
    ]
    if adx_14 is not None:
        rationale_parts.append(f"Trend strength: ADX 14 at {adx_14:.1f}.")

    return ShortTermEntrySetup(
        setup_type=chosen_setup,
        suggested_entry=entry_price,
        entry_zone_low=zone_low,
        entry_zone_high=zone_high,
        composite_score=Decimal(str(round(total_score, 1))),
        rationale=" ".join(rationale_parts),
        is_valid=True,
        metadata={
            "rsi_14": round(rsi_14, 2),
            "adx_14": round(adx_14, 2) if adx_14 is not None else None,
            "rel_volume": round(rel_vol, 2),
            "ema_20": round(ema_20, 2),
            "trend_score": trend_score,
            "momentum_score": momentum_score,
            "volume_score": volume_score,
            "pattern_score": pattern_score,
        },
    )
