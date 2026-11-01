"""Unit and integration tests for stock scoring and stock engine."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.engines.stock_engine import (
    analyze_single_security,
    run_all_stocks_analysis,
)
from apps.technical_analysis.indicators import Candle, calculate_all_indicators
from apps.technical_analysis.scoring.relative_strength import calculate_relative_performance
from apps.technical_analysis.scoring.stock_scoring import score_stock_technical


def _make_candles(prices: list[float], start_date: datetime.date) -> list[Candle]:
    candles = []
    d = start_date
    for p in prices:
        candles.append(
            Candle(
                trading_date=d,
                open=p - 1.0,
                high=p + 2.0,
                low=p - 2.0,
                close=p,
                volume=10000,
            )
        )
        d += datetime.timedelta(days=1)
    return candles


class TestStockScoring:
    """Test stock scoring rules and signals."""

    def test_strong_technical_candidate_score(self) -> None:
        # Realistic healthy uptrend with mild pullbacks so RSI is in 55-65 zone
        prices = []
        p = 100.0
        for i in range(220):
            # Oscillating uptrend
            p += 0.8 if i % 4 != 0 else -0.3
            prices.append(round(p, 2))

        start_d = datetime.date(2025, 1, 1)
        stock_c = _make_candles(prices, start_d)
        # Add a volume breakout on the final candle
        last_c = stock_c[-1]
        stock_c[-1] = Candle(
            trading_date=last_c.trading_date,
            open=last_c.open,
            high=last_c.high + 10.0,
            low=last_c.low,
            close=last_c.close + 10.0,
            volume=30000,  # 3x volume
        )

        bench_c = _make_candles([float(100 + i * 0.1) for i in range(220)], start_d)

        indicators = calculate_all_indicators(stock_c)
        rs_m = calculate_relative_performance(stock_c, bench_c)
        rs_s = calculate_relative_performance(stock_c, bench_c)

        score = score_stock_technical(indicators, rs_m, rs_s, is_sector_strong=True)

        assert score.total_score >= 80.0
        assert score.classification == "Strong Technical Candidate"
        assert len(score.bullish_signals) >= 3
        assert score.trend_score >= 20.0
        assert score.momentum_score >= 10.0

    def test_weak_bearish_stock_score(self) -> None:
        prices = [float(500 - i * 2) for i in range(220)]
        start_d = datetime.date(2025, 1, 1)
        stock_c = _make_candles(prices, start_d)
        bench_c = _make_candles([float(100 + i * 0.5) for i in range(220)], start_d)

        indicators = calculate_all_indicators(stock_c)
        rs_m = calculate_relative_performance(stock_c, bench_c)
        rs_s = calculate_relative_performance(stock_c, bench_c)

        score = score_stock_technical(indicators, rs_m, rs_s, is_sector_strong=False)

        assert score.total_score < 35.0
        assert score.classification == "Bearish"
        assert len(score.bearish_signals) >= 2
        assert len(score.warnings) >= 1


@pytest.mark.django_db
class TestStockEngineDatabase:
    """Test stock engine execution with Django models."""

    def test_analyze_single_security(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        stock = Security.objects.create(nepse_id=1001, symbol="NABIL", company_name="Nabil Bank", sector=sec)
        nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

        d = datetime.date(2026, 1, 1)
        for i in range(30):
            cur_d = d + datetime.timedelta(days=i)
            DailyPrice.objects.create(
                security=stock,
                trading_date=cur_d,
                open=Decimal("1000.0"),
                high=Decimal("1020.0"),
                low=Decimal("990.0"),
                close=Decimal(str(1000 + i * 5)),
                percentage_change=Decimal("1.0"),
                volume=5000,
            )
            IndexSnapshot.objects.create(
                index=nepse,
                trading_date=cur_d,
                open=Decimal("2000.0"),
                high=Decimal("2020.0"),
                low=Decimal("1990.0"),
                close=Decimal(str(2000 + i * 2)),
                volume=100000,
            )

        target = d + datetime.timedelta(days=29)
        res = analyze_single_security(stock, target)

        assert res is not None
        assert res.symbol == "NABIL"
        assert res.latest_close > 0
        assert res.score.total_score > 0
        assert "NABIL" in res.explanation

    def test_run_all_stocks_analysis_bulk(self) -> None:
        sec = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        s1 = Security.objects.create(nepse_id=1001, symbol="STK1", company_name="Stock 1", sector=sec)
        s2 = Security.objects.create(nepse_id=1002, symbol="STK2", company_name="Stock 2", sector=sec)
        nepse = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")

        d = datetime.date(2026, 1, 1)
        for i in range(25):
            cur_d = d + datetime.timedelta(days=i)
            DailyPrice.objects.create(
                security=s1,
                trading_date=cur_d,
                open=Decimal("100.0"), high=Decimal("105.0"), low=Decimal("95.0"),
                close=Decimal(str(100 + i)), percentage_change=Decimal("1.0"), volume=1000,
            )
            DailyPrice.objects.create(
                security=s2,
                trading_date=cur_d,
                open=Decimal("200.0"), high=Decimal("205.0"), low=Decimal("195.0"),
                close=Decimal(str(200 - i)), percentage_change=Decimal("-1.0"), volume=1000,
            )
            IndexSnapshot.objects.create(
                index=nepse,
                trading_date=cur_d,
                open=Decimal("2000.0"), high=Decimal("2020.0"), low=Decimal("1990.0"),
                close=Decimal(str(2000 + i)), volume=50000,
            )

        target = d + datetime.timedelta(days=24)
        all_res = run_all_stocks_analysis(target)

        assert len(all_res) == 2
        symbols = [s.symbol for s in all_res]
        assert "STK1" in symbols
        assert "STK2" in symbols
