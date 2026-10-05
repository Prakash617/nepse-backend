"""Market snapshot synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.market.services import sync_market_snapshot, sync_market_snapshot_from_indices
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
        is_all_zeros = (
            summary_data.get("total_traded_volume") in (0, None)
            and summary_data.get("total_traded_value") in (0, None)
        )
        if is_all_zeros:
            result = sync_market_snapshot_from_indices(client)
            if result.skipped and not result.created and not result.updated:
                result = sync_market_snapshot(summary_data)
        else:
            result = sync_market_snapshot(summary_data)
    except NepseError as e:
        logger.error("Failed to fetch market summary: %s", e)
        raise
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }
