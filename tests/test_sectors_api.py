"""Tests for sector API endpoints."""

import pytest
from rest_framework.test import APIClient

from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sectors_data():
    Sector.objects.create(nepse_id=1, name="Commercial Banks", display_name="Commercial Banks Sector")
    Sector.objects.create(nepse_id=2, name="Hydro Power", display_name="Hydro Power Sector")


@pytest.mark.django_db
class TestSectorList:
    def test_list_sectors(self, api_client, sectors_data):
        response = api_client.get("/api/v1/sectors/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_sector_ordering(self, api_client, sectors_data):
        response = api_client.get("/api/v1/sectors/")
        assert response.data[0]["name"] == "Commercial Banks"
        assert response.data[1]["name"] == "Hydro Power"

    def test_sector_security_count(self, api_client, sectors_data):
        sector = Sector.objects.get(name="Commercial Banks")
        Security.objects.create(
            nepse_id=58,
            symbol="NABIL",
            company_name="Nabil Bank",
            sector=sector,
        )
        response = api_client.get("/api/v1/sectors/")
        commercial = next(s for s in response.data if s["name"] == "Commercial Banks")
        assert commercial["security_count"] == 1

    def test_empty_sectors(self, api_client):
        response = api_client.get("/api/v1/sectors/")
        assert response.status_code == 200
        assert len(response.data) == 0
