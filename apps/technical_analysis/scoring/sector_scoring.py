"""Sector strength scoring and rotation classification.

Implements the 0 to 100 Sector Strength Score according to Section 7.B:
1. Sector price momentum (25 pts)
2. Sector EMA trend (20 pts)
3. Relative strength against NEPSE (20 pts)
4. Volume participation (15 pts)
5. RSI momentum (10 pts)
6. ADX/trend strength (10 pts)
Total: 100 pts.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.scoring.relative_strength import RelativeStrengthAnalysis


@dataclass(frozen=True)
class SectorStrengthScore:
    """Consolidated sector strength metrics and component breakdown."""

    total_score: float  # 0 to 100
    classification: str # "Strong Trending", "Bullish", "Neutral", "Weakening", "Bearish"
    rotation_stage: str # "leading", "improving", "weakening", "lagging", "emerging"

    price_momentum_score: float     # Max 25
    ema_trend_score: float          # Max 20
    relative_strength_score: float  # Max 20
    volume_score: float             # Max 15
    rsi_score: float                # Max 10
    adx_score: float                # Max 10

    explanation: str
    component_details: dict[str, Any]


def score_sector_strength(
    indicator_set: FullIndicatorSet,
    relative_strength: RelativeStrengthAnalysis,
    *,
    daily_return_pct: float | None = None,
    weekly_return_pct: float | None = None,
    monthly_return_pct: float | None = None,
) -> SectorStrengthScore:
    """Calculate the 0–100 Sector Strength Score."""
    ma = indicator_set.moving_averages
    mom = indicator_set.momentum
    tr = indicator_set.trend
    vol = indicator_set.volume

    # 1. Sector Price Momentum (Max 25 pts)
    # Evaluates daily, weekly (5-session), and monthly (20-session) returns
    pm_points = 0.0
    if daily_return_pct is not None:
        if daily_return_pct >= 1.5:
            pm_points += 6.0
        elif daily_return_pct > 0.0:
            pm_points += 4.0
        elif daily_return_pct > -1.0:
            pm_points += 2.0

    if weekly_return_pct is not None:
        if weekly_return_pct >= 3.0:
            pm_points += 9.0
        elif weekly_return_pct > 0.0:
            pm_points += 6.0
        elif weekly_return_pct > -2.0:
            pm_points += 3.0

    if monthly_return_pct is not None:
        if monthly_return_pct >= 5.0:
            pm_points += 10.0
        elif monthly_return_pct > 0.0:
            pm_points += 7.0
        elif monthly_return_pct > -4.0:
            pm_points += 3.0

    # 2. Sector EMA Trend (Max 20 pts)
    trend_points = 0.0
    if ma.price_above_ema_20 is True:
        trend_points += 5.0
    if ma.price_above_ema_50 is True:
        trend_points += 5.0
    if ma.price_above_sma_200 is True:
        trend_points += 5.0
    if ma.ema_20_above_ema_50 is True:
        trend_points += 3.0
    if ma.ema_20_slope is not None and ma.ema_20_slope > 0:
        trend_points += 2.0

    # 3. Relative Strength Against NEPSE (Max 20 pts)
    rs_points = 0.0
    rs_20 = relative_strength.rs_20.excess_return_pct
    rs_60 = relative_strength.rs_60.excess_return_pct

    if rs_20 is not None:
        if rs_20 >= 5.0:
            rs_points += 12.0
        elif rs_20 > 0.0:
            rs_points += 8.0
        elif rs_20 >= -3.0:
            rs_points += 4.0

    if rs_60 is not None:
        if rs_60 >= 5.0:
            rs_points += 8.0
        elif rs_60 > 0.0:
            rs_points += 5.0
        elif rs_60 >= -5.0:
            rs_points += 2.0

    # 4. Volume Participation (Max 15 pts)
    vol_points = 0.0
    rvol = vol.relative_volume
    if rvol is not None:
        if rvol >= 1.5:
            vol_points += 8.0
        elif rvol >= 1.0:
            vol_points += 6.0
        elif rvol >= 0.7:
            vol_points += 3.0

    if vol.volume_trend == "expanding":
        vol_points += 4.0
    elif vol.volume_trend == "stable":
        vol_points += 2.0

    if vol.price_volume_confirmation == "bullish_confirmation":
        vol_points += 3.0

    # 5. RSI Momentum (Max 10 pts)
    rsi_points = 0.0
    rsi_val = mom.rsi.value
    if rsi_val is not None:
        if 55.0 <= rsi_val <= 70.0:
            rsi_points += 10.0  # Sweet spot
        elif rsi_val > 70.0:
            rsi_points += 7.0   # Strong but slightly overbought
        elif 45.0 <= rsi_val < 55.0:
            rsi_points += 5.0   # Neutral
        elif 35.0 <= rsi_val < 45.0:
            rsi_points += 2.0   # Weak

    # 6. ADX / Trend Strength (Max 10 pts)
    adx_points = 0.0
    if tr.directional_dominance == "bullish":
        adx_points += 4.0
        if tr.trend_strength in ("strong", "very_strong"):
            adx_points += 6.0
        elif tr.trend_strength == "developing":
            adx_points += 4.0
        else:
            adx_points += 2.0
    elif tr.directional_dominance == "neutral":
        adx_points += 2.0

    total = round(pm_points + trend_points + rs_points + vol_points + rsi_points + adx_points, 1)

    # Classification
    if total >= 80.0:
        classification = "Strong Trending"
    elif total >= 65.0:
        classification = "Bullish"
    elif total >= 50.0:
        classification = "Neutral"
    elif total >= 35.0:
        classification = "Weakening"
    else:
        classification = "Bearish"

    # Rotation Stage Identification
    # leading: high score + positive RS
    # improving: moderate score + positive momentum
    # emerging: lower score but volume breakout / RSI turning up
    # weakening: deteriorating score
    # lagging: low score + negative RS
    if total >= 70.0 and (rs_20 is not None and rs_20 > 0):
        stage = "leading"
    elif total >= 50.0 and (weekly_return_pct is not None and weekly_return_pct > 0):
        stage = "improving"
    elif total < 55.0 and vol.is_volume_breakout:
        stage = "emerging"
    elif 35.0 <= total < 50.0:
        stage = "weakening"
    else:
        stage = "lagging"

    explanation = (
        f"Sector strength {total}/100 ({classification}, {stage}). "
        f"Trend points: {trend_points}/20, Momentum: {pm_points}/25, "
        f"Relative Strength: {rs_points}/20, Volume: {vol_points}/15, "
        f"RSI: {rsi_points}/10, ADX: {adx_points}/10."
    )

    return SectorStrengthScore(
        total_score=total,
        classification=classification,
        rotation_stage=stage,
        price_momentum_score=round(pm_points, 1),
        ema_trend_score=round(trend_points, 1),
        relative_strength_score=round(rs_points, 1),
        volume_score=round(vol_points, 1),
        rsi_score=round(rsi_points, 1),
        adx_score=round(adx_points, 1),
        explanation=explanation,
        component_details={
            "daily_return_pct": daily_return_pct,
            "weekly_return_pct": weekly_return_pct,
            "monthly_return_pct": monthly_return_pct,
            "relative_strength_20d": rs_20,
            "relative_strength_60d": rs_60,
            "adx_trend_strength": tr.trend_strength,
            "directional_dominance": tr.directional_dominance,
        },
    )
