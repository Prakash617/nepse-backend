"""Sector synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.sectors.services import sync_sectors
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


@shared_task(name="sectors.sync_sectors")
def sync_sectors_task() -> dict:
    """Synchronize sectors from NEPSE upstream.

    Thin wrapper around the service layer. This task should be
    called by Celery Beat or manually, not invoked directly
    with business logic.
    """
    try:
        client = NepseClient()
        sectors_data = client.get_sectors()
    except NepseError as e:
        logger.error("Failed to fetch sectors: %s", e)
        raise

    result = sync_sectors(sectors_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }
