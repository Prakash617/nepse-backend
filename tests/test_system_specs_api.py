"""Tests for system specifications and sync telemetry API."""

from __future__ import annotations

import pytest
from django.db.utils import OperationalError
from rest_framework import status
from rest_framework.test import APIClient

from apps.market.system_service import calculate_market_session, get_system_specs, trigger_feed_sync


@pytest.fixture
def api_client() -> APIClient:
    return APIClient()


@pytest.mark.django_db
class TestSystemSpecsService:
    """Test suite for system specifications calculation and telemetry service."""

    def test_get_system_specs_returns_all_keys(self) -> None:
        data = get_system_specs()
        assert "system_time" in data
        assert "market_schedule" in data
        assert "fetch_intervals" in data
        assert "infrastructure" in data
        assert "telegram_bot" in data
        assert "recent_execution_logs" in data

        # Validate system_time structure
        st = data["system_time"]
        assert "utc" in st
        assert "nepal" in st
        assert "timezone" in st
        assert "Asia/Kathmandu" in st["timezone"]

        # Validate market_schedule structure
        ms = data["market_schedule"]
        assert "trading_days" in ms
        assert "pre_open_session" in ms
        assert "regular_session" in ms
        assert "current_session" in ms
        assert ms["current_session"] in ("OPEN", "REGULAR", "PRE_OPEN", "CLOSED")

        # Validate fetch_intervals
        fi = data["fetch_intervals"]
        assert isinstance(fi, list)
        assert len(fi) >= 5

        # Confirm required sync telemetry elements
        ids = [item["id"] for item in fi]
        assert "intraday_prices" in ids
        assert "market_summary" in ids
        assert "market_indices" in ids
        assert "alerts_engine" in ids
        assert "daily_prices" in ids

        intraday = next(item for item in fi if item["id"] == "intraday_prices")
        assert intraday["interval_minutes"] == 5
        assert "Every 5 minutes" in intraday["interval_display"]
        assert intraday["trading_hours_only"] is True

        alerts = next(item for item in fi if item["id"] == "alerts_engine")
        assert alerts["interval_minutes"] == 2
        assert "Every 2 minutes" in alerts["interval_display"]

    def test_calculate_market_session_logic(self) -> None:
        from datetime import datetime
        from zoneinfo import ZoneInfo

        npt = ZoneInfo("Asia/Kathmandu")
        # Monday 11:05 AM -> PRE_OPEN
        dt_pre = datetime(2026, 10, 19, 11, 5, 0, tzinfo=npt)
        session_pre = calculate_market_session(dt_pre)
        assert session_pre["is_open"] is True
        assert session_pre["current_session"] == "PRE_OPEN"

        # Monday 12:00 PM -> REGULAR
        dt_reg = datetime(2026, 10, 19, 12, 0, 0, tzinfo=npt)
        session_reg = calculate_market_session(dt_reg)
        assert session_reg["is_open"] is True
        assert session_reg["current_session"] == "REGULAR"

        # Monday 4:00 PM -> CLOSED
        dt_close = datetime(2026, 10, 19, 16, 0, 0, tzinfo=npt)
        session_close = calculate_market_session(dt_close)
        assert session_close["is_open"] is False
        assert session_close["current_session"] == "CLOSED"

        # Saturday -> CLOSED
        dt_sat = datetime(2026, 10, 24, 12, 0, 0, tzinfo=npt)
        session_sat = calculate_market_session(dt_sat)
        assert session_sat["is_open"] is False
        assert session_sat["current_session"] == "CLOSED"

    def test_trigger_feed_sync_alerts_engine(self) -> None:
        res = trigger_feed_sync("alerts_engine")
        assert res["feed_id"] == "alerts_engine"
        assert res["status"] == "SUCCESS"
        assert "duration_ms" in res
        assert "Evaluated" in res["message"]


@pytest.mark.django_db
class TestSystemSpecsAPI:
    """Test suite for GET /api/v1/system/specs/ endpoint."""

    def test_get_system_specs_endpoint(self, api_client: APIClient) -> None:
        url = "/api/v1/system/specs/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK

        data = response.json()
        assert "system_time" in data
        assert "market_schedule" in data
        assert "fetch_intervals" in data
        assert "infrastructure" in data
        assert "telegram_bot" in data
        assert data["infrastructure"]["database"]["status"] in ("Connected", "Healthy", "Disconnected")
        assert data["infrastructure"]["cache_broker"]["status"] in ("Connected", "Healthy", "Disconnected")

    def test_post_sync_trigger_endpoint(self, api_client: APIClient) -> None:
        url = "/api/v1/system/sync/"
        response = api_client.post(url, {"feed_id": "alerts_engine"}, format="json")
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert data["feed_id"] == "alerts_engine"
        assert data["status"] == "SUCCESS"

    def test_get_sync_history_endpoint(self, api_client: APIClient) -> None:
        # Trigger one sync to generate history
        trigger_feed_sync("alerts_engine")

        url = "/api/v1/system/sync/history/"
        response = api_client.get(url)
        assert response.status_code == status.HTTP_200_OK
        data = response.json()
        assert isinstance(data, list)
        assert len(data) >= 1
        assert data[0]["feed_id"] == "alerts_engine"


@pytest.mark.django_db
class TestHealthCheckAPI:
    """Test suite for GET /api/v1/system/health/."""

    def test_health_endpoint_ok(self, api_client: APIClient) -> None:
        response = api_client.get("/api/v1/system/health/")
        assert response.status_code == status.HTTP_200_OK
        assert response.json() == {"status": "ok", "database": "ok"}

    def test_health_endpoint_reports_database_failure(
        self, api_client: APIClient, monkeypatch: pytest.MonkeyPatch
    ) -> None:
        def _raise_operational_error() -> None:
            raise OperationalError("database down")

        monkeypatch.setattr(
            "apps.market.system_views.connection.ensure_connection",
            _raise_operational_error,
        )

        response = api_client.get("/api/v1/system/health/")
        assert response.status_code == status.HTTP_503_SERVICE_UNAVAILABLE
        assert response.json()["status"] == "error"
        assert response.json()["database"] == "unavailable"
