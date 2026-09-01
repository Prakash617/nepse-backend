"""Tests for price synchronization service."""
import datetime
import decimal

import pytest

from apps.prices.models import DailyPrice, IntradayPrice
from apps.prices.services import sync_daily_prices, sync_intraday_prices
from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def security():
    sector = Sector.objects.create(nepse_id=1, name="Banks")
    return Security.objects.create(
        nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=sector
    )


@pytest.fixture
def securities():
    sector = Sector.objects.create(nepse_id=1, name="Banks")
    s1 = Security.objects.create(nepse_id=58, symbol="NABIL", company_name="Nabil", sector=sector)
    s2 = Security.objects.create(nepse_id=59, symbol="NHPC", company_name="NHPC", sector=sector)
    return s1, s2


@pytest.mark.django_db
class TestSyncDailyPrices:
    def test_create_new_prices(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1020.00",
                "open": "1000.00",
                "high": "1050.00",
                "low": "990.00",
                "close": "1020.00",
                "volume": 150000,
                "turnover": "150000000.00",
                "change": "10.00",
                "percent_change": "0.99",
                "prev_close": "1010.00",
                "business_date": "2025-01-15",
            },
        ]
        result = sync_daily_prices(data)
        assert result.created == 1
        assert result.skipped == 0
        assert DailyPrice.objects.count() == 1

        price = DailyPrice.objects.first()
        assert price.security == security
        assert price.trading_date == datetime.date(2025, 1, 15)
        assert price.ltp == decimal.Decimal("1020.00")
        assert price.open == decimal.Decimal("1000.00")
        assert price.volume == 150000

    def test_idempotent_sync(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1020.00",
                "business_date": "2025-01-15",
            },
        ]
        result1 = sync_daily_prices(data)
        assert result1.created == 1

        result2 = sync_daily_prices(data)
        assert result2.created == 0
        assert result2.skipped == 1
        assert DailyPrice.objects.count() == 1

    def test_update_existing_prices(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1020.00",
                "business_date": "2025-01-15",
            },
        ]
        sync_daily_prices(data)

        data_updated = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1050.00",
                "business_date": "2025-01-15",
            },
        ]
        result = sync_daily_prices(data_updated)
        assert result.updated == 1
        assert result.skipped == 0

        price = DailyPrice.objects.first()
        assert price.ltp == decimal.Decimal("1050.00")

    def test_unresolved_security_skipped(self):
        data = [
            {
                "symbol": "UNKNOWN",
                "security_id": 999,
                "ltp": "100.00",
                "business_date": "2025-01-15",
            },
        ]
        result = sync_daily_prices(data)
        assert result.created == 0
        assert result.skipped == 1
        assert len(result.errors) == 1

    def test_missing_date_defaults_to_today(self, security):
        """When business_date is None, default to today's date."""
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "100.00",
                "business_date": None,
            },
        ]
        result = sync_daily_prices(data)
        assert result.created == 1
        assert result.skipped == 0
        dp = DailyPrice.objects.get(security=security)
        assert dp.trading_date == datetime.date.today()
        assert dp.ltp == decimal.Decimal("100.00")

    def test_multiple_dates(self, security):
        data = [
            {"symbol": "NABIL", "security_id": 58, "ltp": "1000", "business_date": "2025-01-15"},
            {"symbol": "NABIL", "security_id": 58, "ltp": "1010", "business_date": "2025-01-16"},
            {"symbol": "NABIL", "security_id": 58, "ltp": "1020", "business_date": "2025-01-17"},
        ]
        result = sync_daily_prices(data)
        assert result.created == 3
        assert DailyPrice.objects.count() == 3

    def test_multiple_securities(self, securities):
        s1, s2 = securities
        data = [
            {"symbol": "NABIL", "security_id": 58, "ltp": "1000", "business_date": "2025-01-15"},
            {"symbol": "NHPC", "security_id": 59, "ltp": "500", "business_date": "2025-01-15"},
        ]
        result = sync_daily_prices(data)
        assert result.created == 2
        assert DailyPrice.objects.count() == 2

    def test_nullable_fields(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "business_date": "2025-01-15",
            },
        ]
        result = sync_daily_prices(data)
        assert result.created == 1
        price = DailyPrice.objects.first()
        assert price.ltp is None
        assert price.open is None
        assert price.volume is None

    def test_preserves_historical_data(self, security):
        old_data = [
            {"symbol": "NABIL", "security_id": 58, "ltp": "900", "business_date": "2024-06-01"},
        ]
        sync_daily_prices(old_data)

        new_data = [
            {"symbol": "NABIL", "security_id": 58, "ltp": "1000", "business_date": "2025-01-15"},
        ]
        sync_daily_prices(new_data)

        assert DailyPrice.objects.count() == 2
        old_price = DailyPrice.objects.get(trading_date=datetime.date(2024, 6, 1))
        assert old_price.ltp == decimal.Decimal("900")


@pytest.mark.django_db
class TestSyncIntradayPrices:
    def test_create_intraday_prices(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1020.00",
                "volume": 100,
                "turnover": "102000.00",
                "business_date": "2025-01-15T10:30:00",
            },
        ]
        result = sync_intraday_prices(data)
        assert result.created == 1
        assert IntradayPrice.objects.count() == 1

    def test_appends_without_dedup(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "1020.00",
                "business_date": "2025-01-15T10:30:00",
            },
        ]
        sync_intraday_prices(data)
        sync_intraday_prices(data)
        # No uniqueness constraint — both records are created
        assert IntradayPrice.objects.count() == 2

    def test_unresolved_security_skipped(self):
        data = [
            {
                "symbol": "UNKNOWN",
                "security_id": 999,
                "ltp": "100.00",
                "business_date": "2025-01-15T10:30:00",
            },
        ]
        result = sync_intraday_prices(data)
        assert result.created == 0
        assert result.skipped == 1

    def test_missing_timestamp_skipped(self, security):
        data = [
            {
                "symbol": "NABIL",
                "security_id": 58,
                "ltp": "100.00",
                "business_date": None,
            },
        ]
        result = sync_intraday_prices(data)
        assert result.created == 0
        assert result.skipped == 1
