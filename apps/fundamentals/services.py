"""Fundamentals synchronization service.

Syncs company profile and financial report data from NEPSE upstream.
Uses nepse_id as the primary synchronization identity.
"""

import logging
from typing import Any

from django.db import transaction

from apps.common.sync import SyncResult
from apps.fundamentals.models import CompanyProfile, FinancialReport
from apps.securities.models import Security

logger = logging.getLogger(__name__)


def _normalize_profile_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single company profile record.

    Handles both NEPSE raw API fields (companyName, addressField, phoneNumber)
    and pre-normalized fields (name, address, contact_number).

    Returns None if the record is invalid and cannot be synced.
    """
    nepse_id = data.get("nepse_id")
    if nepse_id is None:
        return None

    return {
        "nepse_id": int(nepse_id),
        "name": str(data.get("name") or data.get("companyName") or "").strip(),
        "address": str(
            data.get("address") or data.get("addressField") or ""
        ).strip(),
        "contact_number": str(
            data.get("contact_number") or data.get("phoneNumber") or ""
        ).strip(),
        "website": str(data.get("website") or "").strip(),
        "email": str(
            data.get("email") or data.get("companyEmail") or ""
        ).strip(),
        "description": str(
            data.get("description") or data.get("companyProfile") or ""
        ).strip(),
    }


def sync_company_profiles(profiles_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize company profiles from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new profiles and updates existing ones (matched by nepse_id).
    Does not delete profiles that are missing from upstream.

    Args:
        profiles_data: List of normalized profile dicts from parse_company_profile().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_profiles: list[dict[str, Any]] = []
    for data in profiles_data:
        normalized = _normalize_profile_data(data)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid profile data: {data}")
            continue
        valid_profiles.append(normalized)

    if not valid_profiles:
        return result

    nepse_ids = [p["nepse_id"] for p in valid_profiles]
    existing_map = {
        p.nepse_id: p for p in CompanyProfile.objects.filter(nepse_id__in=nepse_ids)
    }

    security_nepse_ids = [p["nepse_id"] for p in valid_profiles]
    security_map = {
        s.nepse_id: s for s in Security.objects.filter(nepse_id__in=security_nepse_ids)
    }

    to_create: list[CompanyProfile] = []
    to_update: list[tuple[CompanyProfile, set[str]]] = []
    update_fields = {"name", "address", "contact_number", "website", "email", "description"}

    for profile_data in valid_profiles:
        nepse_id = profile_data["nepse_id"]
        security = security_map.get(nepse_id)
        if security is None:
            result.skipped += 1
            result.errors.append(f"No security found for nepse_id {nepse_id}")
            continue

        existing = existing_map.get(nepse_id)
        if existing is not None:
            changed_fields: set[str] = set()
            for field_name in update_fields:
                if getattr(existing, field_name) != profile_data[field_name]:
                    setattr(existing, field_name, profile_data[field_name])
                    changed_fields.add(field_name)

            if changed_fields:
                to_update.append((existing, changed_fields))
            else:
                result.skipped += 1
        else:
            to_create.append(CompanyProfile(security=security, **profile_data))

    with transaction.atomic():
        if to_create:
            CompanyProfile.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            for profile, changed_fields in to_update:
                fields = changed_fields & update_fields
                if fields:
                    profile.save(update_fields=fields)
            result.updated = len(to_update)

    logger.info(
        "Company profile sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result


def _normalize_report_data(data: dict[str, Any]) -> dict[str, Any] | None:
    """Validate and normalize a single financial report record.

    Returns None if the record is invalid and cannot be synced.
    """
    nepse_id = data.get("nepse_id")
    fiscal_year = data.get("fiscal_year")
    report_type = data.get("report_type")

    if nepse_id is None or not fiscal_year or not report_type:
        return None

    return {
        "nepse_id": int(nepse_id),
        "fiscal_year": str(fiscal_year).strip(),
        "report_type": str(report_type).strip(),
        "file_url": str(data.get("file_url") or "").strip(),
    }


def sync_financial_reports(reports_data: list[dict[str, Any]]) -> SyncResult:
    """Synchronize financial reports from upstream data.

    Idempotent: running multiple times with the same data produces no duplicates.
    Creates new reports and updates existing ones (matched by nepse_id + fiscal_year + report_type).
    Does not delete reports that are missing from upstream.

    Args:
        reports_data: List of normalized report dicts from parse_company_financials().

    Returns:
        SyncResult with created/updated/skipped/failed counts.
    """
    result = SyncResult()

    valid_reports: list[dict[str, Any]] = []
    for data in reports_data:
        normalized = _normalize_report_data(data)
        if normalized is None:
            result.skipped += 1
            result.errors.append(f"Invalid report data: {data}")
            continue
        valid_reports.append(normalized)

    if not valid_reports:
        return result

    security_nepse_ids = list(set(r["nepse_id"] for r in valid_reports))
    security_map = {
        s.nepse_id: s for s in Security.objects.filter(nepse_id__in=security_nepse_ids)
    }

    existing_reports = FinancialReport.objects.filter(
        security__nepse_id__in=security_nepse_ids,
    )
    existing_map = {}
    for report in existing_reports:
        key = (report.security.nepse_id, report.fiscal_year, report.report_type)
        existing_map[key] = report

    to_create: list[FinancialReport] = []
    to_update: list[tuple[FinancialReport, set[str]]] = []

    for report_data in valid_reports:
        nepse_id = report_data["nepse_id"]
        security = security_map.get(nepse_id)
        if security is None:
            result.skipped += 1
            result.errors.append(f"No security found for nepse_id {nepse_id}")
            continue

        key = (nepse_id, report_data["fiscal_year"], report_data["report_type"])
        existing = existing_map.get(key)

        if existing is not None:
            changed_fields: set[str] = set()
            if existing.file_url != report_data["file_url"]:
                existing.file_url = report_data["file_url"]
                changed_fields.add("file_url")

            if changed_fields:
                to_update.append((existing, changed_fields))
            else:
                result.skipped += 1
        else:
            to_create.append(
                FinancialReport(
                    security=security,
                    fiscal_year=report_data["fiscal_year"],
                    report_type=report_data["report_type"],
                    file_url=report_data["file_url"],
                )
            )

    with transaction.atomic():
        if to_create:
            FinancialReport.objects.bulk_create(to_create, ignore_conflicts=True)
            result.created = len(to_create)

        if to_update:
            for report, changed_fields in to_update:
                fields = changed_fields & {"file_url"}
                if fields:
                    report.save(update_fields=fields)
            result.updated = len(to_update)

    logger.info(
        "Financial report sync complete: created=%d, updated=%d, skipped=%d, failed=%d",
        result.created,
        result.updated,
        result.skipped,
        result.failed,
    )
    return result
