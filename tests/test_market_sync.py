"""Tests for market snapshot synchronization service."""
import datetime
import decimal

import pytest

from apps.market.models import MarketSnapshot
from apps.market.services import sync_market_snapshot


@pytest.mark.django_db
class TestSyncMarketSnapshot:
    def test_create_snapshot(self):
        data = {
            "total_traded_volume": 10000000,
            "total_traded_value": "5000000000.00",
            "transactions": 25000,
            "open": "2000.1234",
            "high": "2050.5678",
            "low": "1980.0000",
            "close": "2020.1234",
            "prev_close": "2000.0000",
            "change": "20.1234",
            "percent_change": "1.0067",
        }
        result = sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))
        assert result.created == 1
        assert MarketSnapshot.objects.count() == 1

        snapshot = MarketSnapshot.objects.first()
        assert snapshot.trading_date == datetime.date(2025, 1, 15)
        assert snapshot.total_volume == 10000000
        assert snapshot.close == decimal.Decimal("2020.1234")

    def test_idempotent_sync(self):
        data = {"total_traded_volume": 10000000, "close": "2000.1234"}
        result1 = sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))
        assert result1.created == 1

        result2 = sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))
        assert result2.created == 0
        assert result2.skipped == 1
        assert MarketSnapshot.objects.count() == 1

    def test_update_existing_snapshot(self):
        data = {"total_traded_volume": 10000000, "close": "2000.1234"}
        sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))

        data_updated = {"total_traded_volume": 12000000, "close": "2050.1234"}
        result = sync_market_snapshot(data_updated, trading_date=datetime.date(2025, 1, 15))
        assert result.updated == 1

        snapshot = MarketSnapshot.objects.first()
        assert snapshot.total_volume == 12000000
        assert snapshot.close == decimal.Decimal("2050.1234")

    def test_multiple_dates(self):
        data1 = {"total_traded_volume": 10000000, "close": "2000.1234"}
        data2 = {"total_traded_volume": 11000000, "close": "2050.1234"}

        sync_market_snapshot(data1, trading_date=datetime.date(2025, 1, 15))
        sync_market_snapshot(data2, trading_date=datetime.date(2025, 1, 16))

        assert MarketSnapshot.objects.count() == 2

    def test_nullable_fields(self):
        data = {}
        result = sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))
        assert result.created == 1
        snapshot = MarketSnapshot.objects.first()
        assert snapshot.total_volume is None
        assert snapshot.total_turnover is None
        assert snapshot.close is None

    def test_ordering(self):
        data = {"close": "2000.0000"}
        sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 15))
        sync_market_snapshot(data, trading_date=datetime.date(2025, 1, 16))

        dates = list(MarketSnapshot.objects.values_list("trading_date", flat=True))
        assert dates == [datetime.date(2025, 1, 16), datetime.date(2025, 1, 15)]
