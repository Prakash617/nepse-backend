"""Technical Indicators Engine package.

Exposes deterministic mathematical indicators, data models, and the
top-level `calculate_all_indicators` pipeline.
"""

from __future__ import annotations

from collections.abc import Sequence
from dataclasses import dataclass

from apps.technical_analysis.indicators.momentum import (
    MACDAnalysis,
    MomentumAnalysis,
    RSIAnalysis,
    analyze_momentum,
    calculate_macd,
    calculate_rsi,
)
from apps.technical_analysis.indicators.moving_averages import (
    MovingAverageAnalysis,
    analyze_moving_averages,
    calculate_ema,
    calculate_sma,
)
from apps.technical_analysis.indicators.price_structure import (
    PriceStructureAnalysis,
    analyze_price_structure,
)
from apps.technical_analysis.indicators.trend import (
    ADXAnalysis,
    analyze_trend,
    calculate_dmi_adx,
)
from apps.technical_analysis.indicators.types import (
    Candle,
    candles_from_records,
    sanitize_and_sort_candles,
)
from apps.technical_analysis.indicators.volatility import (
    ATRAnalysis,
    BollingerBandsAnalysis,
    VolatilityAnalysis,
    analyze_volatility,
    calculate_atr,
    calculate_bollinger_bands,
)
from apps.technical_analysis.indicators.volume import (
    VolumeAnalysis,
    analyze_volume,
)


@dataclass(frozen=True)
class FullIndicatorSet:
    """Consolidated technical indicator outputs for a security or index."""

    candles_count: int
    moving_averages: MovingAverageAnalysis
    momentum: MomentumAnalysis
    trend: ADXAnalysis
    volatility: VolatilityAnalysis
    volume: VolumeAnalysis
    price_structure: PriceStructureAnalysis


def calculate_all_indicators(
    candles: Sequence[Candle],
    *,
    rsi_period: int = 14,
    rsi_overbought: float = 70.0,
    rsi_oversold: float = 30.0,
    adx_period: int = 14,
    bb_period: int = 20,
    bb_std: float = 2.0,
    atr_period: int = 14,
) -> FullIndicatorSet:
    """Calculate all technical indicators on a chronological sequence of candles.

    Deterministic and unit-testable. Does not mutate inputs or look forward.
    """
    clean_candles = sanitize_and_sort_candles(candles, min_required=1)

    ma_res = analyze_moving_averages(clean_candles)
    mom_res = analyze_momentum(
        clean_candles,
        rsi_period=rsi_period,
        rsi_overbought=rsi_overbought,
        rsi_oversold=rsi_oversold,
    )
    trend_res = analyze_trend(clean_candles, period=adx_period)
    vol_res = analyze_volatility(
        clean_candles,
        bb_period=bb_period,
        bb_std=bb_std,
        atr_period=atr_period,
    )
    volume_res = analyze_volume(clean_candles)
    struct_res = analyze_price_structure(clean_candles)

    return FullIndicatorSet(
        candles_count=len(clean_candles),
        moving_averages=ma_res,
        momentum=mom_res,
        trend=trend_res,
        volatility=vol_res,
        volume=volume_res,
        price_structure=struct_res,
    )


__all__ = [
    "ADXAnalysis",
    "ATRAnalysis",
    "BollingerBandsAnalysis",
    "Candle",
    "FullIndicatorSet",
    "MACDAnalysis",
    "MomentumAnalysis",
    "MovingAverageAnalysis",
    "PriceStructureAnalysis",
    "RSIAnalysis",
    "VolatilityAnalysis",
    "VolumeAnalysis",
    "analyze_momentum",
    "analyze_moving_averages",
    "analyze_price_structure",
    "analyze_trend",
    "analyze_volatility",
    "analyze_volume",
    "calculate_all_indicators",
    "calculate_atr",
    "calculate_bollinger_bands",
    "calculate_dmi_adx",
    "calculate_ema",
    "calculate_macd",
    "calculate_rsi",
    "calculate_sma",
    "candles_from_records",
    "sanitize_and_sort_candles",
]
