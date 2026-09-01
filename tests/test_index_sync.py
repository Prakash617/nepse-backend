"""Tests for index synchronization service."""
import decimal

import pytest

from apps.indices.models import IndexSnapshot, MarketIndex
from apps.indices.services import sync_index_snapshots, sync_indices


@pytest.mark.django_db
class TestSyncIndices:
    def test_create_new_indices(self):
        data = [
            {"id": 58, "name": "NEPSE Index"},
            {"id": 59, "name": "Sensitive Index"},
        ]
        result = sync_indices(data)
        assert result.created == 2
        assert result.skipped == 0
        assert MarketIndex.objects.count() == 2

    def test_idempotent_sync(self):
        data = [{"id": 58, "name": "NEPSE Index"}]
        result1 = sync_indices(data)
        assert result1.created == 1

        result2 = sync_indices(data)
        assert result2.created == 0
        assert result2.skipped == 1
        assert MarketIndex.objects.count() == 1

    def test_update_existing_indices(self):
        data = [{"id": 58, "name": "Old Name"}]
        sync_indices(data)

        data_updated = [{"id": 58, "name": "New Name"}]
        result = sync_indices(data_updated)
        assert result.updated == 1

        idx = MarketIndex.objects.get(nepse_id=58)
        assert idx.name == "New Name"

    def test_skip_invalid_data(self):
        data = [
            {"id": None, "name": "Index"},
            {"id": 58, "name": None},
            {"id": 59, "name": "Valid Index"},
        ]
        result = sync_indices(data)
        assert result.created == 1
        assert result.skipped == 2

    def test_does_not_delete_indices(self):
        data = [{"id": 58, "name": "NEPSE Index"}]
        sync_indices(data)

        sync_indices([])
        assert MarketIndex.objects.count() == 1

    def test_mixed_nepse_and_sector_indices(self):
        data = [
            {"id": 58, "name": "NEPSE Index"},
            {"id": 60, "name": "Banking Sub Index"},
        ]
        result = sync_indices(data)
        assert result.created == 2


@pytest.mark.django_db
class TestSyncIndexSnapshots:
    def _make_index(self, nepse_id=58, name="NEPSE Index"):
        return MarketIndex.objects.create(nepse_id=nepse_id, name=name)

    def test_create_snapshots(self):
        self._make_index()
        data = [
            {
                "business_date": "2025-01-15",
                "open": "2000.1234",
                "high": "2050.5678",
                "low": "1980.0000",
                "close": "2020.1234",
                "volume": 5000000,
                "turnover": "1000000000.00",
            },
        ]
        result = sync_index_snapshots(58, data)
        assert result.created == 1
        assert IndexSnapshot.objects.count() == 1

    def test_idempotent_sync(self):
        self._make_index()
        data = [{"business_date": "2025-01-15", "close": "2000.0000"}]
        result1 = sync_index_snapshots(58, data)
        assert result1.created == 1

        result2 = sync_index_snapshots(58, data)
        assert result2.created == 0
        assert result2.skipped == 1
        assert IndexSnapshot.objects.count() == 1

    def test_update_existing_snapshots(self):
        self._make_index()
        data = [{"business_date": "2025-01-15", "close": "2000.0000"}]
        sync_index_snapshots(58, data)

        data_updated = [{"business_date": "2025-01-15", "close": "2100.0000"}]
        result = sync_index_snapshots(58, data_updated)
        assert result.updated == 1

        snap = IndexSnapshot.objects.first()
        assert snap.close == decimal.Decimal("2100.0000")

    def test_missing_index_fails(self):
        data = [{"business_date": "2025-01-15", "close": "2000.0000"}]
        result = sync_index_snapshots(999, data)
        assert result.failed == 1
        assert len(result.errors) == 1

    def test_missing_date_skipped(self):
        self._make_index()
        data = [{"business_date": None, "close": "2000.0000"}]
        result = sync_index_snapshots(58, data)
        assert result.skipped == 1

    def test_preserves_historical_data(self):
        self._make_index()
        old_data = [{"business_date": "2024-06-01", "close": "1800.0000"}]
        sync_index_snapshots(58, old_data)

        new_data = [{"business_date": "2025-01-15", "close": "2000.0000"}]
        sync_index_snapshots(58, new_data)

        assert IndexSnapshot.objects.count() == 2
