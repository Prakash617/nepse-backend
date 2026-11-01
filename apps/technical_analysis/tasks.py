"""Celery tasks for automated technical analysis.

Thin wrappers around the service layer following AGENTS.md guidelines.
"""

from __future__ import annotations

import datetime
import logging
from typing import Any

from celery import shared_task

from apps.prices.models import DailyPrice
from apps.technical_analysis.models import AnalysisRun
from apps.technical_analysis.services.analysis_service import (
    execute_daily_analysis_pipeline,
)

logger = logging.getLogger(__name__)


@shared_task(name="technical_analysis.calculate_daily")
def calculate_daily_technical_analysis(
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Execute end-of-day technical analysis across all NEPSE securities and sectors.

    Args:
        as_of_date: Optional date string in YYYY-MM-DD format. Defaults to latest
                    completed daily trading date.
    """
    target_date: datetime.date | None = None
    if as_of_date:
        try:
            target_date = datetime.date.fromisoformat(as_of_date)
        except (ValueError, TypeError) as exc:
            logger.error("Invalid as_of_date provided: %s", as_of_date)
            return {"status": "error", "error": f"Invalid date: {exc}"}

    try:
        run_record = execute_daily_analysis_pipeline(
            as_of_date=target_date,
            run_type=AnalysisRun.RUN_TYPE_SCHEDULED if not as_of_date else AnalysisRun.RUN_TYPE_MANUAL,
        )
        return {
            "run_id": run_record.id,
            "status": run_record.status,
            "analysis_date": run_record.analysis_date.isoformat(),
            "securities_processed": run_record.securities_processed,
            "sectors_processed": run_record.sectors_processed,
            "errors": run_record.error_count,
        }
    except Exception as exc:
        logger.exception("Error executing calculate_daily_technical_analysis: %s", exc)
        return {"status": "failed", "error": str(exc)}


@shared_task(name="technical_analysis.backfill_historical")
def backfill_historical_technical_analysis(
    start_date: str,
    end_date: str,
) -> dict[str, Any]:
    """Administrative task to backfill historical technical analysis over a date range.

    Iterates through all distinct completed trading sessions between start_date and end_date.
    """
    try:
        s_date = datetime.date.fromisoformat(start_date)
        e_date = datetime.date.fromisoformat(end_date)
    except (ValueError, TypeError) as exc:
        logger.error("Invalid date range format: %s to %s", start_date, end_date)
        return {"status": "error", "error": f"Invalid date: {exc}"}

    trading_dates = list(
        DailyPrice.objects.filter(
            trading_date__gte=s_date,
            trading_date__lte=e_date,
        )
        .values_list("trading_date", flat=True)
        .distinct()
        .order_by("trading_date")
    )

    logger.info("Starting historical technical analysis backfill for %d sessions (%s to %s)", len(trading_dates), s_date, e_date)
    processed_count = 0
    failed_count = 0

    for t_date in trading_dates:
        try:
            execute_daily_analysis_pipeline(
                as_of_date=t_date,
                run_type=AnalysisRun.RUN_TYPE_BACKFILL,
            )
            processed_count += 1
        except Exception as exc:
            logger.error("Backfill failed on %s: %s", t_date, exc)
            failed_count += 1

    return {
        "status": "completed",
        "total_sessions": len(trading_dates),
        "processed_sessions": processed_count,
        "failed_sessions": failed_count,
    }


@shared_task(name="technical_analysis.generate_signals")
def generate_signals_task(
    as_of_date: str | None = None,
) -> dict[str, Any]:
    """Celery task to generate Short-Term and Swing trading signals for a session."""
    target_date: datetime.date | None = None
    if as_of_date:
        try:
            target_date = datetime.date.fromisoformat(as_of_date)
        except (ValueError, TypeError) as exc:
            return {"status": "error", "error": f"Invalid date: {exc}"}

    from apps.technical_analysis.signals import generate_daily_trading_signals

    try:
        return generate_daily_trading_signals(as_of_date=target_date)
    except Exception as exc:
        logger.exception("generate_signals_task failed: %s", exc)
        return {"status": "failed", "error": str(exc)}


@shared_task(name="technical_analysis.update_signal_lifecycle")
def update_signal_lifecycle_task(
    current_date: str | None = None,
) -> dict[str, Any]:
    """Celery task to advance active trade tracking and fill pending orders."""
    target_date: datetime.date | None = None
    if current_date:
        try:
            target_date = datetime.date.fromisoformat(current_date)
        except (ValueError, TypeError) as exc:
            return {"status": "error", "error": f"Invalid date: {exc}"}

    from apps.technical_analysis.signals import update_trading_signals_lifecycle

    try:
        return update_trading_signals_lifecycle(current_date=target_date)
    except Exception as exc:
        logger.exception("update_signal_lifecycle_task failed: %s", exc)
        return {"status": "failed", "error": str(exc)}

