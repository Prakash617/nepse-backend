"""Tests for security synchronization service."""
import pytest

from apps.sectors.models import Sector
from apps.securities.models import Security
from apps.securities.services import sync_securities


@pytest.fixture
def sectors():
    Sector.objects.create(nepse_id=1, name="Commercial Banks")
    Sector.objects.create(nepse_id=2, name="Hydro Power")
    Sector.objects.create(nepse_id=3, name="  Whitespace  Sector  ")


@pytest.mark.django_db
class TestSyncSecurities:
    def test_create_new_securities(self, sectors):
        data = [
            {
                "id": 58,
                "symbol": "NABIL",
                "company_name": "Nabil Bank Limited",
                "sector": "Commercial Banks",
                "security_type": "Ordinary Share",
                "listing_date": "2002-01-01",
                "paid_up_value": "100.00",
                "face_value": "100.00",
            },
            {
                "id": 59,
                "symbol": "NHPC",
                "company_name": "Nepal Hydro Power",
                "sector": "Hydro Power",
                "security_type": "Ordinary Share",
                "listing_date": None,
                "paid_up_value": None,
                "face_value": None,
            },
        ]
        result = sync_securities(data)
        assert result.created == 2
        assert result.skipped == 0
        assert Security.objects.count() == 2

    def test_sector_matching(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "sector": "Commercial Banks"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.sector.name == "Commercial Banks"

    def test_sector_matching_case_insensitive(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "sector": "commercial banks"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.sector.name == "Commercial Banks"

    def test_sector_matching_whitespace(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "sector": "  Whitespace  Sector  "},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.sector is not None

    def test_unknown_sector_leaves_null(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "sector": "Unknown Sector"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.sector is None

    def test_idempotent_sync(self, sectors):
        data = [{"id": 58, "symbol": "NABIL", "company_name": "Nabil Bank", "sector": "Commercial Banks"}]
        result1 = sync_securities(data)
        assert result1.created == 1

        result2 = sync_securities(data)
        assert result2.created == 0
        assert result2.skipped == 1
        assert Security.objects.count() == 1

    def test_update_existing_securities(self, sectors):
        data = [{"id": 58, "symbol": "NABIL", "company_name": "Old Name", "sector": "Commercial Banks"}]
        sync_securities(data)

        data_updated = [{"id": 58, "symbol": "NABIL", "company_name": "New Name", "sector": "Hydro Power"}]
        result = sync_securities(data_updated)
        assert result.updated == 1

        security = Security.objects.get(nepse_id=58)
        assert security.company_name == "New Name"
        assert security.sector.name == "Hydro Power"

    def test_skip_invalid_data(self, sectors):
        data = [
            {"id": None, "symbol": "NABIL"},
            {"id": 58, "symbol": None},
            {"id": 59, "symbol": "NHPC", "company_name": "Valid"},
        ]
        result = sync_securities(data)
        assert result.created == 1
        assert result.skipped == 2

    def test_does_not_delete_securities(self, sectors):
        data = [{"id": 58, "symbol": "NABIL", "company_name": "Nabil Bank"}]
        sync_securities(data)

        sync_securities([])
        assert Security.objects.count() == 1

    def test_listing_date_parsing(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "listing_date": "2002-01-15"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        from datetime import date
        assert security.listing_date == date(2002, 1, 15)

    def test_invalid_listing_date(self, sectors):
        data = [
            {"id": 58, "symbol": "NABIL", "company_name": "Nabil", "listing_date": "invalid-date"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.listing_date is None

    def test_decimal_fields(self, sectors):
        data = [
            {
                "id": 58,
                "symbol": "NABIL",
                "company_name": "Nabil",
                "paid_up_value": "100.50",
                "face_value": "100.00",
            },
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        from decimal import Decimal
        assert security.paid_up_value == Decimal("100.50")
        assert security.face_value == Decimal("100.00")

    def test_symbol_uppercased(self, sectors):
        data = [
            {"id": 58, "symbol": "nabil", "company_name": "Nabil"},
        ]
        sync_securities(data)
        security = Security.objects.get(nepse_id=58)
        assert security.symbol == "NABIL"
