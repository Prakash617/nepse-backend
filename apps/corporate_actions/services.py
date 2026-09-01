"""Corporate actions synchronization service.

Syncs dividend and bonus share data from NEPSE upstream.
Uses nepse_id as the primary synchronization identity.
"""

import logging
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.corporate_actions.models import BonusShare, Dividend
from apps.securities.models import Security

logger = logging.getLogger(__name__)


def _normalize_dividend_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single dividend record.

    Returns None if the record is invalid and cannot be synced.
    """
    nepse_id = data.get("nepse_id")
    fiscal_year = data.get("fiscal_year")

    if nepse_id is None or not fiscal_year:
        return None

    return {
        "nepse_id": int(nepse_id),
        "fiscal_year": str(fiscal_year).strip(),
        "dividend_per_share": data.get("dividend_per_share"),
        "bonus_shares": data.get("bonus_shares"),
        "announcement_date": data.get("announcement_date"),
    }


def sync_dividends(dividends_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize dividends from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new dividends and updates existing ones (matched by nepse_id + fiscal_year).
    Does not delete dividends that are missing from upstream.

    Args:
        dividends_data: List of normalized dividend dicts.

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_dividends: list[dict[str, Any]] = []
    for data in dividends_data:
        normalized = _normalize_dividend_data(data)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid dividend data: {data}")
            continue
        valid_dividends.append(normalized)

    if not valid_dividends:
        return result

    security_nepse_ids = list(set(d["nepse_id"] for d in valid_dividends))
    security_map = {
        s.nepse_id: s for s in Security.objects.filter(nepse_id__in=security_nepse_ids)
    }

    existing_dividends = Dividend.objects.filter(
        security__nepse_id__in=security_nepse_ids,
    )
    existing_map = {}
    for dividend in existing_dividends:
        key = (dividend.security.nepse_id, dividend.fiscal_year)
        existing_map[key] = dividend

    to_create: list[Dividend] = []
    to_update: list[tuple[Dividend, set[str]]] = []

    for dividend_data in valid_dividends:
        nepse_id = dividend_data["nepse_id"]
        security = security_map.get(nepse_id)
        if security is None:
            result.skipped += 1
            result.errors.append(f"No security found for nepse_id {nepse_id}")
            continue

        key = (nepse_id, dividend_data["fiscal_year"])
        existing = existing_map.get(key)

        if existing is not None:
            changed_fields: set[str] = set()
            if existing.dividend_per_share != dividend_data["dividend_per_share"]:
                existing.dividend_per_share = dividend_data["dividend_per_share"]
                changed_fields.add("dividend_per_share")
            if existing.bonus_shares != dividend_data["bonus_shares"]:
                existing.bonus_shares = dividend_data["bonus_shares"]
                changed_fields.add("bonus_shares")
            if existing.announcement_date != dividend_data["announcement_date"]:
                existing.announcement_date = dividend_data["announcement_date"]
                changed_fields.add("announcement_date")

            if changed_fields:
                to_update.append((existing, changed_fields))
            else:
                result.skipped += 1
        else:
            to_create.append(
                Dividend(
                    security=security,
                    fiscal_year=dividend_data["fiscal_year"],
                    dividend_per_share=dividend_data["dividend_per_share"],
                    bonus_shares=dividend_data["bonus_shares"],
                    announcement_date=dividend_data["announcement_date"],
                )
            )

    with transaction.atomic():
        if to_create:
            Dividend.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            for dividend, changed_fields in to_update:
                fields = changed_fields & {"dividend_per_share", "bonus_shares", "announcement_date"}
                if fields:
                    dividend.save(update_fields=fields)
            result.updated = len(to_update)

    logger.info(
        "Dividend sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result


def _normalize_bonus_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single bonus share record.

    Returns None if the record is invalid and cannot be synced.
    """
    nepse_id = data.get("nepse_id")
    fiscal_year = data.get("fiscal_year")

    if nepse_id is None or not fiscal_year:
        return None

    return {
        "nepse_id": int(nepse_id),
        "fiscal_year": str(fiscal_year).strip(),
        "bonus_ratio": str(data.get("bonus_ratio") or "").strip(),
        "announcement_date": data.get("announcement_date"),
    }


def sync_bonus_shares(bonus_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize bonus shares from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new bonus shares and updates existing ones (matched by nepse_id + fiscal_year).
    Does not delete bonus shares that are missing from upstream.

    Args:
        bonus_data: List of normalized bonus share dicts.

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_bonuses: list[dict[str, Any]] = []
    for data in bonus_data:
        normalized = _normalize_bonus_data(data)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid bonus data: {data}")
            continue
        valid_bonuses.append(normalized)

    if not valid_bonuses:
        return result

    security_nepse_ids = list(set(b["nepse_id"] for b in valid_bonuses))
    security_map = {
        s.nepse_id: s for s in Security.objects.filter(nepse_id__in=security_nepse_ids)
    }

    existing_bonuses = BonusShare.objects.filter(
        security__nepse_id__in=security_nepse_ids,
    )
    existing_map = {}
    for bonus in existing_bonuses:
        key = (bonus.security.nepse_id, bonus.fiscal_year)
        existing_map[key] = bonus

    to_create: list[BonusShare] = []
    to_update: list[tuple[BonusShare, set[str]]] = []

    for bonus_data_item in valid_bonuses:
        nepse_id = bonus_data_item["nepse_id"]
        security = security_map.get(nepse_id)
        if security is None:
            result.skipped += 1
            result.errors.append(f"No security found for nepse_id {nepse_id}")
            continue

        key = (nepse_id, bonus_data_item["fiscal_year"])
        existing = existing_map.get(key)

        if existing is not None:
            changed_fields: set[str] = set()
            if existing.bonus_ratio != bonus_data_item["bonus_ratio"]:
                existing.bonus_ratio = bonus_data_item["bonus_ratio"]
                changed_fields.add("bonus_ratio")
            if existing.announcement_date != bonus_data_item["announcement_date"]:
                existing.announcement_date = bonus_data_item["announcement_date"]
                changed_fields.add("announcement_date")

            if changed_fields:
                to_update.append((existing, changed_fields))
            else:
                result.skipped += 1
        else:
            to_create.append(
                BonusShare(
                    security=security,
                    fiscal_year=bonus_data_item["fiscal_year"],
                    bonus_ratio=bonus_data_item["bonus_ratio"],
                    announcement_date=bonus_data_item["announcement_date"],
                )
            )

    with transaction.atomic():
        if to_create:
            BonusShare.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            for bonus, changed_fields in to_update:
                fields = changed_fields & {"bonus_ratio", "announcement_date"}
                if fields:
                    bonus.save(update_fields=fields)
            result.updated = len(to_update)

    logger.info(
        "Bonus share sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result
