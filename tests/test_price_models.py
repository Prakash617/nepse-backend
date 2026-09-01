"""Tests for DailyPrice and IntradayPrice models."""
import datetime
import decimal

import pytest
from django.db import IntegrityError

from apps.prices.models import DailyPrice, IntradayPrice
from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def security():
    sector = Sector.objects.create(nepse_id=1, name="Banks")
    return Security.objects.create(
        nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=sector
    )


@pytest.mark.django_db
class TestDailyPriceModel:
    def test_create_daily_price(self, security):
        price = DailyPrice.objects.create(
            security=security,
            trading_date=datetime.date(2025, 1, 15),
            open=decimal.Decimal("1000.00"),
            high=decimal.Decimal("1050.00"),
            low=decimal.Decimal("990.00"),
            close=decimal.Decimal("1020.00"),
            ltp=decimal.Decimal("1020.00"),
            previous_close=decimal.Decimal("1010.00"),
            volume=150000,
            turnover=decimal.Decimal("150000000.00"),
            percentage_change=decimal.Decimal("0.9901"),
            point_change=decimal.Decimal("10.0000"),
        )
        assert price.pk is not None
        assert price.security == security
        assert price.trading_date == datetime.date(2025, 1, 15)
        assert price.open == decimal.Decimal("1000.00")
        assert price.high == decimal.Decimal("1050.00")
        assert price.low == decimal.Decimal("990.00")
        assert price.close == decimal.Decimal("1020.00")
        assert price.ltp == decimal.Decimal("1020.00")
        assert price.previous_close == decimal.Decimal("1010.00")
        assert price.volume == 150000
        assert price.turnover == decimal.Decimal("150000000.00")
        assert price.percentage_change == decimal.Decimal("0.9901")
        assert price.point_change == decimal.Decimal("10.0000")

    def test_str_representation(self, security):
        price = DailyPrice.objects.create(
            security=security,
            trading_date=datetime.date(2025, 1, 15),
        )
        assert str(price) == "NABIL on 2025-01-15"

    def test_unique_constraint_security_date(self, security):
        DailyPrice.objects.create(
            security=security, trading_date=datetime.date(2025, 1, 15)
        )
        with pytest.raises(IntegrityError):
            DailyPrice.objects.create(
                security=security, trading_date=datetime.date(2025, 1, 15)
            )

    def test_same_date_different_security(self, security):
        sector = Sector.objects.create(nepse_id=2, name="Hydro")
        other = Security.objects.create(
            nepse_id=59, symbol="NHPC", company_name="NHPC", sector=sector
        )
        DailyPrice.objects.create(
            security=security, trading_date=datetime.date(2025, 1, 15)
        )
        price2 = DailyPrice.objects.create(
            security=other, trading_date=datetime.date(2025, 1, 15)
        )
        assert price2.pk is not None

    def test_nullable_fields(self, security):
        price = DailyPrice.objects.create(
            security=security,
            trading_date=datetime.date(2025, 1, 15),
        )
        assert price.open is None
        assert price.high is None
        assert price.low is None
        assert price.close is None
        assert price.ltp is None
        assert price.previous_close is None
        assert price.volume is None
        assert price.turnover is None
        assert price.percentage_change is None
        assert price.point_change is None

    def test_decimal_precision(self, security):
        price = DailyPrice.objects.create(
            security=security,
            trading_date=datetime.date(2025, 1, 15),
            open=decimal.Decimal("1234567890.12"),
            turnover=decimal.Decimal("9999999999999999.99"),
            percentage_change=decimal.Decimal("12.3456"),
        )
        price.refresh_from_db()
        assert price.open == decimal.Decimal("1234567890.12")
        assert price.turnover == decimal.Decimal("9999999999999999.99")
        assert price.percentage_change == decimal.Decimal("12.3456")

    def test_cascade_delete_on_security(self, security):
        DailyPrice.objects.create(
            security=security, trading_date=datetime.date(2025, 1, 15)
        )
        security.delete()
        assert DailyPrice.objects.count() == 0

    def test_ordering(self, security):
        sector = Sector.objects.create(nepse_id=2, name="Hydro")
        other = Security.objects.create(
            nepse_id=59, symbol="NHPC", company_name="NHPC", sector=sector
        )
        DailyPrice.objects.create(
            security=security, trading_date=datetime.date(2025, 1, 15)
        )
        DailyPrice.objects.create(
            security=other, trading_date=datetime.date(2025, 1, 16)
        )
        DailyPrice.objects.create(
            security=security, trading_date=datetime.date(2025, 1, 16)
        )
        prices = list(DailyPrice.objects.values_list("trading_date", "security__symbol"))
        assert prices == [
            (datetime.date(2025, 1, 16), "NABIL"),
            (datetime.date(2025, 1, 16), "NHPC"),
            (datetime.date(2025, 1, 15), "NABIL"),
        ]


@pytest.mark.django_db
class TestIntradayPriceModel:
    def test_create_intraday_price(self, security):
        ts = datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        price = IntradayPrice.objects.create(
            security=security,
            timestamp=ts,
            ltp=decimal.Decimal("1020.00"),
            volume=500,
            turnover=decimal.Decimal("510000.00"),
        )
        assert price.pk is not None
        assert price.security == security
        assert price.timestamp == ts
        assert price.ltp == decimal.Decimal("1020.00")
        assert price.volume == 500
        assert price.turnover == decimal.Decimal("510000.00")

    def test_str_representation(self, security):
        ts = datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        price = IntradayPrice.objects.create(
            security=security, timestamp=ts
        )
        assert "NABIL" in str(price)
        assert "2025" in str(price)

    def test_no_unique_constraint_on_timestamp(self, security):
        ts = datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        IntradayPrice.objects.create(security=security, timestamp=ts, ltp=decimal.Decimal("100"))
        price2 = IntradayPrice.objects.create(
            security=security, timestamp=ts, ltp=decimal.Decimal("101")
        )
        assert price2.pk is not None

    def test_nullable_fields(self, security):
        ts = datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        price = IntradayPrice.objects.create(security=security, timestamp=ts)
        assert price.ltp is None
        assert price.volume is None
        assert price.turnover is None

    def test_cascade_delete_on_security(self, security):
        ts = datetime.datetime(2025, 1, 15, 10, 30, 0, tzinfo=datetime.UTC)
        IntradayPrice.objects.create(security=security, timestamp=ts)
        security.delete()
        assert IntradayPrice.objects.count() == 0

    def test_ordering(self, security):
        ts1 = datetime.datetime(2025, 1, 15, 10, 0, 0, tzinfo=datetime.UTC)
        ts2 = datetime.datetime(2025, 1, 15, 11, 0, 0, tzinfo=datetime.UTC)
        IntradayPrice.objects.create(security=security, timestamp=ts2)
        IntradayPrice.objects.create(security=security, timestamp=ts1)
        timestamps = list(IntradayPrice.objects.values_list("timestamp", flat=True))
        assert timestamps == [ts2, ts1]
