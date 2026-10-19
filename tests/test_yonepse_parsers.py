"""Tests for YONEPSE parsers.

Verifies that YONEPSE data is normalized to the same format as NEPSE parsers.
"""


from integrations.yonepse.parsers import (
    parse_company_financials,
    parse_company_profiles,
    parse_dividends_history,
    parse_index_monthly,
    parse_indices,
    parse_ltp_daily,
    parse_ltp_monthly,
    parse_market_history,
    parse_sector_indices,
    parse_sectors_from_securities,
    parse_securities_list,
)


class TestParseSecuritiesList:
    def test_basic_parse(self) -> None:
        data = [
            {
                "id": 131,
                "symbol": "NABIL",
                "companyName": "Nabil Bank Limited",
                "sectorName": "Commercial Banks",
                "instrumentType": "Equity",
            },
        ]
        result = parse_securities_list(data)
        assert len(result) == 1
        assert result[0]["id"] == 131
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["company_name"] == "Nabil Bank Limited"
        assert result[0]["sector"] == "Commercial Banks"
        assert result[0]["security_type"] == "Equity"

    def test_missing_optional_fields(self) -> None:
        data = [{"id": 1, "symbol": "TEST"}]
        result = parse_securities_list(data)
        assert result[0]["company_name"] is None
        assert result[0]["sector"] is None

    def test_empty_list(self) -> None:
        assert parse_securities_list([]) == []


class TestParseSectorsFromSecurities:
    def test_unique_sectors(self) -> None:
        data = [
            {"sectorName": "Commercial Banks"},
            {"sectorName": "Commercial Banks"},
            {"sectorName": "Hydropower"},
            {"sectorName": None},
        ]
        result = parse_sectors_from_securities(data)
        assert len(result) == 2
        names = {r["name"] for r in result}
        assert names == {"Commercial Banks", "Hydropower"}


class TestParseIndices:
    def test_basic_parse(self) -> None:
        data = [
            {
                "id": 58,
                "index": "NEPSE Index",
                "close": 2558.35,
                "change": -1.04,
                "perChange": -0.04,
            },
        ]
        result = parse_indices(data)
        assert len(result) == 1
        assert result[0]["id"] == 58
        assert result[0]["name"] == "NEPSE Index"
        assert result[0]["index_value"] == 2558.35
        assert result[0]["change"] == -1.04
        assert result[0]["change_percent"] == -0.04


class TestParseSectorIndices:
    def test_basic_parse(self) -> None:
        data = [
            {
                "id": 51,
                "indexCode": "BANKSUBIND",
                "indexName": "Banking SubIndex",
            },
        ]
        result = parse_sector_indices(data)
        assert len(result) == 1
        assert result[0]["id"] == 51
        assert result[0]["name"] == "Banking SubIndex"


class TestParseMarketHistory:
    def test_basic_parse(self) -> None:
        data = [
            {
                "businessDate": "2026-08-27",
                "totalTurnover": 3786455070.27,
                "totalTradedShares": 10626370,
                "totalTransactions": 52575,
                "tradedScrips": 348,
            },
        ]
        result = parse_market_history(data)
        assert len(result) == 1
        assert result[0]["business_date"] == "2026-08-27"
        assert result[0]["total_volume"] == 10626370
        assert result[0]["total_turnover"] == 3786455070.27
        assert result[0]["transactions"] == 52575


class TestParseLtpMonthly:
    def test_basic_parse(self) -> None:
        data = {
            "dates": ["2012-01-01", "2012-01-02"],
            "columns": ["dateIndex", "ltp", "volume", "turnover", "trades"],
            "series": {
                "NABIL": [[0, 1000, 500, 500000, 10], [1, 1010, 600, 606000, 12]],
                "NHPC": [[0, 200, 100, 20000, 5]],
            },
        }
        result = parse_ltp_monthly(data)
        assert len(result) == 3  # 2 NABIL + 1 NHPC

        # Check first NABIL record
        nabil_0 = [r for r in result if r["symbol"] == "NABIL"][0]
        assert nabil_0["business_date"] == "2012-01-01"
        assert nabil_0["ltp"] == 1000
        assert nabil_0["volume"] == 500
        assert nabil_0["turnover"] == 500000

    def test_invalid_date_index(self) -> None:
        data = {
            "dates": ["2012-01-01"],
            "series": {
                "NABIL": [[5, 1000, 500, 500000, 10]],  # dateIndex 5 out of range
            },
        }
        result = parse_ltp_monthly(data)
        assert len(result) == 0

    def test_empty_series(self) -> None:
        data = {"dates": ["2012-01-01"], "series": {}}
        assert parse_ltp_monthly(data) == []


class TestParseLtpDaily:
    def test_basic_parse(self) -> None:
        data = {
            "date": "2026-08-27",
            "times": ["14:59"],
            "columns": ["timeIndex", "ltp", "volume", "turnover", "trades"],
            "series": {
                "NABIL": [[0, 1000, 500, 500000, 10]],
            },
        }
        result = parse_ltp_daily(data)
        assert len(result) == 1
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["business_date"] == "2026-08-27T14:59:00"
        assert result[0]["ltp"] == 1000


class TestParseIndexMonthly:
    def test_basic_parse(self) -> None:
        data = {
            "dates": ["2026-09-01", "2026-09-02"],
            "columns": [
                "dateIndex", "close", "open", "high", "low",
                "turnover", "volume", "trades",
            ],
            "series": {
                "NEPSE": [
                    [0, 2558.35, 2550.0, 2560.0, 2545.0, 1000.0, 500, 10],
                    [1, 2560.0, 2558.0, 2565.0, 2550.0, 1100.0, 550, 12],
                ],
                "BANKSUBIND": [[0, 1416.0, 1422.0, 1422.5, 1407.0, 280.0, 988, 38]],
            },
        }
        result = parse_index_monthly(data)
        assert len(result) == 3
        nepse_0 = [r for r in result if r["index_code"] == "NEPSE"][0]
        assert nepse_0["business_date"] == "2026-09-01"
        assert nepse_0["close"] == 2558.35
        assert nepse_0["volume"] == 500
        assert nepse_0["turnover"] == 1000.0

    def test_missing_trailing_columns(self) -> None:
        data = {
            "dates": ["1997-07-20"],
            "columns": ["dateIndex", "close", "open", "high", "low", "turnover"],
            "series": {"NEPSE": [[0, 173.26, 173.26, 173.26, 173.26, 0]]},
        }
        result = parse_index_monthly(data)
        assert len(result) == 1
        assert result[0]["volume"] is None
        assert result[0]["close"] == 173.26

    def test_invalid_date_index(self) -> None:
        data = {
            "dates": ["2026-09-01"],
            "columns": ["dateIndex", "close"],
            "series": {"NEPSE": [[5, 100.0]]},
        }
        assert parse_index_monthly(data) == []


class TestParseDividendsHistory:
    def test_basic_parse(self) -> None:
        data = {
            "symbols": ["NABIL", "NIMB"],
            "columns": [
                "symbol", "bonus", "cash", "total",
                "announce", "bookclose", "fiscalYear",
            ],
            "records": [
                [0, "5.00", "15.00", "20.00", "2026-10-09", None, "2082/2083"],
                [1, None, "8.25", "8.25", "2026-10-08", "2026-10-20", "2082/2083"],
            ],
        }
        result = parse_dividends_history(data)
        assert len(result) == 2
        assert result[0]["symbol"] == "NABIL"
        assert result[0]["cash"] == "15.00"
        assert result[0]["bonus"] == "5.00"
        assert result[0]["announcement_date"] == "2026-10-09"
        assert result[1]["bookclose_date"] == "2026-10-20"

    def test_invalid_symbol_index_skipped(self) -> None:
        data = {
            "symbols": ["NABIL"],
            "columns": ["symbol", "bonus", "cash", "announce", "fiscalYear"],
            "records": [[9, None, "5.00", "2026-10-09", "2082/2083"]],
        }
        assert parse_dividends_history(data) == []


class TestParseCompanyProfiles:
    def test_basic_parse(self) -> None:
        data = [
            {"id": 131, "companyName": "Nabil Bank", "website": "nabilbank.com"},
        ]
        result = parse_company_profiles(data)
        assert len(result) == 1
        assert result[0]["nepse_id"] == 131
        assert result[0]["name"] == "Nabil Bank"
        assert result[0]["website"] == "nabilbank.com"

    def test_missing_id_skipped(self) -> None:
        data = [{"companyName": "No ID"}]
        assert parse_company_profiles(data) == []


class TestParseCompanyFinancials:
    def test_basic_parse(self) -> None:
        data = [
            {"id": 131, "fiscal_year": "2081/82", "report_type": "Annual Report"},
        ]
        result = parse_company_financials(data)
        assert len(result) == 1
        assert result[0]["nepse_id"] == 131
        assert result[0]["fiscal_year"] == "2081/82"
