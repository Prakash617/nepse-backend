"""Tests for YonepseClient with mocked HTTP responses.

All tests mock the upstream YONEPSE GitHub Pages — no real calls are made.
"""

from unittest.mock import MagicMock, patch

import pytest

from integrations.yonepse.client import YonepseClient
from integrations.yonepse.exceptions import YonepseClientError


def _mock_response(json_data: dict | list, status_code: int = 200) -> MagicMock:
    """Create a mock httpx.Response."""
    response = MagicMock()
    response.status_code = status_code
    response.json.return_value = json_data
    response.raise_for_status.return_value = None
    return response


class TestYonepseClientInit:
    def test_default_init(self) -> None:
        client = YonepseClient()
        assert client.base_url == "https://shubhamnpk.github.io/yonepse"
        assert client.timeout == 30.0
        client.close()

    def test_custom_base_url(self) -> None:
        client = YonepseClient(base_url="https://custom.example.com")
        assert client.base_url == "https://custom.example.com"
        client.close()

    def test_custom_timeout(self) -> None:
        client = YonepseClient(timeout=60.0)
        assert client.timeout == 60.0
        client.close()

    def test_strips_trailing_slash(self) -> None:
        client = YonepseClient(base_url="https://example.com/")
        assert client.base_url == "https://example.com"
        client.close()


class TestYonepseClientContextManager:
    def test_context_manager(self) -> None:
        with YonepseClient() as client:
            assert client is not None


class TestGetAllSecurities:
    @patch("integrations.yonepse.client.httpx.Client")
    def test_success(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response([
            {"id": 131, "symbol": "NABIL", "companyName": "Nabil Bank Limited"},
            {"id": 132, "symbol": "NIMB", "companyName": "Nepal Investment Mega Bank"},
        ])

        client = YonepseClient()
        result = client.get_all_securities()
        assert len(result) == 2
        assert result[0]["symbol"] == "NABIL"
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_http_error(self, mock_http_cls: MagicMock) -> None:
        import httpx

        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        response = MagicMock()
        response.status_code = 404
        response.raise_for_status.side_effect = httpx.HTTPStatusError(
            "Not Found", request=MagicMock(), response=response
        )
        mock_client.get.return_value = response

        client = YonepseClient()
        with pytest.raises(YonepseClientError, match="HTTP 404"):
            client.get_all_securities()
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_unexpected_type(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response({"unexpected": "dict"})

        client = YonepseClient()
        with pytest.raises(YonepseClientError, match="Expected list"):
            client.get_all_securities()
        client.close()


class TestGetLtpMonthly:
    @patch("integrations.yonepse.client.httpx.Client")
    def test_success(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response({
            "dates": ["2012-01-01", "2012-01-02"],
            "columns": ["dateIndex", "ltp", "volume", "turnover", "trades"],
            "series": {
                "NABIL": [[0, 1000, 500, 500000, 10], [1, 1010, 600, 606000, 12]],
            },
        })

        client = YonepseClient()
        result = client.get_ltp_monthly("2012-01")
        assert "series" in result
        assert "NABIL" in result["series"]
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_connection_error(self, mock_http_cls: MagicMock) -> None:
        import httpx

        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.side_effect = httpx.ConnectError("Connection refused")

        client = YonepseClient()
        with pytest.raises(YonepseClientError, match="Request failed"):
            client.get_ltp_monthly("2012-01")
        client.close()


class TestGetIndexMonthly:
    @patch("integrations.yonepse.client.httpx.Client")
    def test_success(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response({
            "dates": ["2026-09-01"],
            "columns": ["dateIndex", "close", "open", "high", "low"],
            "series": {"NEPSE": [[0, 2558.35, 2550.0, 2560.0, 2545.0]]},
        })

        client = YonepseClient()
        result = client.get_index_monthly("2026-09")
        assert "NEPSE" in result["series"]
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_unexpected_type(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response(["not", "a", "dict"])

        client = YonepseClient()
        with pytest.raises(YonepseClientError, match="Expected dict"):
            client.get_index_monthly("2026-09")
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_manifest(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response({
            "availableMonths": ["1997-07", "2026-09"],
            "latestDate": "2026-10-09",
        })

        client = YonepseClient()
        result = client.get_index_manifest()
        assert result["availableMonths"][0] == "1997-07"
        client.close()


class TestGetDividendHistory:
    @patch("integrations.yonepse.client.httpx.Client")
    def test_success(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response({
            "symbols": ["NABIL"],
            "columns": ["symbol", "bonus", "cash", "announce", "fiscalYear"],
            "records": [[0, "5.00", "15.00", "2026-10-09", "2082/2083"]],
        })

        client = YonepseClient()
        result = client.get_dividend_history()
        assert result["symbols"] == ["NABIL"]
        client.close()

    @patch("integrations.yonepse.client.httpx.Client")
    def test_unexpected_type(self, mock_http_cls: MagicMock) -> None:
        mock_client = MagicMock()
        mock_http_cls.return_value = mock_client
        mock_client.get.return_value = _mock_response([1, 2, 3])

        client = YonepseClient()
        with pytest.raises(YonepseClientError, match="Expected dict"):
            client.get_dividend_history()
        client.close()
