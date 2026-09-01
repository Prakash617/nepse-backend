"""Tests for sector synchronization service."""
import pytest

from apps.common.sync import SyncResult
from apps.sectors.models import Sector
from apps.sectors.services import sync_sectors


class TestSyncResult:
    def test_sync_result_defaults(self):
        result = SyncResult()
        assert result.created == 0
        assert result.updated == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert result.errors == []
        assert result.total_processed == 0

    def test_sync_result_total_processed(self):
        result = SyncResult(created=5, updated=3, skipped=2, failed=1)
        assert result.total_processed == 11

    def test_sync_result_str(self):
        result = SyncResult(created=5, updated=3)
        s = str(result)
        assert "Created: 5" in s
        assert "Updated: 3" in s


@pytest.mark.django_db
class TestSyncSectors:
    def test_create_new_sectors(self):
        data = [
            {"id": 1, "name": "Commercial Banks", "display_name": "Commercial Banks"},
            {"id": 2, "name": "Hydro Power", "display_name": "Hydro Power"},
        ]
        result = sync_sectors(data)
        assert result.created == 2
        assert result.updated == 0
        assert result.skipped == 0
        assert result.failed == 0
        assert Sector.objects.count() == 2

    def test_idempotent_sync(self):
        data = [{"id": 1, "name": "Banks", "display_name": "Banks"}]
        result1 = sync_sectors(data)
        assert result1.created == 1

        result2 = sync_sectors(data)
        assert result2.created == 0
        assert result2.updated == 0
        assert result2.skipped == 1
        assert Sector.objects.count() == 1

    def test_update_existing_sectors(self):
        data = [{"id": 1, "name": "Banks", "display_name": "Old Name"}]
        sync_sectors(data)

        data_updated = [{"id": 1, "name": "Banks", "display_name": "New Name"}]
        result = sync_sectors(data_updated)
        assert result.updated == 1
        assert result.skipped == 0

        sector = Sector.objects.get(nepse_id=1)
        assert sector.display_name == "New Name"

    def test_skip_invalid_data(self):
        data = [
            {"id": None, "name": "Banks"},
            {"id": 1, "name": None},
            {"id": 2, "name": "Valid Sector"},
        ]
        result = sync_sectors(data)
        assert result.created == 1
        assert result.skipped == 2
        assert len(result.errors) == 2

    def test_does_not_delete_sectors(self):
        data = [{"id": 1, "name": "Banks"}]
        sync_sectors(data)

        result = sync_sectors([])
        assert result.created == 0
        assert Sector.objects.count() == 1

    def test_multiple_syncs_no_duplicates(self):
        data = [
            {"id": 1, "name": "Banks"},
            {"id": 2, "name": "Hydro"},
        ]
        sync_sectors(data)
        sync_sectors(data)
        sync_sectors(data)
        assert Sector.objects.count() == 2

    def test_ordering(self):
        data = [
            {"id": 2, "name": "Z Sector"},
            {"id": 1, "name": "A Sector"},
        ]
        sync_sectors(data)
        sectors = list(Sector.objects.values_list("name", flat=True))
        assert sectors == ["A Sector", "Z Sector"]
