"""Individual stock technical scoring and signal generation.

Evaluates an individual stock's technical profile across 6 key modules:
1. Trend Direction (30 pts)
2. Momentum (20 pts)
3. Volume Participation (15 pts)
4. Relative Strength vs Market & Sector (15 pts)
5. Breakout & Price Structure (10 pts)
6. Risk & Volatility Stability (10 pts)
Total: 100 points.

Generates bullish signals, bearish signals, cautionary risk warnings,
and research classifications.
"""

from __future__ import annotations

from dataclasses import dataclass
from typing import Any

from apps.technical_analysis.indicators import FullIndicatorSet
from apps.technical_analysis.scoring.relative_strength import RelativeStrengthAnalysis


@dataclass(frozen=True)
class StockTechnicalScore:
    """Consolidated technical evaluation for a single security."""

    total_score: float  # 0 to 100
    classification: str # "Strong Technical Candidate", "Bullish Candidate", "Emerging Candidate", "Neutral / Watchlist", "Weakening", "Bearish"

    trend_score: float             # Max 30
    momentum_score: float          # Max 20
    volume_score: float            # Max 15
    relative_strength_score: float # Max 15
    breakout_score: float          # Max 10
    risk_score: float              # Max 10

    bullish_signals: list[str]
    bearish_signals: list[str]
    warnings: list[str]

    component_details: dict[str, Any]


def score_stock_technical(
    indicator_set: FullIndicatorSet,
    rs_market: RelativeStrengthAnalysis,
    rs_sector: RelativeStrengthAnalysis,
    *,
    is_sector_strong: bool = False,
) -> StockTechnicalScore:
    """Compute the multi-factor Stock Technical Score (0 to 100)."""
    ma = indicator_set.moving_averages
    mom = indicator_set.momentum
    tr = indicator_set.trend
    vol = indicator_set.volume
    struct = indicator_set.price_structure
    volat = indicator_set.volatility

    bullish_signals: list[str] = []
    bearish_signals: list[str] = []
    warnings: list[str] = []

    # --------------------------------------------------------------------------
    # 1. Trend Direction Score (Max 30 pts)
    # --------------------------------------------------------------------------
    trend_pts = 0.0
    if ma.price_above_ema_20 is True:
        trend_pts += 5.0
        bullish_signals.append("Price trading above 20-day EMA")
    elif ma.price_above_ema_20 is False:
        bearish_signals.append("Price trading below 20-day EMA")

    if ma.ema_20_above_ema_50 is True:
        trend_pts += 7.0
        bullish_signals.append("20-day EMA above 50-day EMA (short-term uptrend)")
    elif ma.ema_20_above_ema_50 is False:
        bearish_signals.append("20-day EMA below 50-day EMA (short-term downtrend)")

    if ma.price_above_sma_200 is True:
        trend_pts += 8.0
        bullish_signals.append("Price above 200-day SMA (long-term uptrend)")
    elif ma.price_above_sma_200 is False:
        bearish_signals.append("Price below 200-day SMA (long-term downtrend)")
        warnings.append("Trading below 200-day SMA")

    if ma.ema_50_above_ema_200 is True:
        trend_pts += 5.0
    if ma.ema_20_slope is not None and ma.ema_20_slope > 0:
        trend_pts += 5.0

    if ma.golden_cross:
        bullish_signals.append("Golden Cross confirmed (50 EMA crossed above 200 EMA)")
    if ma.death_cross:
        bearish_signals.append("Death Cross confirmed (50 EMA crossed below 200 EMA)")
        warnings.append("Recent Death Cross on moving averages")

    # ADX trend-strength confirmation
    if tr.adx is not None:
        if tr.trend_strength in ("strong", "very_strong") and trend_pts >= 15.0:
            bullish_signals.append(f"Trend confirmed by strong ADX ({tr.adx})")
        elif tr.trend_strength == "weak" and trend_pts >= 15.0:
            warnings.append(f"Trend strength is weak/choppy (ADX {tr.adx})")
        bearish_signals.append("Death Cross confirmed (50 EMA crossed below 200 EMA)")
        warnings.append("Recent Death Cross on moving averages")

    # --------------------------------------------------------------------------
    # 2. Momentum Score (Max 20 pts)
    # --------------------------------------------------------------------------
    mom_pts = 0.0
    rsi = mom.rsi
    if rsi.value is not None:
        if 50.0 <= rsi.value <= 70.0:
            mom_pts += 8.0
            bullish_signals.append(f"RSI {rsi.value} in prime bullish momentum zone")
        elif rsi.value > 70.0:
            mom_pts += 5.0
            warnings.append(f"RSI {rsi.value} is overbought (> 70)")
        elif 40.0 <= rsi.value < 50.0:
            mom_pts += 3.0
        else:
            bearish_signals.append(f"RSI {rsi.value} shows weak/oversold momentum")

        if rsi.bullish_divergence:
            mom_pts += 2.0
            bullish_signals.append("Bullish RSI divergence detected")
        if rsi.bearish_divergence:
            warnings.append("Bearish RSI divergence detected")

    macd = mom.macd
    if macd.is_above_zero is True:
        mom_pts += 5.0
        bullish_signals.append("MACD line above zero")
    elif macd.is_above_zero is False:
        bearish_signals.append("MACD line below zero")

    if macd.is_above_signal is True:
        mom_pts += 5.0
    if macd.crossover == "bullish_crossover":
        mom_pts += 2.0
        bullish_signals.append("Bullish MACD crossover")
    elif macd.crossover == "bearish_crossover":
        bearish_signals.append("Bearish MACD crossover")

    mom_pts = min(20.0, mom_pts)

    # --------------------------------------------------------------------------
    # 3. Volume Participation Score (Max 15 pts)
    # --------------------------------------------------------------------------
    vol_pts = 0.0
    rvol = vol.relative_volume
    if rvol is not None:
        if rvol >= 1.5:
            vol_pts += 7.0
            bullish_signals.append(f"Unusual high trading volume ({rvol}x 20-day average)")
        elif rvol >= 1.0:
            vol_pts += 5.0
        elif rvol >= 0.7:
            vol_pts += 3.0
        else:
            warnings.append(f"Low relative volume ({rvol}x 20-day average)")

    if vol.volume_trend == "expanding":
        vol_pts += 4.0
    elif vol.volume_trend == "stable":
        vol_pts += 2.0

    if vol.price_volume_confirmation == "bullish_confirmation":
        vol_pts += 4.0
        bullish_signals.append("Price advance confirmed by above-average volume")
    elif vol.price_volume_confirmation == "bearish_confirmation":
        warnings.append("Heavy volume selling detected")
        bearish_signals.append("Price decline on heavy volume")

    vol_pts = min(15.0, vol_pts)

    # --------------------------------------------------------------------------
    # 4. Relative Strength vs Market & Sector (Max 15 pts)
    # --------------------------------------------------------------------------
    rs_pts = 0.0
    excess_m20 = rs_market.rs_20.excess_return_pct
    excess_m60 = rs_market.rs_60.excess_return_pct
    excess_s20 = rs_sector.rs_20.excess_return_pct

    # vs Market (Max 10 pts)
    if excess_m20 is not None:
        if excess_m20 >= 5.0:
            rs_pts += 6.0
            bullish_signals.append(f"Outperforming NEPSE by +{excess_m20}% over 20 days")
        elif excess_m20 > 0.0:
            rs_pts += 4.0
        elif excess_m20 >= -3.0:
            rs_pts += 2.0
        else:
            bearish_signals.append(f"Underperforming NEPSE by {excess_m20}% over 20 days")

    if excess_m60 is not None and excess_m60 > 0.0:
        rs_pts += 4.0

    # vs Sector (Max 5 pts)
    if excess_s20 is not None:
        if excess_s20 > 0.0:
            rs_pts += 5.0
            bullish_signals.append(f"Outperforming its sector by +{excess_s20}% over 20 days")
        elif excess_s20 >= -3.0:
            rs_pts += 2.0
        else:
            bearish_signals.append(f"Underperforming its sector by {excess_s20}% over 20 days")

    rs_pts = min(15.0, rs_pts)

    # --------------------------------------------------------------------------
    # 5. Breakout and Price Structure (Max 10 pts)
    # --------------------------------------------------------------------------
    bo_pts = 0.0
    if struct.is_breakout_20:
        bo_pts += 4.0
        bullish_signals.append("20-day price high breakout confirmed")
    if struct.is_breakout_50:
        bo_pts += 3.0
        bullish_signals.append("50-day price high breakout confirmed")

    if struct.is_breakdown_20:
        bearish_signals.append("20-day price low breakdown")
        warnings.append("Recent 20-day low breakdown")
    if struct.is_breakdown_50:
        bearish_signals.append("50-day price low breakdown")
        warnings.append("Major 50-day low breakdown")

    if struct.structure_trend == "uptrend_structure":
        bo_pts += 3.0
        bullish_signals.append("Constructive market structure (Higher Highs & Higher Lows)")
    elif struct.structure_trend == "downtrend_structure":
        bearish_signals.append("Deteriorating market structure (Lower Highs & Lower Lows)")

    bo_pts = min(10.0, bo_pts)

    # --------------------------------------------------------------------------
    # 6. Risk and Volatility Stability (Max 10 pts)
    # Rewards prudent volatility and sufficient data/liquidity
    # --------------------------------------------------------------------------
    risk_pts = 0.0
    atr = volat.atr
    if atr.volatility_class in ("low", "moderate"):
        risk_pts += 4.0
    elif atr.volatility_class == "high":
        risk_pts += 2.0
        warnings.append(f"High price volatility (ATR {atr.atr_percentage}%)")
    elif atr.volatility_class == "extreme":
        warnings.append(f"Extreme volatility detected (ATR {atr.atr_percentage}%)")

    # Historical data completeness check
    if indicator_set.candles_count >= 50:
        risk_pts += 3.0
    elif indicator_set.candles_count < 30:
        warnings.append("Insufficient price history (< 30 completed bars)")

    if not atr.is_large_movement:
        risk_pts += 3.0
    else:
        warnings.append("Abnormal large single-session price movement")

    risk_pts = min(10.0, risk_pts)

    # Total Score
    total = round(trend_pts + mom_pts + vol_pts + rs_pts + bo_pts + risk_pts, 1)

    # Classification
    if total >= 80.0:
        classification = "Strong Technical Candidate"
    elif total >= 65.0:
        classification = "Bullish Candidate"
    elif total >= 50.0:
        if struct.is_breakout_20 or vol.is_volume_breakout:
            classification = "Emerging Candidate"
        else:
            classification = "Neutral / Watchlist"
    elif total >= 35.0:
        classification = "Weakening"
    else:
        classification = "Bearish"

    return StockTechnicalScore(
        total_score=total,
        classification=classification,
        trend_score=round(trend_pts, 1),
        momentum_score=round(mom_pts, 1),
        volume_score=round(vol_pts, 1),
        relative_strength_score=round(rs_pts, 1),
        breakout_score=round(bo_pts, 1),
        risk_score=round(risk_pts, 1),
        bullish_signals=bullish_signals,
        bearish_signals=bearish_signals,
        warnings=warnings,
        component_details={
            "price_above_ema_20": ma.price_above_ema_20,
            "price_above_sma_200": ma.price_above_sma_200,
            "rsi_value": rsi.value,
            "macd_above_zero": macd.is_above_zero,
            "relative_volume": rvol,
            "relative_strength_market_20d": excess_m20,
            "relative_strength_sector_20d": excess_s20,
            "is_breakout_20": struct.is_breakout_20,
            "atr_percentage": atr.atr_percentage,
            "is_sector_strong": is_sector_strong,
        },
    )
