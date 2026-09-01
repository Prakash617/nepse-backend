"""Market snapshot synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.market.services import sync_market_snapshot
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


@shared_task(name="market.sync_market_snapshot")
def sync_market_snapshot_task() -> dict:
    """Synchronize market snapshot from NEPSE upstream.

    Thin wrapper around the service layer.
    """
    try:
        client = NepseClient()
        summary_data = client.get_market_summary()
    except NepseError as e:
        logger.error("Failed to fetch market summary: %s", e)
        raise

    result = sync_market_snapshot(summary_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }
