"""Periodic Celery tasks for notifications.

Scheduled via django-celery-beat. Evaluates alerts and creates notifications.
"""

import logging

from celery import shared_task

logger = logging.getLogger(__name__)


@shared_task(bind=True, max_retries=2, default_retry_delay=30)
def evaluate_alerts_task(self) -> str:
    """Evaluate all active alerts and create notifications for triggered ones.

    Scheduled to run every 5 minutes during market hours (Sun–Fri, 10:30 AM – 3:00 PM NPT).
    """
    from apps.notifications.services import evaluate_alerts

    try:
        result = evaluate_alerts()
        logger.info("Alert evaluation task complete: %s", result)
        return f"Alerts evaluated: {result}"
    except Exception as exc:
        logger.error("Alert evaluation task failed: %s", exc)
        raise self.retry(exc=exc) from exc
