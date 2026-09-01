"""Tests for security API endpoints."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.prices.models import DailyPrice, IntradayPrice
from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def sector_data():
    return Sector.objects.create(
        nepse_id=1,
        name="Commercial Banks",
        display_name="Commercial Banks Sector",
    )


@pytest.fixture
def securities_data(sector_data):
    Security.objects.create(
        nepse_id=58,
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        sector=sector_data,
        security_type="Ordinary Share",
        listing_date=date(2002, 1, 1),
        paid_up_value=Decimal("100.00"),
        face_value=Decimal("100.00"),
    )
    Security.objects.create(
        nepse_id=59,
        symbol="NHPC",
        company_name="Nepal Hydro Power",
        sector=sector_data,
        security_type="Ordinary Share",
    )


@pytest.mark.django_db
class TestSecurityList:
    def test_list_securities(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_search_by_symbol(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/?search=NABIL")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["symbol"] == "NABIL"

    def test_filter_by_sector(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/?sector=Commercial")
        assert response.status_code == 200
        assert len(response.data["results"]) == 2

    def test_ordering(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/?ordering=-symbol")
        assert response.status_code == 200
        assert response.data["results"][0]["symbol"] == "NHPC"

    def test_empty_search(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/?search=NONEXISTENT")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
class TestSecurityDetail:
    def test_get_security_by_symbol(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NABIL/")
        assert response.status_code == 200
        assert response.data["symbol"] == "NABIL"
        assert response.data["company_name"] == "Nabil Bank Limited"
        assert response.data["sector"]["name"] == "Commercial Banks"

    def test_unknown_symbol(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NONEXISTENT/")
        assert response.status_code == 404

    def test_case_insensitive_lookup(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/nabil/")
        assert response.status_code == 200
        assert response.data["symbol"] == "NABIL"


@pytest.mark.django_db
class TestSecurityHistory:
    def test_empty_history(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NABIL/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_history_with_data(self, api_client, securities_data):
        security = Security.objects.get(symbol="NABIL")
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 1, 15),
            open=Decimal("100.00"),
            high=Decimal("105.00"),
            low=Decimal("99.00"),
            close=Decimal("103.00"),
            ltp=Decimal("103.00"),
            volume=1000000,
            turnover=Decimal("103000000.00"),
        )
        response = api_client.get("/api/v1/securities/NABIL/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_history_date_filter(self, api_client, securities_data):
        security = Security.objects.get(symbol="NABIL")
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 1, 15),
            close=Decimal("103.00"),
        )
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 2, 15),
            close=Decimal("110.00"),
        )
        response = api_client.get(
            "/api/v1/securities/NABIL/history/?start=2026-02-01"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1
        assert response.data["results"][0]["trading_date"] == "2026-02-15"

    def test_history_date_range(self, api_client, securities_data):
        security = Security.objects.get(symbol="NABIL")
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 1, 15),
            close=Decimal("100.00"),
        )
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 2, 15),
            close=Decimal("110.00"),
        )
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 3, 15),
            close=Decimal("120.00"),
        )
        response = api_client.get(
            "/api/v1/securities/NABIL/history/?start=2026-02-01&end=2026-02-28"
        )
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_history_chronological_order(self, api_client, securities_data):
        security = Security.objects.get(symbol="NABIL")
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 3, 15),
            close=Decimal("120.00"),
        )
        DailyPrice.objects.create(
            security=security,
            trading_date=date(2026, 1, 15),
            close=Decimal("100.00"),
        )
        response = api_client.get("/api/v1/securities/NABIL/history/")
        assert response.data["results"][0]["trading_date"] == "2026-01-15"
        assert response.data["results"][1]["trading_date"] == "2026-03-15"

    def test_unknown_security_history(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NONEXISTENT/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0


@pytest.mark.django_db
class TestSecurityIntraday:
    def test_empty_intraday(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NABIL/intraday/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_intraday_with_data(self, api_client, securities_data):
        from datetime import datetime
        security = Security.objects.get(symbol="NABIL")
        IntradayPrice.objects.create(
            security=security,
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            ltp=Decimal("103.00"),
            volume=100,
            turnover=Decimal("10300.00"),
        )
        response = api_client.get("/api/v1/securities/NABIL/intraday/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_intraday_ordering(self, api_client, securities_data):
        from datetime import datetime
        security = Security.objects.get(symbol="NABIL")
        IntradayPrice.objects.create(
            security=security,
            timestamp=datetime(2026, 1, 15, 10, 30, 0),
            ltp=Decimal("103.00"),
        )
        IntradayPrice.objects.create(
            security=security,
            timestamp=datetime(2026, 1, 15, 10, 31, 0),
            ltp=Decimal("104.00"),
        )
        response = api_client.get("/api/v1/securities/NABIL/intraday/")
        assert response.data["results"][0]["timestamp"] > response.data["results"][1]["timestamp"]

    def test_unknown_security_intraday(self, api_client, securities_data):
        response = api_client.get("/api/v1/securities/NONEXISTENT/intraday/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0
