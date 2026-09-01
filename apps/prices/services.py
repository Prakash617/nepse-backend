"""Price synchronization service.

Syncs daily and intraday price data from NEPSE upstream.
DailyPrice uses (security, trading_date) as identity.
IntradayPrice appends records (no uniqueness constraint on upstream data).
"""

import logging
from datetime import date, datetime
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.prices.models import DailyPrice, IntradayPrice
from apps.securities.models import Security

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


def _to_datetime_utc(value: Any) -> datetime | None:
    """Safely convert a value to datetime (UTC). Returns None on failure."""
    if value is None:
        return None
    if isinstance(value, datetime):
        return value
    if isinstance(value, str):
        try:
            return datetime.fromisoformat(value)
        except (ValueError, TypeError):
            return None
    return None


def _resolve_security(
    security_id: int | None,
    symbol: str | None,
    security_map: dict[int, int] | dict[str, int],
) -> int | None:
    """Resolve a security reference to a database ID.

    Tries nepse_id first, then symbol.
    """
    if security_id is not None and security_id in security_map:
        return security_map[security_id]
    if symbol and symbol in security_map:
        return security_map[symbol]
    return None


def sync_daily_prices(prices_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize daily prices from upstream data.

    Idempotent: creates new records, updates existing ones.
    Identity: (security_id, trading_date).

    Args:
        prices_data: List of normalized price dicts from parse_today_prices()
                     or parse_price_history().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    # Build security lookup: nepse_id -> db_id, symbol -> db_id
    securities = Security.objects.all().values_list("id", "nepse_id", "symbol")
    nepse_id_to_db: dict[int, int] = {}
    symbol_to_db: dict[str, int] = {}
    for db_id, nepse_id, symbol in securities:
        nepse_id_to_db[nepse_id] = db_id
        if symbol:
            symbol_to_db[symbol.upper()] = db_id

    today = date.today()
    valid_records: list[dict[str, Any]] = []
    for data in prices_data:
        security_id_raw = data.get("security_id")
        symbol = data.get("symbol")
        trading_date = _to_date(data.get("business_date")) or today

        db_security_id = _resolve_security(security_id_raw, symbol, nepse_id_to_db)
        if db_security_id is None:
            # Try symbol lookup separately
            if symbol and symbol.upper() in symbol_to_db:
                db_security_id = symbol_to_db[symbol.upper()]

        if db_security_id is None:
            result.skipped += 1
            unresolved = symbol or security_id_raw or "unknown"
            result.errors.append(f"Unresolved security: {unresolved}")
            continue

        close_val = _to_decimal(data.get("close"))
        ltp_val = _to_decimal(data.get("ltp"))
        prev_close_val = _to_decimal(data.get("prev_close"))
        open_val = _to_decimal(data.get("open"))
        pct_change = _to_decimal(
            data.get("percent_change") or data.get("change_percent")
        )
        pt_change = _to_decimal(data.get("change"))

        current_val = close_val if close_val is not None else ltp_val
        prev_val = prev_close_val if prev_close_val is not None else open_val
        if pct_change is None and current_val is not None and prev_val is not None and prev_val > 0:
            pt_change = current_val - prev_val
            pct_change = ((current_val - prev_val) / prev_val) * Decimal(100)

        # NEPSE today-price API often only returns ltp, not close.
        # Use ltp as close when close is missing so downstream queries work.
        effective_close = close_val if close_val is not None else ltp_val

        valid_records.append({
            "security_id": db_security_id,
            "trading_date": trading_date,
            "open": open_val,
            "high": _to_decimal(data.get("high")),
            "low": _to_decimal(data.get("low")),
            "close": effective_close,
            "ltp": ltp_val,
            "previous_close": prev_close_val,
            "volume": _to_int(data.get("volume")),
            "turnover": _to_decimal(data.get("turnover")),
            "percentage_change": pct_change,
            "point_change": pt_change,
        })

    if not valid_records:
        return result

    # Build existing record lookup
    existing = DailyPrice.objects.filter(
        security_id__in={r["security_id"] for r in valid_records},
        trading_date__in={r["trading_date"] for r in valid_records},
    )
    existing_map = {
        (dp.security_id, dp.trading_date): dp for dp in existing
    }

    to_create: list[DailyPrice] = []
    to_update: list[DailyPrice] = []
    update_fields = {"open", "high", "low", "close", "ltp", "previous_close",
                     "volume", "turnover", "percentage_change", "point_change"}

    for rec in valid_records:
        key = (rec["security_id"], rec["trading_date"])
        existing_record = existing_map.get(key)

        if existing_record is not None:
            changed = False
            for field_name in update_fields:
                new_val = rec[field_name]
                old_val = getattr(existing_record, field_name)
                if old_val != new_val:
                    setattr(existing_record, field_name, new_val)
                    changed = True

            if changed:
                to_update.append(existing_record)
            else:
                result.skipped += 1
        else:
            to_create.append(DailyPrice(**rec))

    with transaction.atomic():
        if to_create:
            DailyPrice.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            DailyPrice.objects.bulk_update(to_update, update_fields)
            result.updated = len(to_update)

    logger.info(
        "Daily price sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result


def sync_historical_prices(
    symbols: list[str],
    start_date: date,
    end_date: date,
    client: Any | None = None,
    page_size: int = 500,
) -> SyncResult:
    """Synchronize historical daily prices for a list of securities over a date range.

    Fetches price history per-security from the upstream API (paginated),
    then persists using the existing sync_daily_prices() logic.

    Idempotent: safe to run repeatedly with overlapping ranges.
    Uses the existing DailyPrice (security, trading_date) uniqueness constraint.

    Args:
        symbols: List of ticker symbols to sync (e.g., ["NABIL", "NHPC"]).
        start_date: Start of date range (inclusive).
        end_date: End of date range (inclusive).
        client: Optional NepseClient instance. Creates one if not provided.
        page_size: Records per API page (default 500, upstream max).

    Returns:
        Aggregated SyncResult across all symbols and pages.
    """
    from integrations.nepse import NepseClient as NepseClientCls

    if client is None:
        client = NepseClientCls()

    aggregated = SyncResult()

    for symbol in symbols:
        symbol_upper = symbol.upper()
        page = 0

        while True:
            try:
                history_data = client.get_price_history(
                    ticker=symbol_upper,
                    start_date=start_date.isoformat(),
                    end_date=end_date.isoformat(),
                    page=page,
                    size=page_size,
                )
            except Exception as e:
                aggregated.failed += 1
                aggregated.errors.append(f"Failed to fetch history for {symbol_upper}: {e}")
                logger.error("Failed to fetch history for %s page %d: %s", symbol_upper, page, e)
                break

            if not history_data:
                break

            # Tag each record with the symbol for sync_daily_prices()
            tagged_data = []
            for record in history_data:
                tagged = dict(record)
                tagged["symbol"] = symbol_upper
                tagged_data.append(tagged)

            result = sync_daily_prices(tagged_data)
            aggregated.created += result.created
            aggregated.updated += result.updated
            aggregated.skipped += result.skipped
            aggregated.failed += result.failed
            aggregated.errors.extend(result.errors)

            # If fewer records than page_size, we've reached the end
            if len(history_data) < page_size:
                break

            page += 1

    logger.info(
        "Historical price sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        aggregated.created,
        aggregated.updated,
        aggregated.skipped,
        aggregated.failed,
    )
    return aggregated


def sync_intraday_prices(prices_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize intraday/live price data from upstream.

    NOTE: No uniqueness constraint is enforced on (security, timestamp)
    because upstream live data may contain multiple trades at the same
    timestamp. Each sync call appends new records. This is intentional —
    the upstream timestamp semantics are unclear and we do not invent
    deduplication rules.

    Args:
        prices_data: List of normalized live trade dicts from get_live_trades().

    Returns:
        SyncResult with created/skipped/failed counts.
    """
    result = SyncResult()

    securities = Security.objects.all().values_list("id", "nepse_id", "symbol")
    nepse_id_to_db: dict[int, int] = {}
    symbol_to_db: dict[str, int] = {}
    for db_id, nepse_id, symbol in securities:
        nepse_id_to_db[nepse_id] = db_id
        if symbol:
            symbol_to_db[symbol.upper()] = db_id

    to_create: list[IntradayPrice] = []
    for data in prices_data:
        security_id_raw = data.get("security_id")
        symbol = data.get("symbol")
        timestamp = _to_datetime_utc(data.get("business_date"))

        if timestamp is None:
            # For intraday, business_date may not have time component
            # Use current time as fallback is not appropriate — skip
            result.skipped += 1
            result.errors.append(f"Missing/invalid timestamp: {data}")
            continue

        db_security_id = _resolve_security(security_id_raw, symbol, nepse_id_to_db)
        if db_security_id is None and symbol and symbol.upper() in symbol_to_db:
            db_security_id = symbol_to_db[symbol.upper()]

        if db_security_id is None:
            result.skipped += 1
            unresolved = symbol or security_id_raw or "unknown"
            result.errors.append(f"Unresolved security: {unresolved}")
            continue

        to_create.append(IntradayPrice(
            security_id=db_security_id,
            timestamp=timestamp,
            ltp=_to_decimal(data.get("ltp")),
            volume=_to_int(data.get("volume")),
            turnover=_to_decimal(data.get("turnover")),
        ))

    if to_create:
        IntradayPrice.objects.bulk_create(to_create)
        result.created = len(to_create)

    logger.info(
        "Intraday price sync complete: created=%d, skipped=%d, failed=%d",
        result.created,
        result.skipped,
        result.failed,
    )
    return result
