"""Centralized Alert Evaluation Engine.

Evaluates user-configured market alerts against live prices and snapshots,
handles state transitions (ACTIVE <-> TRIGGERED <-> PAUSED), executes crossing operators,
cooldown enforcement, and dispatches multi-channel notifications (In-App, WebSockets, Web Push).
"""

import logging
from datetime import timedelta
from decimal import Decimal
from typing import Any

from django.db import transaction
from django.utils import timezone

from apps.alerts.models import Alert, AlertHistory
from apps.notifications.models import Notification
from apps.notifications.services import NotificationService
from apps.notifications.webpush import PushNotificationService
from apps.prices.models import DailyPrice

logger = logging.getLogger(__name__)


class AlertEngine:
    """Evaluates alerts and manages alert lifecycle state transitions."""

    @classmethod
    def evaluate_condition(
        cls,
        alert: Alert,
        current_price: DailyPrice,
        previous_price: DailyPrice | None = None,
    ) -> tuple[bool, Decimal | None, str]:
        """Check if an alert condition is met.

        Returns:
            (is_triggered, triggered_value, reason_message)
        """
        ltp = getattr(current_price, "ltp", None)
        pct = getattr(current_price, "percentage_change", None)
        vol = getattr(current_price, "volume", None)
        pt_change = getattr(current_price, "point_change", None)

        symbol = alert.security.symbol
        thresh = alert.threshold

        if alert.condition == Alert.ConditionType.PRICE_ABOVE:
            if ltp is not None and ltp >= thresh:
                return True, ltp, f"{symbol} reached Rs. {ltp} (Target >= Rs. {thresh})"

        elif alert.condition == Alert.ConditionType.PRICE_BELOW:
            if ltp is not None and ltp <= thresh:
                return True, ltp, f"{symbol} dropped to Rs. {ltp} (Target <= Rs. {thresh})"

        elif alert.condition == Alert.ConditionType.PRICE_CROSS_ABOVE:
            prev_ltp = previous_price.ltp if previous_price else None
            if ltp is not None and ltp >= thresh:
                if prev_ltp is None or prev_ltp < thresh:
                    return True, ltp, f"{symbol} crossed above Rs. {thresh} (Current: Rs. {ltp})"

        elif alert.condition == Alert.ConditionType.PRICE_CROSS_BELOW:
            prev_ltp = previous_price.ltp if previous_price else None
            if ltp is not None and ltp <= thresh:
                if prev_ltp is None or prev_ltp > thresh:
                    return True, ltp, f"{symbol} crossed below Rs. {thresh} (Current: Rs. {ltp})"

        elif alert.condition == Alert.ConditionType.PERCENT_CHANGE_UP:
            if pct is not None and pct >= thresh:
                return True, pct, f"{symbol} surged +{pct}% (Target >= +{thresh}%)"

        elif alert.condition == Alert.ConditionType.PERCENT_CHANGE_DOWN:
            target_loss = -abs(thresh)
            if pct is not None and pct <= target_loss:
                return True, pct, f"{symbol} declined {pct}% (Target <= {target_loss}%)"

        elif alert.condition == Alert.ConditionType.VOLUME_ABOVE:
            if vol is not None and Decimal(vol) >= thresh:
                return True, Decimal(vol), f"{symbol} traded volume reached {vol:,} shares (Target >= {int(thresh):,})"

        elif alert.condition == Alert.ConditionType.PRICE_CHANGE_ABOVE:
            if pt_change is not None and pt_change >= thresh:
                return True, pt_change, f"{symbol} gained +Rs. {pt_change} (Target >= +Rs. {thresh})"

        elif alert.condition == Alert.ConditionType.PRICE_CHANGE_BELOW:
            target_drop = -abs(thresh)
            if pt_change is not None and pt_change <= target_drop:
                return True, pt_change, f"{symbol} lost Rs. {pt_change} (Target <= Rs. {target_drop})"

        return False, None, ""

    @classmethod
    def check_and_update_reset_state(cls, alert: Alert, current_price: DailyPrice) -> None:
        """Reset a TRIGGERED recurring alert to ACTIVE when price moves past the boundary."""
        if alert.status != Alert.AlertStatus.TRIGGERED or alert.frequency != Alert.FrequencyType.RECURRING:
            return

        ltp = current_price.ltp
        if ltp is None:
            return

        # Check boundary reset
        should_reset = False
        if alert.condition in (Alert.ConditionType.PRICE_ABOVE, Alert.ConditionType.PRICE_CROSS_ABOVE):
            if ltp < alert.threshold:
                should_reset = True
        elif alert.condition in (Alert.ConditionType.PRICE_BELOW, Alert.ConditionType.PRICE_CROSS_BELOW):
            if ltp > alert.threshold:
                should_reset = True

        if should_reset:
            alert.status = Alert.AlertStatus.ACTIVE
            alert.save(update_fields=["status", "updated_at"])
            logger.info("Alert #%s for %s reset to ACTIVE", alert.id, alert.security.symbol)

    @classmethod
    def evaluate_single_alert(
        cls,
        alert: Alert,
        current_price: DailyPrice,
        previous_price: DailyPrice | None = None,
    ) -> bool:
        """Evaluate and trigger a single alert if eligible."""
        if not alert.is_active or alert.status == Alert.AlertStatus.PAUSED:
            return False

        # Check reset condition first for recurring alerts
        cls.check_and_update_reset_state(alert, current_price)

        # Check cooldown
        now = timezone.now()
        if alert.last_triggered_at:
            if alert.status == Alert.AlertStatus.TRIGGERED and alert.frequency == Alert.FrequencyType.ONCE:
                return False

            if alert.cooldown_minutes > 0:
                elapsed = now - alert.last_triggered_at
                if elapsed < timedelta(minutes=alert.cooldown_minutes):
                    logger.debug("Alert #%s in cooldown (%s mins left)", alert.id, alert.cooldown_minutes)
                    return False
            elif alert.status == Alert.AlertStatus.TRIGGERED:
                # If no cooldown specified and already triggered today without reset, prevent spam
                if alert.last_triggered_at.date() == now.date():
                    return False

        triggered, triggered_val, message_text = cls.evaluate_condition(
            alert=alert,
            current_price=current_price,
            previous_price=previous_price,
        )

        if not triggered or triggered_val is None:
            return False

        # Execute trigger
        cls.trigger_alert(alert, current_price, triggered_val, message_text)
        return True

    @classmethod
    def trigger_alert(
        cls,
        alert: Alert,
        current_price: DailyPrice,
        triggered_val: Decimal,
        message: str,
    ) -> None:
        """Execute alert trigger: update state, record history, and dispatch notifications."""
        now = timezone.now()
        symbol = alert.security.symbol

        with transaction.atomic():
            alert.status = Alert.AlertStatus.TRIGGERED
            alert.last_triggered_at = now
            alert.triggered_price = current_price.ltp
            alert.trigger_count += 1

            if alert.frequency == Alert.FrequencyType.ONCE:
                alert.is_active = False

            alert.save(update_fields=["status", "last_triggered_at", "triggered_price", "trigger_count", "is_active", "updated_at"])

            # Determine notification type
            if "volume" in alert.condition:
                notif_type = Notification.NotificationType.VOLUME_ALERT
            elif "percent" in alert.condition:
                notif_type = Notification.NotificationType.PERCENTAGE_ALERT
            else:
                notif_type = Notification.NotificationType.PRICE_ALERT

            title = f"{symbol} Alert: {alert.get_condition_display()} {alert.threshold}"

            # 1. In-App Notification & WebSocket
            if alert.notify_in_app:
                NotificationService.create(
                    user=alert.user,
                    notification_type=notif_type,
                    title=title,
                    message=message,
                    security=alert.security,
                    alert=alert,
                    data={
                        "symbol": symbol,
                        "company_name": alert.security.company_name,
                        "price": str(current_price.ltp) if current_price.ltp else "",
                        "triggered_value": str(triggered_val),
                        "threshold": str(alert.threshold),
                        "condition": alert.condition,
                        "url": f"/securities/{symbol}",
                    },
                )

            # 2. Browser Web Push Notification
            push_sent = False
            if alert.notify_browser_push:
                try:
                    from apps.notifications.tasks import send_push_notification_task

                    send_push_notification_task.delay(
                        user_id=alert.user_id,
                        title=f"🔔 {title}",
                        body=message,
                        data={
                            "type": "PRICE_ALERT",
                            "symbol": symbol,
                            "url": f"/securities/{symbol}",
                            "alert_id": alert.id,
                        },
                        tag=f"nepse-{symbol}",
                    )
                    push_sent = True
                except Exception:
                    push_res = PushNotificationService.send_push_to_user(
                        user=alert.user,
                        title=f"🔔 {title}",
                        body=message,
                        data={
                            "type": "PRICE_ALERT",
                            "symbol": symbol,
                            "url": f"/securities/{symbol}",
                            "alert_id": alert.id,
                        },
                        tag=f"nepse-{symbol}",
                    )
                    push_sent = push_res.get("sent", 0) > 0

            # 3. Telegram Bot Notification
            if getattr(alert, "notify_telegram", True):
                try:
                    from apps.notifications.tasks import send_telegram_notification_task
                    send_telegram_notification_task.delay(
                        user_id=alert.user_id,
                        title=title,
                        body=message,
                        data={
                            "symbol": symbol,
                            "current_price": str(current_price.ltp) if current_price.ltp else str(triggered_val),
                            "threshold": str(alert.threshold),
                            "condition": alert.condition,
                        },
                    )
                except Exception:
                    from apps.notifications.telegram import send_telegram_alert
                    send_telegram_alert(
                        user=alert.user,
                        title=title,
                        body=message,
                        data={
                            "symbol": symbol,
                            "current_price": str(current_price.ltp) if current_price.ltp else str(triggered_val),
                            "threshold": str(alert.threshold),
                            "condition": alert.condition,
                        },
                    )

            # Record audit history
            AlertHistory.objects.create(
                alert=alert,
                user=alert.user,
                security=alert.security,
                triggered_value=triggered_val,
                threshold=alert.threshold,
                condition=alert.condition,
                message=message,
                push_sent=push_sent,
                in_app_sent=alert.notify_in_app,
            )

        logger.info("Successfully triggered alert #%s for user %s on %s", alert.id, alert.user.username, symbol)

    @classmethod
    def evaluate_securities(cls, security_ids: list[int] | None = None) -> dict[str, int]:
        """Evaluate alerts for specific securities or all active alerts."""
        qs = Alert.objects.filter(is_active=True).exclude(status=Alert.AlertStatus.PAUSED).select_related("security", "user")
        if security_ids:
            qs = qs.filter(security_id__in=security_ids)

        stats = {"evaluated": 0, "triggered": 0, "skipped": 0, "errors": 0}

        # Cache latest prices per security
        price_map: dict[int, tuple[DailyPrice | None, DailyPrice | None]] = {}

        for alert in qs:
            stats["evaluated"] += 1
            sec_id = alert.security_id

            if sec_id not in price_map:
                prices = list(DailyPrice.objects.filter(security_id=sec_id).order_by("-trading_date")[:2])
                curr = prices[0] if prices else None
                prev = prices[1] if len(prices) > 1 else None
                price_map[sec_id] = (curr, prev)

            current_price, previous_price = price_map[sec_id]
            if not current_price:
                stats["skipped"] += 1
                continue

            try:
                fired = cls.evaluate_single_alert(alert, current_price, previous_price)
                if fired:
                    stats["triggered"] += 1
                else:
                    stats["skipped"] += 1
            except Exception:
                stats["errors"] += 1
                logger.exception("Error evaluating alert #%s", alert.id)

        return stats
