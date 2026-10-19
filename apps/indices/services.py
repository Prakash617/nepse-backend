"""Index synchronization service.

Syncs market index definitions and historical snapshots from NEPSE upstream.
MarketIndex uses nepse_id as identity.
IndexSnapshot uses (index, trading_date) as identity.
"""

import logging
from datetime import date, datetime, timedelta, timezone as dt_timezone
from decimal import Decimal, InvalidOperation
from typing import Any

from django.core.cache import cache
from django.db import transaction
from django.db.models import Max

from apps.common.sync import SyncResult
from apps.indices.models import IndexSnapshot, MarketIndex
from apps.market.models import MarketSnapshot
from apps.market.services import get_current_market_status
from apps.prices.models import DailyPrice
from integrations.nepse.client import NepseClient

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


def sync_indices(indices_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize market index definitions from upstream data.

    Idempotent: creates new indices and updates existing ones (matched by nepse_id).
    Does not delete indices that are missing from upstream.

    Args:
        indices_data: List of normalized index dicts from parse_indices()
                      or parse_sector_indices().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_indices: list[dict[str, Any]] = []
    for data in indices_data:
        nepse_id = data.get("id")
        name = data.get("name")

        if nepse_id is None or name is None:
            result.skipped += 1
            result.errors.append(f"Invalid index data: {data}")
            continue

        valid_indices.append({
            "nepse_id": int(nepse_id),
            "name": str(name).strip(),
        })

    if not valid_indices:
        return result

    nepse_ids = [idx["nepse_id"] for idx in valid_indices]
    existing_map = {
        idx.nepse_id: idx for idx in MarketIndex.objects.filter(nepse_id__in=nepse_ids)
    }

    to_create: list[MarketIndex] = []
    to_update: list[MarketIndex] = []

    for idx_data in valid_indices:
        nepse_id = idx_data["nepse_id"]
        existing = existing_map.get(nepse_id)

        if existing is not None:
            if existing.name != idx_data["name"]:
                existing.name = idx_data["name"]
                to_update.append(existing)
            else:
                result.skipped += 1
        else:
            to_create.append(MarketIndex(**idx_data))

    with transaction.atomic():
        if to_create:
            MarketIndex.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            MarketIndex.objects.bulk_update(to_update, ["name"])
            result.updated = len(to_update)

    logger.info(
        "Index sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result


def sync_index_snapshots(
    index_id: int,
    snapshots_data: list[dict[str, Any]],
) -> SyncResult:
    """Synchronize index history snapshots for a specific index.

    Idempotent: creates new snapshots and updates existing ones.
    Identity: (index_id, trading_date).

    Args:
        index_id: The MarketIndex nepse_id.
        snapshots_data: List of normalized history dicts from parse_index_history().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    try:
        market_index = MarketIndex.objects.get(nepse_id=index_id)
    except MarketIndex.DoesNotExist:
        result.failed = len(snapshots_data)
        result.errors.append(f"MarketIndex with nepse_id={index_id} not found. Sync indices first.")
        return result

    valid_records: list[dict[str, Any]] = []
    for data in snapshots_data:
        trading_date = _to_date(data.get("business_date"))
        if trading_date is None:
            result.skipped += 1
            result.errors.append(f"Missing/invalid trading_date: {data}")
            continue

        valid_records.append({
            "index_id": market_index.id,
            "trading_date": trading_date,
            "open": _to_decimal(data.get("open")),
            "high": _to_decimal(data.get("high")),
            "low": _to_decimal(data.get("low")),
            "close": _to_decimal(data.get("close")),
            "volume": _to_int(data.get("volume")),
            "turnover": _to_decimal(data.get("turnover")),
            "point_change": _to_decimal(data.get("point_change")),
            "percentage_change": _to_decimal(data.get("percentage_change")),
        })

    if not valid_records:
        return result

    # Build existing lookup
    existing = IndexSnapshot.objects.filter(
        index=market_index,
        trading_date__in={r["trading_date"] for r in valid_records},
    )
    existing_map = {snap.trading_date: snap for snap in existing}

    to_create: list[IndexSnapshot] = []
    to_update: list[IndexSnapshot] = []
    update_fields = {"open", "high", "low", "close", "volume", "turnover",
                     "point_change", "percentage_change"}

    for rec in valid_records:
        existing_snap = existing_map.get(rec["trading_date"])

        if existing_snap is not None:
            changed = False
            for field_name in update_fields:
                new_val = rec[field_name]
                old_val = getattr(existing_snap, field_name)
                if old_val != new_val:
                    setattr(existing_snap, field_name, new_val)
                    changed = True

            if changed:
                to_update.append(existing_snap)
            else:
                result.skipped += 1
        else:
            to_create.append(IndexSnapshot(**rec))

    with transaction.atomic():
        if to_create:
            IndexSnapshot.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            IndexSnapshot.objects.bulk_update(to_update, update_fields)
            result.updated = len(to_update)

    logger.info(
        "Index snapshot sync complete (index=%s): created=%d, updated=%d, skipped=%d, failed=%d",
        index_id,
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result


def get_index_intraday_data(nepse_id: int = 58) -> dict[str, Any]:
    """Retrieve full intraday details, session curve, and breadth for an index.

    Includes:
    - Real-time / latest index quote (value, change, per_change, high, low, open, close)
    - Full intraday session tick series (time, timestamp, value) from /graph/index/{nepse_id}
    - Market breadth (advanced, declined, unchanged count) from /securityDailyTradeStat/{nepse_id}
    - Total turnover, traded volume, and transactions
    - Market status (MARKET OPEN / MARKET CLOSED) and as_of date string
    """
    cache_key = f"nepse_index_intraday_{nepse_id}"
    cached_data = cache.get(cache_key)
    if cached_data is not None:
        return cached_data

    npt = dt_timezone(timedelta(hours=5, minutes=45))
    status_info = get_current_market_status()
    is_open = status_info.get("is_open", False)
    market_status_text = "MARKET OPEN" if is_open else "MARKET CLOSED"

    # Default fallback values from DB
    market_index = MarketIndex.objects.filter(nepse_id=nepse_id).first()
    index_name = market_index.name if market_index else ("NEPSE Index" if nepse_id == 58 else f"Index {nepse_id}")

    latest_snapshot = (
        IndexSnapshot.objects.filter(index__nepse_id=nepse_id)
        .order_by("-trading_date")
        .first()
    )
    latest_market_snap = MarketSnapshot.objects.order_by("-trading_date").first()

    current_value = float(latest_snapshot.close if latest_snapshot and latest_snapshot.close else 2634.17)
    point_change = float(latest_snapshot.point_change if latest_snapshot and latest_snapshot.point_change else 0.0)
    percentage_change = float(latest_snapshot.percentage_change if latest_snapshot and latest_snapshot.percentage_change else 0.0)
    high_val = float(latest_snapshot.high if latest_snapshot and latest_snapshot.high else current_value)
    low_val = float(latest_snapshot.low if latest_snapshot and latest_snapshot.low else current_value)
    open_val = float(latest_snapshot.open if latest_snapshot and latest_snapshot.open else current_value)
    close_val = current_value
    prev_close_val = current_value - point_change

    total_turnover = float(latest_market_snap.total_turnover) if latest_market_snap and latest_market_snap.total_turnover else None
    total_shares = latest_market_snap.total_volume if latest_market_snap else None
    transactions = latest_market_snap.transactions if latest_market_snap else None

    # Fallback breadth from DailyPrice
    adv_count = 0
    dec_count = 0
    unc_count = 0
    total_count = 0
    latest_dp_date = DailyPrice.objects.aggregate(latest=Max("trading_date")).get("latest")
    if latest_dp_date:
        dp_qs = DailyPrice.objects.filter(trading_date=latest_dp_date)
        adv_count = dp_qs.filter(point_change__gt=0).count()
        dec_count = dp_qs.filter(point_change__lt=0).count()
        unc_count = dp_qs.filter(point_change=0).count()
        total_count = dp_qs.count()

    points: list[dict[str, Any]] = []
    as_of_str = status_info.get("as_of") or "Oct 16 | 3:00 PM"

    # Attempt upstream fetch
    try:
        client = NepseClient()
        # 1. Intraday graph
        raw_graph = client.get_live_index(nepse_id)
        if raw_graph and isinstance(raw_graph, list):
            for pt in raw_graph:
                if isinstance(pt, (list, tuple)) and len(pt) >= 2:
                    ts = int(pt[0])
                    val = float(pt[1])
                    dt_pt = datetime.fromtimestamp(ts, tz=npt)
                    points.append({
                        "time": dt_pt.strftime("%H:%M"),
                        "timestamp": ts,
                        "value": round(val, 2),
                    })

        # 2. Upstream index details
        raw_indices = client._request("GET", "/api/nots/nepse-index") if nepse_id in (57, 58, 62, 63) else client._request("GET", "/api/nots/index")
        if isinstance(raw_indices, list):
            matching = next((item for item in raw_indices if item.get("id") == nepse_id), None)
            if matching:
                if matching.get("index") or matching.get("indexName"):
                    index_name = matching.get("index") or matching.get("indexName")
                if matching.get("currentValue") is not None:
                    current_value = float(matching["currentValue"])
                elif matching.get("close") is not None:
                    current_value = float(matching["close"])

                if matching.get("change") is not None:
                    point_change = float(matching["change"])
                elif matching.get("pointChange") is not None:
                    point_change = float(matching["pointChange"])

                if matching.get("perChange") is not None:
                    percentage_change = float(matching["perChange"])
                elif matching.get("percentChange") is not None:
                    percentage_change = float(matching["percentChange"])

                if matching.get("high") is not None:
                    high_val = float(matching["high"])
                if matching.get("low") is not None:
                    low_val = float(matching["low"])
                if matching.get("close") is not None:
                    close_val = float(matching["close"])
                if matching.get("previousClose") is not None:
                    prev_close_val = float(matching["previousClose"])

        # 3. Upstream market summary for turnover and shares
        raw_summary = client._request("GET", "/api/nots/market-summary")
        if isinstance(raw_summary, list):
            for s in raw_summary:
                d = str(s.get("detail", ""))
                v = s.get("value")
                if "Turnover" in d and v is not None:
                    total_turnover = float(v)
                elif "Traded Shares" in d and v is not None:
                    total_shares = int(v)
                elif "Transactions" in d and v is not None:
                    transactions = int(v)

        # 4. Upstream breadth
        raw_stats = client.get_security_daily_trade_stat(nepse_id)
        if raw_stats and isinstance(raw_stats, list):
            adv_count = sum(1 for t in raw_stats if (t.get("percentageChange") or 0) > 0)
            dec_count = sum(1 for t in raw_stats if (t.get("percentageChange") or 0) < 0)
            unc_count = sum(1 for t in raw_stats if (t.get("percentageChange") or 0) == 0)
            total_count = len(raw_stats)

        # Compute accurate as_of string
        if points:
            last_ts = points[-1]["timestamp"]
            last_dt = datetime.fromtimestamp(last_ts, tz=npt)
            if not is_open:
                as_of_str = f"{last_dt.strftime('%b %d')} | 3:00 PM"
            else:
                as_of_str = last_dt.strftime("%b %d | %I:%M %p")
    except Exception as e:
        logger.warning("Failed to fetch live index intraday from NEPSE upstream: %s", e)

    result_payload = {
        "nepse_id": nepse_id,
        "name": index_name,
        "current_value": round(current_value, 2),
        "point_change": round(point_change, 2),
        "percentage_change": round(percentage_change, 2),
        "high": round(high_val, 2),
        "low": round(low_val, 2),
        "open": round(open_val, 2),
        "close": round(close_val, 2),
        "previous_close": round(prev_close_val, 2),
        "as_of": as_of_str,
        "status": market_status_text,
        "is_open": is_open,
        "total_turnover": total_turnover,
        "total_shares": total_shares,
        "transactions": transactions,
        "breadth": {
            "advanced": adv_count,
            "declined": dec_count,
            "unchanged": unc_count,
            "total": total_count,
        },
        "points": points,
    }

    cache_ttl = 15 if is_open else 120
    cache.set(cache_key, result_payload, timeout=cache_ttl)
    return result_payload
