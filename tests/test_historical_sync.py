"""Tests for historical price synchronization service."""
from datetime import date
from decimal import Decimal
from unittest.mock import MagicMock

import pytest

from apps.prices.models import DailyPrice
from apps.prices.services import sync_historical_prices
from apps.sectors.models import Sector
from apps.securities.models import Security


@pytest.fixture
def sector():
    return Sector.objects.create(nepse_id=1, name="Commercial Banks")


@pytest.fixture
def securities(sector):
    Security.objects.create(
        nepse_id=58,
        symbol="NABIL",
        company_name="Nabil Bank Limited",
        sector=sector,
    )
    Security.objects.create(
        nepse_id=59,
        symbol="NHPC",
        company_name="Nepal Hydro Power",
        sector=sector,
    )


def _make_history_data(symbol: str, dates: list[str]) -> list[dict]:
    """Create mock price history data from upstream parser."""
    results = []
    for d in dates:
        results.append({
            "business_date": d,
            "open": "100.00",
            "high": "105.00",
            "low": "99.00",
            "close": "103.00",
            "ltp": "103.00",
            "volume": 100000,
            "turnover": "10300000.00",
        })
    return results


@pytest.mark.django_db
class TestSyncHistoricalPrices:
    def test_single_security_single_day(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = _make_history_data(
            "NABIL", ["2024-06-15"]
        )

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.created == 1
        assert result.failed == 0
        assert DailyPrice.objects.count() == 1
        dp = DailyPrice.objects.first()
        assert dp.security.symbol == "NABIL"
        assert dp.trading_date == date(2024, 6, 15)
        assert dp.open == Decimal("100.00")
        assert dp.close == Decimal("103.00")
        mock_client.get_price_history.assert_called_once_with(
            ticker="NABIL",
            start_date="2024-06-15",
            end_date="2024-06-15",
            page=0,
            size=500,
        )

    def test_multi_day_sync(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = _make_history_data(
            "NABIL", ["2024-06-10", "2024-06-11", "2024-06-12"]
        )

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 10),
            end_date=date(2024, 6, 12),
            client=mock_client,
        )

        assert result.created == 3
        assert DailyPrice.objects.count() == 3

    def test_multi_security_sync(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.side_effect = [
            _make_history_data("NABIL", ["2024-06-15"]),
            _make_history_data("NHPC", ["2024-06-15"]),
        ]

        result = sync_historical_prices(
            symbols=["NABIL", "NHPC"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.created == 2
        assert DailyPrice.objects.count() == 2
        assert mock_client.get_price_history.call_count == 2

    def test_idempotent_sync(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = _make_history_data(
            "NABIL", ["2024-06-15", "2024-06-16"]
        )

        # First sync
        result1 = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 16),
            client=mock_client,
        )
        assert result1.created == 2
        assert DailyPrice.objects.count() == 2

        # Second sync — should update, not create
        result2 = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 16),
            client=mock_client,
        )
        assert result2.created == 0
        assert DailyPrice.objects.count() == 2

    def test_overlapping_ranges(self, securities):
        mock_client = MagicMock()

        # First range: Jan 1-15
        mock_client.get_price_history.return_value = _make_history_data(
            "NABIL", ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-15"]
        )
        result1 = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 15),
            client=mock_client,
        )
        assert result1.created == 4
        assert DailyPrice.objects.count() == 4

        # Second range: Jan 5-20 (overlaps)
        mock_client.get_price_history.return_value = _make_history_data(
            "NABIL",
            ["2024-01-10", "2024-01-11", "2024-01-12", "2024-01-15",
             "2024-01-16", "2024-01-17", "2024-01-18", "2024-01-19", "2024-01-20"],
        )
        result2 = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 1, 5),
            end_date=date(2024, 1, 20),
            client=mock_client,
        )
        # 4 existing skipped, 5 new created
        assert result2.created == 5
        assert result2.skipped == 4
        assert DailyPrice.objects.count() == 9

    def test_empty_response(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = []

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.created == 0
        assert result.skipped == 0
        assert DailyPrice.objects.count() == 0

    def test_unknown_security_skipped(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = [
            {
                "business_date": "2024-06-15",
                "open": "100.00",
                "high": "105.00",
                "low": "99.00",
                "close": "103.00",
                "ltp": "103.00",
                "volume": 100000,
                "turnover": "10300000.00",
            }
        ]

        result = sync_historical_prices(
            symbols=["UNKNOWN"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        # sync_daily_prices should skip the record because UNKNOWN security
        # won't resolve in the security lookup map
        assert result.created == 0
        assert DailyPrice.objects.count() == 0

    def test_api_failure_recorded(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.side_effect = Exception("Network error")

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.failed == 1
        assert any("Network error" in e for e in result.errors)

    def test_pagination(self, securities):
        mock_client = MagicMock()
        # Simulate pages: first page returns full page_size, second returns fewer
        # We mock page_size=3 for testing (in real code it's 500)
        page1 = [
            {"business_date": "2024-01-02", "open": "100", "high": "105", "low": "99",
             "close": "103", "ltp": "103", "volume": 100000, "turnover": "10300000"},
            {"business_date": "2024-01-03", "open": "103", "high": "107", "low": "101",
             "close": "105", "ltp": "105", "volume": 110000, "turnover": "11550000"},
            {"business_date": "2024-01-04", "open": "105", "high": "110", "low": "103",
             "close": "108", "ltp": "108", "volume": 120000, "turnover": "12960000"},
        ]
        page2 = [
            {"business_date": "2024-01-05", "open": "108", "high": "112", "low": "106",
             "close": "110", "ltp": "110", "volume": 130000, "turnover": "14300000"},
        ]
        mock_client.get_price_history.side_effect = [page1, page2]

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 1, 1),
            end_date=date(2024, 1, 5),
            client=mock_client,
            page_size=3,
        )

        # page1 has 3, page2 has 1 = 4 total
        assert result.created == 4
        assert mock_client.get_price_history.call_count == 2
        calls = mock_client.get_price_history.call_args_list
        assert calls[0].kwargs["page"] == 0
        assert calls[1].kwargs["page"] == 1

    def test_null_optional_fields(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = [
            {
                "business_date": "2024-06-15",
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "ltp": None,
                "volume": None,
                "turnover": None,
            }
        ]

        result = sync_historical_prices(
            symbols=["NABIL"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.created == 1
        dp = DailyPrice.objects.first()
        assert dp.open is None
        assert dp.close is None
        assert dp.volume is None

    def test_symbol_case_insensitive(self, securities):
        mock_client = MagicMock()
        mock_client.get_price_history.return_value = _make_history_data(
            "nabil", ["2024-06-15"]
        )

        result = sync_historical_prices(
            symbols=["nabil"],
            start_date=date(2024, 6, 15),
            end_date=date(2024, 6, 15),
            client=mock_client,
        )

        assert result.created == 1
        dp = DailyPrice.objects.first()
        assert dp.security.symbol == "NABIL"
        # Verify the client was called with uppercase
        mock_client.get_price_history.assert_called_once_with(
            ticker="NABIL",
            start_date="2024-06-15",
            end_date="2024-06-15",
            page=0,
            size=500,
        )
