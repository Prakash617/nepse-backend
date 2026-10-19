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


@pytest.mark.django_db
class TestIndexIntraday:
    def test_get_intraday_data_mocked(self, api_client, indices_data, monkeypatch):
        class MockClient:
            def get_live_index(self, index_id=58):
                return [[1792127100, 2626.42], [1792142040, 2636.20]]

            def _request(self, method, path):
                if "nepse-index" in path:
                    return [{
                        "id": 58,
                        "index": "NEPSE Index",
                        "currentValue": 2634.17,
                        "change": 8.23,
                        "perChange": 0.31,
                        "high": 2638.42,
                        "low": 2622.78,
                        "close": 2625.93,
                        "previousClose": 2634.17,
                    }]
                if "market-summary" in path:
                    return [
                        {"detail": "Total Turnover Rs:", "value": 4880089108.16},
                        {"detail": "Total Traded Shares", "value": 13376489.0},
                        {"detail": "Total Transactions", "value": 39295.0},
                    ]
                return []

            def get_security_daily_trade_stat(self, index_id=58):
                return [
                    {"symbol": "A", "percentageChange": 2.5},
                    {"symbol": "B", "percentageChange": -1.2},
                    {"symbol": "C", "percentageChange": 0.0},
                ]

        from django.core.cache import cache
        cache.clear()
        monkeypatch.setattr("apps.indices.services.NepseClient", lambda: MockClient())

        response = api_client.get("/api/v1/indices/58/intraday/")
        assert response.status_code == 200
        assert response.data["nepse_id"] == 58
        assert response.data["name"] == "NEPSE Index"
        assert response.data["current_value"] == 2634.17
        assert response.data["point_change"] == 8.23
        assert response.data["percentage_change"] == 0.31
        assert response.data["total_turnover"] == 4880089108.16
        assert response.data["total_shares"] == 13376489
        assert response.data["breadth"]["advanced"] == 1
        assert response.data["breadth"]["declined"] == 1
        assert response.data["breadth"]["unchanged"] == 1
        assert len(response.data["points"]) == 2
        assert response.data["points"][0]["value"] == 2626.42

    def test_get_intraday_fallback(self, api_client, indices_data, monkeypatch):
        class FailingClient:
            def get_live_index(self, index_id=58):
                raise Exception("Upstream down")

            def _request(self, method, path):
                raise Exception("Upstream down")

            def get_security_daily_trade_stat(self, index_id=58):
                raise Exception("Upstream down")

        from django.core.cache import cache
        cache.clear()
        monkeypatch.setattr("apps.indices.services.NepseClient", lambda: FailingClient())

        response = api_client.get("/api/v1/indices/58/intraday/")
        assert response.status_code == 200
        assert response.data["nepse_id"] == 58
        assert response.data["name"] == "NEPSE Index"

