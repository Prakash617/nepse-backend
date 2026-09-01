"""Index synchronization service.

Syncs market index definitions and historical snapshots from NEPSE upstream.
MarketIndex uses nepse_id as identity.
IndexSnapshot uses (index, trading_date) as identity.
"""

import logging
from datetime import date
from decimal import Decimal, InvalidOperation
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.indices.models import IndexSnapshot, MarketIndex

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
