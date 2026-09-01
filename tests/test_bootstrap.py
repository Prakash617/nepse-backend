"""Tests for bootstrap_yonepse_data management command.

All tests mock the YonepseClient — no real API calls are made.
"""

from datetime import date
from io import StringIO
from unittest.mock import MagicMock, patch

import pytest
from django.core.management import call_command

from integrations.yonepse.client import YonepseClient


def _make_securities_data() -> list[dict]:
    return [
        {"id": 131, "symbol": "NABIL", "companyName": "Nabil Bank", "sectorName": "Commercial Banks"},
        {"id": 132, "symbol": "NIMB", "companyName": "NIMB", "sectorName": "Commercial Banks"},
    ]


def _make_indices_data() -> list[dict]:
    return [
        {"id": 58, "index": "NEPSE Index", "close": 2558.35, "change": -1.04, "perChange": -0.04},
    ]


def _make_sector_indices_data() -> list[dict]:
    return [
        {"id": 51, "indexCode": "BANKSUBIND", "indexName": "Banking SubIndex"},
    ]


def _make_market_history_data() -> list[dict]:
    return [
        {
            "businessDate": "2026-08-27",
            "totalTurnover": 3786455070.27,
            "totalTradedShares": 10626370,
            "totalTransactions": 52575,
            "tradedScrips": 348,
        },
    ]


def _make_ltp_manifest() -> dict:
    return {
        "availableMonths": ["2026-07", "2026-08"],
        "latestDate": "2026-08-27",
    }


def _make_ltp_monthly() -> dict:
    return {
        "dates": ["2026-07-01", "2026-07-02"],
        "columns": ["dateIndex", "ltp", "volume", "turnover", "trades"],
        "series": {
            "NABIL": [[0, 1000, 500, 500000, 10], [1, 1010, 600, 606000, 12]],
        },
    }


def _build_mock_client() -> MagicMock:
    client = MagicMock(spec=YonepseClient)
    client.get_all_securities.return_value = _make_securities_data()
    client.get_indices.return_value = _make_indices_data()
    client.get_sector_indices.return_value = _make_sector_indices_data()
    client.get_market_history.return_value = _make_market_history_data()
    client.get_ltp_manifest.return_value = _make_ltp_manifest()
    client.get_ltp_monthly.return_value = _make_ltp_monthly()
    return client


@pytest.mark.django_db
class TestBootstrapDryRun:
    @patch("integrations.yonepse.YonepseClient")
    def test_dry_run_no_persistence(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        out = StringIO()
        call_command("bootstrap_yonepse_data", "--dry-run", "--all", stdout=out)
        output = out.getvalue()
        assert "DRY RUN" in output
        from apps.securities.models import Security
        assert Security.objects.count() == 0


@pytest.mark.django_db
class TestBootstrapSecurities:
    @patch("integrations.yonepse.YonepseClient")
    def test_securities_bootstrap(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        out = StringIO()
        call_command("bootstrap_yonepse_data", "--securities", stdout=out)
        from apps.securities.models import Security
        assert Security.objects.count() == 2
        assert Security.objects.filter(symbol="NABIL").exists()
        assert Security.objects.filter(symbol="NIMB").exists()


@pytest.mark.django_db
class TestBootstrapMarketHistory:
    @patch("integrations.yonepse.YonepseClient")
    def test_market_history_bootstrap(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        from apps.sectors.services import sync_sectors
        from integrations.yonepse.parsers import parse_sectors_from_securities
        sync_sectors(parse_sectors_from_securities(_make_securities_data()))

        out = StringIO()
        call_command("bootstrap_yonepse_data", "--market", stdout=out)
        from apps.market.models import MarketSnapshot
        assert MarketSnapshot.objects.count() == 1
        snap = MarketSnapshot.objects.first()
        assert snap.trading_date == date(2026, 8, 27)


@pytest.mark.django_db
class TestBootstrapIndices:
    @patch("integrations.yonepse.YonepseClient")
    def test_indices_bootstrap(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        out = StringIO()
        call_command("bootstrap_yonepse_data", "--indices", stdout=out)
        from apps.indices.models import MarketIndex
        assert MarketIndex.objects.count() >= 1


@pytest.mark.django_db
class TestBootstrapPrices:
    @patch("integrations.yonepse.YonepseClient")
    def test_prices_bootstrap(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        from apps.sectors.services import sync_sectors
        from apps.securities.services import sync_securities
        from integrations.yonepse.parsers import (
            parse_sectors_from_securities,
            parse_securities_list,
        )
        sync_sectors(parse_sectors_from_securities(_make_securities_data()))
        sync_securities(parse_securities_list(_make_securities_data()))

        out = StringIO()
        call_command("bootstrap_yonepse_data", "--prices", stdout=out)
        from apps.prices.models import DailyPrice
        assert DailyPrice.objects.count() == 2


@pytest.mark.django_db
class TestBootstrapDateRange:
    @patch("integrations.yonepse.YonepseClient")
    def test_date_range_filter(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        from apps.sectors.services import sync_sectors
        from apps.securities.services import sync_securities
        from integrations.yonepse.parsers import (
            parse_sectors_from_securities,
            parse_securities_list,
        )
        sync_sectors(parse_sectors_from_securities(_make_securities_data()))
        sync_securities(parse_securities_list(_make_securities_data()))

        out = StringIO()
        call_command(
            "bootstrap_yonepse_data", "--prices",
            "--start", "2026-07-01", "--end", "2026-07-31",
            stdout=out,
        )
        from apps.prices.models import DailyPrice
        assert DailyPrice.objects.count() == 2


@pytest.mark.django_db
class TestBootstrapReport:
    @patch("integrations.yonepse.YonepseClient")
    def test_report_output(self, mock_cls: MagicMock) -> None:
        mock_cls.return_value = _build_mock_client()
        out = StringIO()
        call_command("bootstrap_yonepse_data", "--all", stdout=out)
        output = out.getvalue()
        assert "YONEPSE Bootstrap Report" in output
        assert "Sectors" in output
        assert "Securities" in output
