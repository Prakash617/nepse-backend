"""Historical backtesting and strategy evaluation package."""

from apps.technical_analysis.backtesting.engine import (
    BacktestConfiguration,
    BacktestReport,
    TechnicalBacktestEngine,
)
from apps.technical_analysis.backtesting.metrics import (
    HorizonReturnMetric,
    StrategyPerformanceMetrics,
)
from apps.technical_analysis.backtesting.portfolio import (
    PortfolioEquityPoint,
    PortfolioSimulationResult,
    SimulatedTrade,
)

__all__ = [
    "BacktestConfiguration",
    "BacktestReport",
    "HorizonReturnMetric",
    "PortfolioEquityPoint",
    "PortfolioSimulationResult",
    "SimulatedTrade",
    "StrategyPerformanceMetrics",
    "TechnicalBacktestEngine",
]
