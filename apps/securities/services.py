"""Security synchronization service.

Syncs security data from NEPSE upstream into the Security model.
Uses nepse_id as the primary synchronization identity.
Handles sector matching by normalizing sector name strings.
"""

import logging
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.sectors.models import Sector
from apps.securities.models import Security

logger = logging.getLogger(__name__)


def _build_sector_lookup() -> dict[str, int]:
    """Build a normalized sector name -> id lookup map.

    Normalizes: lowercase, strips whitespace.
    If multiple sectors normalize to the same key, the last one wins
    (this should not happen in practice).
    """
    sectors = Sector.objects.all()
    lookup: dict[str, int] = {}
    for sector in sectors:
        normalized = _normalize_sector_name(sector.name)
        if normalized:
            lookup[normalized] = sector.id
    return lookup


def _normalize_sector_name(name: str | None) -> str:
    """Normalize a sector name for matching.

    - lowercase
    - strip whitespace
    - collapse multiple spaces
    """
    if not name:
        return ""
    import re
    return re.sub(r"\s+", " ", name.strip().lower())


def _match_sector(
    sector_name: str | None,
    sector_lookup: dict[str, int],
) -> int | None:
    """Match an upstream sector name to a Sector database ID.

    Returns the Sector ID if a confident match is found, None otherwise.
    """
    if not sector_name or not sector_name.strip():
        return None

    normalized = _normalize_sector_name(sector_name)
    if not normalized:
        return None

    sector_id = sector_lookup.get(normalized)
    if sector_id is not None:
        return sector_id

    logger.debug("No sector match for upstream name: '%s' (normalized: '%s')", sector_name, normalized)
    return None


def _normalize_security_data(
    data: dict[str, Any],
    sector_lookup: dict[str, int],
) -> dict[str, Any] | None:
    """Validate and normalize a single security record.

    Returns None if the record is invalid.
    """
    nepse_id = data.get("id")
    symbol = data.get("symbol")
    company_name = data.get("company_name")

    if nepse_id is None or symbol is None:
        return None

    sector_name = data.get("sector")
    sector_id = _match_sector(sector_name, sector_lookup)

    listing_date = data.get("listing_date")
    if listing_date and isinstance(listing_date, str):
        from datetime import date
        try:
            listing_date = date.fromisoformat(listing_date)
        except (ValueError, TypeError):
            listing_date = None

    paid_up_value = data.get("paid_up_value")
    if paid_up_value is not None:
        try:
            from decimal import Decimal
            paid_up_value = Decimal(str(paid_up_value))
        except (ValueError, TypeError):
            paid_up_value = None

    face_value = data.get("face_value")
    if face_value is not None:
        try:
            from decimal import Decimal
            face_value = Decimal(str(face_value))
        except (ValueError, TypeError):
            face_value = None

    return {
        "nepse_id": int(nepse_id),
        "symbol": str(symbol).strip().upper(),
        "company_name": str(company_name or "").strip(),
        "sector_id": sector_id,
        "security_type": str(data.get("security_type") or "").strip(),
        "listing_date": listing_date,
        "paid_up_value": paid_up_value,
        "face_value": face_value,
    }


def sync_securities(securities_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize securities from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new securities and updates existing ones (matched by nepse_id).
    Does not delete securities that disappear from upstream.

    Args:
        securities_data: List of normalized security dicts from parse_securities_list().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()
    sector_lookup = _build_sector_lookup()

    valid_securities: list[dict[str, Any]] = []
    for data in securities_data:
        normalized = _normalize_security_data(data, sector_lookup)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid security data: {data}")
            continue
        valid_securities.append(normalized)

    if not valid_securities:
        return result

    nepse_ids = [s["nepse_id"] for s in valid_securities]
    existing_map = {
        s.nepse_id: s for s in Security.objects.filter(nepse_id__in=nepse_ids)
    }

    to_create: list[Security] = []
    to_update: list[tuple[Security, set[str]]] = []
    update_fields = {"symbol", "company_name", "sector_id", "security_type",
                     "listing_date", "paid_up_value", "face_value"}

    for sec_data in valid_securities:
        nepse_id = sec_data["nepse_id"]
        existing = existing_map.get(nepse_id)

        if existing is not None:
            changed_fields: set[str] = set()
            if existing.symbol != sec_data["symbol"]:
                changed_fields.add("symbol")
                existing.symbol = sec_data["symbol"]
            if existing.company_name != sec_data["company_name"]:
                changed_fields.add("company_name")
                existing.company_name = sec_data["company_name"]
            if existing.sector_id != sec_data["sector_id"]:
                changed_fields.add("sector_id")
                existing.sector_id = sec_data["sector_id"]
            if existing.security_type != sec_data["security_type"]:
                changed_fields.add("security_type")
                existing.security_type = sec_data["security_type"]
            if existing.listing_date != sec_data["listing_date"]:
                changed_fields.add("listing_date")
                existing.listing_date = sec_data["listing_date"]
            if existing.paid_up_value != sec_data["paid_up_value"]:
                changed_fields.add("paid_up_value")
                existing.paid_up_value = sec_data["paid_up_value"]
            if existing.face_value != sec_data["face_value"]:
                changed_fields.add("face_value")
                existing.face_value = sec_data["face_value"]

            if changed_fields:
                to_update.append((existing, changed_fields))
            else:
                result.skipped += 1
        else:
            to_create.append(Security(**sec_data))

    with transaction.atomic():
        if to_create:
            Security.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            for security, changed_fields in to_update:
                fields = changed_fields & update_fields
                if fields:
                    security.save(update_fields=fields)
            result.updated = len(to_update)

    logger.info(
        "Security sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result
