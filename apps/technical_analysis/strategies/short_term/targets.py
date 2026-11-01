"""Target calculations for Short-Term Trading Strategy."""

from __future__ import annotations

from decimal import Decimal


def calculate_short_term_targets(
    entry_price: Decimal,
    stop_loss: Decimal,
    *,
    target_1_multiplier: float = 1.5,
    target_2_multiplier: float = 2.0,
    resistance_level: float | None = None,
) -> tuple[Decimal, Decimal]:
    """Calculate Target 1 and Target 2 based on risk multiple.

    Risk per share = Entry price - Stop loss
    Target 1 = Entry price + (1.5 * Risk)
    Target 2 = Entry price + (2.0 * Risk)
    """
    entry = float(entry_price)
    stop = float(stop_loss)
    risk_per_share = max(0.1, entry - stop)

    t1 = entry + (risk_per_share * target_1_multiplier)
    t2 = entry + (risk_per_share * target_2_multiplier)

    # If an obvious resistance level sits comfortably above target 1, respect it for target 2
    if resistance_level is not None and resistance_level > t1 and resistance_level < t2:
        t2 = resistance_level * 0.998  # Just under resistance

    return (
        Decimal(str(round(t1, 2))),
        Decimal(str(round(t2, 2))),
    )
