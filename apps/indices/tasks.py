"""Index synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.indices.services import sync_index_snapshots, sync_indices
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


@shared_task(name="indices.sync_indices")
def sync_indices_task() -> dict:
    """Synchronize market index definitions from NEPSE upstream.

    Thin wrapper around the service layer.
    """
    try:
        client = NepseClient()
        nepse_indices = client.get_indices()
        sector_indices = client.get_sector_indices()
        all_indices = nepse_indices + sector_indices
    except NepseError as e:
        logger.error("Failed to fetch indices: %s", e)
        raise

    result = sync_indices(all_indices)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }


@shared_task(name="indices.sync_index_snapshots")
def sync_index_snapshots_task(
    index_id: int,
    start_date: str,
    end_date: str,
) -> dict:
    """Synchronize index history snapshots for a specific index.

    Thin wrapper around the service layer.

    Args:
        index_id: The MarketIndex nepse_id.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
    """
    try:
        client = NepseClient()
        snapshots_data = client.get_index_history(index_id, start_date, end_date)
    except NepseError as e:
        logger.error("Failed to fetch index history for %d: %s", index_id, e)
        raise

    result = sync_index_snapshots(index_id, snapshots_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors,
    }
