"""Unit and integration tests for Market Analysis Engine."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.securities.models import Security
from apps.technical_analysis.engines.market_engine import (
    compute_market_breadth,
    get_market_candles,
    run_market_analysis,
)


@pytest.mark.django_db
class TestMarketEngine:
    """Test market engine candle fetching, breadth, and scoring."""

    def test_get_market_candles_prefers_index_snapshot(self) -> None:
        idx = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        d = datetime.date(2026, 1, 1)

        # Create 20 index snapshots
        for i in range(20):
            IndexSnapshot.objects.create(
                index=idx,
                trading_date=d + datetime.timedelta(days=i),
                open=Decimal("2000.0"),
                high=Decimal("2050.0"),
                low=Decimal("1990.0"),
                close=Decimal("2020.0") + Decimal(str(i)),
                volume=1000000,
            )

        target_date = d + datetime.timedelta(days=19)
        candles, source = get_market_candles(target_date, lookback_bars=50)

        assert source == "official_index"
        assert len(candles) == 20
        assert candles[-1].trading_date == target_date

    def test_compute_market_breadth_with_mock_securities(self) -> None:
        d = datetime.date(2026, 1, 1)
        sec1 = Security.objects.create(nepse_id=101, symbol="SEC1", company_name="Sec 1")
        sec2 = Security.objects.create(nepse_id=102, symbol="SEC2", company_name="Sec 2")

        # 25 days of daily prices so EMA 20 can be computed
        for i in range(25):
            cur_d = d + datetime.timedelta(days=i)
            # sec1 rising
            DailyPrice.objects.create(
                security=sec1,
                trading_date=cur_d,
                open=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("95.0"),
                close=Decimal(str(100 + i * 2)),
                percentage_change=Decimal("2.0"),
                volume=1000,
            )
            # sec2 falling
            DailyPrice.objects.create(
                security=sec2,
                trading_date=cur_d,
                open=Decimal("200.0"),
                high=Decimal("205.0"),
                low=Decimal("190.0"),
                close=Decimal(str(200 - i * 2)),
                percentage_change=Decimal("-2.0"),
                volume=1000,
            )

        as_of = d + datetime.timedelta(days=24)
        breadth = compute_market_breadth(as_of)

        assert breadth.total_eligible == 2
        assert breadth.advancing_count == 1
        assert breadth.declining_count == 1
        assert breadth.advance_decline_ratio == 1.0
        assert breadth.stocks_above_ema_20 == 1
        assert breadth.pct_above_ema_20 == 50.0

    def test_run_market_analysis_end_to_end(self) -> None:
        idx = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        d = datetime.date(2026, 1, 1)

        for i in range(30):
            IndexSnapshot.objects.create(
                index=idx,
                trading_date=d + datetime.timedelta(days=i),
                open=Decimal("2000.0"),
                high=Decimal("2050.0"),
                low=Decimal("1990.0"),
                close=Decimal(str(2000 + i * 5)),
                volume=500000,
            )

        target_date = d + datetime.timedelta(days=29)
        result = run_market_analysis(target_date)

        assert result.as_of_date == target_date
        assert result.latest_close > 0
        assert result.condition.condition in ("Strong Bullish", "Bullish", "Neutral", "Bearish", "Strong Bearish")
        assert result.indicators.candles_count == 30
