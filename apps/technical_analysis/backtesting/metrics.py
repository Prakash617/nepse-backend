"""Performance and risk metrics for technical analysis backtesting and strategy evaluation."""

from __future__ import annotations

import math
from collections.abc import Sequence
from dataclasses import dataclass, field


@dataclass(frozen=True)
class HorizonReturnMetric:
    """Forward return statistics for a specific evaluation horizon (e.g., 5, 10, 20, 60 sessions)."""

    horizon_days: int
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    average_return_pct: float
    median_return_pct: float
    max_return_pct: float
    min_return_pct: float
    benchmark_average_return_pct: float
    excess_return_pct: float  # Strategy return - Benchmark return


@dataclass(frozen=True)
class StrategyPerformanceMetrics:
    """Consolidated quantitative metrics for evaluating technical candidate strategies."""

    total_candidates_evaluated: int
    overall_win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    approx_sharpe_ratio: float
    horizon_metrics: dict[int, HorizonReturnMetric] = field(default_factory=dict)
    summary_notes: list[str] = field(default_factory=list)


def calculate_horizon_metrics(
    horizon_days: int,
    strategy_returns: Sequence[float],
    benchmark_returns: Sequence[float],
) -> HorizonReturnMetric:
    """Calculate directional win-rate, excess return, and dispersion for a specific forward window."""
    n = len(strategy_returns)
    if n == 0:
        return HorizonReturnMetric(
            horizon_days=horizon_days,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            average_return_pct=0.0,
            median_return_pct=0.0,
            max_return_pct=0.0,
            min_return_pct=0.0,
            benchmark_average_return_pct=0.0,
            excess_return_pct=0.0,
        )

    wins = sum(1 for r in strategy_returns if r > 0.0)
    losses = sum(1 for r in strategy_returns if r < 0.0)
    win_rate = (wins / n) * 100.0

    avg_strat = sum(strategy_returns) / n
    sorted_returns = sorted(strategy_returns)
    mid = n // 2
    if n % 2 == 1:
        median_strat = sorted_returns[mid]
    else:
        median_strat = (sorted_returns[mid - 1] + sorted_returns[mid]) / 2.0

    max_strat = max(strategy_returns)
    min_strat = min(strategy_returns)

    avg_bench = sum(benchmark_returns) / len(benchmark_returns) if benchmark_returns else 0.0
    excess = avg_strat - avg_bench

    return HorizonReturnMetric(
        horizon_days=horizon_days,
        total_trades=n,
        winning_trades=wins,
        losing_trades=losses,
        win_rate_pct=round(win_rate, 2),
        average_return_pct=round(avg_strat, 2),
        median_return_pct=round(median_strat, 2),
        max_return_pct=round(max_strat, 2),
        min_return_pct=round(min_strat, 2),
        benchmark_average_return_pct=round(avg_bench, 2),
        excess_return_pct=round(excess, 2),
    )


def calculate_profit_factor(strategy_returns: Sequence[float]) -> float:
    """Calculate ratio of gross profits to gross losses."""
    gross_profit = sum(r for r in strategy_returns if r > 0.0)
    gross_loss = abs(sum(r for r in strategy_returns if r < 0.0))

    if gross_loss == 0.0:
        return round(gross_profit, 2) if gross_profit > 0.0 else 1.0
    return round(gross_profit / gross_loss, 2)


def calculate_max_drawdown(equity_curve: Sequence[float]) -> float:
    """Calculate maximum peak-to-trough decline as a percentage."""
    if len(equity_curve) < 2:
        return 0.0

    peak = equity_curve[0]
    max_dd = 0.0

    for value in equity_curve:
        if value > peak:
            peak = value
        dd = (peak - value) / peak if peak > 0.0 else 0.0
        if dd > max_dd:
            max_dd = dd

    return round(max_dd * 100.0, 2)


def calculate_approx_sharpe(returns: Sequence[float], risk_free_rate_pct: float = 6.0) -> float:
    """Calculate annualized Sharpe ratio approximation for daily trading returns."""
    if len(returns) < 2:
        return 0.0

    n = len(returns)
    mean_ret = sum(returns) / n
    variance = sum((r - mean_ret) ** 2 for r in returns) / (n - 1)
    std_dev = math.sqrt(variance)

    if std_dev == 0.0:
        return 0.0

    daily_rf = risk_free_rate_pct / 240.0  # Approx 240 NEPSE trading sessions/year
    excess_daily = mean_ret - daily_rf
    # Annualized Sharpe = (Mean Excess Daily / Daily Std Dev) * sqrt(240)
    annualized_sharpe = (excess_daily / std_dev) * math.sqrt(240.0)
    return round(annualized_sharpe, 2)
