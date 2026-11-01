"""Exit condition evaluation for Short-Term Trading Strategy."""

from __future__ import annotations

from decimal import Decimal

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle
from apps.technical_analysis.strategies.base import ExitEvaluationResult


def check_short_term_exit(
    current_candle: Candle,
    entry_price: Decimal,
    stop_loss: Decimal,
    target_1: Decimal,
    target_2: Decimal | None,
    trailing_stop: Decimal | None,
    days_in_trade: int,
    indicators: FullIndicatorSet | None = None,
    *,
    max_holding_period: int = 10,
) -> ExitEvaluationResult:
    """Evaluate whether an active short-term position should be closed or stop trailed.

    Rule priority:
    1. Stop Loss triggered (conservative check: if low touches active stop).
    2. Target 2 reached.
    3. Target 1 reached (can signal partial exit or stop update to breakeven).
    4. Technical breakdown (close below falling EMA 20 with bearish MACD).
    5. Time-based exit (days_in_trade >= max_holding_period).
    """
    effective_stop = trailing_stop if trailing_stop is not None else stop_loss
    candle_low = Decimal(str(round(current_candle.low, 2)))
    candle_high = Decimal(str(round(current_candle.high, 2)))
    candle_close = Decimal(str(round(current_candle.close, 2)))

    # 1. Stop loss hit
    if candle_low <= effective_stop:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Stop loss triggered at {effective_stop}.",
            exit_type="stopped_out",
            exit_price=effective_stop,
            is_stop_loss=True,
            notes=f"Position stopped out on session low of {candle_low}.",
        )

    # 2. Target 2 hit
    if target_2 is not None and candle_high >= target_2:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Target 2 reached at {target_2}.",
            exit_type="target_2_hit",
            exit_price=target_2,
            is_target_2=True,
            notes=f"Full profit target 2 achieved at {target_2}.",
        )

    # 3. Target 1 hit
    new_trailing = trailing_stop
    if candle_high >= target_1:
        # Move stop to breakeven if not already higher
        if effective_stop < entry_price:
            new_trailing = entry_price

    # 4. Technical trend breakdown (close below falling EMA 20 with bearish momentum)
    if indicators is not None and days_in_trade >= 3:
        ema_20 = indicators.moving_averages.ema_20
        ema_slope = indicators.moving_averages.ema_20_slope
        macd = indicators.momentum.macd
        if ema_20 is not None and float(candle_close) < ema_20 * 0.99 and ema_slope is not None and ema_slope < 0:
            if macd.crossover == "bearish_crossover" or (macd.histogram is not None and macd.histogram < 0):
                return ExitEvaluationResult(
                    should_exit=True,
                    exit_reason=f"Technical breakdown: closed below falling EMA 20 ({ema_20:.2f}) with negative MACD.",
                    exit_type="closed",
                    exit_price=candle_close,
                    notes="Momentum deterioration exit.",
                    updated_trailing_stop=new_trailing,
                )

    # 5. Time-based max holding period exit
    if days_in_trade >= max_holding_period:
        return ExitEvaluationResult(
            should_exit=True,
            exit_reason=f"Maximum holding period of {max_holding_period} sessions reached.",
            exit_type="expired",
            exit_price=candle_close,
            is_time_exit=True,
            notes=f"Time exit executed at market close {candle_close}.",
            updated_trailing_stop=new_trailing,
        )

    return ExitEvaluationResult(
        should_exit=False,
        updated_trailing_stop=new_trailing,
        notes="Trade remains active within risk parameters.",
    )
