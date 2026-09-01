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

    with transaction.atomic():
        existing = MarketSnapshot.objects.filter(trading_date=trading_date).first()

        if existing is not None:
            changed = False
            for field_name, new_val in snapshot_data.items():
                old_val = getattr(existing, field_name)
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
    return result
