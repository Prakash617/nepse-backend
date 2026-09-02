"""Notification and Alert Evaluation Service.

Centralized service for creating, managing, and broadcasting user notifications,
as well as evaluating market alerts against live price data.
"""

import logging
from datetime import date
from typing import Any

from asgiref.sync import async_to_sync
from channels.layers import get_channel_layer
from django.contrib.auth import get_user_model
from django.db import transaction
from django.utils import timezone

from apps.alerts.models import Alert
from apps.notifications.models import Notification
from apps.prices.models import DailyPrice

User = get_user_model()
logger = logging.getLogger(__name__)


class NotificationService:
    """Centralized service for managing and dispatching notifications."""

    @staticmethod
    def create(
        user: Any,
        notification_type: str = Notification.NotificationType.SYSTEM,
        title: str = "",
        message: str = "",
        security: Any = None,
        alert: Any = None,
        data: dict[str, Any] | None = None,
    ) -> Notification:
        """Create a notification in the database and broadcast it via WebSockets in real time."""
        if data is None:
            data = {}

        # If security is passed, attach symbol/name to metadata if not present
        if security is not None:
            if "symbol" not in data:
                data["symbol"] = getattr(security, "symbol", "")
            if "company_name" not in data:
                data["company_name"] = getattr(security, "company_name", "")

        with transaction.atomic():
            notification = Notification.objects.create(
                user=user,
                notification_type=notification_type,
                title=title,
                message=message,
                security=security,
                alert=alert,
                data=data,
            )

        # Broadcast via Channels to user's private group
        try:
            channel_layer = get_channel_layer()
            if channel_layer:
                from apps.notifications.serializers import NotificationSerializer

                payload = NotificationSerializer(notification).data
                async_to_sync(channel_layer.group_send)(
                    f"user_{user.id}",
                    {
                        "type": "notification.message",
                        "notification": payload,
                    },
                )
                logger.debug("Dispatched notification %s to group user_%s", notification.id, user.id)
        except Exception as e:
            logger.warning("Failed to broadcast notification %s over WebSocket: %s", notification.id, e)

        # Dispatch real browser push notification
        try:
            from apps.notifications.tasks import send_push_notification_task

            send_push_notification_task.delay(
                user_id=user.id,
                title=title,
                body=message,
                data=data,
            )
        except Exception:
            # Fallback to synchronous push if Celery broker is unavailable or in eager mode
            try:
                from apps.notifications.webpush import PushNotificationService

                PushNotificationService.send_push_to_user(
                    user=user,
                    title=title,
                    body=message,
                    data=data,
                )
            except Exception as e:
                logger.warning("Failed to dispatch push notification for user %s: %s", user.id, e)

        return notification

    @staticmethod
    def mark_as_read(user: Any, notification_id: int) -> Notification | None:
        """Mark a specific notification as read for a user."""
        try:
            notification = Notification.objects.get(user=user, id=notification_id)
            if not notification.is_read:
                notification.is_read = True
                notification.save(update_fields=["is_read"])
            return notification
        except Notification.DoesNotExist:
            return None

    @staticmethod
    def mark_all_as_read(user: Any) -> int:
        """Mark all unread notifications as read for a user."""
        return Notification.objects.filter(user=user, is_read=False).update(is_read=True)

    @staticmethod
    def delete(user: Any, notification_id: int) -> bool:
        """Delete a notification belonging to a user."""
        deleted_count, _ = Notification.objects.filter(user=user, id=notification_id).delete()
        return deleted_count > 0

    @staticmethod
    def get_unread_count(user: Any) -> int:
        """Get the count of unread notifications for a user."""
        if not user or not user.is_authenticated:
            return 0
        return Notification.objects.filter(user=user, is_read=False).count()


def _get_latest_price(security_id: int) -> DailyPrice | None:
    """Get the most recent daily price for a security."""
    return (
        DailyPrice.objects.filter(security_id=security_id)
        .order_by("-trading_date")
        .first()
    )


def _evaluate_condition(
    alert: Alert,
    latest_price: DailyPrice,
) -> bool:
    """Evaluate whether an alert condition is met."""
    ltp = latest_price.ltp
    if ltp is None:
        return False

    if alert.condition == Alert.ConditionType.PRICE_ABOVE:
        return ltp >= alert.threshold

    if alert.condition == Alert.ConditionType.PRICE_BELOW:
        return ltp <= alert.threshold

    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_UP:
        pct = latest_price.percentage_change
        if pct is None:
            return False
        return pct >= alert.threshold

    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_DOWN:
        pct = latest_price.percentage_change
        if pct is None:
            return False
        return pct <= -alert.threshold

    return False


def _build_notification_title(alert: Alert, latest_price: DailyPrice) -> str:
    """Build a human-readable notification title."""
    symbol = alert.security.symbol
    if alert.condition == Alert.ConditionType.PRICE_ABOVE:
        return f"Price Alert: {symbol} reached {alert.threshold}"
    if alert.condition == Alert.ConditionType.PRICE_BELOW:
        return f"Price Alert: {symbol} fell to {alert.threshold}"
    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_UP:
        return f"Gain Alert: {symbol} is up +{alert.threshold}%"
    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_DOWN:
        return f"Drop Alert: {symbol} is down -{alert.threshold}%"
    return f"Price Alert: {symbol}"


def _build_notification_message(alert: Alert, latest_price: DailyPrice) -> str:
    """Build a human-readable notification message."""
    ltp = latest_price.ltp
    date_str = latest_price.trading_date.isoformat()
    pct = latest_price.percentage_change
    pct_str = f"{pct}%" if pct is not None else "N/A"
    return (
        f"{alert.security.symbol} current LTP is Rs. {ltp} ({pct_str}) on {date_str}. "
        f"Triggered condition: {alert.get_condition_display()} {alert.threshold}."
    )


def evaluate_alerts(security_ids: list[int] | None = None) -> dict[str, int]:
    """Evaluate alerts against latest market data using AlertEngine."""
    from apps.alerts.engine import AlertEngine

    return AlertEngine.evaluate_securities(security_ids=security_ids)
