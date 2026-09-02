"""WebSocket consumers for real-time notifications."""

import json
import logging
from typing import Any

from channels.generic.websocket import AsyncWebsocketConsumer

logger = logging.getLogger(__name__)


class NotificationConsumer(AsyncWebsocketConsumer):
    """Handles real-time WebSocket connections for user notifications.

    Each authenticated user is joined to their private channel group `user_{user_id}`.
    Notifications are dispatched only to the matching user's group.
    """

    user_group_name: str | None = None

    async def connect(self) -> None:
        user = self.scope.get("user")

        if not user or not user.is_authenticated:
            logger.warning("Unauthenticated WebSocket connection attempt rejected.")
            await self.close(code=4401)
            return

        self.user_group_name = f"user_{user.id}"
        await self.channel_layer.group_add(self.user_group_name, self.channel_name)
        await self.accept()

        logger.info("WebSocket connected for user %s (group: %s)", user.username, self.user_group_name)

        # Send welcome ack message
        await self.send(
            text_data=json.dumps(
                {
                    "type": "connection_established",
                    "user_id": user.id,
                    "username": user.username,
                }
            )
        )

    async def disconnect(self, close_code: int) -> None:
        if self.user_group_name:
            await self.channel_layer.group_discard(self.user_group_name, self.channel_name)
            logger.info("WebSocket disconnected for group: %s (code: %s)", self.user_group_name, close_code)

    async def receive(self, text_data: str | None = None, bytes_data: bytes | None = None) -> None:
        """Handle incoming messages from client (e.g. heartbeat ping)."""
        if not text_data:
            return

        try:
            data = json.loads(text_data)
            msg_type = data.get("type")

            if msg_type == "ping":
                await self.send(text_data=json.dumps({"type": "pong"}))
        except Exception:
            logger.debug("Ignored unparseable WebSocket message: %s", text_data)

    async def notification_message(self, event: dict[str, Any]) -> None:
        """Handler for 'notification.message' events sent from channel layer."""
        notification_data = event.get("notification", {})
        await self.send(
            text_data=json.dumps(
                {
                    "type": "notification",
                    "data": notification_data,
                }
            )
        )
