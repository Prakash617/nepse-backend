"""Strategies package for quantitative trading signal engine."""

from apps.technical_analysis.strategies.base import (
    BaseStrategy,
    ExitEvaluationResult,
    StrategySignalCandidate,
)
from apps.technical_analysis.strategies.short_term import (
    ShortTermTradingStrategy,
)
from apps.technical_analysis.strategies.swing import (
    SwingTradingStrategy,
)

__all__ = [
    "BaseStrategy",
    "ExitEvaluationResult",
    "StrategySignalCandidate",
    "ShortTermTradingStrategy",
    "SwingTradingStrategy",
]
