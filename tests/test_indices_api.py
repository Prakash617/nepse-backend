"""Tests for index API endpoints."""
from datetime import date
from decimal import Decimal

import pytest
from rest_framework.test import APIClient

from apps.indices.models import IndexSnapshot, MarketIndex


@pytest.fixture
def api_client():
    return APIClient()


@pytest.fixture
def indices_data():
    MarketIndex.objects.create(nepse_id=58, name="NEPSE Index")
    MarketIndex.objects.create(nepse_id=59, name="Sensitive Index")


@pytest.mark.django_db
class TestIndexList:
    def test_list_indices(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/")
        assert response.status_code == 200
        assert len(response.data) == 2

    def test_index_ordering(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/")
        assert response.data[0]["nepse_id"] == 58
        assert response.data[1]["nepse_id"] == 59


@pytest.mark.django_db
class TestIndexDetail:
    def test_get_index(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/58/")
        assert response.status_code == 200
        assert response.data["name"] == "NEPSE Index"

    def test_unknown_index(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/999/")
        assert response.status_code == 404


@pytest.mark.django_db
class TestIndexHistory:
    def test_empty_history(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/58/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0

    def test_history_with_data(self, api_client, indices_data):
        index = MarketIndex.objects.get(nepse_id=58)
        IndexSnapshot.objects.create(
            index=index,
            trading_date=date(2026, 1, 15),
            open=Decimal("2000.0000"),
            high=Decimal("2050.0000"),
            low=Decimal("1990.0000"),
            close=Decimal("2030.0000"),
            volume=1000000,
            turnover=Decimal("2030000000.00"),
        )
        response = api_client.get("/api/v1/indices/58/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_history_date_filter(self, api_client, indices_data):
        index = MarketIndex.objects.get(nepse_id=58)
        IndexSnapshot.objects.create(
            index=index,
            trading_date=date(2026, 1, 15),
            close=Decimal("2000.0000"),
        )
        IndexSnapshot.objects.create(
            index=index,
            trading_date=date(2026, 2, 15),
            close=Decimal("2100.0000"),
        )
        response = api_client.get("/api/v1/indices/58/history/?start=2026-02-01")
        assert response.status_code == 200
        assert len(response.data["results"]) == 1

    def test_unknown_index_history(self, api_client, indices_data):
        response = api_client.get("/api/v1/indices/999/history/")
        assert response.status_code == 200
        assert len(response.data["results"]) == 0
