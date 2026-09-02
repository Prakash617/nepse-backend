"""Web Push Notification Service using VAPID and pywebpush.

Handles dispatching real browser/OS-level push notifications to registered user devices,
managing active push subscriptions, and automatically pruning expired/invalid subscriptions.
"""

import json
import logging
from typing import Any

from django.conf import settings
from pywebpush import WebPushException, webpush

from apps.notifications.models import PushSubscription

logger = logging.getLogger(__name__)


class PushNotificationService:
    """Centralized service for dispatching Web Push notifications."""

    @classmethod
    def send_push_to_user(
        cls,
        user: Any,
        title: str,
        body: str,
        icon: str = "/icon-192x192.png",
        badge: str = "/icon-192x192.png",
        data: dict[str, Any] | None = None,
        tag: str | None = None,
    ) -> dict[str, int]:
        """Dispatch a Web Push notification to all active devices/subscriptions of a user."""
        if not user:
            return {"sent": 0, "failed": 0, "deactivated": 0}

        active_subs = PushSubscription.objects.filter(user=user, is_active=True)
        if not active_subs.exists():
            logger.debug("No active push subscriptions found for user %s", getattr(user, "username", user))
            return {"sent": 0, "failed": 0, "deactivated": 0}

        if data is None:
            data = {}

        # Default URL navigation if symbol or path is present
        if "url" not in data:
            if "symbol" in data:
                data["url"] = f"/securities/{data['symbol']}"
            else:
                data["url"] = "/notifications"

        payload = {
            "title": title,
            "body": body,
            "icon": icon,
            "badge": badge,
            "data": data,
        }
        if tag:
            payload["tag"] = tag

        payload_json = json.dumps(payload)

        vapid_private = getattr(settings, "VAPID_PRIVATE_KEY", None)
        vapid_claims = {"sub": getattr(settings, "VAPID_ADMIN_EMAIL", "mailto:admin@nepse.local")}

        if not vapid_private:
            logger.error("VAPID_PRIVATE_KEY is not configured in Django settings.")
            return {"sent": 0, "failed": 0, "deactivated": 0}

        sent_count = 0
        failed_count = 0
        deactivated_count = 0

        for sub in active_subs:
            sub_info = {
                "endpoint": sub.endpoint,
                "keys": {
                    "p256dh": sub.p256dh,
                    "auth": sub.auth,
                },
            }

            try:
                webpush(
                    subscription_info=sub_info,
                    data=payload_json,
                    vapid_private_key=vapid_private,
                    vapid_claims=vapid_claims,
                    timeout=10,
                )
                sent_count += 1
                logger.info(
                    "Successfully delivered browser push notification to user %s (sub #%s)",
                    user.username,
                    sub.id,
                )
            except WebPushException as exc:
                failed_count += 1
                status_code = exc.response.status_code if exc.response is not None else None
                logger.warning(
                    "WebPushException sending to user %s (sub #%s): status=%s, error=%s",
                    user.username,
                    sub.id,
                    status_code,
                    exc,
                )

                # HTTP 404 (Not Found) or 410 (Gone) indicates the subscription is expired or cancelled
                if status_code in (404, 410):
                    logger.info("Deactivating expired/gone push subscription #%s for user %s", sub.id, user.username)
                    sub.is_active = False
                    sub.save(update_fields=["is_active", "updated_at"])
                    deactivated_count += 1

            except Exception as exc:
                failed_count += 1
                logger.exception(
                    "Unexpected error delivering browser push to user %s (sub #%s): %s",
                    user.username,
                    sub.id,
                    exc,
                )

        return {
            "sent": sent_count,
            "failed": failed_count,
            "deactivated": deactivated_count,
        }

    @classmethod
    def send_test_push(cls, user: Any) -> dict[str, int]:
        """Send a test push notification to verify browser push subscription and OS delivery."""
        return cls.send_push_to_user(
            user=user,
            title="NEPSE Notifications",
            body="Browser push notifications are active and working!",
            data={
                "type": "TEST_NOTIFICATION",
                "url": "/notifications",
            },
            tag="nepse-test-notification",
        )
