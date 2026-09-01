"""Alert evaluation service.

Checks active alerts against the latest price data and creates notifications
when conditions are met. Each alert is evaluated independently.
"""

import logging
from datetime import date

from django.db import transaction
from django.utils import timezone

from apps.alerts.models import Alert
from apps.notifications.models import Notification
from apps.prices.models import DailyPrice

logger = logging.getLogger(__name__)


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
    """Evaluate whether an alert condition is met.

    Returns True if the condition triggers.
    """
    ltp = latest_price.ltp
    if ltp is None:
        return False

    if alert.condition == Alert.ConditionType.PRICE_ABOVE:
        return ltp > alert.threshold

    if alert.condition == Alert.ConditionType.PRICE_BELOW:
        return ltp < alert.threshold

    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_UP:
        pct = latest_price.percentage_change
        if pct is None:
            return False
        return pct > alert.threshold

    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_DOWN:
        pct = latest_price.percentage_change
        if pct is None:
            return False
        return pct < -alert.threshold

    return False


def _build_notification_title(alert: Alert, latest_price: DailyPrice) -> str:
    """Build a human-readable notification title."""
    symbol = alert.security.symbol
    if alert.condition == Alert.ConditionType.PRICE_ABOVE:
        return f"{symbol} is above {alert.threshold}"
    if alert.condition == Alert.ConditionType.PRICE_BELOW:
        return f"{symbol} is below {alert.threshold}"
    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_UP:
        return f"{symbol} changed up by more than {alert.threshold}%"
    if alert.condition == Alert.ConditionType.PERCENT_CHANGE_DOWN:
        return f"{symbol} changed down by more than {alert.threshold}%"
    return f"Alert triggered for {symbol}"


def _build_notification_message(alert: Alert, latest_price: DailyPrice) -> str:
    """Build a human-readable notification message."""
    ltp = latest_price.ltp
    date_str = latest_price.trading_date.isoformat()
    pct = latest_price.percentage_change
    pct_str = f"{pct}%" if pct is not None else "N/A"
    return (
        f"{alert.security.symbol} (LTP: {ltp}) on {date_str}. "
        f"Condition: {alert.get_condition_display()} {alert.threshold}. "
        f"Change: {pct_str}."
    )


def evaluate_alerts() -> dict[str, int]:
    """Evaluate all active alerts against latest price data.

    Creates notifications for triggered alerts and updates last_triggered_at.
    Idempotent: re-running immediately produces no duplicate notifications
    (because triggered alerts get last_triggered_at updated to now).

    Returns:
        Dict with counts of evaluated, triggered, and skipped alerts.
    """
    now = timezone.now()
    today = date.today()

    active_alerts = Alert.objects.filter(is_active=True).select_related("security")

    result = {"evaluated": 0, "triggered": 0, "skipped": 0, "errors": 0}

    for alert in active_alerts:
        result["evaluated"] += 1

        try:
            latest_price = _get_latest_price(alert.security_id)
            if latest_price is None:
                result["skipped"] += 1
                continue

            # Skip if already triggered today
            if (
                alert.last_triggered_at is not None
                and alert.last_triggered_at.date() == today
            ):
                result["skipped"] += 1
                continue

            if _evaluate_condition(alert, latest_price):
                with transaction.atomic():
                    Notification.objects.create(
                        user=alert.user,
                        alert=alert,
                        title=_build_notification_title(alert, latest_price),
                        message=_build_notification_message(alert, latest_price),
                    )
                    alert.last_triggered_at = now
                    alert.save(update_fields=["last_triggered_at"])
                result["triggered"] += 1
                logger.info(
                    "Alert triggered: %s %s %s",
                    alert.user.username,
                    alert.security.symbol,
                    alert.condition,
                )
            else:
                result["skipped"] += 1

        except Exception:
            result["errors"] += 1
            logger.exception("Error evaluating alert %s", alert.pk)

    logger.info(
        "Alert evaluation complete: evaluated=%d, triggered=%d, skipped=%d, errors=%d",
        result["evaluated"],
        result["triggered"],
        result["skipped"],
        result["errors"],
    )
    return result
