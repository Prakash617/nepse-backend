"""Tests for market API endpoints."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.market.models import MarketSnapshot
from apps.prices.models import DailyPrice
from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def market_data():
    sector = Sector.objects.create(nepse_id=1, name="Commercial Banks")
    nabil = Security.objects.create(
        nepse_id=58, symbol="NABIL", company_name="Nabil Bank", sector=sector
    )
    nicl = Security.objects.create(
        nepse_id=59, symbol="NICL", company_name="Nepal Insurance", sector=sector
    )

    MarketSnapshot.objects.create(
        trading_date=date(2026, 1, 15),
        total_volume=10000000,
        total_turnover=Decimal("15000000000.00"),
        transactions=50000,
        open=Decimal("2000.0000"),
        high=Decimal("2050.0000"),
        low=Decimal("1990.0000"),
        close=Decimal("2030.0000"),
        previous_close=Decimal("2000.0000"),
        point_change=Decimal("30.0000"),
        percentage_change=Decimal("1.5000"),
    )

    DailyPrice.objects.create(
        security=nabil,
        trading_date=date(2026, 1, 15),
        open=Decimal("100.00"),
        high=Decimal("105.00"),
        low=Decimal("99.00"),
        close=Decimal("103.00"),
        ltp=Decimal("103.00"),
        previous_close=Decimal("100.00"),
        volume=1000000,
        turnover=Decimal("103000000.00"),
        percentage_change=Decimal("3.0000"),
    )

    DailyPrice.objects.create(
        security=nicl,
        trading_date=date(2026, 1, 15),
        open=Decimal("50.00"),
        high=Decimal("52.00"),
        low=Decimal("48.00"),
        close=Decimal("49.00"),
        ltp=Decimal("49.00"),
        previous_close=Decimal("50.00"),
        volume=2000000,
        turnover=Decimal("98000000.00"),
        percentage_change=Decimal("-2.0000"),
    )


@pytest.mark.django_db
class TestMarketSummary:
    def test_summary_with_data(self, api_client, market_data):
        response = api_client.get("/api/v1/market/summary/")
        assert response.status_code == 200
        assert response.data["trading_date"] == "2026-01-15"
        assert response.data["total_volume"] == 10000000

    def test_summary_empty_database(self, api_client):
        response = api_client.get("/api/v1/market/summary/")
        assert response.status_code == 200
        assert "detail" in response.data


@pytest.mark.django_db
class TestMarketGainers:
    def test_gainers(self, api_client, market_data):
        response = api_client.get("/api/v1/market/gainers/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["symbol"] == "NABIL"
        assert float(response.data["results"][0]["percentage_change"]) == 3.0

    def test_gainers_empty_database(self, api_client):
        response = api_client.get("/api/v1/market/gainers/")
        assert response.status_code == 200
        assert response.data["results"] == []

    def test_gainers_limit(self, api_client, market_data):
        response = api_client.get("/api/v1/market/gainers/?limit=1")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1


@pytest.mark.django_db
class TestMarketLosers:
    def test_losers(self, api_client, market_data):
        response = api_client.get("/api/v1/market/losers/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["symbol"] == "NICL"
        assert float(response.data["results"][0]["percentage_change"]) == -2.0

    def test_losers_empty_database(self, api_client):
        response = api_client.get("/api/v1/market/losers/")
        assert response.status_code == 200
        assert response.data["results"] == []


@pytest.mark.django_db
class TestMarketTurnover:
    def test_turnover(self, api_client, market_data):
        response = api_client.get("/api/v1/market/turnover/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["symbol"] == "NABIL"

    def test_turnover_empty_database(self, api_client):
        response = api_client.get("/api/v1/market/turnover/")
        assert response.status_code == 200
        assert response.data["results"] == []


@pytest.mark.django_db
class TestMarketVolume:
    def test_volume(self, api_client, market_data):
        response = api_client.get("/api/v1/market/volume/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2
        assert response.data["results"][0]["symbol"] == "NICL"

    def test_volume_empty_database(self, api_client):
        response = api_client.get("/api/v1/market/volume/")
        assert response.status_code == 200
        assert response.data["results"] == []
