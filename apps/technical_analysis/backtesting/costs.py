"""NEPSE transaction cost calculations conforming to SEBON and broker tariff tiers."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class NepseTransactionCost:
    """Breakdown of transaction fees for a NEPSE buy or sell order."""

    turnover: Decimal
    broker_commission: Decimal
    sebon_fee: Decimal
    dp_charge: Decimal
    capital_gains_tax: Decimal
    total_costs: Decimal
    net_amount: Decimal  # turnover + costs for buy; turnover - costs for sell


def calculate_broker_commission(turnover: float) -> float:
    """Calculate tiered broker commission according to SEBON tariff guidelines.

    Tier 1: Up to Rs. 50,000: 0.40%
    Tier 2: Rs. 50,001 to Rs. 500,000: 0.37%
    Tier 3: Rs. 500,001 to Rs. 2,000,000: 0.34%
    Tier 4: Rs. 2,000,001 to Rs. 10,000,000: 0.30%
    Tier 5: Above Rs. 10,000,000: 0.27%
    Minimum commission: Rs. 10
    """
    if turnover <= 0:
        return 0.0

    if turnover <= 50000.0:
        rate = 0.0040
    elif turnover <= 500000.0:
        rate = 0.0037
    elif turnover <= 2000000.0:
        rate = 0.0034
    elif turnover <= 10000000.0:
        rate = 0.0030
    else:
        rate = 0.0027

    comm = turnover * rate
    return max(10.0, comm)


def calculate_nepse_buy_costs(
    turnover: Decimal | float,
    *,
    dp_charge: float = 25.0,
    sebon_fee_rate: float = 0.00015,  # 0.015%
) -> NepseTransactionCost:
    """Calculate all transaction costs for a share purchase in NEPSE."""
    turnover_flt = float(turnover)
    if turnover_flt <= 0:
        return NepseTransactionCost(
            turnover=Decimal("0.00"),
            broker_commission=Decimal("0.00"),
            sebon_fee=Decimal("0.00"),
            dp_charge=Decimal("0.00"),
            capital_gains_tax=Decimal("0.00"),
            total_costs=Decimal("0.00"),
            net_amount=Decimal("0.00"),
        )

    comm = calculate_broker_commission(turnover_flt)
    sebon = turnover_flt * sebon_fee_rate
    dp = dp_charge

    total_cost = comm + sebon + dp
    net = turnover_flt + total_cost

    return NepseTransactionCost(
        turnover=Decimal(str(round(turnover_flt, 2))),
        broker_commission=Decimal(str(round(comm, 2))),
        sebon_fee=Decimal(str(round(sebon, 2))),
        dp_charge=Decimal(str(round(dp, 2))),
        capital_gains_tax=Decimal("0.00"),
        total_costs=Decimal(str(round(total_cost, 2))),
        net_amount=Decimal(str(round(net, 2))),
    )


def calculate_nepse_sell_costs(
    buy_turnover: Decimal | float,
    sell_turnover: Decimal | float,
    *,
    cgt_rate: float = 0.075,  # 7.5% short-term individual CGT
    dp_charge: float = 25.0,
    sebon_fee_rate: float = 0.00015,
) -> NepseTransactionCost:
    """Calculate transaction costs and capital gains tax for a share sale in NEPSE."""
    sell_flt = float(sell_turnover)
    buy_flt = float(buy_turnover)

    if sell_flt <= 0:
        return NepseTransactionCost(
            turnover=Decimal("0.00"),
            broker_commission=Decimal("0.00"),
            sebon_fee=Decimal("0.00"),
            dp_charge=Decimal("0.00"),
            capital_gains_tax=Decimal("0.00"),
            total_costs=Decimal("0.00"),
            net_amount=Decimal("0.00"),
        )

    comm = calculate_broker_commission(sell_flt)
    sebon = sell_flt * sebon_fee_rate
    dp = dp_charge

    # Profit calculation for CGT
    gross_profit = sell_flt - buy_flt
    # Allowable trading expenses reduce taxable capital gain
    taxable_gain = max(0.0, gross_profit - comm - sebon)
    cgt = taxable_gain * cgt_rate if gross_profit > 0 else 0.0

    total_cost = comm + sebon + dp + cgt
    net = sell_flt - total_cost

    return NepseTransactionCost(
        turnover=Decimal(str(round(sell_flt, 2))),
        broker_commission=Decimal(str(round(comm, 2))),
        sebon_fee=Decimal(str(round(sebon, 2))),
        dp_charge=Decimal(str(round(dp, 2))),
        capital_gains_tax=Decimal(str(round(cgt, 2))),
        total_costs=Decimal(str(round(total_cost, 2))),
        net_amount=Decimal(str(round(net, 2))),
    )
