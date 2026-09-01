"""Tests for MarketSnapshot model."""
import datetime
import decimal

import pytest
from django.db import IntegrityError

from apps.market.models import MarketSnapshot


@pytest.mark.django_db
class TestMarketSnapshotModel:
    def test_create_market_snapshot(self):
        snapshot = MarketSnapshot.objects.create(
            trading_date=datetime.date(2025, 1, 15),
            total_volume=10000000,
            total_turnover=decimal.Decimal("5000000000.00"),
            transactions=25000,
            open=decimal.Decimal("2000.1234"),
            high=decimal.Decimal("2050.5678"),
            low=decimal.Decimal("1980.0000"),
            close=decimal.Decimal("2020.1234"),
            previous_close=decimal.Decimal("2000.0000"),
            point_change=decimal.Decimal("20.1234"),
            percentage_change=decimal.Decimal("1.0067"),
        )
        assert snapshot.pk is not None
        assert snapshot.trading_date == datetime.date(2025, 1, 15)
        assert snapshot.total_volume == 10000000
        assert snapshot.total_turnover == decimal.Decimal("5000000000.00")
        assert snapshot.transactions == 25000
        assert snapshot.close == decimal.Decimal("2020.1234")

    def test_str_representation(self):
        snapshot = MarketSnapshot.objects.create(
            trading_date=datetime.date(2025, 1, 15),
        )
        assert str(snapshot) == "Market on 2025-01-15"

    def test_unique_constraint_trading_date(self):
        MarketSnapshot.objects.create(trading_date=datetime.date(2025, 1, 15))
        with pytest.raises(IntegrityError):
            MarketSnapshot.objects.create(trading_date=datetime.date(2025, 1, 15))

    def test_nullable_fields(self):
        snapshot = MarketSnapshot.objects.create(
            trading_date=datetime.date(2025, 1, 15),
        )
        assert snapshot.total_volume is None
        assert snapshot.total_turnover is None
        assert snapshot.transactions is None
        assert snapshot.open is None
        assert snapshot.high is None
        assert snapshot.low is None
        assert snapshot.close is None
        assert snapshot.previous_close is None
        assert snapshot.point_change is None
        assert snapshot.percentage_change is None

    def test_decimal_precision(self):
        snapshot = MarketSnapshot.objects.create(
            trading_date=datetime.date(2025, 1, 15),
            total_turnover=decimal.Decimal("9999999999999999.99"),
            close=decimal.Decimal("12345.1234"),
            percentage_change=decimal.Decimal("12.3456"),
        )
        snapshot.refresh_from_db()
        assert snapshot.total_turnover == decimal.Decimal("9999999999999999.99")
        assert snapshot.close == decimal.Decimal("12345.1234")
        assert snapshot.percentage_change == decimal.Decimal("12.3456")

    def test_ordering(self):
        MarketSnapshot.objects.create(trading_date=datetime.date(2025, 1, 15))
        MarketSnapshot.objects.create(trading_date=datetime.date(2025, 1, 16))
        dates = list(MarketSnapshot.objects.values_list("trading_date", flat=True))
        assert dates == [datetime.date(2025, 1, 16), datetime.date(2025, 1, 15)]

    def test_verbose_name(self):
        assert MarketSnapshot._meta.verbose_name == "Market Snapshot"
        assert MarketSnapshot._meta.verbose_name_plural == "Market Snapshots"
