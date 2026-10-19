"""YONEPSE response parsers.

Normalize YONEPSE static JSON datasets into the same dict format
produced by integrations.nepse.parsers, so domain services work unchanged.
"""

from __future__ import annotations

from typing import Any


def _get_optional(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Extract an optional field from a dict, returning default if missing."""
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


# ---------------------------------------------------------------------------
# Securities / reference data
# ---------------------------------------------------------------------------


def parse_securities_list(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE all_securities.json into the same format as NEPSE parse_securities_list.

    YONEPSE schema: {id, companyName, symbol, securityName, status, sectorName, ...}
    Target schema:  {id, symbol, company_name, sector, security_type, ...}
    """
    results = []
    for item in data:
        results.append({
            "id": _get_optional(item, "id"),
            "symbol": _get_optional(item, "symbol"),
            "company_name": _get_optional(item, "companyName") or _get_optional(item, "securityName"),
            "sector": _get_optional(item, "sectorName"),
            "security_type": _get_optional(item, "instrumentType", ""),
            "listing_date": None,
            "paid_up_value": None,
            "face_value": None,
        })
    return results


def parse_sectors_from_securities(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Extract unique sector definitions from all_securities.json.

    Returns list of {id, name, display_name} dicts.
    YONEPSE doesn't provide sector IDs, so we generate stable synthetic IDs
    from the sector name to ensure idempotent sync.
    """
    import hashlib

    seen: set[str] = set()
    results = []
    for item in data:
        sector_name = _get_optional(item, "sectorName")
        if sector_name and sector_name not in seen:
            seen.add(sector_name)
            # Generate stable synthetic ID from name
            hash_val = int(hashlib.md5(sector_name.encode()).hexdigest()[:8], 16)
            synthetic_id = (hash_val % 9000) + 1000  # 1000-9999 range
            results.append({
                "id": synthetic_id,
                "name": sector_name,
                "display_name": sector_name,
            })
    return results


# ---------------------------------------------------------------------------
# Indices
# ---------------------------------------------------------------------------


def parse_indices(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE indices.json into the same format as NEPSE parse_indices.

    YONEPSE schema: {id, index, close, high, low, previousClose, change, perChange, ...}
    Target schema:  {id, name, index_value, change, change_percent}
    """
    results = []
    for item in data:
        results.append({
            "id": _get_optional(item, "id"),
            "name": _get_optional(item, "index"),
            "index_value": _get_optional(item, "close"),
            "change": _get_optional(item, "change"),
            "change_percent": _get_optional(item, "perChange"),
        })
    return results


def parse_sector_indices(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE sector_indices.json into the same format as NEPSE parse_sector_indices.

    YONEPSE schema: {id, indexCode, indexName, description, sectorMaster, ...}
    Target schema:  {id, name, index_value, change, change_percent, code}

    ``code`` (indexCode) is retained because index-history shards are keyed by
    index code rather than id.
    """
    results = []
    for item in data:
        results.append({
            "id": _get_optional(item, "id"),
            "name": _get_optional(item, "indexName"),
            "index_value": None,
            "change": None,
            "change_percent": None,
            "code": _get_optional(item, "indexCode"),
        })
    return results


def parse_index_monthly(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse a YONEPSE index monthly shard into index-snapshot dicts.

    YONEPSE monthly schema:
    {
        "month": "2026-09",
        "dates": ["2026-09-01", ...],
        "columns": ["dateIndex", "close", "open", "high", "low",
                    "turnover", "volume", "trades"],
        "series": {
            "NEPSE": [[dateIndex, close, open, high, low, turnover, volume, trades], ...],
            "BANKSUBIND": [...],
            ...
        }
    }

    Older shards may omit trailing columns (e.g. volume/trades); missing values
    are returned as None.

    Target schema per record:
    {index_code, business_date, open, high, low, close, volume, turnover}
    """
    dates = data.get("dates", [])
    columns = data.get("columns", [])
    series = data.get("series", {})

    # Map column name -> position so shard column-order changes are tolerated.
    col_index: dict[str, int] = {
        name: idx for idx, name in enumerate(columns) if isinstance(name, str)
    }

    def _value(row: list[Any], name: str) -> Any:
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    results: list[dict[str, Any]] = []
    for index_code, rows in series.items():
        for row in rows:
            if not isinstance(row, list):
                continue
            date_idx = _value(row, "dateIndex")
            if date_idx is None:
                date_idx = row[0] if row else None
            if not isinstance(date_idx, int) or date_idx < 0 or date_idx >= len(dates):
                continue
            results.append({
                "index_code": index_code,
                "business_date": dates[date_idx],
                "open": _value(row, "open"),
                "high": _value(row, "high"),
                "low": _value(row, "low"),
                "close": _value(row, "close"),
                "volume": _value(row, "volume"),
                "turnover": _value(row, "turnover"),
                "point_change": None,
                "percentage_change": None,
            })
    return results


# ---------------------------------------------------------------------------
# Market history / summary
# ---------------------------------------------------------------------------


def parse_market_history(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE market/history.json for MarketSnapshot sync.

    YONEPSE schema: {businessDate, totalTurnover, totalTradedShares, totalTransactions, tradedScrips}
    Target schema:  {business_date, total_volume, total_turnover, transactions}
    """
    results = []
    for item in data:
        results.append({
            "business_date": _get_optional(item, "businessDate"),
            "total_volume": _get_optional(item, "totalTradedShares"),
            "total_turnover": _get_optional(item, "totalTurnover"),
            "transactions": _get_optional(item, "totalTransactions"),
            "open": None,
            "high": None,
            "low": None,
            "close": None,
            "previous_close": None,
            "point_change": None,
            "percentage_change": None,
        })
    return results


# ---------------------------------------------------------------------------
# LTP / daily prices
# ---------------------------------------------------------------------------


def parse_ltp_monthly(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse a YONEPSE LTP monthly shard into DailyPrice-compatible dicts.

    YONEPSE monthly schema:
    {
        "dates": ["2012-01-01", ...],
        "columns": ["dateIndex", "ltp", "volume", "turnover", "trades"],
        "series": {
            "NABIL": [[dateIndex, ltp, volume, turnover, trades], ...],
            ...
        }
    }

    Target schema per record:
    {symbol, business_date, ltp, volume, turnover}
    """
    dates = data.get("dates", [])
    series = data.get("series", {})
    results = []
    for symbol, rows in series.items():
        for row in rows:
            if not isinstance(row, list) or len(row) < 4:
                continue
            date_idx = row[0]
            if not isinstance(date_idx, int) or date_idx < 0 or date_idx >= len(dates):
                continue
            results.append({
                "symbol": symbol,
                "business_date": dates[date_idx],
                "ltp": row[1],
                "volume": row[2],
                "turnover": row[3],
                "open": None,
                "high": None,
                "low": None,
                "close": None,
                "previous_close": None,
                "percentage_change": None,
                "point_change": None,
            })
    return results


def parse_ltp_daily(
    data: dict[str, Any],
) -> list[dict[str, Any]]:
    """Parse a YONEPSE LTP daily shard into IntradayPrice-compatible dicts.

    YONEPSE daily schema:
    {
        "date": "2026-08-27",
        "times": ["14:59"],
        "columns": ["timeIndex", "ltp", "volume", "turnover", "trades"],
        "series": {
            "NABIL": [[0, 1000, 500, 500000, 10], ...],
            ...
        }
    }

    Target schema per record:
    {symbol, business_date, ltp, volume, turnover}
    """
    trading_date = data.get("date")
    times = data.get("times", [])
    series = data.get("series", {})
    results = []
    for symbol, rows in series.items():
        for row in rows:
            if not isinstance(row, list) or len(row) < 4:
                continue
            time_idx = row[0]
            if not isinstance(time_idx, int) or time_idx < 0 or time_idx >= len(times):
                timestamp = trading_date
            else:
                timestamp = f"{trading_date}T{times[time_idx]}:00"
            results.append({
                "symbol": symbol,
                "business_date": timestamp,
                "ltp": row[1],
                "volume": row[2],
                "turnover": row[3],
            })
    return results


# ---------------------------------------------------------------------------
# Dividends / bonus
# ---------------------------------------------------------------------------


def parse_dividends_history(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse YONEPSE dividend/history.json into corporate-action dicts.

    YONEPSE schema:
    {
        "symbols": ["AADHYANTA", ...],
        "columns": ["symbol", "bonus", "cash", "total", "announce",
                    "bookclose", "fiscalYear"],
        "records": [[<symbolIndex>, "<bonus>", "<cash>", "<total>",
                     "<announce>", "<bookclose>", "<fiscalYear>"], ...]
    }

    The first record field is an index into ``symbols`` (not a NEPSE id).

    Target schema per record:
    {symbol, fiscal_year, bonus, cash, total, announcement_date, bookclose_date}
    """
    symbols = data.get("symbols", [])
    columns = data.get("columns", [])
    records = data.get("records", [])

    col_index: dict[str, int] = {
        name: idx for idx, name in enumerate(columns) if isinstance(name, str)
    }

    def _value(row: list[Any], name: str) -> Any:
        idx = col_index.get(name)
        if idx is None or idx >= len(row):
            return None
        return row[idx]

    results: list[dict[str, Any]] = []
    for row in records:
        if not isinstance(row, list):
            continue
        symbol_idx = _value(row, "symbol")
        if not isinstance(symbol_idx, int) or symbol_idx < 0 or symbol_idx >= len(symbols):
            continue
        symbol = symbols[symbol_idx]
        if not symbol:
            continue
        results.append({
            "symbol": str(symbol).upper(),
            "fiscal_year": _value(row, "fiscalYear"),
            "bonus": _value(row, "bonus"),
            "cash": _value(row, "cash"),
            "total": _value(row, "total"),
            "announcement_date": _value(row, "announce"),
            "bookclose_date": _value(row, "bookclose"),
        })
    return results


# ---------------------------------------------------------------------------
# Company / fundamentals
# ---------------------------------------------------------------------------


def parse_company_profiles(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE company/profiles.json into CompanyProfile-compatible dicts.

    YONEPSE schema varies; normalize to:
    {nepse_id, name, address, contact_number, website, email, description}
    """
    results = []
    for item in data:
        nepse_id = _get_optional(item, "id") or _get_optional(item, "nepse_id")
        if nepse_id is None:
            continue
        results.append({
            "nepse_id": int(nepse_id),
            "name": _get_optional(item, "companyName") or _get_optional(item, "name", ""),
            "address": _get_optional(item, "addressField") or _get_optional(item, "address", ""),
            "contact_number": _get_optional(item, "phoneNumber") or _get_optional(item, "contact_number", ""),
            "website": _get_optional(item, "website", ""),
            "email": _get_optional(item, "companyEmail") or _get_optional(item, "email", ""),
            "description": _get_optional(item, "companyProfile") or _get_optional(item, "description", ""),
        })
    return results


def parse_company_financials(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse YONEPSE company/financials.json into FinancialReport-compatible dicts.

    YONEPSE schema varies; normalize to:
    {nepse_id, fiscal_year, report_type, file_url}
    """
    results = []
    for item in data:
        nepse_id = _get_optional(item, "id") or _get_optional(item, "nepse_id")
        if nepse_id is None:
            continue
        results.append({
            "nepse_id": int(nepse_id),
            "fiscal_year": _get_optional(item, "fiscal_year", ""),
            "report_type": _get_optional(item, "report_type", ""),
            "file_url": _get_optional(item, "file_url", ""),
        })
    return results
