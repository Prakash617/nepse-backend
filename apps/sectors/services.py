"""Sector synchronization service.

Syncs sector data from NEPSE upstream into the Sector model.
Uses nepse_id as the primary synchronization identity.
"""

import logging
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.sectors.models import Sector

logger = logging.getLogger(__name__)


def _normalize_sector_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single sector record.

    Returns None if the record is invalid and cannot be synced.
    """
    nepse_id = data.get("id")
    name = data.get("name")

    if nepse_id is None or name is None:
        return None

    return {
        "nepse_id": int(nepse_id),
        "name": str(name).strip(),
        "display_name": str(data.get("display_name") or "").strip(),
    }


def sync_sectors(sectors_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize sectors from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new sectors and updates existing ones (matched by nepse_id).
    Does not delete sectors that are missing from upstream.

    Args:
        sectors_data: List of normalized sector dicts from parse_sectors().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_sectors: list[dict[str, Any]] = []
    for data in sectors_data:
        normalized = _normalize_sector_data(data)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid sector data: {data}")
            continue
        valid_sectors.append(normalized)

    if not valid_sectors:
        return result

    nepse_ids = [s["nepse_id"] for s in valid_sectors]
    existing_map = {
        s.nepse_id: s for s in Sector.objects.filter(nepse_id__in=nepse_ids)
    }

    to_create: list[Sector] = []
    to_update: list[tuple[Sector, dict[str, Any]]] = []

    for sector_data in valid_sectors:
        nepse_id = sector_data["nepse_id"]
        existing = existing_map.get(nepse_id)

        if existing is not None:
            changed = False
            if existing.name != sector_data["name"]:
                existing.name = sector_data["name"]
                changed = True
            if existing.display_name != sector_data["display_name"]:
                existing.display_name = sector_data["display_name"]
                changed = True

            if changed:
                to_update.append((existing, sector_data))
            else:
                result.skipped += 1
        else:
            to_create.append(Sector(**sector_data))

    with transaction.atomic():
        if to_create:
            Sector.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            fields_to_update = {"name", "display_name"}
            bulk_update_list = [item[0] for item in to_update]
            Sector.objects.bulk_update(bulk_update_list, fields_to_update)
            result.updated = len(to_update)

    logger.info(
        "Sector sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result
