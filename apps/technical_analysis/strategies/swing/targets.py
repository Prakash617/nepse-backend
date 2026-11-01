"""Target calculations for Swing Trading Strategy."""

from __future__ import annotations

from decimal import Decimal


def calculate_swing_targets(
    entry_price: Decimal,
    stop_loss: Decimal,
    *,
    target_1_multiplier: float = 2.0,
    target_2_multiplier: float = 3.0,
    historical_resistance: float | None = None,
) -> tuple[Decimal, Decimal]:
    """Calculate Target 1 and Target 2 based on swing risk multiples.

    Risk per share = Entry price - Stop loss
    Target 1 = Entry price + (2.0 * Risk)
    Target 2 = Entry price + (3.0 * Risk)
    """
    entry = float(entry_price)
    stop = float(stop_loss)
    risk_per_share = max(0.1, entry - stop)

    t1 = entry + (risk_per_share * target_1_multiplier)
    t2 = entry + (risk_per_share * target_2_multiplier)

    # Respect major resistance if it sits above target 1
    if historical_resistance is not None and historical_resistance > t1 and historical_resistance < t2:
        t2 = historical_resistance * 0.998

    return (
        Decimal(str(round(t1, 2))),
        Decimal(str(round(t2, 2))),
    )
