"""Unit tests for market scoring, sector scoring, and relative strength."""

from __future__ import annotations

import datetime

from apps.technical_analysis.indicators import (
    Candle,
    calculate_all_indicators,
)
from apps.technical_analysis.scoring import (
    MarketBreadth,
    calculate_relative_performance,
    score_market_condition,
    score_sector_strength,
)


def _make_candles(prices: list[float], start_date: datetime.date) -> list[Candle]:
    candles = []
    d = start_date
    for p in prices:
        candles.append(
            Candle(
                trading_date=d,
                open=p,
                high=p + 2.0,
                low=p - 2.0,
                close=p,
                volume=10000,
            )
        )
        d += datetime.timedelta(days=1)
    return candles


class TestRelativeStrength:
    """Test relative performance matching and classification."""

    def test_outperformer_vs_benchmark(self) -> None:
        start_d = datetime.date(2026, 1, 1)
        # Asset rises 20%, benchmark rises 5%
        asset_p = [100.0 + i * 1.0 for i in range(25)]
        bench_p = [100.0 + i * 0.25 for i in range(25)]

        asset_c = _make_candles(asset_p, start_d)
        bench_c = _make_candles(bench_p, start_d)

        res = calculate_relative_performance(asset_c, bench_c)
        assert res.rs_20.is_outperforming is True
        assert res.rs_20.excess_return_pct is not None and res.rs_20.excess_return_pct > 10.0
        assert res.classification == "strong_outperformer"

    def test_underperformer_vs_benchmark(self) -> None:
        start_d = datetime.date(2026, 1, 1)
        # Asset drops, benchmark flat
        asset_p = [100.0 - i * 1.0 for i in range(25)]
        bench_p = [100.0] * 25

        asset_c = _make_candles(asset_p, start_d)
        bench_c = _make_candles(bench_p, start_d)

        res = calculate_relative_performance(asset_c, bench_c)
        assert res.rs_20.is_outperforming is False
        assert res.rs_20.excess_return_pct is not None and res.rs_20.excess_return_pct < -5.0
        assert res.classification == "strong_underperformer"


class TestMarketScoring:
    """Test multi-factor market condition score."""

    def test_strong_bullish_market_condition(self) -> None:
        # Strong uptrend over 220 bars
        prices = [float(100 + i * 2) for i in range(220)]
        candles = _make_candles(prices, datetime.date(2025, 1, 1))
        indicators = calculate_all_indicators(candles)

        # High breadth: 80% above EMA 20, 75% above EMA 50, 70% above SMA 200, A/D = 2.5
        breadth = MarketBreadth(
            total_eligible=300,
            advancing_count=200,
            declining_count=80,
            unchanged_count=20,
            advance_decline_ratio=2.5,
            stocks_above_ema_20=240,
            pct_above_ema_20=80.0,
            stocks_above_ema_50=225,
            pct_above_ema_50=75.0,
            stocks_above_sma_200=210,
            pct_above_sma_200=70.0,
        )

        score = score_market_condition(indicators, breadth)
        assert score.total_score >= 80.0
        assert score.condition == "Strong Bullish"
        assert score.trend_score > 20.0
        assert score.breadth_score > 20.0

    def test_bearish_market_condition(self) -> None:
        # Downtrend over 220 bars
        prices = [float(500 - i * 1.5) for i in range(220)]
        candles = _make_candles(prices, datetime.date(2025, 1, 1))
        indicators = calculate_all_indicators(candles)

        # Low breadth: 15% above EMA 20, A/D = 0.3
        breadth = MarketBreadth(
            total_eligible=300,
            advancing_count=60,
            declining_count=200,
            unchanged_count=40,
            advance_decline_ratio=0.3,
            stocks_above_ema_20=45,
            pct_above_ema_20=15.0,
            stocks_above_ema_50=30,
            pct_above_ema_50=10.0,
            stocks_above_sma_200=25,
            pct_above_sma_200=8.3,
        )

        score = score_market_condition(indicators, breadth)
        assert score.total_score < 45.0
        assert score.condition in ("Bearish", "Strong Bearish")


class TestSectorScoring:
    """Test 0 to 100 Sector Strength Score and classification."""

    def test_strong_trending_sector_score(self) -> None:
        prices = [float(100 + i * 2) for i in range(220)]
        candles = _make_candles(prices, datetime.date(2025, 1, 1))
        indicators = calculate_all_indicators(candles)

        bench_p = [float(100 + i * 0.5) for i in range(220)]
        bench_c = _make_candles(bench_p, datetime.date(2025, 1, 1))
        rs = calculate_relative_performance(candles, bench_c)

        score = score_sector_strength(
            indicators,
            rs,
            daily_return_pct=2.5,
            weekly_return_pct=4.8,
            monthly_return_pct=12.0,
        )

        assert score.total_score >= 80.0
        assert score.classification == "Strong Trending"
        assert score.rotation_stage == "leading"
        assert score.price_momentum_score >= 20.0
        assert score.ema_trend_score >= 15.0
