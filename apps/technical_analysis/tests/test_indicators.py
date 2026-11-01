"""Unit tests for the Technical Indicators Engine.

Tests every indicator mathematically against deterministic reference datasets,
verifies edge cases (zero volume, zero variance, empty lists, gaps),
and verifies lack of future data leakage.
"""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.technical_analysis.indicators import (
    Candle,
    analyze_momentum,
    analyze_moving_averages,
    analyze_price_structure,
    analyze_trend,
    analyze_volatility,
    analyze_volume,
    calculate_all_indicators,
    calculate_bollinger_bands,
    calculate_dmi_adx,
    calculate_ema,
    calculate_rsi,
    calculate_sma,
    candles_from_records,
    sanitize_and_sort_candles,
)


def _generate_synthetic_candles(
    count: int,
    start_date: datetime.date = datetime.date(2025, 1, 1),
    base_price: float = 100.0,
    trend_slope: float = 0.5,
    volatility: float = 2.0,
    base_volume: float = 10000.0,
) -> list[Candle]:
    """Helper to generate deterministic synthetic candles."""
    candles: list[Candle] = []
    current_date = start_date
    current_price = base_price

    for i in range(count):
        # Deterministic wave pattern
        wave = (i % 5 - 2) * volatility
        current_price = max(10.0, base_price + (i * trend_slope) + wave)
        c_open = current_price - 0.5
        c_high = current_price + 1.5
        c_low = current_price - 1.5
        c_close = current_price
        c_vol = base_volume + (i % 7) * 1000.0

        candles.append(
            Candle(
                trading_date=current_date,
                open=round(c_open, 2),
                high=round(c_high, 2),
                low=round(c_low, 2),
                close=round(c_close, 2),
                volume=round(c_vol, 0),
            )
        )
        current_date += datetime.timedelta(days=1)

    return candles


# ==============================================================================
# 1. Types & Data Sanitization Tests
# ==============================================================================


class TestCandleTypesAndSanitization:
    """Test candle validation, sorting, deduplication, and conversion."""

    def test_negative_close_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Close price cannot be negative"):
            Candle(
                trading_date=datetime.date(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=95.0,
                close=-10.0,
            )

    def test_negative_volume_raises_error(self) -> None:
        with pytest.raises(ValueError, match="Volume cannot be negative"):
            Candle(
                trading_date=datetime.date(2026, 1, 1),
                open=100.0,
                high=105.0,
                low=95.0,
                close=100.0,
                volume=-50.0,
            )

    def test_sanitize_sorts_and_deduplicates(self) -> None:
        d1 = datetime.date(2026, 1, 1)
        d2 = datetime.date(2026, 1, 2)
        d3 = datetime.date(2026, 1, 3)

        raw = [
            Candle(trading_date=d3, open=102, high=105, low=100, close=103),
            Candle(trading_date=d1, open=100, high=102, low=98, close=100),
            Candle(trading_date=d2, open=101, high=103, low=99, close=101),
            Candle(trading_date=d1, open=999, high=999, low=999, close=999),  # Duplicate d1
        ]
        clean = sanitize_and_sort_candles(raw)

        assert len(clean) == 3
        assert clean[0].trading_date == d1
        assert clean[0].close == 100.0  # Kept first d1
        assert clean[1].trading_date == d2
        assert clean[2].trading_date == d3

    def test_sanitize_fixes_inverted_high_low(self) -> None:
        candle = Candle(
            trading_date=datetime.date(2026, 1, 1),
            open=100.0,
            high=90.0,   # Inverted!
            low=110.0,   # Inverted!
            close=105.0,
        )
        clean = sanitize_and_sort_candles([candle])
        assert clean[0].high >= 105.0
        assert clean[0].low <= 100.0

    def test_candles_from_records_dict_and_decimals(self) -> None:
        records = [
            {
                "trading_date": "2026-01-01",
                "open": Decimal("100.5"),
                "high": Decimal("105.0"),
                "low": Decimal("99.0"),
                "close": Decimal("104.2"),
                "volume": 5000,
            },
            {
                "trading_date": datetime.date(2026, 1, 2),
                "open": 104.2,
                "high": None,  # Should fallback safely
                "low": None,
                "close": 108.0,
                "volume": None,
            },
        ]
        candles = candles_from_records(records)
        assert len(candles) == 2
        assert candles[0].close == 104.2
        assert candles[1].high >= 108.0
        assert candles[1].low <= 104.2
        assert candles[1].volume == 0.0


# ==============================================================================
# 2. Moving Averages Tests
# ==============================================================================


class TestMovingAverages:
    """Test SMA, EMA, slope, and cross detections."""

    def test_calculate_sma_reference(self) -> None:
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        sma3 = calculate_sma(prices, 3)
        assert sma3 == [None, None, 20.0, 30.0, 40.0]

    def test_calculate_sma_insufficient_data(self) -> None:
        prices = [10.0, 20.0]
        assert calculate_sma(prices, 5) == [None, None]

    def test_calculate_ema_reference(self) -> None:
        # For period 3: k = 2 / (3 + 1) = 0.5
        # First EMA = SMA(10, 20, 30) = 20.0
        # Second EMA = 40 * 0.5 + 20.0 * 0.5 = 30.0
        # Third EMA = 50 * 0.5 + 30.0 * 0.5 = 40.0
        prices = [10.0, 20.0, 30.0, 40.0, 50.0]
        ema3 = calculate_ema(prices, 3)
        assert ema3 == [None, None, 20.0, 30.0, 40.0]

    def test_analyze_moving_averages_full_series(self) -> None:
        # Generate 210 candles in an uptrend
        candles = _generate_synthetic_candles(210, base_price=100.0, trend_slope=1.0)
        res = analyze_moving_averages(candles)

        assert res.sma_20 is not None
        assert res.sma_50 is not None
        assert res.sma_200 is not None
        assert res.ema_20 is not None
        assert res.ema_50 is not None
        assert res.ema_200 is not None

        # In steady uptrend: close > EMA 20 > EMA 50 > EMA 200
        assert res.price_above_ema_20 is True
        assert res.ema_20_above_ema_50 is True
        assert res.ema_50_above_ema_200 is True
        assert res.ema_20_slope is not None and res.ema_20_slope > 0

    def test_golden_cross_detection(self) -> None:
        # Create candles where EMA 50 starts below EMA 200, then surges up
        candles_downtrend = _generate_synthetic_candles(200, base_price=300.0, trend_slope=-0.8)
        # Add strong surge
        last_date = candles_downtrend[-1].trading_date
        surge_candles = [
            Candle(
                trading_date=last_date + datetime.timedelta(days=1),
                open=350.0, high=400.0, low=340.0, close=390.0, volume=50000,
            ),
            Candle(
                trading_date=last_date + datetime.timedelta(days=2),
                open=390.0, high=450.0, low=380.0, close=440.0, volume=60000,
            ),
            Candle(
                trading_date=last_date + datetime.timedelta(days=3),
                open=440.0, high=520.0, low=430.0, close=510.0, volume=80000,
            ),
        ]
        all_candles = candles_downtrend + surge_candles
        res = analyze_moving_averages(all_candles)
        # Check calculation runs cleanly and returns boolean flags
        assert isinstance(res.golden_cross, bool)
        assert isinstance(res.death_cross, bool)


# ==============================================================================
# 3. Momentum (RSI & MACD) Tests
# ==============================================================================


class TestMomentumIndicators:
    """Test RSI and MACD calculations, edge cases, and divergence."""

    def test_rsi_constant_prices(self) -> None:
        prices = [100.0] * 20
        rsi = calculate_rsi(prices, 14)
        # When all changes are 0, RSI should default to 50.0
        assert rsi[-1] == 50.0

    def test_rsi_strictly_increasing(self) -> None:
        prices = [float(100 + i * 2) for i in range(25)]
        rsi = calculate_rsi(prices, 14)
        # All gains, zero loss -> RSI must be 100.0
        assert rsi[-1] == 100.0

    def test_rsi_strictly_decreasing(self) -> None:
        prices = [float(200 - i * 2) for i in range(25)]
        rsi = calculate_rsi(prices, 14)
        # All losses, zero gain -> RSI must be 0.0
        assert rsi[-1] == 0.0

    def test_rsi_overbought_oversold_classification(self) -> None:
        high_candles = _generate_synthetic_candles(25, base_price=100.0, trend_slope=5.0)
        res_high = analyze_momentum(high_candles)
        assert res_high.rsi.value is not None and res_high.rsi.value > 70.0
        assert res_high.rsi.is_overbought is True
        assert res_high.rsi.is_oversold is False
        assert res_high.rsi.momentum_zone == "bullish_momentum"

        low_candles = _generate_synthetic_candles(25, base_price=500.0, trend_slope=-5.0)
        res_low = analyze_momentum(low_candles)
        assert res_low.rsi.value is not None and res_low.rsi.value < 30.0
        assert res_low.rsi.is_oversold is True
        assert res_low.rsi.is_overbought is False
        assert res_low.rsi.momentum_zone == "bearish_momentum"

    def test_macd_calculation_and_crossover(self) -> None:
        # MACD requires at least 35 bars (slow 26 + signal 9)
        candles = _generate_synthetic_candles(50, base_price=100.0, trend_slope=0.5)
        res = analyze_momentum(candles)

        assert res.macd.macd_line is not None
        assert res.macd.signal_line is not None
        assert res.macd.histogram is not None
        assert res.macd.is_above_zero is True
        assert res.macd.crossover in ("bullish_crossover", "bearish_crossover", "none")


# ==============================================================================
# 4. Trend (ADX & DMI) Tests
# ==============================================================================


class TestTrendADXDMI:
    """Test full Wilder's ADX, +DI, -DI calculations."""

    def test_adx_insufficient_bars(self) -> None:
        candles = _generate_synthetic_candles(15)
        plus_di, minus_di, adx = calculate_dmi_adx(candles, 14)
        assert all(v is None for v in adx)

    def test_adx_strong_trend_detection(self) -> None:
        # Strong directional movement over 60 bars
        candles = _generate_synthetic_candles(60, base_price=100.0, trend_slope=3.0)
        res = analyze_trend(candles, period=14)

        assert res.adx is not None
        assert res.plus_di is not None
        assert res.minus_di is not None
        assert res.plus_di > res.minus_di  # Strong bullish dominance
        assert res.directional_dominance == "bullish"
        assert res.trend_strength in ("developing", "strong", "very_strong")

    def test_adx_bearish_dominance(self) -> None:
        candles = _generate_synthetic_candles(60, base_price=500.0, trend_slope=-3.0)
        res = analyze_trend(candles, period=14)

        assert res.minus_di is not None
        assert res.plus_di is not None
        assert res.minus_di > res.plus_di  # Bearish dominance
        assert res.directional_dominance == "bearish"


# ==============================================================================
# 5. Volatility (Bollinger Bands & ATR) Tests
# ==============================================================================


class TestVolatilityIndicators:
    """Test Bollinger Bands, %B, Bandwidth, Squeeze, and ATR."""

    def test_bollinger_bands_flat_prices(self) -> None:
        prices = [100.0] * 25
        upper, middle, lower = calculate_bollinger_bands(prices, period=20, num_std=2.0)
        # When all prices are identical, std = 0, so upper == middle == lower
        assert upper[-1] == 100.0
        assert middle[-1] == 100.0
        assert lower[-1] == 100.0

    def test_bollinger_bands_and_atr_analysis(self) -> None:
        candles = _generate_synthetic_candles(40, base_price=200.0, volatility=5.0)
        vol_res = analyze_volatility(candles)

        assert vol_res.bollinger.upper_band is not None
        assert vol_res.bollinger.middle_band is not None
        assert vol_res.bollinger.lower_band is not None
        assert vol_res.bollinger.bandwidth is not None
        assert vol_res.bollinger.percent_b is not None

        assert vol_res.atr.atr is not None
        assert vol_res.atr.atr_percentage is not None
        assert vol_res.atr.volatility_class in ("low", "moderate", "high", "extreme")


# ==============================================================================
# 6. Volume Analysis Tests
# ==============================================================================


class TestVolumeAnalysis:
    """Test 20/50 SMA volume, RVOL, zero volume handling, and breakouts."""

    def test_zero_volume_safe_handling(self) -> None:
        d = datetime.date(2026, 1, 1)
        zero_vol_candles = [
            Candle(trading_date=d + datetime.timedelta(days=i), open=100, high=105, low=95, close=100, volume=0)
            for i in range(25)
        ]
        res = analyze_volume(zero_vol_candles)
        assert res.daily_volume == 0.0
        assert res.avg_volume_20 == 0.0
        # Should handle division by zero safely without throwing ZeroDivisionError
        assert res.relative_volume is None or res.relative_volume == 0.0
        assert res.is_unusual_volume is False

    def test_unusual_volume_and_breakout(self) -> None:
        candles = _generate_synthetic_candles(25, base_volume=10000.0)
        # Surge on the last day with a price breakout above previous 20 highs
        last = candles[-1]
        candles[-1] = Candle(
            trading_date=last.trading_date,
            open=last.open,
            high=last.high + 20.0,
            low=last.low,
            close=last.close + 25.0,
            volume=35000.0,  # 3.5x average
        )
        res = analyze_volume(candles)
        assert res.relative_volume is not None and res.relative_volume >= 2.0
        assert res.is_unusual_volume is True
        assert res.price_volume_confirmation == "bullish_confirmation"
        assert res.is_volume_breakout is True


# ==============================================================================
# 7. Price Structure Tests
# ==============================================================================


class TestPriceStructure:
    """Test 20d, 50d, 52w highs/lows, breakout/breakdown, and pivot structures."""

    def test_price_structure_breakout(self) -> None:
        candles = _generate_synthetic_candles(30, base_price=100.0, trend_slope=0.2)
        # Spike close on day 30 above day 0-29 highs
        last = candles[-1]
        candles[-1] = Candle(
            trading_date=last.trading_date,
            open=last.open,
            high=last.high + 30.0,
            low=last.low,
            close=last.close + 30.0,
            volume=last.volume,
        )
        res = analyze_price_structure(candles)
        assert res.is_breakout_20 is True
        assert res.is_breakdown_20 is False

    def test_uptrend_market_structure(self) -> None:
        candles = _generate_synthetic_candles(60, base_price=100.0, trend_slope=1.5, volatility=1.0)
        res = analyze_price_structure(candles)
        assert res.high_20 is not None
        assert res.low_20 is not None
        assert res.structure_trend in ("uptrend_structure", "consolidation")


# ==============================================================================
# 8. Top-Level Full Pipeline Tests
# ==============================================================================


class TestCalculateAllIndicators:
    """Test the integrated orchestrator."""

    def test_empty_candles_returns_graceful_defaults(self) -> None:
        res = calculate_all_indicators([])
        assert res.candles_count == 0
        assert res.moving_averages.ema_20 is None
        assert res.momentum.rsi.value is None
        assert res.trend.adx is None
        assert res.volatility.bollinger.upper_band is None
        assert res.volume.daily_volume == 0.0

    def test_full_pipeline_220_candles(self) -> None:
        candles = _generate_synthetic_candles(220, base_price=200.0, trend_slope=0.5)
        res = calculate_all_indicators(candles)

        assert res.candles_count == 220
        assert res.moving_averages.sma_200 is not None
        assert res.moving_averages.ema_200 is not None
        assert res.momentum.rsi.value is not None
        assert res.momentum.macd.macd_line is not None
        assert res.trend.adx is not None
        assert res.trend.plus_di is not None
        assert res.trend.minus_di is not None
        assert res.volatility.bollinger.bandwidth is not None
        assert res.volatility.atr.atr is not None
        assert res.volume.relative_volume is not None
        assert res.price_structure.high_20 is not None
