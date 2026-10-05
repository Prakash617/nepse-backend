"""Market snapshot synchronization service.

Syncs daily market-wide aggregate data from NEPSE upstream.
MarketSnapshot uses trading_date as identity.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.market.models import MarketSnapshot
from integrations.nepse import NepseClient

logger = logging.getLogger(__name__)


def _to_decimal(value: Any) -> Decimal | None:
    """Safely convert a value to Decimal. Returns None on failure."""
    if value is None:
        return None
    try:
        return Decimal(str(value))
    except (InvalidOperation, ValueError, TypeError):
        return None


def _to_int(value: Any) -> int | None:
    """Safely convert a value to int. Returns None on failure."""
    if value is None:
        return None
    try:
        return int(value)
    except (ValueError, TypeError):
        return None


def _to_date(value: Any) -> date | None:
    """Safely convert a value to date. Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, date):
        return value
    if isinstance(value, str):
        try:
            return date.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


def sync_market_snapshot(summary_data: dict[str, Any], trading_date: date | None = None) -> SyncResult:
    """Synchronize a market snapshot from upstream summary data.

    Idempotent: creates or updates a single snapshot for the given trading date.
    Identity: trading_date.

    Args:
        summary_data: Normalized market summary dict from parse_market_summary().
        trading_date: The trading date for this snapshot. If None, uses today.

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    if trading_date is None:
        from datetime import date as date_cls
        trading_date = date_cls.today()

    snapshot_data = {
        "total_volume": _to_int(summary_data.get("total_traded_volume")),
        "total_turnover": _to_decimal(summary_data.get("total_traded_value")),
        "transactions": _to_int(summary_data.get("transactions")),
        "open": _to_decimal(summary_data.get("open")),
        "high": _to_decimal(summary_data.get("high")),
        "low": _to_decimal(summary_data.get("low")),
        "close": _to_decimal(summary_data.get("close")),
        "previous_close": _to_decimal(summary_data.get("prev_close")),
        "point_change": _to_decimal(summary_data.get("change")),
        "percentage_change": _to_decimal(summary_data.get("percent_change")),
    }

    # Skip if the incoming data is explicitly all zeros from upstream closed market
    is_upstream_all_zeros = (
        summary_data.get("total_traded_volume") == 0
        and summary_data.get("total_traded_value") == 0
    )
    if is_upstream_all_zeros:
        logger.info("Skipping market snapshot sync — upstream returned all zeros (market closed).")
        result.skipped = 1
        return result

    _apply_snapshot(trading_date, snapshot_data, result)
    return result


def sync_market_snapshot_from_indices(client: Any, trading_date: date | None = None) -> SyncResult:
    """Synchronize market snapshot from NEPSE index and summary history APIs.

    Uses get_index_history() for OHLC index values and get_market_summary_history()
    for volume/turnover. This is more reliable than get_market_summary() which
    returns zeros when the market is closed.

    Args:
        client: NepseClient instance.
        trading_date: The trading date. If None, uses today.

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    if trading_date is None:
        from datetime import date as date_cls
        trading_date = date_cls.today()

    date_str = trading_date.isoformat()

    # 1. Get NEPSE Index OHLC from index history (id=58 is NEPSE Index)
    # Fetch a range to include previous trading day for prev_close calculation
    from datetime import timedelta
    lookback = trading_date - timedelta(days=7)
    try:
        index_history = client.get_index_history(
            index_id=58, start_date=lookback.isoformat(), end_date=date_str
        )
    except Exception as e:
        logger.warning("Failed to fetch index history: %s", e)
        index_history = []

    # 2. Get volume/turnover/transactions from market summary history
    try:
        summary_history = client.get_market_summary_history()
        today_summary = None
        for h in summary_history:
            if h.get("businessDate") == date_str:
                today_summary = h
                break
    except Exception as e:
        logger.warning("Failed to fetch market summary history: %s", e)
        today_summary = None

    # 3. Get previous day close for percentage calculation
    prev_close = None
    try:
        # Find yesterday's entry in the index history (keys are snake_case after parsing)
        if index_history:
            for entry in index_history:
                entry_date = _to_date(entry.get("business_date"))
                if entry_date and entry_date < trading_date:
                    prev_close = _to_decimal(entry.get("close"))
                    if prev_close and prev_close > 0:
                        break
    except Exception as e:
        logger.warning("Failed to get previous close: %s", e)

    # If today's index history has the data, use it (keys are snake_case after parsing)
    open_val = None
    high_val = None
    low_val = None
    close_val = None

    if index_history:
        today_entry = index_history[0] if index_history else {}
        open_val = _to_decimal(today_entry.get("open"))
        high_val = _to_decimal(today_entry.get("high"))
        low_val = _to_decimal(today_entry.get("low"))
        # close may be None if market is still open; fall back to live index
        raw_close = _to_decimal(today_entry.get("close"))
        if raw_close and raw_close > 0:
            close_val = raw_close

    # If close is still missing/zero, use live index
    if not close_val or close_val == 0:
        try:
            live_data = client.get_live_index(index_id=58)
            if live_data:
                close_val = _to_decimal(live_data[-1][1])
        except Exception as e:
            logger.warning("Failed to fetch live index: %s", e)

    # If open is missing, use close
    if not open_val or open_val == 0:
        open_val = close_val

    # If high/low missing, use close
    if not high_val or high_val == 0:
        high_val = close_val
    if not low_val or low_val == 0:
        low_val = close_val

    # Calculate change from previous close
    point_change = None
    pct_change = None
    if close_val and prev_close and prev_close > 0:
        point_change = close_val - prev_close
        pct_change = (point_change / prev_close) * Decimal("100")

    # Extract volume/turnover from summary history
    total_volume = None
    total_turnover = None
    transactions = None
    if today_summary:
        total_volume = _to_int(today_summary.get("totalTradedShares"))
        total_turnover = _to_decimal(today_summary.get("totalTurnover"))
        transactions = _to_int(today_summary.get("totalTransactions"))

    snapshot_data = {
        "total_volume": total_volume,
        "total_turnover": total_turnover,
        "transactions": transactions,
        "open": open_val,
        "high": high_val,
        "low": low_val,
        "close": close_val,
        "previous_close": prev_close,
        "point_change": point_change,
        "percentage_change": pct_change,
    }

    # Skip if no index data at all
    if not close_val or close_val == 0:
        logger.info("Skipping — no valid NEPSE Index value available.")
        result.skipped = 1
        return result

    _apply_snapshot(trading_date, snapshot_data, result)
    return result


def _apply_snapshot(trading_date: date, snapshot_data: dict[str, Any], result: SyncResult) -> None:
    """Apply snapshot data to database (create or update)."""
    with transaction.atomic():
        existing = MarketSnapshot.objects.filter(trading_date=trading_date).first()

        if existing is not None:
            changed = False
            for field_name, new_val in snapshot_data.items():
                old_val = getattr(existing, field_name)
                # Skip zero/None values when existing has real data
                if old_val is not None and old_val != 0 and (new_val is None or new_val == 0):
                    continue
                if old_val != new_val:
                    setattr(existing, field_name, new_val)
                    changed = True

            if changed:
                existing.save()
                result.updated = 1
            else:
                result.skipped = 1
        else:
            MarketSnapshot.objects.create(trading_date=trading_date, **snapshot_data)
            result.created = 1

    logger.info(
        "Market snapshot sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )


def get_current_market_status(client: Any = None) -> dict[str, Any]:
    """Determine current NEPSE market status (live or closed).

    Tries upstream NEPSE client first; falls back to NEPSE market trading hours
    (Sun-Thu, 11:00 AM - 3:00 PM Asia/Kathmandu) if upstream is unreachable or in tests.
    """
    import zoneinfo

    from django.core.cache import cache
    from django.db.models import Max
    from django.utils import timezone

    from apps.prices.models import DailyPrice

    now_npt = timezone.now().astimezone(zoneinfo.ZoneInfo("Asia/Kathmandu"))

    # Simulation check: allow tests and demo simulation to force market state
    simulated_market_open = cache.get("nepse_simulation_market_open")
    if simulated_market_open is not None:
        is_open = bool(simulated_market_open)
        latest_date_res = DailyPrice.objects.aggregate(latest=Max("trading_date"))
        latest_date = latest_date_res.get("latest")
        return {
            "is_open": is_open,
            "status": "LIVE" if is_open else "CLOSED",
            "as_of": now_npt.isoformat(),
            "trading_date": latest_date.isoformat() if latest_date else now_npt.date().isoformat(),
            "source": "simulation",
            "message": "Market is LIVE (Simulated)" if is_open else "Market is CLOSED (Simulated)",
            "detail": "Simulation — Continuous Trading Active" if is_open else "Simulation — Market is closed",
            "trading_hours": "Sunday - Thursday, 11:00 AM - 3:00 PM NPT",
        }

    upstream_status = None
    if client is None:
        try:
            client = NepseClient()
        except Exception as e:
            logger.debug("Could not initialize NepseClient: %s", e)
            client = None

    if client is not None:
        try:
            upstream_status = client.get_market_status()
        except Exception as e:
            logger.debug("Failed to query market status from upstream: %s", e)
            upstream_status = None

    weekday = now_npt.weekday()  # Monday=0 ... Sunday=6
    is_trading_day = weekday in (6, 0, 1, 2, 3)
    minutes_from_midnight = now_npt.hour * 60 + now_npt.minute

    if upstream_status is not None and "is_open" in upstream_status:
        is_open = bool(upstream_status["is_open"])
        source = "nepse_api"
        if is_open:
            detail = "Continuous Trading Session"
        else:
            if not is_trading_day:
                detail = "Weekend — Market is closed"
            elif minutes_from_midnight < (11 * 60):
                detail = "Closed — Opens at 11:00 AM NPT"
            elif minutes_from_midnight >= (15 * 60):
                detail = "Closed for today — Closed at 3:00 PM NPT"
            else:
                detail = "Market is currently closed"
    else:
        # Schedule-based evaluation
        source = "schedule_fallback"
        if not is_trading_day:
            is_open = False
            detail = "Weekend — Market is closed"
        elif minutes_from_midnight < (10 * 60 + 30):
            is_open = False
            detail = "Closed — Opens today at 11:00 AM NPT"
        elif (10 * 60 + 30) <= minutes_from_midnight < (11 * 60):
            is_open = False
            detail = "Pre-Open Session (10:30 AM – 11:00 AM NPT)"
        elif (11 * 60) <= minutes_from_midnight < (15 * 60):
            is_open = True
            detail = "Continuous Trading Live — Closes at 3:00 PM NPT"
        else:
            is_open = False
            detail = "Closed for today — Closed at 3:00 PM NPT"

    latest_date_res = DailyPrice.objects.aggregate(latest=Max("trading_date"))
    latest_date = latest_date_res.get("latest")

    return {
        "is_open": is_open,
        "status": "LIVE" if is_open else "CLOSED",
        "as_of": now_npt.isoformat(),
        "trading_date": latest_date.isoformat() if latest_date else None,
        "source": source,
        "message": "Market is LIVE" if is_open else "Market is CLOSED",
        "detail": detail,
        "trading_hours": "Sunday - Thursday, 11:00 AM - 3:00 PM NPT",
    }

