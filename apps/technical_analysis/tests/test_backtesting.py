"""Tests for backtesting engine, quantitative metrics, and portfolio simulation."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.backtesting.engine import (
    BacktestConfiguration,
    TechnicalBacktestEngine,
)
from apps.technical_analysis.backtesting.metrics import (
    calculate_approx_sharpe,
    calculate_horizon_metrics,
    calculate_max_drawdown,
    calculate_profit_factor,
)
from apps.technical_analysis.backtesting.portfolio import (
    PortfolioTracker,
    SimulatedTrade,
)
from apps.technical_analysis.services.analysis_service import (
    persist_technical_analysis_run,
    run_full_technical_pipeline,
)


class TestBacktestingMetrics:
    """Unit tests for statistical performance metrics."""

    def test_calculate_horizon_metrics_basic(self) -> None:
        strat_rets = [10.0, 5.0, -3.0, 8.0, -2.0]
        bench_rets = [2.0, 1.0, 0.0, 3.0, -1.0]

        metric = calculate_horizon_metrics(5, strat_rets, bench_rets)
        assert metric.horizon_days == 5
        assert metric.total_trades == 5
        assert metric.winning_trades == 3
        assert metric.losing_trades == 2
        assert metric.win_rate_pct == 60.0
        assert metric.average_return_pct == 3.6
        assert metric.benchmark_average_return_pct == 1.0
        assert metric.excess_return_pct == 2.6

    def test_profit_factor_calculation(self) -> None:
        rets = [10.0, 20.0, -10.0]
        pf = calculate_profit_factor(rets)
        # Gross profit: 30, gross loss: 10 -> PF = 3.0
        assert pf == 3.0

        # All wins
        assert calculate_profit_factor([5.0, 10.0]) == 15.0

        # No trades
        assert calculate_profit_factor([]) == 1.0

    def test_max_drawdown_calculation(self) -> None:
        equity = [100.0, 120.0, 90.0, 110.0, 80.0, 130.0]
        # Peak 120, trough 80 -> (120 - 80) / 120 = 33.33%
        dd = calculate_max_drawdown(equity)
        assert dd == 33.33

    def test_approx_sharpe_calculation(self) -> None:
        rets = [1.0, 0.5, 1.2, 0.8, -0.2, 1.5]
        sharpe = calculate_approx_sharpe(rets)
        assert sharpe > 0.0


class TestPortfolioTracker:
    """Test equal-weighted simulated portfolio tracker."""

    def test_portfolio_tracker_simulation(self) -> None:
        tracker = PortfolioTracker(initial_capital=100000.0)
        d1 = datetime.date(2026, 1, 10)
        d2 = datetime.date(2026, 1, 15)

        t1 = SimulatedTrade(
            security_id=1,
            symbol="TEST1",
            entry_date=d1,
            exit_date=d2,
            entry_price=100.0,
            exit_price=110.0,
            return_pct=10.0,
            benchmark_return_pct=2.0,
            excess_return_pct=8.0,
            holding_period_days=5,
            candidate_category="trending_sector_top",
            technical_score_at_entry=85.0,
        )
        t2 = SimulatedTrade(
            security_id=2,
            symbol="TEST2",
            entry_date=d1,
            exit_date=d2,
            entry_price=200.0,
            exit_price=190.0,
            return_pct=-5.0,
            benchmark_return_pct=2.0,
            excess_return_pct=-7.0,
            holding_period_days=5,
            candidate_category="trending_sector_top",
            technical_score_at_entry=80.0,
        )

        tracker.record_trades_batch(d1, [t1, t2], benchmark_period_return_pct=2.0)
        summary = tracker.summarize()

        assert summary.total_trades == 2
        assert summary.winning_trades == 1
        assert summary.losing_trades == 1
        assert summary.win_rate_pct == 50.0
        # Avg return = (10 + -5) / 2 = +2.5%
        assert summary.final_strategy_equity == 102500.0
        assert summary.final_benchmark_equity == 102000.0


@pytest.mark.django_db
class TestBacktestEngineIntegration:
    """Integration test verifying point-in-time backtest on seeded historical database."""

    def test_run_historical_backtest(self) -> None:
        sec = Sector.objects.create(nepse_id=301, name="Banking")
        stock = Security.objects.create(nepse_id=4001, symbol="BOK", company_name="Bank of Kathmandu", sector=sec)
        nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

        start = datetime.date(2026, 1, 1)
        for i in range(35):
            cur = start + datetime.timedelta(days=i)
            DailyPrice.objects.create(
                security=stock,
                trading_date=cur,
                open=Decimal("300.0"),
                high=Decimal("310.0"),
                low=Decimal("295.0"),
                close=Decimal(str(300 + i * 2)),
                percentage_change=Decimal("0.5"),
                volume=10000 + i * 100,
            )
            IndexSnapshot.objects.create(
                index=nepse,
                trading_date=cur,
                open=Decimal("2000.0"),
                high=Decimal("2020.0"),
                low=Decimal("1990.0"),
                close=Decimal(str(2000 + i * 3)),
                volume=100000,
            )

        # Run pipeline at day 25 to generate snapshots
        eval_date = start + datetime.timedelta(days=25)
        report = run_full_technical_pipeline(eval_date)
        persist_technical_analysis_run(report)

        config = BacktestConfiguration(
            start_date=start,
            end_date=eval_date,
            min_technical_score=20.0,
            horizons=[5, 10],
            rebalance_frequency_days=5,
        )

        engine = TechnicalBacktestEngine(config)
        backtest_report = engine.run()

        assert backtest_report.total_signals >= 1
        assert 5 in backtest_report.overall_performance.horizon_metrics
        assert backtest_report.portfolio_simulation.total_trades >= 1
        assert len(backtest_report.portfolio_simulation.equity_curve) >= 1
