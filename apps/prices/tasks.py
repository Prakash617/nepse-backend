"""Price synchronization Celery tasks."""

import logging

from celery import shared_task

from apps.prices.services import (
    sync_daily_prices,
    sync_historical_prices,
    sync_intraday_prices,
)
from integrations.nepse import NepseClient, NepseError

logger = logging.getLogger(__name__)


@shared_task(name="prices.sync_daily_prices")
def sync_daily_prices_task(business_date: str | None = None) -> dict:
    """Synchronize daily prices from NEPSE upstream.

    Thin wrapper around the service layer.

    Args:
        business_date: Optional date in YYYY-MM-DD format.
    """
    try:
        client = NepseClient()
        prices_data = client.get_today_prices(business_date=business_date)
    except NepseError as e:
        logger.error("Failed to fetch daily prices: %s", e)
        raise

    result = sync_daily_prices(prices_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors[:10],  # Limit error output
    }


@shared_task(name="prices.sync_intraday_prices")
def sync_intraday_prices_task() -> dict:
    """Synchronize intraday/live prices from NEPSE upstream.

    Thin wrapper around the service layer.
    """
    try:
        client = NepseClient()
        trades_data = client.get_live_trades()
    except NepseError as e:
        logger.error("Failed to fetch intraday prices: %s", e)
        raise

    result = sync_intraday_prices(trades_data)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors[:10],
    }


@shared_task(name="prices.sync_historical_prices")
def sync_historical_prices_task(
    symbols: list[str],
    start_date: str,
    end_date: str,
) -> dict:
    """Synchronize historical daily prices for a list of securities over a date range.

    Thin wrapper around the service layer. Historically large backfills
    should be manually initiated, not scheduled automatically.

    Args:
        symbols: List of ticker symbols to sync.
        start_date: Start date in YYYY-MM-DD format.
        end_date: End date in YYYY-MM-DD format.
    """
    from datetime import date as date_cls

    try:
        sd = date_cls.fromisoformat(start_date)
        ed = date_cls.fromisoformat(end_date)
    except ValueError as e:
        raise ValueError(f"Invalid date format: {e}") from e

    result = sync_historical_prices(symbols=symbols, start_date=sd, end_date=ed)
    return {
        "created": result.created,
        "updated": result.updated,
        "skipped": result.skipped,
        "failed": result.failed,
        "errors": result.errors[:20],
    }
