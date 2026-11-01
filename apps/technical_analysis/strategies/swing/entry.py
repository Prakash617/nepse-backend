"""Entry evaluation and pattern detection for Swing Trading Strategy (1-8 Weeks)."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal
from typing import Any

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle


@dataclass(frozen=True)
class SwingEntrySetup:
    """Detected entry setup for swing trading."""

    setup_type: str  # "trend_continuation", "consolidation_breakout", "pullback"
    suggested_entry: Decimal
    entry_zone_low: Decimal
    entry_zone_high: Decimal
    composite_score: Decimal
    rationale: str
    is_valid: bool
    metadata: dict[str, Any]


def evaluate_swing_entry(
    candles: list[Candle],
    indicators: FullIndicatorSet,
    *,
    market_context: dict[str, Any] | None = None,
    sector_context: dict[str, Any] | None = None,
    min_composite_score: float = 68.0,
) -> SwingEntrySetup | None:
    """Evaluate whether candles and indicators present a sustained trend swing BUY opportunity."""
    if len(candles) < 50:
        return None

    last_candle = candles[-1]
    close = last_candle.close

    # Indicator checks
    ema_20 = indicators.moving_averages.ema_20
    ema_50 = indicators.moving_averages.ema_50
    ema_50_slope = indicators.moving_averages.ema_50_slope
    rsi_14 = indicators.momentum.rsi.value
    macd_hist = indicators.momentum.macd.histogram
    adx_14 = indicators.trend.adx
    plus_di = indicators.trend.plus_di
    minus_di = indicators.trend.minus_di
    rel_vol = indicators.volume.relative_volume or 1.0
    high_52w = indicators.price_structure.high_52w

    if ema_20 is None or ema_50 is None or rsi_14 is None:
        return None

    # Condition 1: Trend Alignment (Price > EMA 20 > EMA 50)
    trend_aligned = close >= ema_20 >= ema_50
    ema50_rising = ema_50_slope is not None and ema_50_slope > 0
    if not (trend_aligned or (close >= ema_50 and ema_20 >= ema_50 * 0.99)):
        return None

    # Condition 2: Directional confirmation (ADX >= 18 and +DI > -DI)
    directional_bullish = False
    if plus_di is not None and minus_di is not None:
        directional_bullish = plus_di >= minus_di
    else:
        directional_bullish = True

    # Condition 3: Momentum zone (healthy, not overbought)
    rsi_healthy = 48.0 <= rsi_14 <= 68.0

    # Relative strength against NEPSE index
    relative_strength_nepse = 0.0
    if market_context and "benchmark_change_pct" in market_context:
        # If stock outperformed benchmark over 20 days
        stock_perf = 0.0
        if len(candles) >= 20:
            stock_perf = ((close - candles[-20].close) / candles[-20].close) * 100.0
        bench_perf = float(market_context["benchmark_change_pct"])
        relative_strength_nepse = stock_perf - bench_perf

    # Identify Setup Pattern
    is_trend_continuation = False
    is_consolidation_breakout = False
    is_pullback = False

    # Check Base/Consolidation Breakout (closing near 52w or 20-day high on expansion)
    if high_52w is not None and close >= high_52w * 0.98 and rel_vol >= 1.2:
        is_consolidation_breakout = True
    elif last_candle.low <= ema_20 * 1.01 and close >= ema_20:
        is_pullback = True
    elif close > ema_20 and ema50_rising and directional_bullish:
        is_trend_continuation = True

    chosen_setup = None
    if is_consolidation_breakout:
        chosen_setup = "consolidation_breakout"
    elif is_pullback:
        chosen_setup = "pullback"
    elif is_trend_continuation:
        chosen_setup = "trend_continuation"
    else:
        return None

    # Quantitative Composite Scoring (0 - 100)
    # 1. Trend Structure (max 30)
    trend_score = 15.0
    if trend_aligned:
        trend_score += 10.0
    if ema50_rising:
        trend_score += 5.0

    # 2. Trend Strength ADX & DMI (max 25)
    adx_score = 5.0
    if adx_14 is not None:
        if adx_14 >= 25.0:
            adx_score += 15.0
        elif adx_14 >= 20.0:
            adx_score += 10.0
        elif adx_14 >= 18.0:
            adx_score += 5.0
    if directional_bullish:
        adx_score += 5.0

    # 3. Relative Strength vs NEPSE / Sector (max 25)
    rs_score = 10.0
    if relative_strength_nepse > 5.0:
        rs_score += 15.0
    elif relative_strength_nepse > 0.0:
        rs_score += 10.0

    # 4. Volume and Momentum (max 20)
    vm_score = 5.0
    if rsi_healthy:
        vm_score += 8.0
    if macd_hist is not None and macd_hist > 0:
        vm_score += 4.0
    if rel_vol >= 1.1:
        vm_score += 3.0

    total_score = min(100.0, trend_score + adx_score + rs_score + vm_score)

    if total_score < min_composite_score:
        return None

    entry_price = Decimal(str(round(close, 2)))
    zone_low = Decimal(str(round(close * 0.990, 2)))
    zone_high = Decimal(str(round(close * 1.015, 2)))

    slope_label = "rising" if ema50_rising else "neutral/falling"
    rationale_parts = [
        f"Swing {chosen_setup.replace('_', ' ').title()} Setup (Score: {total_score:.1f}/100).",
        f"Trend alignment: Price ({close:.2f}) > EMA 20 ({ema_20:.2f}) > EMA 50 ({ema_50:.2f}, {slope_label}).",
    ]
    if adx_14 is not None:
        rationale_parts.append(f"ADX 14: {adx_14:.1f} (+DI={plus_di or 0:.1f}, -DI={minus_di or 0:.1f}).")
    rationale_parts.append(f"RSI 14: {rsi_14:.1f}, Volume: {rel_vol:.2f}x.")

    return SwingEntrySetup(
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
            "plus_di": round(plus_di, 2) if plus_di is not None else None,
            "minus_di": round(minus_di, 2) if minus_di is not None else None,
            "rel_volume": round(rel_vol, 2),
            "ema_20": round(ema_20, 2),
            "ema_50": round(ema_50, 2),
            "trend_score": trend_score,
            "adx_score": adx_score,
            "rs_score": rs_score,
            "vm_score": vm_score,
        },
    )
