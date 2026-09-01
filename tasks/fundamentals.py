"""Periodic Celery tasks for NEPSE data synchronization.

Scheduled via django-celery-beat. Each task calls a thin wrapper around
the corresponding service function, per Phase 4 thin-task rule.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


# ---------------------------------------------------------------------------
# Fundamentals sync tasks
# ---------------------------------------------------------------------------


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_company_profiles_task(self) -> str:
    """Sync company profiles from NEPSE upstream.

    Scheduled to run once daily after market close (Sun–Fri).
    Retries up to 3 times on failure.
    """
    from apps.fundamentals.services import sync_company_profiles
    from integrations.nepse import NepseClient, NepseError

    try:
        client = NepseClient()
        securities = client.get_securities_simple()
        profiles_data = []
        for sec in securities:
            nepse_id = sec.get("id")
            if nepse_id is None:
                continue
            try:
                profile = client.get_company_profile(nepse_id)
                if isinstance(profile, dict):
                    profile["nepse_id"] = nepse_id
                    profiles_data.append(profile)
            except NepseError:
                continue

        result = sync_company_profiles(profiles_data)
        logger.info("Company profile sync task complete: %s", result)
        return f"Company profiles synced: {result}"
    except NepseError as exc:
        logger.error("Company profile sync task failed: %s", exc)
        raise self.retry(exc=exc) from exc


@shared_task(bind=True, max_retries=3, default_retry_delay=60)
def sync_financial_reports_task(self) -> str:
    """Sync financial reports from NEPSE upstream.

    Scheduled to run once daily after market close (Sun–Fri).
    Retries up to 3 times on failure.
    """
    from apps.fundamentals.services import sync_financial_reports
    from integrations.nepse import NepseClient, NepseError

    try:
        client = NepseClient()
        securities = client.get_securities_simple()
        reports_data = []
        for sec in securities:
            nepse_id = sec.get("id")
            if nepse_id is None:
                continue
            try:
                financials = client.get_company_financials(nepse_id)
                for report in financials:
                    report["nepse_id"] = nepse_id
                    reports_data.append(report)
            except NepseError:
                continue

        result = sync_financial_reports(reports_data)
        logger.info("Financial report sync task complete: %s", result)
        return f"Financial reports synced: {result}"
    except NepseError as exc:
        logger.error("Financial report sync task failed: %s", exc)
        raise self.retry(exc=exc) from exc
