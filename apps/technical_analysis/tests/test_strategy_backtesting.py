"""Unit and integration tests for NEPSE transaction costs and event-driven Strategy Backtest Engine."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.prices.models import DailyPrice
from apps.securities.models import Security
from apps.technical_analysis.backtesting.costs import (
    calculate_broker_commission,
    calculate_nepse_buy_costs,
    calculate_nepse_sell_costs,
)
from apps.technical_analysis.backtesting.strategy_engine import (
    StrategyBacktestConfig,
    StrategyBacktestEngine,
)


class TestNepseTransactionCosts:
    """Tests for NEPSE commission tariffs and tax calculations."""

    def test_tiered_broker_commission(self) -> None:
        # Tier 1 (<= 50,000): 0.40%
        assert calculate_broker_commission(40000.0) == 160.0

        # Tier 2 (50,001 - 500,000): 0.37%
        assert round(calculate_broker_commission(100000.0), 2) == 370.0

        # Tier 3 (500,001 - 2,000,000): 0.34%
        assert round(calculate_broker_commission(1000000.0), 2) == 3400.0

        # Minimum commission check
        assert calculate_broker_commission(1000.0) == 10.0

    def test_calculate_buy_costs(self) -> None:
        # Buy Rs. 100,000:
        # Broker = 370.00
        # SEBON = 100,000 * 0.00015 = 15.00
        # DP = 25.00
        # Total fee = 410.00
        # Net amount = 100,410.00
        res = calculate_nepse_buy_costs(100000.0)
        assert res.broker_commission == Decimal("370.00")
        assert res.sebon_fee == Decimal("15.00")
        assert res.dp_charge == Decimal("25.00")
        assert res.total_costs == Decimal("410.00")
        assert res.net_amount == Decimal("100410.00")

    def test_calculate_sell_costs_with_capital_gains(self) -> None:
        # Bought for Rs. 100,000, Sold for Rs. 120,000:
        # Gross profit = 20,000.00
        # Broker sell = 120,000 * 0.37% = 444.00
        # SEBON sell = 120,000 * 0.00015 = 18.00
        # DP = 25.00
        # Taxable gain = 20,000 - 444 - 18 = 19,538.00
        # CGT 7.5% = 1,465.35
        # Total cost = 444 + 18 + 25 + 1465.35 = 1,952.35
        res = calculate_nepse_sell_costs(100000.0, 120000.0, cgt_rate=0.075)
        assert res.broker_commission == Decimal("444.00")
        assert res.sebon_fee == Decimal("18.00")
        assert res.dp_charge == Decimal("25.00")
        assert res.capital_gains_tax == Decimal("1465.35")
        assert res.total_costs == Decimal("1952.35")
        assert res.net_amount == Decimal("118047.65")


@pytest.fixture
def sample_backtest_data(db) -> tuple[Security, list[DailyPrice]]:
    sec = Security.objects.create(
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        nepse_id=101,
    )
    start_date = datetime.date(2026, 7, 1)
    prices = []
    curr = 500.0

    for i in range(50):
        d = start_date + datetime.timedelta(days=i)
        drift = 0.5
        osc = 2.0 if i % 2 == 0 else -1.5
        curr = max(100.0, curr + drift + osc)
        o = curr - 1.0
        c = curr
        h = c + 3.0
        low_val = o - 2.0
        v = 15000.0 + (i * 100.0)
        p = DailyPrice.objects.create(
            security=sec,
            trading_date=d,
            open=Decimal(str(round(o, 2))),
            high=Decimal(str(round(h, 2))),
            low=Decimal(str(round(low_val, 2))),
            close=Decimal(str(round(c, 2))),
            volume=Decimal(str(round(v, 2))),
            turnover=Decimal(str(round(v * c, 2))),
        )
        prices.append(p)

    return sec, prices


@pytest.mark.django_db
class TestStrategyBacktestEngine:
    """Integration tests for chronological StrategyBacktestEngine."""

    def test_run_strategy_backtest(
        self, sample_backtest_data: tuple[Security, list[DailyPrice]]
    ) -> None:
        sec, prices = sample_backtest_data
        start_d = prices[20].trading_date
        end_d = prices[-1].trading_date

        config = StrategyBacktestConfig(
            strategy_type="short_term",
            start_date=start_d,
            end_date=end_d,
            initial_capital=1000000.0,
            risk_per_trade_pct=1.0,
            min_composite_score=50.0,
            include_costs=True,
            include_cgt=True,
        )

        engine = StrategyBacktestEngine(config)
        result = engine.run()

        assert result.initial_capital == 1000000.0
        assert len(result.equity_curve) > 0
        assert result.equity_curve[0].strategy_equity > 0
