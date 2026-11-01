"""Position sizing service conforming to NEPSE board lot requirements and portfolio risk limits."""

from __future__ import annotations

import math
from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class PositionSizingResult:
    """Calculated position sizing parameters."""

    portfolio_capital: Decimal
    risk_percentage: Decimal
    capital_at_risk: Decimal
    entry_price: Decimal
    stop_loss: Decimal
    risk_per_share: Decimal
    suggested_shares: int
    board_lot_size: int
    total_outlay: Decimal
    portfolio_allocation_pct: Decimal
    is_valid: bool
    rejection_reason: str | None = None


def calculate_position_size(
    portfolio_capital: Decimal | float,
    entry_price: Decimal | float,
    stop_loss: Decimal | float,
    *,
    risk_percentage: float = 1.0,  # 1% portfolio risk per trade
    max_portfolio_allocation_pct: float = 20.0,  # Max 20% of account in one stock
    board_lot_size: int = 10,  # Standard NEPSE board lot size
) -> PositionSizingResult:
    """Calculate the optimal share count based on fixed fractional risk and NEPSE lot constraints.

    Args:
        portfolio_capital: Total account portfolio equity.
        entry_price: Expected purchase price per share.
        stop_loss: Validated stop-loss price.
        risk_percentage: Max portfolio capital percentage to risk (e.g. 1.0 = 1%).
        max_portfolio_allocation_pct: Maximum allowed capital in a single security.
        board_lot_size: Standard NEPSE lot size (10 shares).

    Returns:
        PositionSizingResult with computed share counts and capital allocation metrics.
    """
    capital = Decimal(str(round(float(portfolio_capital), 2)))
    entry = Decimal(str(round(float(entry_price), 2)))
    stop = Decimal(str(round(float(stop_loss), 2)))
    risk_pct = Decimal(str(round(float(risk_percentage), 2)))

    if capital <= 0:
        return PositionSizingResult(
            portfolio_capital=capital,
            risk_percentage=risk_pct,
            capital_at_risk=Decimal("0.00"),
            entry_price=entry,
            stop_loss=stop,
            risk_per_share=Decimal("0.00"),
            suggested_shares=0,
            board_lot_size=board_lot_size,
            total_outlay=Decimal("0.00"),
            portfolio_allocation_pct=Decimal("0.00"),
            is_valid=False,
            rejection_reason="Portfolio capital must be positive.",
        )

    if stop >= entry or entry <= 0:
        return PositionSizingResult(
            portfolio_capital=capital,
            risk_percentage=risk_pct,
            capital_at_risk=Decimal("0.00"),
            entry_price=entry,
            stop_loss=stop,
            risk_per_share=Decimal("0.00"),
            suggested_shares=0,
            board_lot_size=board_lot_size,
            total_outlay=Decimal("0.00"),
            portfolio_allocation_pct=Decimal("0.00"),
            is_valid=False,
            rejection_reason=f"Stop loss ({stop}) must be strictly less than entry price ({entry}).",
        )

    risk_per_share = entry - stop
    capital_at_risk = capital * (risk_pct / Decimal("100.0"))

    # Raw shares based on dollar risk
    raw_shares_by_risk = float(capital_at_risk) / float(risk_per_share)

    # Max shares by portfolio allocation cap
    max_allowed_outlay = capital * (Decimal(str(max_portfolio_allocation_pct)) / Decimal("100.0"))
    max_shares_by_allocation = float(max_allowed_outlay) / float(entry)

    # Constrain to the lower of risk budget and allocation ceiling
    max_shares = min(raw_shares_by_risk, max_shares_by_allocation)

    # Round down to nearest NEPSE board lot
    if board_lot_size > 0:
        lots = math.floor(max_shares / board_lot_size)
        suggested_shares = lots * board_lot_size
    else:
        suggested_shares = math.floor(max_shares)

    if suggested_shares < board_lot_size:
        return PositionSizingResult(
            portfolio_capital=capital,
            risk_percentage=risk_pct,
            capital_at_risk=capital_at_risk,
            entry_price=entry,
            stop_loss=stop,
            risk_per_share=risk_per_share,
            suggested_shares=0,
            board_lot_size=board_lot_size,
            total_outlay=Decimal("0.00"),
            portfolio_allocation_pct=Decimal("0.00"),
            is_valid=False,
            rejection_reason=(
                f"Calculated share count ({max_shares:.1f}) is less than minimum NEPSE board lot of {board_lot_size}."
            ),
        )

    total_outlay = Decimal(str(round(suggested_shares * float(entry), 2)))
    allocation_pct = Decimal(str(round(float(total_outlay / capital) * 100.0, 2)))

    return PositionSizingResult(
        portfolio_capital=capital,
        risk_percentage=risk_pct,
        capital_at_risk=capital_at_risk,
        entry_price=entry,
        stop_loss=stop,
        risk_per_share=risk_per_share,
        suggested_shares=suggested_shares,
        board_lot_size=board_lot_size,
        total_outlay=total_outlay,
        portfolio_allocation_pct=allocation_pct,
        is_valid=True,
    )
