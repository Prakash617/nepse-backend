"""Short-Term Trading Strategy Implementation (2-10 Sessions)."""

from __future__ import annotations

from decimal import Decimal
from typing import Any

from apps.securities.models import Security
from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.indicators.types import Candle
from apps.technical_analysis.risk.risk_reward import evaluate_risk_reward
from apps.technical_analysis.strategies.base import (
    BaseStrategy,
    ExitEvaluationResult,
    StrategySignalCandidate,
)
from apps.technical_analysis.strategies.short_term.entry import (
    evaluate_short_term_entry,
)
from apps.technical_analysis.strategies.short_term.exit import (
    check_short_term_exit,
)
from apps.technical_analysis.strategies.short_term.stop_loss import (
    calculate_short_term_stop_loss,
)
from apps.technical_analysis.strategies.short_term.targets import (
    calculate_short_term_targets,
)


class ShortTermTradingStrategy(BaseStrategy):
    """Captures quick momentum swings and breakout moves over 2 to 10 NEPSE sessions."""

    name: str = "Short-Term Trading Strategy"
    strategy_type: str = "short_term"
    min_holding_period: int = 2
    max_holding_period: int = 10

    def __init__(
        self,
        *,
        min_composite_score: float = 65.0,
        min_risk_reward_ratio: float = 1.5,
        max_stop_distance_pct: float = 8.0,
        atr_multiplier: float = 1.5,
    ) -> None:
        self.min_composite_score = min_composite_score
        self.min_risk_reward_ratio = min_risk_reward_ratio
        self.max_stop_distance_pct = max_stop_distance_pct
        self.atr_multiplier = atr_multiplier

    def evaluate_security(
        self,
        security: Security,
        candles: list[Candle],
        indicators: FullIndicatorSet,
        *,
        market_context: dict[str, Any] | None = None,
        sector_context: dict[str, Any] | None = None,
    ) -> StrategySignalCandidate | None:
        """Run short-term evaluation pipeline on completed daily candle."""
        # 1. Entry setup detection
        setup = evaluate_short_term_entry(
            candles=candles,
            indicators=indicators,
            market_context=market_context,
            min_composite_score=self.min_composite_score,
        )
        if setup is None or not setup.is_valid:
            return None

        # 2. Stop-loss calculation
        stop_loss = calculate_short_term_stop_loss(
            candles=candles,
            indicators=indicators,
            entry_price=setup.suggested_entry,
            atr_multiplier=self.atr_multiplier,
        )

        # 3. Target calculations
        nearest_resistance = None
        if len(candles) >= 2:
            prior_highs = [c.high for c in candles[:-1][-50:]]
            if prior_highs:
                max_prior_high = max(prior_highs)
                if max_prior_high > float(setup.suggested_entry):
                    nearest_resistance = max_prior_high

        target_1, target_2 = calculate_short_term_targets(
            entry_price=setup.suggested_entry,
            stop_loss=stop_loss,
            resistance_level=nearest_resistance,
        )

        # 4. Risk / Reward validation
        rr = evaluate_risk_reward(
            entry_price=setup.suggested_entry,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            min_rr_ratio=self.min_risk_reward_ratio,
            max_risk_pct=self.max_stop_distance_pct,
            overhead_resistance=nearest_resistance,
        )
        if not rr.is_valid:
            return None

        signal_date = candles[-1].trading_date

        return StrategySignalCandidate(
            security=security,
            strategy_type=self.strategy_type,
            setup_type=setup.setup_type,
            signal_date=signal_date,
            suggested_entry=setup.suggested_entry,
            entry_zone_low=setup.entry_zone_low,
            entry_zone_high=setup.entry_zone_high,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            risk_per_share=rr.risk_per_share,
            risk_reward_ratio=rr.risk_reward_ratio,
            composite_score=setup.composite_score,
            max_holding_period=self.max_holding_period,
            rationale=setup.rationale,
            metadata={
                **setup.metadata,
                "target_1": float(target_1),
                "target_2": float(target_2) if target_2 else None,
                "stop_loss": float(stop_loss),
                "risk_pct": float(rr.risk_pct),
            },
        )

    def check_exit_conditions(
        self,
        current_candle: Candle,
        entry_price: Decimal,
        stop_loss: Decimal,
        target_1: Decimal,
        target_2: Decimal | None,
        trailing_stop: Decimal | None,
        days_in_trade: int,
        indicators: FullIndicatorSet | None = None,
    ) -> ExitEvaluationResult:
        """Evaluate exit rules for active position."""
        return check_short_term_exit(
            current_candle=current_candle,
            entry_price=entry_price,
            stop_loss=stop_loss,
            target_1=target_1,
            target_2=target_2,
            trailing_stop=trailing_stop,
            days_in_trade=days_in_trade,
            indicators=indicators,
            max_holding_period=self.max_holding_period,
        )
