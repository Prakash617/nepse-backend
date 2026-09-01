"""Tests for NepseClient with mocked HTTP responses.

All tests mock the upstream NEPSE API — no real calls are made.
"""

import json
from pathlib import Path
from unittest.mock import MagicMock, patch

import pytest

from integrations.nepse.client import NepseClient
from integrations.nepse.exceptions import (
    NepseAuthenticationError,
    NepseConnectionError,
    NepseInvalidResponseError,
    NepseRateLimitError,
    NepseServerError,
    NepseSSLError,
    NepseTimeoutError,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nepse"


def _load_fixture(name: str) -> dict | list:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


def _mock_response(json_data: dict | list, status_code: int = 200) -> MagicMock:
    """Create a mock requests.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


class TestClientInitialization:
    def test_default_initialization(self) -> None:
        client = NepseClient()
        assert client._base_url == "https://www.nepalstock.com"
        assert client._timeout == 30

    def test_custom_initialization(self) -> None:
        client = NepseClient(
            base_url="https://custom.example.com",
            timeout=60,
            max_retries=5,
        )
        assert client._base_url == "https://custom.example.com"
        assert client._timeout == 60

    def test_ssl_verify_disabled(self) -> None:
        client = NepseClient(verify_ssl=False)
        assert client._session.verify is False


class TestAuthentication:
    def test_authenticate_success(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        market_response = _load_fixture("market_status.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(market_response)

            client._ensure_authenticated()
            assert client._access_token is not None
            assert client._token_details is not None

    def test_authenticate_ssl_error(self) -> None:
        import requests
        client = NepseClient()

        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = requests.exceptions.SSLError("SSL error")
            with pytest.raises(NepseSSLError):
                client._ensure_authenticated()

    def test_authenticate_connection_error(self) -> None:
        import requests
        client = NepseClient()

        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = requests.exceptions.ConnectionError("Connection refused")
            with pytest.raises(NepseConnectionError):
                client._ensure_authenticated()

    def test_authenticate_timeout(self) -> None:
        import requests
        client = NepseClient()

        with patch.object(client._session, "request") as mock_request:
            mock_request.side_effect = requests.exceptions.Timeout("Timeout")
            with pytest.raises(NepseTimeoutError):
                client._ensure_authenticated()

    def test_authenticate_401(self) -> None:
        import requests
        client = NepseClient()

        with patch.object(client._session, "request") as mock_request:
            mock_response = MagicMock()
            mock_response.status_code = 401
            error = requests.exceptions.HTTPError(response=mock_response)
            mock_request.side_effect = error
            with pytest.raises(NepseAuthenticationError):
                client._ensure_authenticated()

    def test_authenticate_caches_token(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")

        with patch.object(client._session, "request") as mock_request:
            mock_request.return_value = _mock_response(auth_response)
            client._ensure_authenticated()

            # Second call should not trigger a new request
            client._ensure_authenticated()
            assert mock_request.call_count == 1

    def test_reset_auth_clears_state(self) -> None:
        client = NepseClient()
        client._access_token = "test_token"
        client._token_details = {"salt1": 1}
        client._market_open_id = 123

        client._reset_auth()
        assert client._access_token is None
        assert client._token_details is None
        assert client._market_open_id is None


class TestGetMarketStatus:
    def test_get_market_status(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        market_response = _load_fixture("market_status.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(market_response)

            result = client.get_market_status()
            assert result["is_open"] is True
            assert result["id"] == 42


class TestGetMarketSummary:
    def test_get_market_summary(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        summary_response = _load_fixture("market_summary.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(summary_response)

            result = client.get_market_summary()
            assert result["total_traded_volume"] == 15000000
            assert result["close"] == 2830.00


class TestGetSecurities:
    def test_get_securities(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        securities_response = _load_fixture("securities.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(securities_response)

            result = client.get_securities()
            assert len(result) == 2
            assert result[0]["symbol"] == "NABIL"


class TestGetTodayPrices:
    def test_get_today_prices(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        market_response = _load_fixture("market_status.json")
        prices_response = _load_fixture("today_prices.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get, \
             patch.object(client._session, "post") as mock_post:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(market_response)
            mock_post.return_value = _mock_response(prices_response)

            result = client.get_today_prices()
            assert len(result) == 2
            assert result[0]["symbol"] == "NABIL"
            assert result[0]["ltp"] == 950.00


class TestGetIndices:
    def test_get_indices(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        indices_response = _load_fixture("indices.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(indices_response)

            result = client.get_indices()
            assert len(result) == 2
            assert result[0]["name"] == "NEPSE Index"


class TestGetSectorIndices:
    def test_get_sector_indices(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        data = _load_fixture("sector_indices.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(data)

            result = client.get_sector_indices()
            assert len(result) == 2


class TestGetSectors:
    def test_get_sectors(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        sectors_response = _load_fixture("sectors.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(sectors_response)

            result = client.get_sectors()
            assert len(result) == 2
            assert result[0]["name"] == "Banking"


class TestGetTopStocks:
    def test_get_top_gainers(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        gainers_response = _load_fixture("top_gainers.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(gainers_response)

            result = client.get_top_stocks("top_gainer")
            assert len(result) == 2
            assert result[0]["symbol"] == "NABIL"

    def test_invalid_category_raises(self) -> None:
        client = NepseClient()
        with pytest.raises(ValueError, match="Invalid category"):
            client.get_top_stocks("invalid_category")


class TestGetIndexHistory:
    def test_get_index_history(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        history_response = _load_fixture("index_history.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(history_response)

            result = client.get_index_history(58, "2026-01-01", "2026-01-31")
            assert len(result) == 2

    def test_invalid_index_id_raises(self) -> None:
        client = NepseClient()
        with pytest.raises(ValueError, match="not valid"):
            client.get_index_history(100, "2026-01-01", "2026-01-31")


class TestGetBrokers:
    def test_get_brokers(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        brokers_response = _load_fixture("brokers.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "post") as mock_post:
            mock_request.return_value = _mock_response(auth_response)
            mock_post.return_value = _mock_response(brokers_response)

            result = client.get_brokers()
            assert len(result) == 2
            assert result[0]["name"] == "Nabil Capital"


class TestGetNotices:
    def test_get_notices(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        notices_response = _load_fixture("notices.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(notices_response)

            result = client.get_notices()
            assert len(result) == 1
            assert result[0]["title"] == "Notice about trading hours"


class TestErrorHandling:
    def test_http_401_resets_auth(self) -> None:
        import requests
        client = NepseClient()
        client._access_token = "old_token"

        with patch.object(client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 401
            error = requests.exceptions.HTTPError(response=mock_response)
            mock_get.side_effect = error

            with pytest.raises(NepseAuthenticationError):
                client._get("/api/test")
            assert client._access_token is None

    def test_http_429_raises_rate_limit(self) -> None:
        import requests
        client = NepseClient()
        client._access_token = "token"

        with patch.object(client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 429
            error = requests.exceptions.HTTPError(response=mock_response)
            mock_get.side_effect = error

            with pytest.raises(NepseRateLimitError):
                client._get("/api/test")

    def test_http_500_raises_server_error(self) -> None:
        import requests
        client = NepseClient()
        client._access_token = "token"

        with patch.object(client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 500
            error = requests.exceptions.HTTPError(response=mock_response)
            mock_get.side_effect = error

            with pytest.raises(NepseServerError):
                client._get("/api/test")

    def test_invalid_json_raises(self) -> None:
        client = NepseClient()
        client._access_token = "token"

        with patch.object(client._session, "get") as mock_get:
            mock_response = MagicMock()
            mock_response.status_code = 200
            mock_response.raise_for_status.return_value = None
            mock_response.json.side_effect = ValueError("No JSON")
            mock_get.return_value = mock_response

            with pytest.raises(NepseInvalidResponseError, match="Invalid JSON"):
                client._get("/api/test")

    def test_connection_error(self) -> None:
        import requests
        client = NepseClient()
        client._access_token = "token"

        with patch.object(client._session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.ConnectionError("Connection refused")

            with pytest.raises(NepseConnectionError):
                client._get("/api/test")

    def test_timeout_error(self) -> None:
        import requests
        client = NepseClient()
        client._access_token = "token"

        with patch.object(client._session, "get") as mock_get:
            mock_get.side_effect = requests.exceptions.Timeout("Timeout")

            with pytest.raises(NepseTimeoutError):
                client._get("/api/test")


class TestLiveTrades:
    def test_returns_empty_when_market_closed(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        closed_response = _load_fixture("market_status_closed.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(closed_response)

            result = client.get_live_trades()
            assert result == []


class TestGetTickerInfo:
    def test_empty_ticker_raises(self) -> None:
        client = NepseClient()
        with pytest.raises(ValueError, match="Ticker is required"):
            client.get_ticker_info("")

    def test_unknown_ticker_raises(self) -> None:
        client = NepseClient()
        auth_response = _load_fixture("auth_response.json")
        securities_response = _load_fixture("securities.json")

        with patch.object(client._session, "request") as mock_request, \
             patch.object(client._session, "get") as mock_get:
            mock_request.return_value = _mock_response(auth_response)
            mock_get.return_value = _mock_response(securities_response)

            with pytest.raises(NepseInvalidResponseError, match="not found"):
                client.get_ticker_info("NONEXISTENT")
