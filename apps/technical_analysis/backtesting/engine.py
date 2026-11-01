"""Historical backtesting engine for technical analysis strategies and candidate ranking evaluation."""

from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass, field

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.technical_analysis.backtesting.metrics import (
    HorizonReturnMetric,
    StrategyPerformanceMetrics,
    calculate_approx_sharpe,
    calculate_horizon_metrics,
    calculate_max_drawdown,
    calculate_profit_factor,
)
from apps.technical_analysis.backtesting.portfolio import (
    PortfolioSimulationResult,
    PortfolioTracker,
    SimulatedTrade,
)
from apps.technical_analysis.models import (
    RecommendationSnapshot,
    TechnicalScoreSnapshot,
)

logger = logging.getLogger(__name__)


@dataclass
class BacktestConfiguration:
    """Parameters for running a technical strategy backtest."""

    start_date: datetime.date
    end_date: datetime.date
    min_technical_score: float = 70.0
    category: str | None = None  # None = all, or 'trending_sector_top', 'idiosyncratic', 'strong_bullish'
    horizons: list[int] = field(default_factory=lambda: [5, 10, 20, 60])
    rebalance_frequency_days: int = 5
    initial_capital: float = 1000000.0


@dataclass
class BacktestReport:
    """Comprehensive historical strategy evaluation and forward return analysis."""

    config: BacktestConfiguration
    total_signals: int
    overall_performance: StrategyPerformanceMetrics
    portfolio_simulation: PortfolioSimulationResult
    recent_sample_trades: list[SimulatedTrade] = field(default_factory=list)


class TechnicalBacktestEngine:
    """Executes point-in-time historical backtests of technical scores and recommendations."""

    def __init__(self, config: BacktestConfiguration) -> None:
        self.config = config

    def run(self) -> BacktestReport:
        """Execute backtest over historical price sessions and recommendation snapshots."""
        logger.info(
            "Starting technical strategy backtest from %s to %s (min_score=%.1f)",
            self.config.start_date,
            self.config.end_date,
            self.config.min_technical_score,
        )

        # 1. Fetch all distinct trading dates in range + enough future dates to resolve 60d horizons
        trading_dates = list(
            DailyPrice.objects.filter(trading_date__gte=self.config.start_date)
            .values_list("trading_date", flat=True)
            .distinct()
            .order_by("trading_date")
        )

        if not trading_dates:
            return self._empty_report()

        date_to_idx = {d: i for i, d in enumerate(trading_dates)}

        # 2. Benchmark index prices (NEPSE index nepse_id=58)
        nepse_idx = MarketIndex.objects.filter(nepse_id=58).first()
        bench_snaps = {}
        if nepse_idx:
            for snap in IndexSnapshot.objects.filter(
                index=nepse_idx,
                trading_date__gte=self.config.start_date,
            ).values("trading_date", "close"):
                if snap["close"] is not None:
                    bench_snaps[snap["trading_date"]] = float(snap["close"])

        # 3. Retrieve eligible candidates/scores in backtest window
        sim_trades_by_horizon: dict[int, list[SimulatedTrade]] = defaultdict(list)
        all_evaluated_trades: list[SimulatedTrade] = []

        # Try RecommendationSnapshot first, fallback to TechnicalScoreSnapshot
        recs_qs = RecommendationSnapshot.objects.filter(
            trading_date__gte=self.config.start_date,
            trading_date__lte=self.config.end_date,
            technical_score__gte=self.config.min_technical_score,
        ).select_related("security")

        if self.config.category:
            recs_qs = recs_qs.filter(category=self.config.category.lower())

        candidate_records = list(recs_qs)

        # If no recommendation snapshots found, generate candidates from TechnicalScoreSnapshot
        if not candidate_records:
            scores_qs = TechnicalScoreSnapshot.objects.filter(
                trading_date__gte=self.config.start_date,
                trading_date__lte=self.config.end_date,
                total_score__gte=self.config.min_technical_score,
            ).select_related("security")
            for sc in scores_qs:
                candidate_records.append(
                    RecommendationSnapshot(
                        security=sc.security,
                        trading_date=sc.trading_date,
                        category=RecommendationSnapshot.CATEGORY_STRONG_BULLISH if sc.total_score >= 80 else RecommendationSnapshot.CATEGORY_TRENDING_SECTOR_TOP,
                        technical_score=sc.total_score,
                    )
                )

        if not candidate_records:
            return self._empty_report()

        # Cache security prices in memory for fast simulation lookups
        sec_ids = {c.security_id for c in candidate_records}
        price_records = (
            DailyPrice.objects.filter(
                security_id__in=sec_ids,
                trading_date__gte=self.config.start_date,
            )
            .values("security_id", "trading_date", "close")
        )
        sec_price_map: dict[tuple[int, datetime.date], float] = {
            (p["security_id"], p["trading_date"]): float(p["close"])
            for p in price_records
            if p["close"] is not None
        }

        # 4. Evaluate forward returns for each horizon
        portfolio_rebalance_trades: dict[datetime.date, list[SimulatedTrade]] = defaultdict(list)

        for cand in candidate_records:
            entry_d = cand.trading_date
            sec_id = cand.security_id
            sym = cand.security.symbol if cand.security else f"SEC_{sec_id}"
            entry_p = sec_price_map.get((sec_id, entry_d))

            if entry_p is None or entry_p <= 0.0:
                continue

            entry_idx = date_to_idx.get(entry_d)
            if entry_idx is None:
                continue

            entry_bench = bench_snaps.get(entry_d, 0.0)

            # Evaluate each forward horizon
            for h in self.config.horizons:
                exit_idx = entry_idx + h
                if exit_idx < len(trading_dates):
                    exit_d = trading_dates[exit_idx]
                    exit_p = sec_price_map.get((sec_id, exit_d))
                    if exit_p is not None and exit_p > 0.0:
                        stock_ret = ((exit_p - entry_p) / entry_p) * 100.0
                        exit_bench = bench_snaps.get(exit_d, entry_bench)
                        bench_ret = ((exit_bench - entry_bench) / entry_bench * 100.0) if entry_bench > 0 else 0.0
                        excess_ret = stock_ret - bench_ret

                        trade = SimulatedTrade(
                            security_id=sec_id,
                            symbol=sym,
                            entry_date=entry_d,
                            exit_date=exit_d,
                            entry_price=entry_p,
                            exit_price=exit_p,
                            return_pct=round(stock_ret, 2),
                            benchmark_return_pct=round(bench_ret, 2),
                            excess_return_pct=round(excess_ret, 2),
                            holding_period_days=h,
                            candidate_category=cand.category,
                            technical_score_at_entry=float(cand.technical_score),
                        )
                        sim_trades_by_horizon[h].append(trade)
                        if h == self.config.rebalance_frequency_days:
                            portfolio_rebalance_trades[entry_d].append(trade)

        # 5. Build Horizon Metrics
        horizon_metrics_map: dict[int, HorizonReturnMetric] = {}
        all_strat_returns: list[float] = []

        for h in self.config.horizons:
            trades_h = sim_trades_by_horizon.get(h, [])
            strat_rets = [t.return_pct for t in trades_h]
            bench_rets = [t.benchmark_return_pct for t in trades_h]
            h_metric = calculate_horizon_metrics(h, strat_rets, bench_rets)
            horizon_metrics_map[h] = h_metric
            if h == self.config.rebalance_frequency_days:
                all_strat_returns = strat_rets
                all_evaluated_trades = trades_h

        # 6. Simulate Equal-Weighted Rebalanced Portfolio
        tracker = PortfolioTracker(initial_capital=self.config.initial_capital)
        sorted_entry_dates = sorted(portfolio_rebalance_trades.keys())

        for idx, d in enumerate(sorted_entry_dates):
            trades_for_date = portfolio_rebalance_trades[d]
            next_d = sorted_entry_dates[idx + 1] if idx + 1 < len(sorted_entry_dates) else trading_dates[-1]
            b_start = bench_snaps.get(d, 1.0)
            b_end = bench_snaps.get(next_d, b_start)
            b_ret = ((b_end - b_start) / b_start * 100.0) if b_start > 0 else 0.0
            tracker.record_trades_batch(d, trades_for_date, b_ret)

        portfolio_summary = tracker.summarize()

        # 7. Overall Performance Metrics
        total_eval = len(all_evaluated_trades)
        wins = sum(1 for t in all_evaluated_trades if t.is_win)
        overall_wr = (wins / total_eval * 100.0) if total_eval > 0 else 0.0
        profit_factor = calculate_profit_factor(all_strat_returns)
        equity_vals = [p.strategy_equity for p in tracker.equity_curve]
        max_dd = calculate_max_drawdown(equity_vals) if equity_vals else 0.0
        sharpe = calculate_approx_sharpe(all_strat_returns)

        notes = [
            f"Evaluated {total_eval} algorithmic candidate signals over holding period {self.config.rebalance_frequency_days}d.",
            f"Strategy Win Rate: {overall_wr:.1f}% vs NEPSE benchmark.",
            f"Maximum Drawdown: {max_dd:.2f}%, Profit Factor: {profit_factor:.2f}.",
        ]

        overall_metrics = StrategyPerformanceMetrics(
            total_candidates_evaluated=total_eval,
            overall_win_rate_pct=round(overall_wr, 2),
            profit_factor=profit_factor,
            max_drawdown_pct=max_dd,
            approx_sharpe_ratio=sharpe,
            horizon_metrics=horizon_metrics_map,
            summary_notes=notes,
        )

        return BacktestReport(
            config=self.config,
            total_signals=total_eval,
            overall_performance=overall_metrics,
            portfolio_simulation=portfolio_summary,
            recent_sample_trades=all_evaluated_trades[-20:],
        )

    def _empty_report(self) -> BacktestReport:
        """Fallback empty report when insufficient data exists."""
        return BacktestReport(
            config=self.config,
            total_signals=0,
            overall_performance=StrategyPerformanceMetrics(
                total_candidates_evaluated=0,
                overall_win_rate_pct=0.0,
                profit_factor=1.0,
                max_drawdown_pct=0.0,
                approx_sharpe_ratio=0.0,
                horizon_metrics={},
                summary_notes=["No historical candidates matched the evaluation criteria in the selected range."],
            ),
            portfolio_simulation=PortfolioSimulationResult(
                initial_capital=self.config.initial_capital,
                final_strategy_equity=self.config.initial_capital,
                final_benchmark_equity=self.config.initial_capital,
                total_strategy_return_pct=0.0,
                total_benchmark_return_pct=0.0,
                total_trades=0,
                winning_trades=0,
                losing_trades=0,
                win_rate_pct=0.0,
            ),
            recent_sample_trades=[],
        )
