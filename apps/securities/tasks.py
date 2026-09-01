"""Security synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.securities.services import sync_securities
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


@shared_task(name="securities.sync_securities")
def sync_securities_task() -> dict:
    """Synchronize securities from NEPSE upstream.

    Thin wrapper around the service layer.
    """
    try:
        client = NepseClient()
        securities_data = client.get_securities()
    except NepseError as e:
        logger.error("Failed to fetch securities: %s", e)
        raise

    result = sync_securities(securities_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }
