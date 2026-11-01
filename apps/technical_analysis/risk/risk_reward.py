"""Risk/Reward evaluation and trade feasibility validation for trading strategies."""

from __future__ import annotations

from dataclasses import dataclass
from decimal import Decimal


@dataclass(frozen=True)
class RiskRewardAssessment:
    """Output of risk-reward ratio evaluation."""

    entry_price: Decimal
    stop_loss: Decimal
    target_1: Decimal
    target_2: Decimal | None
    risk_per_share: Decimal
    risk_pct: Decimal
    reward_target_1: Decimal
    reward_target_2: Decimal | None
    risk_reward_ratio: Decimal
    is_valid: bool
    rejection_reason: str | None = None


def evaluate_risk_reward(
    entry_price: Decimal | float,
    stop_loss: Decimal | float,
    target_1: Decimal | float,
    target_2: Decimal | float | None = None,
    *,
    min_rr_ratio: float = 1.5,
    max_risk_pct: float = 8.0,
    min_risk_pct: float = 0.5,
    overhead_resistance: Decimal | float | None = None,
) -> RiskRewardAssessment:
    """Evaluate and validate risk-reward parameters for a candidate long trade.

    Args:
        entry_price: Proposed entry price.
        stop_loss: Proposed structural or ATR stop-loss level.
        target_1: First profit target.
        target_2: Optional second profit target.
        min_rr_ratio: Minimum acceptable reward-to-risk ratio (Target 1 / Risk).
        max_risk_pct: Maximum acceptable stop-loss distance percentage.
        min_risk_pct: Minimum sensible stop distance percentage (to prevent unrealistic stops).
        overhead_resistance: Optional nearby horizontal resistance level.

    Returns:
        RiskRewardAssessment with validation status and calculated metrics.
    """
    entry = Decimal(str(round(float(entry_price), 2)))
    stop = Decimal(str(round(float(stop_loss), 2)))
    t1 = Decimal(str(round(float(target_1), 2)))
    t2 = Decimal(str(round(float(target_2), 2))) if target_2 is not None else None

    # Fundamental sanity check: stop must be below entry, target must be above entry
    if stop >= entry:
        return RiskRewardAssessment(
            entry_price=entry,
            stop_loss=stop,
            target_1=t1,
            target_2=t2,
            risk_per_share=Decimal("0.00"),
            risk_pct=Decimal("0.00"),
            reward_target_1=Decimal("0.00"),
            reward_target_2=None,
            risk_reward_ratio=Decimal("0.00"),
            is_valid=False,
            rejection_reason=f"Stop loss ({stop}) must be below entry price ({entry}).",
        )

    if t1 <= entry:
        return RiskRewardAssessment(
            entry_price=entry,
            stop_loss=stop,
            target_1=t1,
            target_2=t2,
            risk_per_share=Decimal("0.00"),
            risk_pct=Decimal("0.00"),
            reward_target_1=Decimal("0.00"),
            reward_target_2=None,
            risk_reward_ratio=Decimal("0.00"),
            is_valid=False,
            rejection_reason=f"Target 1 ({t1}) must be above entry price ({entry}).",
        )

    risk_per_share = entry - stop
    risk_pct = Decimal(str(round(float(risk_per_share / entry) * 100.0, 2)))
    reward_t1 = t1 - entry
    reward_t2 = (t2 - entry) if t2 is not None else None

    rr_ratio = Decimal(str(round(float(reward_t1 / risk_per_share), 2)))

    # Constraint 1: Maximum stop distance
    if float(risk_pct) > max_risk_pct:
        return RiskRewardAssessment(
            entry_price=entry,
            stop_loss=stop,
            target_1=t1,
            target_2=t2,
            risk_per_share=risk_per_share,
            risk_pct=risk_pct,
            reward_target_1=reward_t1,
            reward_target_2=reward_t2,
            risk_reward_ratio=rr_ratio,
            is_valid=False,
            rejection_reason=(
                f"Stop loss distance of {risk_pct}% exceeds maximum permitted threshold of {max_risk_pct}%."
            ),
        )

    # Constraint 2: Minimum stop distance
    if float(risk_pct) < min_risk_pct:
        return RiskRewardAssessment(
            entry_price=entry,
            stop_loss=stop,
            target_1=t1,
            target_2=t2,
            risk_per_share=risk_per_share,
            risk_pct=risk_pct,
            reward_target_1=reward_t1,
            reward_target_2=reward_t2,
            risk_reward_ratio=rr_ratio,
            is_valid=False,
            rejection_reason=(
                f"Stop loss distance of {risk_pct}% is too tight (minimum: {min_risk_pct}%)."
            ),
        )

    # Constraint 3: Minimum reward-to-risk ratio
    if float(rr_ratio) < min_rr_ratio:
        return RiskRewardAssessment(
            entry_price=entry,
            stop_loss=stop,
            target_1=t1,
            target_2=t2,
            risk_per_share=risk_per_share,
            risk_pct=risk_pct,
            reward_target_1=reward_t1,
            reward_target_2=reward_t2,
            risk_reward_ratio=rr_ratio,
            is_valid=False,
            rejection_reason=(
                f"Reward-to-risk ratio of {rr_ratio} is below required minimum of {min_rr_ratio}."
            ),
        )

    # Constraint 4: Resistance conflict
    if overhead_resistance is not None:
        res = Decimal(str(round(float(overhead_resistance), 2)))
        # If immediate resistance is closer than Target 1
        if entry < res < t1:
            return RiskRewardAssessment(
                entry_price=entry,
                stop_loss=stop,
                target_1=t1,
                target_2=t2,
                risk_per_share=risk_per_share,
                risk_pct=risk_pct,
                reward_target_1=reward_t1,
                reward_target_2=reward_t2,
                risk_reward_ratio=rr_ratio,
                is_valid=False,
                rejection_reason=(
                    f"Overhead resistance at {res} blocks Target 1 ({t1})."
                ),
            )

    return RiskRewardAssessment(
        entry_price=entry,
        stop_loss=stop,
        target_1=t1,
        target_2=t2,
        risk_per_share=risk_per_share,
        risk_pct=risk_pct,
        reward_target_1=reward_t1,
        reward_target_2=reward_t2,
        risk_reward_ratio=rr_ratio,
        is_valid=True,
    )
