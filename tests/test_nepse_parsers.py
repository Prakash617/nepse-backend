"""Tests for NEPSE response parsers."""

import json
from pathlib import Path

import pytest

from integrations.nepse.exceptions import NepseInvalidResponseError
from integrations.nepse.parsers import (
    parse_brokers,
    parse_company_financials,
    parse_index_history,
    parse_indices,
    parse_market_status,
    parse_market_summary,
    parse_notices,
    parse_price_history,
    parse_sector_indices,
    parse_sectors,
    parse_sectorwise_summary,
    parse_securities_list,
    parse_securities_simple,
    parse_today_prices,
    parse_top_stocks,
)

FIXTURES_DIR = Path(__file__).parent / "fixtures" / "nepse"


def _load_fixture(name: str) -> dict | list:
    with open(FIXTURES_DIR / name) as f:
        return json.load(f)


class TestParseMarketStatus:
    def test_parse_open_market(self) -> None:
        data = _load_fixture("market_status.json")
        result = parse_market_status(data)
        assert result["id"] == 42
        assert result["is_open"] is True

    def test_parse_closed_market(self) -> None:
        data = _load_fixture("market_status_closed.json")
        result = parse_market_status(data)
        assert result["is_open"] is False

    def test_missing_is_open_defaults_close(self) -> None:
        result = parse_market_status({"id": 1})
        assert result["is_open"] is False

    def test_missing_id_raises(self) -> None:
        with pytest.raises(NepseInvalidResponseError, match="Missing required field 'id'"):
            parse_market_status({})


class TestParseMarketSummary:
    def test_parse_full_summary(self) -> None:
        data = _load_fixture("market_summary.json")
        result = parse_market_summary(data)
        assert result["total_traded_volume"] == 15000000
        assert result["total_traded_value"] == 5000000000
        assert result["close"] == 2830.00
        assert result["percent_change"] == 1.05

    def test_empty_dict_returns_defaults(self) -> None:
        result = parse_market_summary({})
        assert result["total_traded_volume"] == 0
        assert result["close"] == 0


class TestParseSecuritiesList:
    def test_parse_securities(self) -> None:
        data = _load_fixture("securities.json")
        result = parse_securities_list(data)
        assert len(result) == 2
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["company_name"] == "Nabil Bank Limited"
        assert result[1]["symbol"] == "SCB"

    def test_empty_list(self) -> None:
        result = parse_securities_list([])
        assert result == []

    def test_missing_optional_fields(self) -> None:
        result = parse_securities_list([{"id": 1}])
        assert result[0]["id"] == 1
        assert result[0]["symbol"] is None


class TestParseSecuritiesSimple:
    def test_parse_simple_securities(self) -> None:
        data = [{"securityId": 1, "securitySymbol": "NABIL", "securityName": "Nabil Bank", "securityType": "Equity"}]
        result = parse_securities_simple(data)
        assert len(result) == 1
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["name"] == "Nabil Bank"


class TestParseTodayPrices:
    def test_parse_prices(self) -> None:
        data = _load_fixture("today_prices.json")
        content = data["content"]
        result = parse_today_prices(content)
        assert len(result) == 2
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["ltp"] == 950.00
        assert result[0]["volume"] == 500000

    def test_empty_list(self) -> None:
        result = parse_today_prices([])
        assert result == []


class TestParseTopStocks:
    def test_parse_top_gainers(self) -> None:
        data = _load_fixture("top_gainers.json")
        result = parse_top_stocks(data)
        assert len(result) == 2
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["percent_change"] == 1.61


class TestParseIndices:
    def test_parse_indices(self) -> None:
        data = _load_fixture("indices.json")
        result = parse_indices(data)
        assert len(result) == 2
        assert result[0]["name"] == "NEPSE Index"
        assert result[0]["id"] == 58


class TestParseSectorIndices:
    def test_parse_sector_indices(self) -> None:
        data = _load_fixture("sector_indices.json")
        result = parse_sector_indices(data)
        assert len(result) == 2
        assert result[0]["name"] == "Banking Sub-Index"


class TestParseSectors:
    def test_parse_sectors(self) -> None:
        data = _load_fixture("sectors.json")
        result = parse_sectors(data)
        assert len(result) == 2
        assert result[0]["name"] == "Banking"


class TestParseSectorwiseSummary:
    def test_parse_summary(self) -> None:
        data = [
            {"sector": "Banking", "lastTradedPrice": 1200, "pointChange": 15, "percentChange": 1.25,
             "totalTradedVolume": 5000000, "totalTradedValue": 6000000000}
        ]
        result = parse_sectorwise_summary(data)
        assert len(result) == 1
        assert result[0]["sector"] == "Banking"
        assert result[0]["ltp"] == 1200


class TestParsePriceHistory:
    def test_parse_with_content_key(self) -> None:
        data = {"content": [_load_fixture("price_history.json")]}
        result = parse_price_history(data)
        assert len(result) == 1
        assert result[0]["ltp"] == 950.00

    def test_parse_direct_list(self) -> None:
        data = [_load_fixture("price_history.json")]
        result = parse_price_history(data)
        assert len(result) == 1

    def test_empty_dict(self) -> None:
        result = parse_price_history({})
        assert result == []


class TestParseIndexHistory:
    def test_parse_history(self) -> None:
        data = _load_fixture("index_history.json")
        result = parse_index_history(data)
        assert len(result) == 2
        assert result[0]["business_date"] == "2026-01-15"


class TestParseCompanyFinancials:
    def test_parse_financials(self) -> None:
        data = _load_fixture("company_financials.json")
        result = parse_company_financials(data)
        assert len(result) == 1
        assert result[0]["fiscal_year"] == "2081/82"


class TestParseNotices:
    def test_parse_notices(self) -> None:
        data = _load_fixture("notices.json")
        result = parse_notices(data)
        assert len(result) == 1
        assert result[0]["title"] == "Notice about trading hours"


class TestParseBrokers:
    def test_parse_brokers(self) -> None:
        data = _load_fixture("brokers.json")
        content = data["content"]
        result = parse_brokers(content)
        assert len(result) == 2
        assert result[0]["name"] == "Nabil Capital"
