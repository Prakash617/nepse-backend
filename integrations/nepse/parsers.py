"""NEPSE response parsers.

Functions to normalize raw API responses into consistent dicts.
Each parser validates required fields and raises NepseInvalidResponseError on malformed data.
"""

from __future__ import annotations

from typing import Any

from integrations.nepse.exceptions import NepseInvalidResponseError


def _get_required(data: dict[str, Any], key: str, context: str = "") -> Any:
    """Extract a required field from a dict, raising on missing."""
    try:
        return data[key]
    except (KeyError, TypeError) as exc:
        msg = f"Missing required field '{key}'"
        if context:
            msg += f" in {context}"
        raise NepseInvalidResponseError(msg) from exc


def _get_optional(data: dict[str, Any], key: str, default: Any = None) -> Any:
    """Extract an optional field from a dict, returning default if missing."""
    if not isinstance(data, dict):
        return default
    return data.get(key, default)


# ---------------------------------------------------------------------------
# Market data parsers
# ---------------------------------------------------------------------------


def parse_market_status(data: dict[str, Any]) -> dict[str, Any]:
    """Parse market status from /api/nots/nepse-data/market-open."""
    is_open_raw = _get_optional(data, "isOpen", "CLOSE")
    return {
        "id": _get_required(data, "id", "market status"),
        "is_open": is_open_raw == "OPEN",
    }


def parse_today_prices(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse today's prices from /api/nots/nepse-data/today-price."""
    results = []
    for item in data:
        results.append(
            {
                "symbol": _get_optional(item, "symbol"),
                "nepse_id": _get_optional(item, "securityId"),
                "ltp": _get_optional(item, "lastTradedPrice")
                    or _get_optional(item, "lastUpdatedPrice"),
                "open": _get_optional(item, "openPrice"),
                "high": _get_optional(item, "highPrice"),
                "low": _get_optional(item, "lowPrice"),
                "close": _get_optional(item, "closePrice"),
                "prev_close": _get_optional(item, "previousDayClosePrice")
                    or _get_optional(item, "previousClose")
                    or _get_optional(item, "prevClose"),
                "volume": _get_optional(item, "totalTradedVolume")
                    or _get_optional(item, "totalTradedQuantity"),
                "turnover": _get_optional(item, "totalTradedValue"),
                "change": _get_optional(item, "pointChange")
                    or _get_optional(item, "change"),
                "change_percent": _get_optional(item, "percentageChange")
                    or _get_optional(item, "percentChange"),
            }
        )
    return results


def parse_market_summary(data: dict[str, Any]) -> dict[str, Any]:
    """Parse market summary from /api/nots/market-summary."""
    return {
        "total_traded_volume": _get_optional(data, "totalTradedVolume", 0),
        "total_traded_value": _get_optional(data, "totalTradedValue", 0),
        "transactions": _get_optional(data, "transactions", 0),
        "previous_close": _get_optional(data, "previousClose", 0),
        "open": _get_optional(data, "open", 0),
        "high": _get_optional(data, "high", 0),
        "low": _get_optional(data, "low", 0),
        "close": _get_optional(data, "close", 0),
        "point_change": _get_optional(data, "pointChange", 0),
        "percent_change": _get_optional(data, "percentChange", 0),
    }


# ---------------------------------------------------------------------------
# Securities parsers
# ---------------------------------------------------------------------------


def parse_securities_list(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse securities list from /api/nots/securities."""
    results = []
    for item in data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "symbol": _get_optional(item, "symbol"),
                "company_name": _get_optional(item, "companyName"),
                "sector": _get_optional(item, "sector"),
                "security_type": _get_optional(item, "securityType"),
                "listing_date": _get_optional(item, "listingDate"),
                "paid_up_value": _get_optional(item, "paidUpValue"),
                "face_value": _get_optional(item, "faceValue"),
            }
        )
    return results


def parse_securities_simple(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse simple securities list from /api/nots/securities."""
    results = []
    for item in data:
        nepse_id = _get_optional(item, "securityId")
        if nepse_id is not None:
            try:
                nepse_id = int(nepse_id)
            except (ValueError, TypeError):
                nepse_id = None
        results.append(
            {
                "id": nepse_id,
                "symbol": _get_optional(item, "securitySymbol"),
                "name": _get_optional(item, "securityName"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Index parsers
# ---------------------------------------------------------------------------


def parse_indices(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse indices from /api/nots/nepse-index."""
    if isinstance(data, list):
        indices_data = data
    else:
        indices_data = _get_optional(data, "data", [])
    if not isinstance(indices_data, list):
        return []
    results = []
    for item in indices_data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "name": _get_optional(item, "indexName"),
                "index_value": _get_optional(item, "close"),
                "change": _get_optional(item, "pointChange"),
                "change_percent": _get_optional(item, "percentChange"),
            }
        )
    return results


def parse_sector_indices(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse sector indices from /api/nots/index."""
    if isinstance(data, list):
        indices_data = data
    else:
        indices_data = _get_optional(data, "data", [])
    if not isinstance(indices_data, list):
        return []
    results = []
    for item in indices_data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "name": _get_optional(item, "indexName"),
                "index_value": _get_optional(item, "close"),
                "change": _get_optional(item, "pointChange"),
                "change_percent": _get_optional(item, "percentChange"),
            }
        )
    return results


def parse_index_history(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse index history from /api/nots/index/history."""
    if isinstance(data, list):
        history_data = data
    elif isinstance(data, dict):
        history_data = _get_optional(data, "content", [])
        if not history_data:
            history_data = _get_optional(data, "data", [])
    else:
        return []
    if not isinstance(history_data, list):
        return []
    results = []
    for item in history_data:
        # API returns openIndex/highIndex/lowIndex/closingIndex
        open_val = _get_optional(item, "openIndex") or _get_optional(item, "open")
        high_val = _get_optional(item, "highIndex") or _get_optional(item, "high")
        low_val = _get_optional(item, "lowIndex") or _get_optional(item, "low")
        close_val = _get_optional(item, "closingIndex") or _get_optional(item, "close")
        results.append(
            {
                "business_date": _get_optional(item, "businessDate"),
                "open": open_val,
                "high": high_val,
                "low": low_val,
                "close": close_val,
                "volume": _get_optional(item, "totalTradedVolume") or _get_optional(item, "turnoverVolume"),
                "turnover": _get_optional(item, "totalTradedValue") or _get_optional(item, "turnoverValue"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Sector parsers
# ---------------------------------------------------------------------------


def parse_sectors(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse sectors from /api/nots/sector."""
    results = []
    for item in data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "name": _get_optional(item, "name"),
                "display_name": _get_optional(item, "desc"),
            }
        )
    return results


def parse_sectorwise_summary(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse sectorwise summary from /api/nots/sectorwise."""
    results = []
    for item in data:
        results.append(
            {
                "sector": _get_optional(item, "sector"),
                "ltp": _get_optional(item, "lastTradedPrice"),
                "change": _get_optional(item, "pointChange"),
                "change_percent": _get_optional(item, "percentChange"),
                "volume": _get_optional(item, "totalTradedVolume"),
                "turnover": _get_optional(item, "totalTradedValue"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Price history parser
# ---------------------------------------------------------------------------


def parse_price_history(data: dict[str, Any]) -> list[dict[str, Any]]:
    """Parse price history from /api/nots/security/price-history."""
    content = _get_optional(data, "content", data)
    if isinstance(content, dict):
        content = _get_optional(content, "content", [])
    if not isinstance(content, list):
        return []
    results = []
    for item in content:
        results.append(
            {
                "nepse_id": _get_optional(item, "securityId"),
                "business_date": _get_optional(item, "businessDate"),
                "ltp": _get_optional(item, "lastTradedPrice"),
                "open": _get_optional(item, "openPrice"),
                "high": _get_optional(item, "highPrice"),
                "low": _get_optional(item, "lowPrice"),
                "close": _get_optional(item, "closePrice"),
                "volume": _get_optional(item, "totalTradedVolume"),
                "turnover": _get_optional(item, "totalTradedValue"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Top stocks parser
# ---------------------------------------------------------------------------


def parse_top_stocks(data: dict[str, Any] | list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse top stocks from /api/nots/top-ten/* endpoints."""
    if isinstance(data, list):
        stocks_data = data
    elif isinstance(data, dict):
        stocks_data = _get_optional(data, "data", data)
        if isinstance(stocks_data, dict):
            stocks_data = _get_optional(stocks_data, "data", [])
    else:
        return []
    if not isinstance(stocks_data, list):
        return []
    results = []
    for item in stocks_data:
        results.append(
            {
                "symbol": _get_optional(item, "symbol"),
                "nepse_id": _get_optional(item, "securityId"),
                "ltp": _get_optional(item, "lastTradedPrice")
                    or _get_optional(item, "ltp")
                    or _get_optional(item, "closingPrice")
                    or _get_optional(item, "cp"),
                "change": _get_optional(item, "pointChange")
                    or _get_optional(item, "change"),
                "percent_change": _get_optional(item, "percentageChange")
                    or _get_optional(item, "percentChange"),
                "volume": _get_optional(item, "totalTradedVolume")
                    or _get_optional(item, "shareTraded")
                    or _get_optional(item, "volume"),
                "turnover": _get_optional(item, "totalTradedValue")
                    or _get_optional(item, "turnover"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Company fundamentals parsers
# ---------------------------------------------------------------------------


def parse_company_financials(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse company financials from /api/nots/application/reports/{id}.

    The API returns a list of application objects, each containing a nested
    ``fiscalReport`` dict with the actual financial metadata.

    Args:
        data: List of raw application dicts.

    Returns:
        List of normalized financial report dicts.
    """
    results = []
    for item in data:
        fr = item.get("fiscalReport")
        if not fr or not isinstance(fr, dict):
            continue

        fy = fr.get("financialYear")
        fy_name = fy.get("fyName") if isinstance(fy, dict) else None

        rtm = fr.get("reportTypeMaster")
        report_name = rtm.get("reportName") if isinstance(rtm, dict) else None

        if not fy_name and not report_name:
            continue

        # Build file URL from document details if available
        docs = item.get("applicationDocumentDetailsList") or []
        file_url = ""
        if docs and isinstance(docs, list):
            file_path = docs[0].get("filePath")
            if file_path:
                file_url = f"https://www.nepalstock.com/{file_path}"

        results.append({
            "fiscal_year": fy_name or "",
            "report_type": report_name or "",
            "file_url": file_url,
        })
    return results


# ---------------------------------------------------------------------------
# News parsers
# ---------------------------------------------------------------------------


def parse_notices(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse notices from /api/web/notice/.

    Args:
        data: List of raw notice dicts.

    Returns:
        List of normalized notice dicts.
    """
    results = []
    for item in data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "title": _get_optional(item, "title"),
                "date": _get_optional(item, "date"),
                "url": _get_optional(item, "url"),
            }
        )
    return results


# ---------------------------------------------------------------------------
# Broker parser
# ---------------------------------------------------------------------------


def parse_brokers(data: list[dict[str, Any]]) -> list[dict[str, Any]]:
    """Parse broker list from /api/nots/member.

    Args:
        data: List of raw broker dicts (from response 'content' field).

    Returns:
        List of normalized broker dicts.
    """
    results = []
    for item in data:
        results.append(
            {
                "id": _get_optional(item, "id"),
                "name": _get_optional(item, "memberName"),
                "code": _get_optional(item, "memberCode"),
                "contact_person": _get_optional(item, "contactPerson"),
                "contact_number": _get_optional(item, "contactNumber"),
            }
        )
    return results
