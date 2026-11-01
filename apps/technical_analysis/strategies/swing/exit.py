"""Exit condition evaluation and trailing stop management for Swing Trading Strategy."""

from __future__ import annotations

from decimal import Decimal

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle
from apps.technical_analysis.strategies.base import ExitEvaluationResult


def check_swing_exit(
    current_candle: Candle,
    entry_price: Decimal,
    stop_loss: Decimal,
    target_1: Decimal,
    target_2: Decimal | None,
    trailing_stop: Decimal | None,
    days_in_trade: int,
    indicators: FullIndicatorSet | None = None,
    *,
    max_holding_period: int = 40,
) -> ExitEvaluationResult:
    """Evaluate whether an active swing position should exit or trail stop.

    Rule priority:
    1. Stop Loss triggered.
    2. Target 2 reached (full exit).
    3. Trailing stop updates on Target 1 or dynamic trend trailing.
    4. Trend breakdown (Close < EMA 50 or -DI crosses above +DI with strong ADX).
    5. Max holding period (40 sessions) elapsed.
    """
    effective_stop = trailing_stop if trailing_stop is not None else stop_loss
    candle_low = Decimal(str(round(current_candle.low, 2)))
    candle_high = Decimal(str(round(current_candle.high, 2)))
    candle_close = Decimal(str(round(current_candle.close, 2)))

    # 1. Stop loss hit
    if candle_low <= effective_stop:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Swing stop loss hit at {effective_stop}.",
            exit_type="stopped_out",
            exit_price=effective_stop,
            is_stop_loss=True,
            notes=f"Position stopped out on low of {candle_low}.",
        )

    # 2. Target 2 hit
    if target_2 is not None and candle_high >= target_2:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Swing target 2 reached at {target_2}.",
            exit_type="target_2_hit",
            exit_price=target_2,
            is_target_2=True,
            notes=f"Full swing profit target 2 achieved at {target_2}.",
        )

    # 3. Trailing stop updates
    new_trailing = trailing_stop
    if candle_high >= target_1:
        # Move stop to breakeven if not already higher
        if effective_stop < entry_price:
            new_trailing = entry_price

    # Dynamic trailing along EMA 20 if price has expanded significantly
    if indicators is not None:
        ema_20 = indicators.moving_averages.ema_20
        if ema_20 is not None and candle_close > target_1:
            buffered_ema20 = Decimal(str(round(ema_20 * 0.995, 2)))
            if buffered_ema20 > (new_trailing or effective_stop):
                new_trailing = buffered_ema20

    # 4. Major trend breakdown (close below EMA 50 in mature trade)
    if indicators is not None and days_in_trade >= 5:
        ema_50 = indicators.moving_averages.ema_50
        plus_di = indicators.trend.plus_di
        minus_di = indicators.trend.minus_di
        adx_14 = indicators.trend.adx

        # Trend break below EMA 50
        if ema_50 is not None and float(candle_close) < ema_50 * 0.99:
            return ExitEvaluationResult(
                should_exit=True,
                exit_reason=f"Major trend breakdown: closed below EMA 50 ({ema_50:.2f}).",
                exit_type="closed",
                exit_price=candle_close,
                notes="Trend structure failure exit.",
                updated_trailing_stop=new_trailing,
            )

        # Bearish directional expansion
        if plus_di is not None and minus_di is not None and adx_14 is not None:
            if minus_di > plus_di and adx_14 >= 25.0:
                return ExitEvaluationResult(
                    should_exit=True,
                    exit_reason=f"Bearish trend reversal: -DI ({minus_di:.1f}) crossed above +DI with ADX={adx_14:.1f}.",
                    exit_type="closed",
                    exit_price=candle_close,
                    notes="DMI directional flip exit.",
                    updated_trailing_stop=new_trailing,
                )

    # 5. Max holding period reached (40 sessions)
    if days_in_trade >= max_holding_period:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Swing maximum holding period ({max_holding_period} sessions) elapsed.",
            exit_type="expired",
            exit_price=candle_close,
            is_time_exit=True,
            notes=f"Time-based exit executed at session close {candle_close}.",
            updated_trailing_stop=new_trailing,
        )

    return ExitEvaluationResult(
        should_exit=False,
        updated_trailing_stop=new_trailing,
        notes="Swing trade healthy; trailing stop maintained.",
    )
