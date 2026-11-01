"""Chronological, event-driven strategy backtesting engine with realistic NEPSE execution."""

from __future__ import annotations

import datetime
import logging
from collections import defaultdict
from dataclasses import dataclass, field
from decimal import Decimal
from typing import Any

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.securities.models import Security
from apps.technical_analysis.backtesting.costs import (
    calculate_nepse_buy_costs,
    calculate_nepse_sell_costs,
)
from apps.technical_analysis.backtesting.metrics import (
    calculate_approx_sharpe,
    calculate_max_drawdown,
    calculate_profit_factor,
)
from apps.technical_analysis.backtesting.portfolio import PortfolioEquityPoint
from apps.technical_analysis.indicators import calculate_all_indicators
from apps.technical_analysis.indicators.types import Candle, candles_from_records
from apps.technical_analysis.risk.position_sizing import calculate_position_size
from apps.technical_analysis.strategies.short_term import ShortTermTradingStrategy
from apps.technical_analysis.strategies.swing import SwingTradingStrategy

logger = logging.getLogger(__name__)


@dataclass
class SimulatedStrategyTrade:
    """Historical trade executed during backtest simulation."""

    security_id: int
    symbol: str
    strategy_type: str
    setup_type: str
    signal_date: datetime.date
    entry_date: datetime.date
    exit_date: datetime.date
    shares: int
    entry_price: float
    exit_price: float
    stop_loss: float
    target_1: float
    target_2: float | None
    exit_reason: str
    holding_period_days: int
    gross_pnl: float
    transaction_fees: float
    cgt_paid: float
    net_pnl: float
    net_return_pct: float
    is_win: bool = False

    def __post_init__(self) -> None:
        self.is_win = self.net_pnl > 0.0


@dataclass
class StrategyBacktestConfig:
    """Configuration options for historical strategy backtesting."""

    strategy_type: str  # "short_term" or "swing"
    start_date: datetime.date
    end_date: datetime.date
    initial_capital: float = 1000000.0
    risk_per_trade_pct: float = 1.0
    max_portfolio_allocation_pct: float = 20.0
    min_composite_score: float = 65.0
    include_costs: bool = True
    include_cgt: bool = True


@dataclass
class StrategyBacktestResult:
    """Complete performance results of strategy backtest."""

    config: StrategyBacktestConfig
    initial_capital: float
    final_equity: float
    total_net_return_pct: float
    total_gross_return_pct: float
    benchmark_return_pct: float
    excess_return_pct: float
    total_trades: int
    winning_trades: int
    losing_trades: int
    win_rate_pct: float
    profit_factor: float
    max_drawdown_pct: float
    sharpe_ratio: float
    average_trade_return_pct: float
    average_holding_days: float
    total_fees_paid: float
    trades: list[SimulatedStrategyTrade] = field(default_factory=list)
    equity_curve: list[PortfolioEquityPoint] = field(default_factory=list)


class StrategyBacktestEngine:
    """Simulates point-in-time daily execution for Short-Term or Swing strategies."""

    def __init__(self, config: StrategyBacktestConfig) -> None:
        self.config = config
        self.strategy = (
            ShortTermTradingStrategy(min_composite_score=config.min_composite_score)
            if config.strategy_type == "short_term"
            else SwingTradingStrategy(min_composite_score=config.min_composite_score)
        )

    def run(self) -> StrategyBacktestResult:
        """Run historical chronological backtest."""
        logger.info(
            "Starting %s strategy backtest from %s to %s",
            self.config.strategy_type,
            self.config.start_date,
            self.config.end_date,
        )

        # 1. Distinct trading dates
        trading_dates = list(
            DailyPrice.objects.filter(
                trading_date__gte=self.config.start_date,
                trading_date__lte=self.config.end_date,
            )
            .values_list("trading_date", flat=True)
            .distinct()
            .order_by("trading_date")
        )

        if not trading_dates:
            return self._empty_result()

        # Benchmark NEPSE Index prices
        nepse_idx = MarketIndex.objects.filter(nepse_id=58).first()
        bench_prices: dict[datetime.date, float] = {}
        if nepse_idx:
            for snap in IndexSnapshot.objects.filter(
                index=nepse_idx,
                trading_date__gte=self.config.start_date,
                trading_date__lte=self.config.end_date,
            ).values("trading_date", "close"):
                if snap["close"] is not None:
                    bench_prices[snap["trading_date"]] = float(snap["close"])

        # Fetch historical daily prices with pre-buffer for indicator calculation
        buffer_start = self.config.start_date - datetime.timedelta(days=120)
        all_prices = list(
            DailyPrice.objects.filter(
                trading_date__gte=buffer_start,
                trading_date__lte=self.config.end_date,
            )
            .order_by("security_id", "trading_date")
            .values("security_id", "trading_date", "open", "high", "low", "close", "volume", "turnover")
        )

        prices_by_sec_and_date: dict[int, dict[datetime.date, dict[str, Any]]] = defaultdict(dict)
        dates_by_sec: dict[int, list[datetime.date]] = defaultdict(list)
        for p in all_prices:
            sec_id = p["security_id"]
            d = p["trading_date"]
            prices_by_sec_and_date[sec_id][d] = p
            dates_by_sec[sec_id].append(d)

        sec_map = {s.id: s for s in Security.objects.filter(id__in=prices_by_sec_and_date.keys())}

        # Simulation State
        cash = self.config.initial_capital
        peak_equity = self.config.initial_capital
        bench_start_price = next((bench_prices[d] for d in trading_dates if d in bench_prices), 100.0)
        bench_equity = self.config.initial_capital

        active_positions: list[dict[str, Any]] = []
        pending_orders: list[dict[str, Any]] = []
        completed_trades: list[SimulatedStrategyTrade] = []
        equity_curve: list[PortfolioEquityPoint] = []
        total_fees = 0.0

        for _day_idx, current_date in enumerate(trading_dates):
            # A. Process Pending Orders -> Attempt Fills on Current Date Open
            unfilled_orders: list[dict[str, Any]] = []
            for order in pending_orders:
                sec_id = order["security_id"]
                p = prices_by_sec_and_date[sec_id].get(current_date)
                if not p or not p["open"]:
                    unfilled_orders.append(order)
                    continue

                c_open = float(p["open"])
                suggested_entry = float(order["suggested_entry"])
                zone_high = float(order["entry_zone_high"])
                zone_low = float(order["entry_zone_low"])
                stop_loss = float(order["stop_loss"])

                # Invalidation checks
                if c_open > zone_high * 1.03 or c_open <= stop_loss:
                    continue  # Invalidated setup

                # Fill condition
                can_fill = (c_open <= zone_high)
                if can_fill:
                    fill_price = c_open if (zone_low <= c_open <= zone_high) else suggested_entry
                    # Position sizing
                    sizing = calculate_position_size(
                        portfolio_capital=cash,
                        entry_price=fill_price,
                        stop_loss=stop_loss,
                        risk_percentage=self.config.risk_per_trade_pct,
                        max_portfolio_allocation_pct=self.config.max_portfolio_allocation_pct,
                    )
                    if sizing.is_valid and sizing.suggested_shares >= 10:
                        shares = sizing.suggested_shares
                        turnover = shares * fill_price
                        buy_costs = calculate_nepse_buy_costs(turnover) if self.config.include_costs else None
                        fee = float(buy_costs.total_costs) if buy_costs else 0.0
                        total_cost = turnover + fee

                        if cash >= total_cost:
                            cash -= total_cost
                            total_fees += fee
                            active_positions.append({
                                "security_id": sec_id,
                                "symbol": order["symbol"],
                                "strategy_type": order["strategy_type"],
                                "setup_type": order["setup_type"],
                                "signal_date": order["signal_date"],
                                "entry_date": current_date,
                                "shares": shares,
                                "entry_price": fill_price,
                                "buy_turnover": turnover,
                                "buy_fees": fee,
                                "stop_loss": stop_loss,
                                "trailing_stop": None,
                                "target_1": float(order["target_1"]),
                                "target_2": float(order["target_2"]) if order["target_2"] else None,
                                "days_in_trade": 1,
                            })

            pending_orders = unfilled_orders

            # B. Evaluate Active Positions against Current Day High/Low Range
            remaining_positions: list[dict[str, Any]] = []
            for pos in active_positions:
                sec_id = pos["security_id"]
                p = prices_by_sec_and_date[sec_id].get(current_date)
                if not p or not p["close"]:
                    pos["days_in_trade"] += 1
                    remaining_positions.append(pos)
                    continue

                c_candle = Candle(
                    trading_date=current_date,
                    open=float(p["open"] or p["close"]),
                    high=float(p["high"] or p["close"]),
                    low=float(p["low"] or p["close"]),
                    close=float(p["close"]),
                    volume=float(p["volume"] or 0.0),
                )

                exit_res = self.strategy.check_exit_conditions(
                    current_candle=c_candle,
                    entry_price=Decimal(str(pos["entry_price"])),
                    stop_loss=Decimal(str(pos["stop_loss"])),
                    target_1=Decimal(str(pos["target_1"])),
                    target_2=Decimal(str(pos["target_2"])) if pos["target_2"] else None,
                    trailing_stop=Decimal(str(pos["trailing_stop"])) if pos["trailing_stop"] else None,
                    days_in_trade=pos["days_in_trade"],
                )

                if exit_res.should_exit and exit_res.exit_price is not None:
                    exit_price = float(exit_res.exit_price)
                    shares = pos["shares"]
                    sell_turnover = shares * exit_price
                    sell_costs = (
                        calculate_nepse_sell_costs(pos["buy_turnover"], sell_turnover)
                        if self.config.include_costs
                        else None
                    )
                    sell_fees = float(sell_costs.total_costs) if sell_costs else 0.0
                    cgt = float(sell_costs.capital_gains_tax) if sell_costs and self.config.include_cgt else 0.0
                    total_fees += sell_fees

                    net_proceeds = sell_turnover - sell_fees
                    cash += net_proceeds

                    gross_pnl = sell_turnover - pos["buy_turnover"]
                    net_pnl = net_proceeds - (pos["buy_turnover"] + pos["buy_fees"])
                    ret_pct = (net_pnl / (pos["buy_turnover"] + pos["buy_fees"])) * 100.0

                    completed_trades.append(
                        SimulatedStrategyTrade(
                            security_id=sec_id,
                            symbol=pos["symbol"],
                            strategy_type=pos["strategy_type"],
                            setup_type=pos["setup_type"],
                            signal_date=pos["signal_date"],
                            entry_date=pos["entry_date"],
                            exit_date=current_date,
                            shares=shares,
                            entry_price=pos["entry_price"],
                            exit_price=exit_price,
                            stop_loss=pos["stop_loss"],
                            target_1=pos["target_1"],
                            target_2=pos["target_2"],
                            exit_reason=exit_res.exit_reason or "Exit triggered",
                            holding_period_days=pos["days_in_trade"],
                            gross_pnl=round(gross_pnl, 2),
                            transaction_fees=round(pos["buy_fees"] + sell_fees - cgt, 2),
                            cgt_paid=round(cgt, 2),
                            net_pnl=round(net_pnl, 2),
                            net_return_pct=round(ret_pct, 2),
                        )
                    )
                else:
                    if exit_res.updated_trailing_stop is not None:
                        pos["trailing_stop"] = float(exit_res.updated_trailing_stop)
                    pos["days_in_trade"] += 1
                    remaining_positions.append(pos)

            active_positions = remaining_positions

            # C. Generate Signals on Completed Session T Close
            for sec_id, d_map in prices_by_sec_and_date.items():
                if current_date not in d_map:
                    continue

                # Filter candles up to current_date
                sec_dates = [d for d in dates_by_sec[sec_id] if d <= current_date]
                if len(sec_dates) < 25:
                    continue

                sec_records = [d_map[d] for d in sec_dates[-60:]]
                candles = candles_from_records(sec_records)
                if not candles or candles[-1].trading_date != current_date:
                    continue

                try:
                    indicators = calculate_all_indicators(candles)
                except Exception:
                    continue

                sec = sec_map.get(sec_id)
                if not sec:
                    continue

                candidate = self.strategy.evaluate_security(
                    security=sec,
                    candles=candles,
                    indicators=indicators,
                )
                if candidate is not None:
                    pending_orders.append({
                        "security_id": sec.id,
                        "symbol": sec.symbol,
                        "strategy_type": candidate.strategy_type,
                        "setup_type": candidate.setup_type,
                        "signal_date": current_date,
                        "suggested_entry": candidate.suggested_entry,
                        "entry_zone_low": candidate.entry_zone_low,
                        "entry_zone_high": candidate.entry_zone_high,
                        "stop_loss": candidate.stop_loss,
                        "target_1": candidate.target_1,
                        "target_2": candidate.target_2,
                    })

            # D. Mark-to-Market Portfolio Equity
            open_position_equity = sum(
                pos["shares"] * float(prices_by_sec_and_date[pos["security_id"]].get(current_date, {}).get("close", pos["entry_price"]))
                for pos in active_positions
            )
            total_equity = cash + open_position_equity
            if total_equity > peak_equity:
                peak_equity = total_equity

            dd = ((peak_equity - total_equity) / peak_equity) * 100.0 if peak_equity > 0 else 0.0

            # Benchmark equity
            if current_date in bench_prices and bench_start_price > 0:
                bench_mult = bench_prices[current_date] / bench_start_price
                bench_equity = self.config.initial_capital * bench_mult

            equity_curve.append(
                PortfolioEquityPoint(
                    date=current_date,
                    strategy_equity=round(total_equity, 2),
                    benchmark_equity=round(bench_equity, 2),
                    drawdown_pct=round(dd, 2),
                    active_positions_count=len(active_positions),
                )
            )

        # Performance summary metrics
        final_equity = equity_curve[-1].strategy_equity if equity_curve else self.config.initial_capital
        total_net_ret = ((final_equity - self.config.initial_capital) / self.config.initial_capital) * 100.0
        final_bench = equity_curve[-1].benchmark_equity if equity_curve else self.config.initial_capital
        total_bench_ret = ((final_bench - self.config.initial_capital) / self.config.initial_capital) * 100.0

        n_trades = len(completed_trades)
        wins = sum(1 for t in completed_trades if t.is_win)
        losses = sum(1 for t in completed_trades if not t.is_win)
        win_rate = (wins / n_trades * 100.0) if n_trades > 0 else 0.0

        all_returns = [t.net_return_pct for t in completed_trades]
        avg_ret = (sum(all_returns) / n_trades) if n_trades > 0 else 0.0
        avg_holding = (sum(t.holding_period_days for t in completed_trades) / n_trades) if n_trades > 0 else 0.0

        profit_fac = calculate_profit_factor(all_returns) if all_returns else 1.0
        equity_values = [p.strategy_equity for p in equity_curve]
        max_dd = calculate_max_drawdown(equity_values) if equity_values else 0.0
        sharpe = calculate_approx_sharpe(all_returns) if len(all_returns) >= 2 else 0.0

        gross_gains = sum(t.gross_pnl for t in completed_trades)
        total_gross_ret = (gross_gains / self.config.initial_capital) * 100.0

        return StrategyBacktestResult(
            config=self.config,
            initial_capital=self.config.initial_capital,
            final_equity=round(final_equity, 2),
            total_net_return_pct=round(total_net_ret, 2),
            total_gross_return_pct=round(total_gross_ret, 2),
            benchmark_return_pct=round(total_bench_ret, 2),
            excess_return_pct=round(total_net_ret - total_bench_ret, 2),
            total_trades=n_trades,
            winning_trades=wins,
            losing_trades=losses,
            win_rate_pct=round(win_rate, 2),
            profit_factor=round(profit_fac, 2),
            max_drawdown_pct=round(max_dd, 2),
            sharpe_ratio=round(sharpe, 2),
            average_trade_return_pct=round(avg_ret, 2),
            average_holding_days=round(avg_holding, 1),
            total_fees_paid=round(total_fees, 2),
            trades=completed_trades,
            equity_curve=equity_curve,
        )

    def _empty_result(self) -> StrategyBacktestResult:
        return StrategyBacktestResult(
            config=self.config,
            initial_capital=self.config.initial_capital,
            final_equity=self.config.initial_capital,
            total_net_return_pct=0.0,
            total_gross_return_pct=0.0,
            benchmark_return_pct=0.0,
            excess_return_pct=0.0,
            total_trades=0,
            winning_trades=0,
            losing_trades=0,
            win_rate_pct=0.0,
            profit_factor=0.0,
            max_drawdown_pct=0.0,
            sharpe_ratio=0.0,
            average_trade_return_pct=0.0,
            average_holding_days=0.0,
            total_fees_paid=0.0,
        )
