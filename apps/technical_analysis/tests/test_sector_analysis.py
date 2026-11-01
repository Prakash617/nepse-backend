"""Unit and integration tests for Sector Intelligence Engine."""

from __future__ import annotations

import datetime
from decimal import Decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.technical_analysis.engines.sector_engine import (
    get_sector_candles,
    run_sector_intelligence,
)


@pytest.mark.django_db
class TestSectorEngine:
    """Test sector data fetching, fallback basket, and intelligence ranking."""

    def test_get_sector_candles_official_index(self) -> None:
        sector = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        index = MarketIndex.objects.create(nepse_id=51, name="Banking SubIndex")
        d = datetime.date(2026, 1, 1)

        for i in range(20):
            IndexSnapshot.objects.create(
                index=index,
                trading_date=d + datetime.timedelta(days=i),
                open=Decimal("1500.0"),
                high=Decimal("1520.0"),
                low=Decimal("1490.0"),
                close=Decimal(str(1500 + i * 5)),
                volume=500000,
            )

        target = d + datetime.timedelta(days=19)
        candles, source = get_sector_candles(sector, target, lookback_bars=30)
        assert source == "official_index"
        assert len(candles) == 20

    def test_get_sector_candles_derived_basket_fallback(self) -> None:
        # Create a sector with no corresponding MarketIndex
        sector = Sector.objects.create(nepse_id=9999, name="Custom Sector")
        sec1 = Security.objects.create(nepse_id=201, symbol="CS1", company_name="CS 1", sector=sector)
        d = datetime.date(2026, 1, 1)

        for i in range(20):
            DailyPrice.objects.create(
                security=sec1,
                trading_date=d + datetime.timedelta(days=i),
                open=Decimal("100.0"),
                high=Decimal("105.0"),
                low=Decimal("95.0"),
                close=Decimal(str(100 + i)),
                percentage_change=Decimal("1.0"),
                volume=1000,
            )

        target = d + datetime.timedelta(days=19)
        candles, source = get_sector_candles(sector, target, lookback_bars=30)
        assert source == "derived_basket"
        assert len(candles) == 20

    def test_run_sector_intelligence_top_three_ranking(self) -> None:
        # Create benchmark NEPSE Index
        nepse_idx = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        d = datetime.date(2026, 1, 1)

        for i in range(25):
            IndexSnapshot.objects.create(
                index=nepse_idx,
                trading_date=d + datetime.timedelta(days=i),
                open=Decimal("2000.0"),
                high=Decimal("2050.0"),
                low=Decimal("1990.0"),
                close=Decimal(str(2000 + i * 2)),
                volume=1000000,
            )

        # Create 4 sectors with varying strengths
        s1 = Sector.objects.create(nepse_id=7784, name="Commercial Banks")
        s2 = Sector.objects.create(nepse_id=2208, name="Hydro Power")
        s3 = Sector.objects.create(nepse_id=4941, name="Finance")
        s4 = Sector.objects.create(nepse_id=7880, name="Hotels And Tourism")

        idx_map = {
            s1: (51, "Banking SubIndex", 10.0),   # Highest momentum (+10 per day)
            s2: (54, "HydroPower Index", 5.0),    # Moderate momentum (+5 per day)
            s3: (60, "Finance Index", 2.0),       # Low momentum (+2 per day)
            s4: (52, "Hotels And Tourism Index", -2.0), # Falling (-2 per day)
        }

        for _sec, (idx_id, idx_name, slope) in idx_map.items():
            m_idx = MarketIndex.objects.create(nepse_id=idx_id, name=idx_name)
            for i in range(25):
                IndexSnapshot.objects.create(
                    index=m_idx,
                    trading_date=d + datetime.timedelta(days=i),
                    open=Decimal("1000.0"),
                    high=Decimal("1050.0"),
                    low=Decimal("980.0"),
                    close=Decimal(str(max(100.0, 1000.0 + i * slope))),
                    volume=50000,
                )

        target = d + datetime.timedelta(days=24)
        result = run_sector_intelligence(target)

        assert result.total_sectors == 4
        # Exactly 3 in top_three_trending
        assert len(result.top_three_trending) == 3
        # All 4 sectors accessible in all_sector_rankings
        assert len(result.all_sector_rankings) == 4
        # Commercial Banks should be ranked #1
        assert result.top_three_trending[0].sector_name == "Commercial Banks"
        # Hotel and Tourism (falling) should have lowest score
        assert result.all_sector_rankings[-1].sector_name == "Hotels And Tourism"
