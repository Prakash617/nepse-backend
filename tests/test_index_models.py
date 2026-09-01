"""Tests for MarketIndex and IndexSnapshot models."""
import datetime
import decimal

import pytest
from django.db import IntegrityError

from apps.indices.models import IndexSnapshot, MarketIndex


@pytest.mark.django_db
class TestMarketIndexModel:
    def test_create_market_index(self):
        index = MarketIndex.objects.create(
            nepse_id=58,
            name="NEPSE Index",
        )
        assert index.pk is not None
        assert index.nepse_id == 58
        assert index.name == "NEPSE Index"
        assert index.created_at is not None
        assert index.updated_at is not None

    def test_str_representation(self):
        index = MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        assert str(index) == "NEPSE Index"

    def test_nepse_id_unique(self):
        MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        with pytest.raises(IntegrityError):
            MarketIndex.objects.create(nepse_id=58, name="Other Index")

    def test_name_unique(self):
        MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
        with pytest.raises(IntegrityError):
            MarketIndex.objects.create(nepse_id=59, name="NEPSE Index")

    def test_ordering(self):
        MarketIndex.objects.create(nepse_id=60, name="Z Index")
        MarketIndex.objects.create(nepse_id=58, name="A Index")
        names = list(MarketIndex.objects.values_list("name", flat=True))
        assert names == ["A Index", "Z Index"]

    def test_verbose_name(self):
        assert MarketIndex._meta.verbose_name == "Market Index"
        assert MarketIndex._meta.verbose_name_plural == "Market Indices"


@pytest.mark.django_db
class TestIndexSnapshotModel:
    def _make_index(self, **kwargs):
        defaults = {"nepse_id": 58, "name": "NEPSE Index"}
        defaults.update(kwargs)
        return MarketIndex.objects.create(**defaults)

    def test_create_index_snapshot(self):
        index = self._make_index()
        snapshot = IndexSnapshot.objects.create(
            index=index,
            trading_date=datetime.date(2025, 1, 15),
            open=decimal.Decimal("2000.1234"),
            high=decimal.Decimal("2050.5678"),
            low=decimal.Decimal("1980.0000"),
            close=decimal.Decimal("2020.1234"),
            volume=5000000,
            turnover=decimal.Decimal("1000000000.00"),
            point_change=decimal.Decimal("20.1234"),
            percentage_change=decimal.Decimal("1.0050"),
        )
        assert snapshot.pk is not None
        assert snapshot.index == index
        assert snapshot.trading_date == datetime.date(2025, 1, 15)
        assert snapshot.open == decimal.Decimal("2000.1234")
        assert snapshot.close == decimal.Decimal("2020.1234")
        assert snapshot.volume == 5000000

    def test_str_representation(self):
        index = self._make_index()
        snapshot = IndexSnapshot.objects.create(
            index=index,
            trading_date=datetime.date(2025, 1, 15),
        )
        assert str(snapshot) == "NEPSE Index on 2025-01-15"

    def test_unique_constraint_index_date(self):
        index = self._make_index()
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 15)
        )
        with pytest.raises(IntegrityError):
            IndexSnapshot.objects.create(
                index=index, trading_date=datetime.date(2025, 1, 15)
            )

    def test_same_date_different_index(self):
        idx1 = self._make_index(nepse_id=58, name="NEPSE")
        idx2 = self._make_index(nepse_id=59, name="Sensitive")
        IndexSnapshot.objects.create(
            index=idx1, trading_date=datetime.date(2025, 1, 15)
        )
        snap2 = IndexSnapshot.objects.create(
            index=idx2, trading_date=datetime.date(2025, 1, 15)
        )
        assert snap2.pk is not None

    def test_nullable_fields(self):
        index = self._make_index()
        snapshot = IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 15)
        )
        assert snapshot.open is None
        assert snapshot.high is None
        assert snapshot.low is None
        assert snapshot.close is None
        assert snapshot.volume is None
        assert snapshot.turnover is None
        assert snapshot.point_change is None
        assert snapshot.percentage_change is None

    def test_decimal_precision(self):
        index = self._make_index()
        snapshot = IndexSnapshot.objects.create(
            index=index,
            trading_date=datetime.date(2025, 1, 15),
            open=decimal.Decimal("12345.1234"),
            percentage_change=decimal.Decimal("12.3456"),
        )
        snapshot.refresh_from_db()
        assert snapshot.open == decimal.Decimal("12345.1234")
        assert snapshot.percentage_change == decimal.Decimal("12.3456")

    def test_cascade_delete_on_index(self):
        index = self._make_index()
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 15)
        )
        index.delete()
        assert IndexSnapshot.objects.count() == 0

    def test_ordering(self):
        index = self._make_index()
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 15)
        )
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 16)
        )
        dates = list(IndexSnapshot.objects.values_list("trading_date", flat=True))
        assert dates == [datetime.date(2025, 1, 16), datetime.date(2025, 1, 15)]

    def test_related_name(self):
        index = self._make_index()
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 15)
        )
        IndexSnapshot.objects.create(
            index=index, trading_date=datetime.date(2025, 1, 16)
        )
        assert index.snapshots.count() == 2
