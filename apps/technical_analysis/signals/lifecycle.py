"""Signal Lifecycle Engine: Manages order fills, trailing stops, target achievements, and exits."""

from __future__ import annotations

import datetime
import logging
from decimal import Decimal
from typing import Any

from django.db.models import Max

from apps.prices.models import DailyPrice
from apps.technical_analysis.indicators.types import Candle
from apps.technical_analysis.models import (
    TradingSignal,
    TradingSignalTracking,
)
from apps.technical_analysis.strategies.short_term import (
    ShortTermTradingStrategy,
)
from apps.technical_analysis.strategies.swing import (
    SwingTradingStrategy,
)

logger = logging.getLogger(__name__)


def update_trading_signals_lifecycle(
    current_date: datetime.date | None = None,
) -> dict[str, Any]:
    """Process active and pending trading signals against the latest market session.

    Execution model:
    - Avoids look-ahead bias: Pending signals generated on day T are evaluated against day T+1 session.
    - Active signals evaluate high/low ranges against stop-loss and targets.
    - Conservative assumption: If both stop loss and target are breached on the same bar, stop loss triggers.

    Args:
        current_date: Trading session date to evaluate. Defaults to latest in DB.

    Returns:
        Summary dict of lifecycle transitions.
    """
    if current_date is None:
        latest_d = DailyPrice.objects.aggregate(max_d=Max("trading_date"))["max_d"]
        if not latest_d:
            return {"status": "no_data", "updated": 0}
        current_date = latest_d

    logger.info("Executing trading signals lifecycle update for date: %s", current_date)

    short_term_strategy = ShortTermTradingStrategy()
    swing_strategy = SwingTradingStrategy()

    # 1. Fetch pending signals generated BEFORE current_date
    pending_signals = list(
        TradingSignal.objects.filter(
            status=TradingSignal.STATUS_PENDING,
            signal_date__lt=current_date,
        ).select_related("security")
    )

    # 2. Fetch active signals
    active_signals = list(
        TradingSignal.objects.filter(
            status=TradingSignal.STATUS_ACTIVE,
            entry_date__lt=current_date,
        ).select_related("security")
    )

    all_relevant_sec_ids = {s.security_id for s in pending_signals + active_signals}
    if not all_relevant_sec_ids:
        return {"status": "success", "current_date": current_date.isoformat(), "updated": 0}

    # Fetch today's prices for relevant securities
    todays_prices = {
        p.security_id: p
        for p in DailyPrice.objects.filter(
            trading_date=current_date,
            security_id__in=all_relevant_sec_ids,
        )
    }

    filled_count = 0
    invalidated_count = 0
    closed_count = 0
    tracking_entries: list[TradingSignalTracking] = []

    # Process PENDING signals (Day T -> Day T+1 fill attempt)
    for sig in pending_signals:
        price = todays_prices.get(sig.security_id)
        if not price or price.open is None:
            # If 3 trading days elapsed with no trading, expire pending signal
            days_elapsed = (current_date - sig.signal_date).days
            if days_elapsed > 7:
                sig.status = TradingSignal.STATUS_EXPIRED
                sig.save(update_fields=["status", "updated_at"])
                invalidated_count += 1
            continue

        c_open = Decimal(str(price.open))
        c_high = Decimal(str(price.high))
        c_low = Decimal(str(price.low))
        entry_zone_max = sig.entry_zone_high if sig.entry_zone_high else sig.suggested_entry * Decimal("1.015")
        entry_zone_min = sig.entry_zone_low if sig.entry_zone_low else sig.suggested_entry * Decimal("0.985")

        # Invalidation check: gapped up beyond acceptable entry zone
        if c_open > entry_zone_max * Decimal("1.03"):
            sig.status = TradingSignal.STATUS_INVALIDATED
            sig.save(update_fields=["status", "updated_at"])
            invalidated_count += 1
            continue

        # Invalidation check: opened below stop loss
        if c_open <= sig.stop_loss:
            sig.status = TradingSignal.STATUS_INVALIDATED
            sig.save(update_fields=["status", "updated_at"])
            invalidated_count += 1
            continue

        # Fill condition: price traded within entry zone or opened within bounds
        can_fill = (c_low <= sig.suggested_entry <= c_high) or (c_open <= entry_zone_max)
        if can_fill:
            fill_price = c_open if (entry_zone_min <= c_open <= entry_zone_max) else sig.suggested_entry
            sig.status = TradingSignal.STATUS_ACTIVE
            sig.entry_date = current_date
            sig.actual_entry_price = fill_price
            sig.holding_period_days = 1
            sig.highest_price_reached = max(fill_price, c_high)
            sig.lowest_price_reached = min(fill_price, c_low)
            sig.save(
                update_fields=[
                    "status",
                    "entry_date",
                    "actual_entry_price",
                    "holding_period_days",
                    "highest_price_reached",
                    "lowest_price_reached",
                    "updated_at",
                ]
            )
            filled_count += 1

            # Log Day 1 tracking entry
            c_close = Decimal(str(price.close or price.open))
            unrealized_return = ((c_close - fill_price) / fill_price) * Decimal("100.0")
            tracking_entries.append(
                TradingSignalTracking(
                    signal=sig,
                    trading_date=current_date,
                    close_price=c_close,
                    high_price=c_high,
                    low_price=c_low,
                    unrealized_return_pct=Decimal(str(round(float(unrealized_return), 2))),
                    trailing_stop_level=sig.trailing_stop or sig.stop_loss,
                    day_in_trade=1,
                    notes=f"Order filled at open price {fill_price}.",
                )
            )

    # Process ACTIVE signals
    for sig in active_signals:
        price = todays_prices.get(sig.security_id)
        if not price or price.close is None:
            continue

        candle = Candle(
            trading_date=current_date,
            open=float(price.open or price.close),
            high=float(price.high or price.close),
            low=float(price.low or price.close),
            close=float(price.close),
            volume=float(price.volume or 0.0),
        )

        sig.holding_period_days += 1
        c_high = Decimal(str(candle.high))
        c_low = Decimal(str(candle.low))
        c_close = Decimal(str(candle.close))

        if sig.highest_price_reached is None or c_high > sig.highest_price_reached:
            sig.highest_price_reached = c_high
        if sig.lowest_price_reached is None or c_low < sig.lowest_price_reached:
            sig.lowest_price_reached = c_low

        strategy = short_term_strategy if sig.strategy_type == TradingSignal.STRATEGY_SHORT_TERM else swing_strategy
        entry_price = sig.actual_entry_price or sig.suggested_entry

        exit_res = strategy.check_exit_conditions(
            current_candle=candle,
            entry_price=entry_price,
            stop_loss=sig.stop_loss,
            target_1=sig.target_1,
            target_2=sig.target_2,
            trailing_stop=sig.trailing_stop,
            days_in_trade=sig.holding_period_days,
        )

        if exit_res.should_exit and exit_res.exit_price is not None:
            sig.status = exit_res.exit_type or TradingSignal.STATUS_CLOSED
            sig.exit_date = current_date
            sig.actual_exit_price = exit_res.exit_price
            ret_pct = ((exit_res.exit_price - entry_price) / entry_price) * Decimal("100.0")
            sig.return_pct = Decimal(str(round(float(ret_pct), 2)))
            sig.save(
                update_fields=[
                    "status",
                    "exit_date",
                    "actual_exit_price",
                    "return_pct",
                    "holding_period_days",
                    "highest_price_reached",
                    "lowest_price_reached",
                    "updated_at",
                ]
            )
            closed_count += 1
            note = f"Exited: {exit_res.exit_reason}"
        else:
            if exit_res.updated_trailing_stop is not None and exit_res.updated_trailing_stop != sig.trailing_stop:
                sig.trailing_stop = exit_res.updated_trailing_stop
            sig.save(
                update_fields=[
                    "trailing_stop",
                    "holding_period_days",
                    "highest_price_reached",
                    "lowest_price_reached",
                    "updated_at",
                ]
            )
            note = exit_res.notes or "Position active."

        # Record daily tracking point
        unrealized = ((c_close - entry_price) / entry_price) * Decimal("100.0")
        tracking_entries.append(
            TradingSignalTracking(
                signal=sig,
                trading_date=current_date,
                close_price=c_close,
                high_price=c_high,
                low_price=c_low,
                unrealized_return_pct=Decimal(str(round(float(unrealized), 2))),
                trailing_stop_level=sig.trailing_stop or sig.stop_loss,
                day_in_trade=sig.holding_period_days,
                notes=note,
            )
        )

    # Bulk create tracking snapshots
    if tracking_entries:
        TradingSignalTracking.objects.bulk_create(
            tracking_entries,
            update_conflicts=True,
            update_fields=["close_price", "high_price", "low_price", "unrealized_return_pct", "trailing_stop_level", "notes"],
            unique_fields=["signal", "trading_date"],
        )

    logger.info(
        "Lifecycle update complete for %s: %d filled, %d closed, %d invalidated",
        current_date,
        filled_count,
        closed_count,
        invalidated_count,
    )

    return {
        "status": "success",
        "current_date": current_date.isoformat(),
        "filled": filled_count,
        "closed": closed_count,
        "invalidated": invalidated_count,
        "tracking_recorded": len(tracking_entries),
    }
