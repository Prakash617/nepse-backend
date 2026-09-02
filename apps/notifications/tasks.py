"""Celery tasks for notification evaluation, delivery, Web Push, and Telegram."""

import logging
from typing import Any
from celery import shared_task
from django.contrib.auth import get_user_model

from apps.notifications.services import evaluate_alerts
from apps.notifications.webpush import PushNotificationService
from apps.notifications.telegram import send_telegram_alert

logger = logging.getLogger(__name__)
User = get_user_model()


@shared_task(name="apps.notifications.tasks.evaluate_alerts_task")
def evaluate_alerts_task() -> dict[str, int]:
    """Celery task to evaluate all active user alerts against latest market prices."""
    logger.info("Starting evaluate_alerts_task...")
    result = evaluate_alerts()
    logger.info("Finished evaluate_alerts_task: %s", result)
    return result


@shared_task(name="apps.notifications.tasks.send_push_notification_task")
def send_push_notification_task(
    user_id: int,
    title: str,
    body: str,
    icon: str = "/icon-192x192.png",
    badge: str = "/icon-192x192.png",
    data: dict[str, Any] | None = None,
    tag: str | None = None,
) -> dict[str, int]:
    """Celery task to dispatch Web Push notifications asynchronously without blocking caller."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("User %s not found for push notification task.", user_id)
        return {"sent": 0, "failed": 0, "deactivated": 0}

    return PushNotificationService.send_push_to_user(
        user=user,
        title=title,
        body=body,
        icon=icon,
        badge=badge,
        data=data,
        tag=tag,
    )


@shared_task(name="apps.notifications.tasks.send_telegram_notification_task")
def send_telegram_notification_task(
    user_id: int,
    title: str,
    body: str,
    data: dict[str, Any] | None = None,
) -> int:
    """Celery task to dispatch Telegram alert notifications asynchronously."""
    try:
        user = User.objects.get(pk=user_id)
    except User.DoesNotExist:
        logger.warning("User %s not found for Telegram notification task.", user_id)
        return 0

    return send_telegram_alert(
        user=user,
        title=title,
        body=body,
        data=data,
    )
