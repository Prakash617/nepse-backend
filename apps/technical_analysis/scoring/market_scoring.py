"""Market condition scoring engine.

Evaluates overall NEPSE market condition across trend, momentum,
directional trend strength, and market breadth.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.technical_analysis.indicators import FullIndicatorSet


@dataclass(frozen=True)
class MarketBreadth:
    """Market-wide constituent breadth statistics."""

    total_eligible: int
    advancing_count: int
    declining_count: int
    unchanged_count: int
    advance_decline_ratio: float | None

    stocks_above_ema_20: int
    pct_above_ema_20: float | None

    stocks_above_ema_50: int
    pct_above_ema_50: float | None

    stocks_above_sma_200: int
    pct_above_sma_200: float | None


@dataclass(frozen=True)
class MarketConditionScore:
    """Consolidated market condition rating and component points."""

    total_score: float  # 0 to 100
    condition: str      # "Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish"
    trend_score: float      # Max 30
    momentum_score: float   # Max 25
    adx_score: float        # Max 20
    breadth_score: float    # Max 25
    summary_explanation: str
    component_details: dict[str, Any]


def score_market_condition(
    indicator_set: FullIndicatorSet,
    breadth: MarketBreadth,
) -> MarketConditionScore:
    """Calculate the multi-factor market condition score.

    Weights:
    1. Trend: 30 pts
    2. Momentum: 25 pts
    3. ADX & Direction: 20 pts
    4. Market Breadth: 25 pts
    Total: 100 pts.
    """
    ma = indicator_set.moving_averages
    mom = indicator_set.momentum
    tr = indicator_set.trend

    # 1. Trend Direction Score (Max 30 pts)
    trend_points = 0.0
    if ma.price_above_ema_20 is True:
        trend_points += 6.0
    if ma.price_above_ema_50 is True:
        trend_points += 6.0
    if ma.price_above_sma_200 is True:
        trend_points += 8.0
    if ma.ema_20_above_ema_50 is True:
        trend_points += 5.0
    if ma.ema_20_slope is not None and ma.ema_20_slope > 0:
        trend_points += 5.0

    # 2. Momentum Score (Max 25 pts)
    momentum_points = 0.0
    rsi_val = mom.rsi.value
    if rsi_val is not None:
        if 50.0 <= rsi_val <= 70.0:
            momentum_points += 12.0  # Ideal bullish momentum
        elif rsi_val > 70.0:
            momentum_points += 9.0   # Strong but overbought
        elif 40.0 <= rsi_val < 50.0:
            momentum_points += 5.0   # Neutral/mild weakness
        else:
            momentum_points += 2.0   # Oversold/heavy selling

    macd = mom.macd
    if macd.is_above_zero is True:
        momentum_points += 7.0
    if macd.is_above_signal is True:
        momentum_points += 6.0

    # 3. ADX & Directional Strength Score (Max 20 pts)
    adx_points = 0.0
    if tr.directional_dominance == "bullish":
        adx_points += 10.0
        # If bullish and trend is strong, award bonus strength
        if tr.trend_strength in ("strong", "very_strong"):
            adx_points += 10.0
        elif tr.trend_strength == "developing":
            adx_points += 6.0
        else:
            adx_points += 3.0
    elif tr.directional_dominance == "neutral":
        adx_points += 5.0
    else:  # bearish dominance
        if tr.trend_strength in ("weak", "developing"):
            adx_points += 3.0  # bear trend is at least weak

    # 4. Market Breadth Score (Max 25 pts)
    breadth_points = 0.0
    if breadth.pct_above_ema_20 is not None:
        if breadth.pct_above_ema_20 >= 60.0:
            breadth_points += 7.0
        elif breadth.pct_above_ema_20 >= 45.0:
            breadth_points += 4.0

    if breadth.pct_above_ema_50 is not None:
        if breadth.pct_above_ema_50 >= 55.0:
            breadth_points += 6.0
        elif breadth.pct_above_ema_50 >= 40.0:
            breadth_points += 3.0

    if breadth.pct_above_sma_200 is not None:
        if breadth.pct_above_sma_200 >= 50.0:
            breadth_points += 6.0
        elif breadth.pct_above_sma_200 >= 35.0:
            breadth_points += 3.0

    if breadth.advance_decline_ratio is not None:
        if breadth.advance_decline_ratio >= 1.5:
            breadth_points += 6.0
        elif breadth.advance_decline_ratio >= 1.0:
            breadth_points += 4.0
        elif breadth.advance_decline_ratio >= 0.7:
            breadth_points += 2.0

    total = round(trend_points + momentum_points + adx_points + breadth_points, 1)

    # Classify overall market condition
    if total >= 80.0:
        cond = "Strong Bullish"
        explanation = "Market exhibits broad-based institutional strength with price above long-term averages, bullish momentum, expanding trend strength, and strong market breadth."
    elif total >= 65.0:
        cond = "Bullish"
        explanation = "Market trend is constructive with price above short/medium-term moving averages and positive market breadth confirmation."
    elif total >= 45.0:
        cond = "Neutral"
        explanation = "Market is in consolidation or mixed phase without clear directional dominance across breadth and moving averages."
    elif total >= 30.0:
        cond = "Bearish"
        explanation = "Market structure is deteriorating with price below key moving averages and negative advance-decline participation."
    else:
        cond = "Strong Bearish"
        explanation = "Market is under heavy selling pressure with negative momentum, price below long-term moving averages, and severe breadth breakdown."

    return MarketConditionScore(
        total_score=total,
        condition=cond,
        trend_score=round(trend_points, 1),
        momentum_score=round(momentum_points, 1),
        adx_score=round(adx_points, 1),
        breadth_score=round(breadth_points, 1),
        summary_explanation=explanation,
        component_details={
            "price_above_ema_20": ma.price_above_ema_20,
            "price_above_ema_50": ma.price_above_ema_50,
            "price_above_sma_200": ma.price_above_sma_200,
            "rsi_value": rsi_val,
            "macd_above_zero": macd.is_above_zero,
            "adx_trend_strength": tr.trend_strength,
            "directional_dominance": tr.directional_dominance,
            "pct_above_ema_20": breadth.pct_above_ema_20,
            "advance_decline_ratio": breadth.advance_decline_ratio,
        },
    )
